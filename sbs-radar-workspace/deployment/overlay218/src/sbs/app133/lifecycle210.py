"""Signed, single-allocation inference lifecycle. Restart always changes epoch."""
import base64
import json
import re
import secrets
import threading
import time
from pathlib import Path
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

CAPS = {'generation_posts': 6, 'embedding_posts': 5, 'embedding_tokens': 50000}

class Lifecycle210Error(ValueError):
    pass

class EpochBudget210:
    def __init__(self, public_key, *, clock=time.time):
        if not isinstance(public_key, Ed25519PublicKey):
            raise ValueError('RUNTIME210_PUBLIC_KEY_INVALID')
        self.public_key = public_key
        self.clock = clock
        self.epoch = secrets.token_hex(32)
        self.lock = threading.RLock()
        self.activation_id = None
        self.deadline = 0
        self.posts = 0
        self.embedding_posts = 0
        self.embedding_tokens = 0
        self.max_posts = CAPS['generation_posts']

    def check(self):
        if self.activation_id is None:
            raise Lifecycle210Error('El chat todavía no está habilitado. Contacta al administrador; puedes consultar las fuentes y comparaciones.')
        if self.clock() >= self.deadline:
            raise Lifecycle210Error('La sesión de consultas venció. Contacta al administrador para habilitar una nueva sesión; las fuentes siguen disponibles.')

    def activate(self, envelope):
        with self.lock:
            if self.activation_id is not None:
                raise Lifecycle210Error('RUNTIME210_ALREADY_ACTIVATED')
            if not isinstance(envelope, dict) or set(envelope) != {'payload', 'signature'}:
                raise Lifecycle210Error('RUNTIME210_ENVELOPE_INVALID')
            p = envelope['payload']
            if not isinstance(p, dict) or set(p) != {'epoch', 'activation_id', 'issued_at_unix', 'expires_at_unix', 'caps'}:
                raise Lifecycle210Error('RUNTIME210_PAYLOAD_INVALID')
            if p['epoch'] != self.epoch:
                raise Lifecycle210Error('RUNTIME210_EPOCH_MISMATCH')
            if not isinstance(p['activation_id'], str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', p['activation_id']):
                raise Lifecycle210Error('RUNTIME210_ACTIVATION_ID_INVALID')
            if not isinstance(p['caps'], dict) or p['caps'] != CAPS or any(type(v) is not int for v in p['caps'].values()):
                raise Lifecycle210Error('RUNTIME210_CAPS_INVALID')
            issued, expires = p['issued_at_unix'], p['expires_at_unix']
            now = self.clock()
            if (type(issued) is not int or type(expires) is not int or issued > now + 30
                    or now - issued > 120 or expires <= now or expires <= issued or expires > issued + 28800):
                raise Lifecycle210Error('RUNTIME210_WINDOW_INVALID')
            try:
                signature = base64.b64decode(envelope['signature'], validate=True)
                self.public_key.verify(signature, json.dumps(p, sort_keys=True, separators=(',', ':')).encode())
            except (InvalidSignature, ValueError, TypeError):
                raise Lifecycle210Error('RUNTIME210_SIGNATURE_INVALID') from None
            self.activation_id = p['activation_id']
            self.deadline = expires
            return self.status()

    def reserve(self):
        with self.lock:
            self.check()
            if self.posts >= CAPS['generation_posts']:
                raise Lifecycle210Error('Se agotó el cupo de respuestas. Contacta al administrador para habilitar más consultas.')
            self.posts += 1

    def reserve_embedding(self, tokens):
        with self.lock:
            self.check()
            if type(tokens) is not int or tokens < 0:
                raise Lifecycle210Error('RUNTIME210_TOKEN_COUNT_INVALID')
            if self.embedding_posts >= CAPS['embedding_posts'] or self.embedding_tokens + tokens > CAPS['embedding_tokens']:
                raise Lifecycle210Error('Se agotó el cupo de búsqueda para consultas. Contacta al administrador para habilitar más consultas.')
            self.embedding_posts += 1
            self.embedding_tokens += tokens

    def status(self):
        with self.lock:
            state = ('inactive' if self.activation_id is None else 'expired' if self.clock() >= self.deadline
                     else 'exhausted' if self.posts >= CAPS['generation_posts'] or self.embedding_posts >= CAPS['embedding_posts'] or self.embedding_tokens >= CAPS['embedding_tokens'] else 'active')
            return {'epoch': self.epoch, 'ready': True, 'inference_ready': state == 'active', 'state': state,
                    'activation_id': self.activation_id, 'expires_at_unix': self.deadline,
                    'caps': dict(CAPS), 'used': {'generation_posts': self.posts,
                    'embedding_posts': self.embedding_posts, 'embedding_tokens': self.embedding_tokens}}

class EmbeddingTransport210:
    def __init__(self, delegate, adapter, budget):
        self.delegate, self.adapter, self.budget = delegate, adapter, budget

    def __call__(self, body):
        role = 'query' if 'instruction' in body else 'document'
        tokens = self.adapter.preflight(body['input'], role=role)['reserved_tokens']
        self.budget.reserve_embedding(tokens)
        return self.delegate(body)


def create_service210(environ, *, root, clock=time.time, client_factory=None, binding_loader=None):
    from .bootstrap import create_service133
    key_path = Path(root) / 'config/runtime210-public-key.pem'
    if key_path.is_symlink() or key_path.stat().st_size > 4096:
        raise ValueError('RUNTIME210_PUBLIC_KEY_INVALID')
    budget = EpochBudget210(load_pem_public_key(key_path.read_bytes()), clock=clock)
    service = create_service133(environ, root=root, clock=clock,
                                client_factory=client_factory, binding_loader=binding_loader)
    service.process_budget = budget
    service.provenance['runtime210'] = {'epoch': budget.epoch, 'activation': 'signed_allocation_required'}
    return service
