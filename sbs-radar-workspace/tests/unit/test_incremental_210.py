import base64
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'deployment' / (name + '.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m
m = load('incremental_app210')
a = load('activation210')


class Incremental(unittest.TestCase):
    def test_stage_prechecks_all_and_uploads_delta_once(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'delta').mkdir()
            (root / 'delta/a.py').write_bytes(b'new')
            (root / 'delta/chunks163-manifest.json').write_bytes(b'new manifest')
            remote = {'a.py': b'old', 'chunks163-manifest.json': b'old manifest'}
            plan = {'delta': {n: {'before': m.digest(raw), 'after': m.digest((root / 'delta' / n).read_bytes())} for n, raw in remote.items()}}
            calls = []
            def api(method, path, body=None, query=None):
                calls.append((method, path))
                name = (body or query)['path'][len(m.SOURCE) + 1:]
                if method == 'GET':
                    return {'content': base64.b64encode(remote[name]).decode()}
                remote[name] = base64.b64decode(body['content'])
                return {}
            m.stage(api, plan, root, root / 'state')
            self.assertEqual([c[0] for c in calls], ['GET', 'GET', 'POST', 'GET', 'POST', 'GET'])
            self.assertEqual(remote['a.py'], b'new')
            with self.assertRaisesRegex(ValueError, 'REMOTE_DRIFT'):
                m.stage(api, plan, root, root / 'state')

    def test_remote_drift_before_any_write(self):
        with tempfile.TemporaryDirectory() as folder:
            calls = []
            def api(method, *args, **kwargs):
                calls.append(method)
                return {'content': base64.b64encode(b'foreign').decode()}
            with self.assertRaisesRegex(ValueError, 'REMOTE_DRIFT'):
                m.stage(api, {'delta': {'a': {'before': m.digest(b'old')}}}, folder, folder)
            self.assertEqual(calls, ['GET'])

    def test_ambiguous_import_not_retried(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'delta').mkdir()
            (root / 'delta/a').write_bytes(b'new')
            calls = []
            def api(method, *args, **kwargs):
                calls.append(method)
                if method == 'POST':
                    raise TimeoutError('secret not logged')
                return {'content': base64.b64encode(b'old').decode()}
            with self.assertRaises(TimeoutError):
                m.stage(api, {'delta': {'a': {'before': m.digest(b'old'), 'after': m.digest(b'new')}}}, root, root / 'state')
            self.assertEqual(calls, ['GET', 'POST'])
            self.assertTrue((root / 'state/imports/a.json').exists())

    def test_paths_and_identity(self):
        for name in ('../x', '/x', 'a/../x', 'a//x'):
            with self.assertRaises(ValueError):
                m.safe(name)
        with self.assertRaisesRegex(ValueError, 'IDENTITY'):
            m.identity({'name': m.APP})

    def test_full_flow_readiness_no_stop_and_one_start_deploy(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / m.PACKAGE / 'delta').mkdir(parents=True)
            (root / m.PACKAGE / 'delta/a.py').write_bytes(b'new')
            plan = {'app': m.APP, 'source_path': m.SOURCE, 'expected_deployment': m.OLD_DEPLOYMENT,
                    'automatic_stop': False, 'result_source_sha256': 'result',
                    'delta': {'a.py': {'before': m.digest(b'old'), 'after': m.digest(b'new'), 'bytes': 3}}}
            m.durable(root / m.PACKAGE / 'plan.json', plan)
            runner = (ROOT / 'deployment/incremental_app210.py').read_bytes()
            m.durable(root / 'deployment/incremental_app210.py', runner)
            m.durable(root / m.REVIEW, {'status': 'PASS_INCREMENTAL_210_CODE_ONLY',
                'plan_sha256': m.digest((root / m.PACKAGE / 'plan.json').read_bytes()),
                'files_sha256': {'deployment/incremental_app210.py': m.digest(runner)}})
            class Fake:
                count = 0
                def __init__(self, cfg, state):
                    self.calls, self.started, self.deployed, self.raw = [], False, False, b'old'
                    self.missing_active_seen = False
                def __call__(self, method, path, body=None, query=None):
                    self.calls.append((method, path)); self.count += 1
                    if path.endswith('/Me'):
                        return {'id': '76826984571984', 'userName': m.OWNER, 'active': True}
                    if path.endswith('/export'):
                        return {'content': base64.b64encode(self.raw).decode()}
                    if path.endswith('/import'):
                        self.raw = base64.b64decode(body['content']); return {}
                    if path.endswith('/start'):
                        self.started = True; return {}
                    if method == 'GET' and path.endswith('/deployments'):
                        fixture = m.read(ROOT / 'deployment/state/auth-observation210/deployments.json')
                        return {'app_deployments': []} if query.get('page_token') else fixture
                    deployment = {'create_time': '2026-09-29T21:50:21Z', 'deployment_id': 'new210' if self.deployed else m.OLD_DEPLOYMENT,
                                  'source_code_path': m.SOURCE, 'creator': m.OWNER, 'status': {'state': 'SUCCEEDED'}}
                    if method == 'POST' and path.endswith('/deployments'):
                        self.deployed = True; return {**deployment, 'deployment_id': 'new210'}
                    if '/deployments/' in path:
                        return deployment
                    if not self.started:
                        return m.read(ROOT / 'deployment/state/auth-observation210/app-after-initial-rejection.json')
                    if not self.missing_active_seen:
                        self.missing_active_seen = True
                        fixture = m.read(ROOT / 'deployment/state/auth-observation210/app-after-initial-rejection.json')
                        fixture['compute_status']['state'] = 'STARTING'
                        return fixture
                    return {'id': m.CLIENT, 'name': m.APP, 'service_principal_client_id': m.CLIENT,
                            'service_principal_id': 77041447522099, 'creator': m.OWNER, 'url': m.ORIGIN,
                            'default_source_code_path': m.SOURCE, 'active_deployment': deployment,
                            'compute_status': {'state': 'ACTIVE' if self.started else 'STOPPED'}}
            holder = []
            def factory(cfg, state):
                obj = Fake(cfg, state); holder.append(obj); return obj
            result = m.execute(cfg=None, root=root, api_factory=factory, sleep=lambda _: None)
            self.assertEqual(result['status'], 'deployed_inactive_pending_real_ui')
            posts = [path for method, path in holder[0].calls if method == 'POST']
            self.assertEqual(sum(p.endswith('/start') for p in posts), 1)
            self.assertEqual(sum(p.endswith('/deployments') for p in posts), 1)
            self.assertFalse(any(p.endswith('/stop') for p in posts))
            self.assertFalse(result['activation_started'])

    def test_attempt2_retains_original_and_rejects_mutation_history(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            state = root / m.STATE
            original = {'error_code': 'APP210_INITIAL_STATE', 'http_reserved': 2,
                        'additional_upload_intents': 0, 'additional_start_intents': 0, 'additional_deploy_intents': 0}
            m.durable(state / 'result.json', original)
            m.durable(state / 'http-001.json', {'method': 'GET', 'path': '/api/2.0/preview/scim/v2/Me'})
            m.durable(state / 'http-002.json', {'method': 'GET', 'path': '/api/2.0/apps/' + m.APP})
            before = (state / 'result.json').read_bytes()
            path, retained = m.execution_state(root)
            self.assertEqual(path.name, 'attempt2')
            self.assertEqual(retained['http'], 2)
            self.assertEqual(before, (state / 'result.json').read_bytes())
            with self.assertRaisesRegex(ValueError, 'ATTEMPT2_JOURNAL'):
                m.execution_state(root)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            m.durable(root / m.STATE / 'result.json', {**original, 'additional_start_intents': 1})
            with self.assertRaisesRegex(ValueError, 'PRIOR_EFFECTS'):
                m.execution_state(root)

    def test_observed_stopped_guard_rejects_foreign_latest(self):
        with tempfile.TemporaryDirectory() as folder:
            app = m.read(ROOT / 'deployment/state/auth-observation210/app-after-initial-rejection.json')
            self.assertNotIn('active_deployment', app)
            history = m.read(ROOT / 'deployment/state/auth-observation210/deployments.json')
            expected = history['app_deployments'][0]
            history['app_deployments'].append({**expected, 'deployment_id': 'foreign', 'create_time': '2026-09-30T00:00:00Z'})
            history.pop('next_page_token')
            def api(method, path, **kwargs):
                return expected if path.endswith(m.OLD_DEPLOYMENT) else history
            with self.assertRaisesRegex(ValueError, 'LATEST_DEPLOYMENT'):
                m.stopped_guard(api, app, folder, 'INITIAL')

    def test_allocation_persists_and_restart_cannot_reset(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'control'
            public = a.initialize(path, 'a' * 64)
            epoch = 'x' * 32
            first = a.allocate(path, epoch, clock=lambda: 1000)
            self.assertEqual(a.allocate(path, epoch, clock=lambda: 2000), first)
            with self.assertRaisesRegex(ValueError, 'EXHAUSTED'):
                a.allocate(path, 'y' * 32)
            from cryptography.hazmat.primitives.serialization import load_pem_public_key
            load_pem_public_key(public).verify(base64.b64decode(first['signature']), a.canonical(first['payload']))
            (path / 'ledger.sqlite').unlink()
            with self.assertRaisesRegex(ValueError, 'MISSING'):
                a.allocate(path, epoch)
            with self.assertRaises(FileExistsError):
                a.initialize(path, 'a' * 64)

if __name__ == '__main__':
    unittest.main()
