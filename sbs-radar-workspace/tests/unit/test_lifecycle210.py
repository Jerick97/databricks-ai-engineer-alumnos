import base64
from concurrent.futures import ThreadPoolExecutor
from copy import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from sbs.app133.lifecycle210 import CAPS, EpochBudget210, EmbeddingTransport210, Lifecycle210Error
from sbs.app133.runtime import GuardedTransport


def setup_budget():
    key = Ed25519PrivateKey.generate()
    now = [1000]
    budget = EpochBudget210(key.public_key(), clock=lambda: now[0])
    return key, now, budget


def envelope(key, budget, **changes):
    p = dict(epoch=budget.epoch, activation_id='allocation-1', issued_at_unix=1000,
             expires_at_unix=2000, caps=dict(CAPS))
    p.update(changes)
    return {'payload': p, 'signature': base64.b64encode(key.sign(json.dumps(p, sort_keys=True, separators=(',', ':')).encode())).decode()}


def test_inactive_activation_expiry_restart_and_no_reset():
    key, now, b = setup_budget()
    with pytest.raises(Lifecycle210Error): b.reserve()
    signed = envelope(key, b)
    assert b.activate(signed)['ready']
    b.reserve()
    with pytest.raises(Lifecycle210Error, match='ALREADY'): b.activate(signed)
    assert b.posts == 1
    now[0] = 2000
    with pytest.raises(Lifecycle210Error): b.reserve()
    assert b.status()['state'] == 'expired'
    restarted = EpochBudget210(key.public_key(), clock=lambda: 1000)
    with pytest.raises(Lifecycle210Error, match='EPOCH'): restarted.activate(signed)
    assert restarted.status()['state'] == 'inactive'


@pytest.mark.parametrize('changes', [dict(epoch='old'), dict(caps={**CAPS, 'generation_posts': 9}),
    dict(issued_at_unix=1031), dict(issued_at_unix=879), dict(expires_at_unix=1000),
    dict(expires_at_unix=29801), dict(expires_at_unix=True), dict(extra=1)])
def test_invalid_signed_payload_rejected(changes):
    key, _, b = setup_budget()
    with pytest.raises(Lifecycle210Error): b.activate(envelope(key, b, **changes))
    assert b.activation_id is None


def test_bad_signature_and_other_key_rejected():
    key, _, b = setup_budget()
    signed = envelope(key, b)
    signed['signature'] = 'not base64'
    with pytest.raises(Lifecycle210Error, match='SIGNATURE'): b.activate(signed)
    with pytest.raises(Lifecycle210Error, match='SIGNATURE'):
        b.activate(envelope(Ed25519PrivateKey.generate(), b))


def test_concurrent_actor_views_share_allocation_and_failed_network_is_reserved():
    key, _, b = setup_budget()
    b.activate(envelope(key, b))
    service = SimpleNamespace(process_budget=b)
    views = [copy(service) for _ in range(24)]
    calls = []
    class Raw:
        last_attempt = {}
        def __call__(self, body):
            calls.append(body)
            raise OSError('ambiguous remote failure')
    def attempt(view):
        try: GuardedTransport(Raw(), view.process_budget)({})
        except (OSError, Lifecycle210Error): pass
    with ThreadPoolExecutor(max_workers=12) as pool: list(pool.map(attempt, views))
    assert len(calls) == b.posts == 8


def test_embedding_global_posts_tokens_and_query_preflight():
    key, _, b = setup_budget()
    b.activate(envelope(key, b))
    roles, calls = [], []
    class Adapter:
        def preflight(self, inputs, *, role):
            roles.append(role)
            return {'reserved_tokens': 10000}
    for _ in range(8):
        # Different adapters (including actor-specific initialization) share b.
        EmbeddingTransport210(lambda body: calls.append(body), Adapter(), b)({'input': ['q'], 'instruction': 'i'})
    with pytest.raises(Lifecycle210Error):
        EmbeddingTransport210(lambda body: calls.append(body), Adapter(), b)({'input': ['q']})
    assert len(calls) == 8 and b.embedding_tokens == 80000
    assert roles[:8] == ['query'] * 8
    key, _, b = setup_budget(); b.activate(envelope(key, b))
    b.reserve_embedding(79999)
    with pytest.raises(Lifecycle210Error): b.reserve_embedding(2)
    assert b.embedding_posts == 1


def test_overlay_preserves_host_auth_csrf_and_read_only_inactive(tmp_path):
    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location('webapp210_test', root / 'deployment/overlay210/src/sbs/webapp/__init__.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    module.__file__ = str(root / 'src/sbs/webapp/__init__.py')
    key, _, b = setup_budget()
    source = tmp_path / 'test.pdf'; source.write_bytes(b'%PDF-test')
    class Service:
        mode = 'cloud'
        process_budget = b
        def for_actor(self, actor): return self
        def catalog(self): return {'pairs': [{'id': 'pair', 'provisions': [{'id': 'p'}]}]}
        def source(self, source_id): return source
        def ask(self, *args): b.check(); return {}
    class Identity:
        def authenticate(self, headers):
            if headers.get('x-test-identity') != 'verified': raise PermissionError()
            return {'subject': 'reader'}
    app = module.create_app(Service(), mode='cloud', identity_adapter=Identity(), public_origin='https://demo.example', trusted_proxy='databricks_apps')
    client = TestClient(app, base_url='https://internal.example')
    headers = {'x-forwarded-host': 'demo.example', 'x-test-identity': 'verified'}
    assert client.get('/api/runtime/status').status_code == 403
    assert client.get('/api/runtime/status', headers={'x-forwarded-host': 'demo.example'}).status_code == 401
    assert client.get('/api/runtime/status', headers={**headers, 'x-forwarded-host': 'demo.example,evil'}).status_code == 403
    assert client.get('/api/runtime/status', headers=headers).json()['state'] == 'inactive'
    catalog = client.get('/api/catalog', headers=headers).json()
    assert client.get('/api/sources/source', headers=headers).status_code == 200
    signed = envelope(key, b)
    assert client.post('/api/runtime/activate', headers=headers, json=signed).status_code == 403
    headers['x-csrf-token'] = catalog['csrf_token']
    assert client.post('/api/runtime/activate', headers={**headers, 'origin': 'https://evil.example'}, json=signed).status_code == 403
    question = {'question': 'q', 'pair_id': 'pair', 'provision_id': 'p'}
    assert 'administrador' in client.post('/api/ask', headers=headers, json=question).json()['detail']
    assert client.post('/api/runtime/activate', headers=headers, json=signed).status_code == 200
    b.reserve()
    assert client.post('/api/runtime/activate', headers=headers, json=signed).status_code == 409
    assert b.posts == 1


def test_real_initializer_uses_signed_caps_and_shared_budget_without_network():
    from sbs.app133.bootstrap import load_config
    from sbs.app133.runtime import AppService
    root = Path(__file__).resolve().parents[2]
    config = load_config(root)
    client = SimpleNamespace(config=SimpleNamespace(host=config['workspace_host'], auth_type='oauth-m2m',
        client_id=config['reader_client_id'], authenticate=lambda: (_ for _ in ()).throw(AssertionError('no network'))))
    service = AppService(mode='cloud').configure133(root, config, client_factory=lambda: client)
    key, _, budget = setup_budget(); service.process_budget = budget
    with pytest.raises(Lifecycle210Error): service.initialize_models()
    budget.activate(envelope(key, budget)); service.initialize_models()
    assert service.generator.budget is budget
    assert service.embedding._transport.budget is budget
    assert service.embedding.max_calls == 8 and service.embedding.max_tokens == 80000

    from sbs.models.databricks import EmbeddingServiceError
    expected = service.embedding.preflight(['consulta'], role='query')['reserved_tokens']
    network = []
    def failing_network(body):
        network.append(body)
        raise EmbeddingServiceError()
    service.embedding._transport.delegate = failing_network
    with pytest.raises(EmbeddingServiceError): service.embedding.embed_query('consulta')
    assert len(network) == budget.embedding_posts == service.embedding.calls_attempted == 1
    assert budget.embedding_tokens == service.embedding.tokens_reserved == expected
