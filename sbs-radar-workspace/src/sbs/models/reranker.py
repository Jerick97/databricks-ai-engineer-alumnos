"""CPU cross-encoder; explicit contiguous character windows, maximum raw logit.

Window offsets are relative to the unchanged citation.text. Every character is
covered once (including whitespace); window boundaries may split words/ideas.
This is a scoring adaptation, not replacement citation segmentation. Scores are
uncalibrated logits and max aggregation can favor longer spans. Quality requires
frozen SBS qrels. Injected sessions/tokenizers are test doubles unless constructed
with from_manifest, which verifies all artifacts before opening local weights.
"""
import hashlib
import json
import math
import re
import threading
import time
from pathlib import Path

REPO_ID = 'cross-encoder/mmarco-mMiniLMv2-L12-H384-v1'
WEIGHTS = 'onnx/model_qint8_arm64.onnx'



def execution_identity(manifest, *, system, machine, ort_version):
    """Resolve explicit candidate target; record legacy selection without relabeling it."""
    architecture = {'AMD64':'x86_64', 'amd64':'x86_64', 'aarch64':'arm64'}.get(machine, machine)
    spec = manifest.get('execution')
    weights, selection = WEIGHTS, 'legacy_default'
    if spec is not None:
        if (not isinstance(spec, dict) or set(spec) != {'weights','engine','provider','system','architecture'}
            or spec['engine'] != 'onnxruntime' or spec['provider'] != 'CPUExecutionProvider'
            or spec['weights'] not in {WEIGHTS, 'onnx/model_quint8_avx2.onnx'}):
            raise ValueError('unsupported_execution_identity')
        if spec['system'] != system or spec['architecture'] != architecture:
            raise ValueError('execution_target_mismatch')
        weights, selection = spec['weights'], 'explicit'
    return {'engine':'onnxruntime', 'provider':'CPUExecutionProvider',
            'system':system, 'architecture':architecture, 'onnxruntime_version':ort_version,
            'weights':weights, 'selection':selection}

def verify_manifest(manifest):
    if not re.fullmatch(r'[0-9a-f]{40}', manifest.get('revision', '')):
        raise ValueError('unpinned_model_revision')
    for artifact in manifest['files'].values():
        if hashlib.sha256(Path(artifact['path']).read_bytes()).hexdigest() != artifact['sha256']:
            raise ValueError('artifact_hash_mismatch')


class LocalOnnxReranker:
    def __init__(self, tokenizer, session, *, max_tokens=512):
        if type(max_tokens) is not int or max_tokens < 4:
            raise ValueError('invalid_pair_limit')
        self.tokenizer, self.session, self.max_tokens = tokenizer, session, max_tokens
        self.tokenizer.no_truncation()
        self.tokenizer.no_padding()
        self.last_trace = []
        self._lock = threading.Lock()

    @classmethod
    def from_manifest(cls, manifest_path, *, cpu_threads=2):
        if type(cpu_threads) is not int or not 1 <= cpu_threads <= 4:
            raise ValueError('invalid_cpu_threads')
        from copy import deepcopy
        manifest = deepcopy(manifest_path) if isinstance(manifest_path,dict) else json.loads(Path(manifest_path).read_text())
        verify_manifest(manifest)
        if manifest.get('repo_id') != REPO_ID:
            raise ValueError('unsupported_model_identity')
        files = manifest['files']
        config = json.loads(Path(files['config.json']['path']).read_text())
        tokenizer_config = json.loads(Path(files['tokenizer_config.json']['path']).read_text())
        limit = min(config['max_position_embeddings'], tokenizer_config['model_max_length'])
        if limit != 512 or config.get('num_labels', len(config.get('id2label', {}))) != 1:
            raise ValueError('unsupported_model_configuration')
        from tokenizers import Tokenizer
        import onnxruntime as ort
        import platform
        backend = execution_identity(manifest, system=platform.system(), machine=platform.machine(), ort_version=ort.__version__)
        if backend['weights'] not in files:
            raise ValueError('missing_selected_weights')
        options = ort.SessionOptions()
        options.intra_op_num_threads = cpu_threads
        options.inter_op_num_threads = 1
        session = ort.InferenceSession(files[backend['weights']]['path'], sess_options=options,
                                       providers=['CPUExecutionProvider'])
        instance = cls(Tokenizer.from_file(files['tokenizer.json']['path']), session, max_tokens=limit)
        instance.identity = manifest
        instance.execution_identity = backend | {'weights_sha256':files[backend['weights']]['sha256'], 'cpu_threads':cpu_threads}
        return instance

    def _windows(self, query, text):
        # Budget includes the tokenizer's actual pair postprocessor specials.
        if len(self.tokenizer.encode(query, '', add_special_tokens=True).ids) >= self.max_tokens:
            raise ValueError('query_token_budget_exceeded')
        windows, start = [], 0
        while start < len(text) or not windows:
            # Find a fitting contiguous character prefix; verify actual pair,
            # rather than assuming token counts add or decoding token slices.
            end = len(text)
            encoding = self.tokenizer.encode(query, text[start:end], add_special_tokens=True)
            if len(encoding.ids) > self.max_tokens:
                lo, hi = start + 1, end
                fit = None
                while lo <= hi:
                    mid = (lo + hi)//2
                    candidate = self.tokenizer.encode(query, text[start:mid], add_special_tokens=True)
                    if len(candidate.ids) <= self.max_tokens:
                        fit = (mid, candidate)
                        lo = mid + 1
                    else:
                        hi = mid - 1
                if fit is None:
                    raise ValueError('passage_character_exceeds_remaining_budget')
                end, encoding = fit
            windows.append((start, end, encoding))
            start = end
            if start == len(text):
                break
        return windows

    def __call__(self, query, authorized_rows):
        import numpy as np
        if not isinstance(query, str) or not query.strip():
            raise ValueError('invalid_query')
        with self._lock:
            self.last_trace = []
            plans = []
            for row in authorized_rows:
                text = row.get('citation', {}).get('text')
                if not isinstance(text, str) or not text.strip():
                    raise ValueError('invalid_citation_text')
                plans.append(self._windows(query, text))
            scores, traces = [], []
            for windows in plans:
                trace = {'aggregation':'max_raw_logit', 'windows':[]}
                for start, end, encoding in windows:
                    values = {'input_ids':encoding.ids, 'attention_mask':encoding.attention_mask,
                              'token_type_ids':encoding.type_ids}
                    feeds = {i.name:np.asarray([values[i.name]], dtype=np.int64)
                             for i in self.session.get_inputs()}
                    began = time.perf_counter()
                    output = np.asarray(self.session.run(None, feeds)[0])
                    elapsed = time.perf_counter() - began
                    if output.shape != (1, 1) or not math.isfinite(float(output[0, 0])):
                        raise ValueError('invalid_reranker_response')
                    trace['windows'].append({'start':start, 'end':end, 'pair_tokens':len(encoding.ids),
                        'score':float(output[0, 0]), 'inference_seconds':elapsed})
                score = max(w['score'] for w in trace['windows'])
                trace['score'] = score
                traces.append(trace)
                scores.append(score)
            self.last_trace = traces
            return scores
