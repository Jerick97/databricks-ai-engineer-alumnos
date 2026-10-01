"""Bounded Qwen3 embedding adapter with SDK authentication, no cloud creation.

Databricks API: input strings, optional query instruction, dimensions 32..1024
(power of two). Documents have no instruction. Public Qwen tokenization is
pinned locally; remote weights/revision and server serialization remain mutable.
Local query counts use the author's Instruct/Query format, not a claim of exact
server usage. A caller-selected safety margin is reserved per input.
"""
import hashlib
from copy import deepcopy
import re
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit

from . import ModelManifest, TokenCounter, validate_embeddings

ENDPOINT = 'databricks-qwen3-embedding-0-6b'
REPO_ID = 'Qwen/Qwen3-Embedding-0.6B'
_SAFE_ERRORS = frozenset({'PERMISSION_DENIED','UNAUTHENTICATED','NOT_FOUND',
    'RESOURCE_DOES_NOT_EXIST','INVALID_PARAMETER_VALUE','BAD_REQUEST',
    'TEMPORARILY_UNAVAILABLE','REQUEST_LIMIT_EXCEEDED','INTERNAL_ERROR',
    'ACCOUNT_SUSPENDED','CUSTOMER_UNAUTHORIZED','UNCLASSIFIED_ERROR'})


class EmbeddingServiceError(RuntimeError):
    def __init__(self, code='UNCLASSIFIED_ERROR', http_status=None):
        if not isinstance(code, str) or code not in _SAFE_ERRORS:
            code = f'HTTP_{http_status}' if type(http_status) is int and 100 <= http_status <= 599 else 'UNCLASSIFIED_ERROR'
        self.error_code = code
        self.http_status = http_status
        super().__init__(code)


class PinnedQwenTokenizer:
    repo_id = REPO_ID

    def __init__(self, path, *, revision, sha256):
        if not isinstance(revision, str) or not re.fullmatch(r'[a-f0-9]{40}', revision):
            raise ValueError('unpinned_tokenizer_revision')
        raw = Path(path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != sha256:
            raise ValueError('tokenizer_hash_mismatch')
        from tokenizers import Tokenizer
        self._tokenizer = Tokenizer.from_buffer(raw)
        self._tokenizer.no_truncation()
        self._tokenizer.no_padding()
        self.revision, self.sha256 = revision, sha256

    def count(self, text):
        return len(self._tokenizer.encode(text, add_special_tokens=True).ids)


class SingleShotTransport:
    """SDK credentials with a fresh Requests session: no retries or redirects.

    The SDK's ordinary API client can retry POSTs. This narrowly scoped
    transport instead uses config.authenticate(), its standard credential hook.
    It never exposes response bodies/headers on service failures.
    """
    def __init__(self, workspace_client):
        self._config = workspace_client.config
        host = self._config.host.rstrip('/')
        parsed = urlsplit(host)
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.path
                or parsed.query or parsed.fragment or parsed.username or parsed.password):
            raise ValueError('invalid_workspace_host')
        self._url = host + '/serving-endpoints/' + ENDPOINT + '/invocations'

    def __call__(self, body):
        import requests
        session = requests.Session()  # default HTTPAdapter max_retries=0
        try:
            response = session.post(self._url, json=body,
                headers={**self._config.authenticate(), 'Content-Type':'application/json'},
                timeout=45, allow_redirects=False)
            if response.status_code != 200:
                code = None
                try:
                    candidate = response.json()
                    if isinstance(candidate, dict):
                        code = candidate.get('error_code')
                except Exception:
                    pass
                raise EmbeddingServiceError(code, response.status_code)
            return response.json()
        except EmbeddingServiceError:
            raise
        except Exception:
            raise EmbeddingServiceError() from None
        finally:
            session.close()


class DatabricksEmbeddingAdapter:
    """Process-local call/token quotas, reserved before network, including errors.

    Quotas are execution limits, not price estimates or a monetary authorization.
    The caller must use a single adapter per authorized run and persist its run
    record; constructing another instance starts new counters.
    """
    def __init__(self, manifest: ModelManifest, tokenizer, *, transport,
                 max_calls: int, max_tokens: int, per_input_limit: int = 32768,
                 safety_tokens_per_input: int = 8):
        data = manifest.bundle
        dimension = data['dimension']
        if type(dimension) is not int or not 32 <= dimension <= 1024 or dimension & (dimension-1):
            raise ValueError('invalid_dimension')
        if data['embedding_model'] != ENDPOINT:
            raise ValueError('unsupported_embedding_model')
        params = data['parameters']
        expected_model = params.get('expected_response_model')
        if not isinstance(expected_model, str) or not re.fullmatch(r'[A-Za-z0-9_./:-]{1,200}',expected_model):
            raise ValueError('missing_expected_response_model')
        self._expected_response_model = expected_model
        if (data['tokenizer'] != tokenizer.repo_id or
                params['tokenizer_revision'] != tokenizer.revision or
                params.get('tokenizer_sha256') != tokenizer.sha256):
            raise ValueError('tokenizer_identity_mismatch')
        if params['document_prefix'] != '' or params['query_prefix'] != 'Instruct: ':
            raise ValueError('unsupported_embedding_prefix')
        instruction = params.get('query_instruction')
        if not isinstance(instruction, str) or not instruction.strip():
            raise ValueError('missing_query_instruction')
        if any(type(n) is not int or n <= 0 for n in (max_calls,max_tokens,per_input_limit)):
            raise ValueError('invalid_quota')
        if per_input_limit > 32768 or type(safety_tokens_per_input) is not int or safety_tokens_per_input < 0:
            raise ValueError('invalid_token_limit')
        self.manifest, self.tokenizer = manifest, tokenizer
        self._transport = transport
        self.max_calls, self.max_tokens = max_calls, max_tokens
        self.per_input_limit, self.safety_tokens_per_input = per_input_limit, safety_tokens_per_input
        self.calls_attempted = self.tokens_reserved = 0
        self._instruction, self._dimension = instruction, dimension
        self._lock = threading.Lock()
        self._last_attempt = {}

    @property
    def identity(self):
        return self.manifest.bundle_hash

    @property
    def dimension(self):
        return self._dimension

    @property
    def last_attempt(self):
        """Detached allowlisted diagnostics, including failures; never raw bodies."""
        return deepcopy(self._last_attempt)

    def _query_input(self, text):
        return f'Instruct: {self._instruction}\nQuery:{text}'

    @property
    def token_counter(self):
        """Document parts concatenate exactly; includes tokenizer special tokens."""
        return TokenCounter(self.tokenizer.repo_id, self.tokenizer.revision,
            self.identity, lambda parts: self.tokenizer.count(''.join(parts)))

    @property
    def query_token_counter(self):
        """Includes task instruction plus Instruct/Query framing and specials."""
        return TokenCounter(self.tokenizer.repo_id, self.tokenizer.revision,
            self.identity, lambda parts: self.tokenizer.count(self._query_input(''.join(parts))))

    def embed_documents(self, inputs):
        if (not isinstance(inputs, list) or not inputs or
                any(not isinstance(parts, tuple) or not parts or
                    any(not isinstance(p, str) for p in parts) for parts in inputs)):
            raise ValueError('invalid_document_parts')
        result = self.embed([''.join(parts) for parts in inputs], role='document')
        return [list(vector) for vector in result['embeddings']]

    def embed_query(self, query):
        return list(self.embed([query], role='query')['embeddings'][0])

    def preflight(self, texts, *, role='document'):
        if role not in ('document','query'):
            raise ValueError('invalid_embedding_role')
        if (not isinstance(texts,(list,tuple)) or not texts or
                any(not isinstance(t,str) or not t.strip() for t in texts)):
            raise ValueError('invalid_embedding_inputs')
        counts = []
        for text in texts:
            rendered = text if role == 'document' else self._query_input(text)
            count = self.tokenizer.count(rendered)
            if type(count) is not int or count < 0:
                raise ValueError('invalid_token_count')
            if count + self.safety_tokens_per_input > self.per_input_limit:
                raise ValueError('input_token_limit_exceeded')
            counts.append(count)
        return {'role':role, 'per_input_tokens':counts, 'local_input_tokens':sum(counts),
                'reserved_tokens':sum(counts)+len(texts)*self.safety_tokens_per_input,
                'safety_tokens_per_input':self.safety_tokens_per_input,
                'counting_mode':'pinned_public_tokenizer_with_query_template_and_safety_reserve'}

    def embed(self, texts, *, role='document'):
        preflight = self.preflight(texts,role=role)
        with self._lock:
            if self.calls_attempted >= self.max_calls:
                raise ValueError('call_quota_exceeded')
            if self.tokens_reserved + preflight['reserved_tokens'] > self.max_tokens:
                raise ValueError('token_quota_exceeded')
            self.calls_attempted += 1
            self.tokens_reserved += preflight['reserved_tokens']
        body = {'input':list(texts),'dimensions':self._dimension}
        if role == 'query':
            body['instruction'] = self._instruction
        self._last_attempt = {'stage':'transport', 'calls_attempted':self.calls_attempted,
                              'reserved_tokens':preflight['reserved_tokens'],
                              'endpoint':ENDPOINT,
                              'expected_response_model':self._expected_response_model}
        start = time.perf_counter()
        try:
            response = self._transport(body)
        except EmbeddingServiceError as exc:
            self._last_attempt.update(error_code=exc.error_code,http_status=exc.http_status)
            raise
        except Exception as exc:
            code = getattr(exc,'error_code',None)
            clean = EmbeddingServiceError(code)
            self._last_attempt['error_code'] = clean.error_code
            raise clean from None
        finally:
            self._last_attempt['latency_seconds'] = time.perf_counter()-start
        elapsed = self._last_attempt['latency_seconds']
        self._last_attempt['stage'] = 'response_envelope'
        if not isinstance(response,dict):
            raise ValueError('invalid_embedding_response')
        model = response.get('model')
        rows = response.get('data')
        raw_usage = response.get('usage')
        raw_usage = raw_usage if isinstance(raw_usage,dict) else {}
        usage = {key:raw_usage.get(key) if type(raw_usage.get(key)) is int and raw_usage[key]>=0 else None
                 for key in ('prompt_tokens','total_tokens')}
        self._last_attempt.update(
            response_model=model if isinstance(model,str) and re.fullmatch(r'[A-Za-z0-9_./:-]{1,200}',model) else None,
            response_count=len(rows) if isinstance(rows,list) else None, usage=usage,
            response_dimensions=[len(row['embedding']) if isinstance(row,dict) and isinstance(row.get('embedding'),list) else None for row in rows[:len(texts)]] if isinstance(rows,list) else None,
            response_indices=[row.get('index') if isinstance(row,dict) and type(row.get('index')) is int else None for row in rows[:len(texts)]] if isinstance(rows,list) else None,
            stage='response_model')
        # Routing endpoint/config names are not the model ID returned by inference.
        # Compare only the exact response identity pinned in this immutable bundle.
        if model != self._expected_response_model:
            raise ValueError('embedding_model_mismatch')
        self._last_attempt['stage'] = 'response_count'
        if not isinstance(rows,list) or len(rows) != len(texts):
            raise ValueError('embedding_count_mismatch')
        self._last_attempt['stage'] = 'response_indices'
        indices = [row.get('index') if isinstance(row,dict) else None for row in rows]
        if any(type(i) is not int for i in indices) or sorted(indices) != list(range(len(texts))):
            raise ValueError('embedding_index_mismatch')
        ordered = sorted(rows,key=lambda row:row['index'])
        self._last_attempt['stage'] = 'response_vectors'
        vectors = validate_embeddings([row.get('embedding') for row in ordered],
            expected_count=len(texts),dimension=self._dimension,
            expected_identity=self.manifest.bundle_hash,actual_identity=self.manifest.bundle_hash)
        self._last_attempt['stage'] = 'validated'
        return {**preflight, 'embeddings':vectors,'usage':usage,'model':model,
                'endpoint':ENDPOINT,'expected_response_model':self._expected_response_model,
                'bundle_hash':self.manifest.bundle_hash,'latency_seconds':elapsed,'cost':None,
                'server_usage_exceeds_reserve':usage['prompt_tokens'] is not None and
                    usage['prompt_tokens'] > preflight['reserved_tokens'],
                'identity_evidence':'endpoint_config_and_response_name_not_remote_weight_hash'}
