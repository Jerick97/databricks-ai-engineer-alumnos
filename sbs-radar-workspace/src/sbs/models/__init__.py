"""SK05 configuration/preflight primitives; no inference or cloud mutations.

Injected counters must implement the actual model's complete input serialization,
including prefixes, context, pair separators, roles and special tokens. A fixture
counter verifies budget logic only, never compatibility with a real tokenizer.
"""
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Callable

from sbs.contracts import validate_contract

_IDENTITY_PARAMETERS = ('corpus_hash', 'extractor_version', 'tokenizer_revision',
                        'document_prefix', 'query_prefix', 'normalization',
                        'strategy_id', 'strategy_version')


@dataclass(frozen=True)
class ModelManifest:
    """Detached canonical configuration, not a hash of remote model weights.

    save() refuses to overwrite an existing artifact. Storage authorization and
    durable write-once retention remain responsibilities of the backend.
    """
    canonical_json: str

    def __post_init__(self):
        payload = json.loads(self.canonical_json)
        if not validate_contract('ModelBundle', payload)['valid']:
            raise ValueError('invalid_model_bundle')
        parameters = payload['parameters']
        for field in _IDENTITY_PARAMETERS:
            value = parameters.get(field)
            if not isinstance(value, str) or (not value.strip() and field not in ('document_prefix', 'query_prefix')):
                raise ValueError('missing_identity_parameter:' + field)
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                               separators=(',', ':'), allow_nan=False)
        object.__setattr__(self, 'canonical_json', canonical)

    @classmethod
    def from_bundle(cls, bundle: dict):
        return cls(json.dumps(bundle, allow_nan=False))

    @property
    def bundle(self):
        return json.loads(self.canonical_json)

    @property
    def bundle_hash(self):
        return hashlib.sha256(self.canonical_json.encode('utf-8')).hexdigest()

    def save(self, path):
        with Path(path).open('x', encoding='utf-8') as handle:
            json.dump({'bundle_hash': self.bundle_hash, 'bundle': self.bundle},
                      handle, ensure_ascii=False, sort_keys=True, allow_nan=False)
            handle.write('\n')


@dataclass(frozen=True)
class TokenCounter:
    tokenizer: str
    revision: str
    model_identity: str
    count: Callable[[tuple[str, ...]], int]


def _integer(value, minimum):
    return type(value) is int and value >= minimum


def preflight_budget(parts: tuple[str, ...], limit: int, *, model_identity: str,
                     counter: TokenCounter | None = None, reserved_output: int = 0):
    """Check complete embedding/prompt or query+passage input; never truncate.

    Caller must supply the full serialized inputs to the compatible counter.
    ready means only this budget passed; it grants no execution permission.
    """
    if not _integer(limit, 1) or not _integer(reserved_output, 0):
        raise ValueError('invalid_token_limits')
    if not isinstance(model_identity, str) or not model_identity.strip():
        raise ValueError('missing_model_identity')
    if not isinstance(parts, tuple) or not parts or not all(isinstance(p, str) for p in parts):
        raise ValueError('invalid_complete_input')
    result = {'model_identity': model_identity, 'limit': limit,
              'reserved_output': reserved_output, 'input_tokens': None,
              'total_tokens': None, 'excess_tokens': None,
              'tokenizer': None, 'tokenizer_revision': None}
    if counter is None:
        return {**result, 'status': 'pending_tokenizer'}
    if counter.model_identity != model_identity:
        raise ValueError('counter_model_identity_mismatch')
    if not counter.tokenizer.strip() or not counter.revision.strip():
        raise ValueError('missing_tokenizer_identity')
    count = counter.count(parts)
    if not _integer(count, 0):
        raise ValueError('invalid_token_count')
    total = count + reserved_output
    return {**result, 'status': 'ready' if total <= limit else 'exceeded',
            'input_tokens': count, 'total_tokens': total,
            'excess_tokens': max(0, total-limit), 'tokenizer': counter.tokenizer,
            'tokenizer_revision': counter.revision}


def validate_embeddings(vectors, *, expected_count: int, dimension: int,
                        expected_identity: str, actual_identity: str):
    """Validate a successful response against its pinned bundle identity.

    Service errors must propagate before this function, not become zero vectors.
    This validation does not authenticate the provider's reported model identity.
    """
    if not isinstance(expected_identity, str) or not expected_identity.strip() or expected_identity != actual_identity:
        raise ValueError('embedding_identity_mismatch')
    if not _integer(expected_count, 1) or not _integer(dimension, 1):
        raise ValueError('invalid_embedding_shape')
    if not isinstance(vectors, (list, tuple)) or len(vectors) != expected_count:
        raise ValueError('embedding_count_mismatch')
    result = []
    for vector in vectors:
        if not isinstance(vector, (list, tuple)) or len(vector) != dimension:
            raise ValueError('embedding_dimension_mismatch')
        try:
            if any(type(value) not in (int, float) or not math.isfinite(value) for value in vector):
                raise ValueError('invalid_embedding_value')
        except OverflowError:
            raise ValueError('invalid_embedding_value') from None
        result.append(tuple(float(value) for value in vector))
    return tuple(result)
