"""Incremental own-source deployment; no model traffic, deadline, or stop supervisor."""
from pathlib import Path, PurePosixPath
import base64
import hashlib
import json
import os
import time

ROOT = Path(__file__).resolve().parents[1]
HOST = 'https://dbc-0410b264-20c7.cloud.databricks.com'
APP = 'sbs-radar-pilot'
OWNER = 'sociosdosmilveintiseis@gmail.com'
CLIENT = 'a947eccf-5f94-4369-a3d4-8f83b4ea98a1'
ORIGIN = 'https://sbs-radar-pilot-7474657121564806.aws.databricksapps.com'
OLD_DEPLOYMENT = '01f1bc4fc48b122cb0ecf4fb3ce425b3'
SOURCE = '/Workspace/Users/' + OWNER + '/sbs-radar/releases/experiment199-24687d1435c9b7dbbd0a0689ff02328556031122a37b2fa4cf4b4cbfe789ec98'
BASE = 'deployment/state/experimental-materialized199'
PACKAGE = 'deployment/state/incremental-package210'
STATE = 'deployment/state/incremental-app210'
REVIEW = 'runs/sk09-incremental-210-review.json'
PATCH_ALLOWLIST = {'app133.py', 'config/runtime210-public-key.pem', 'src/sbs/webapp/__init__.py',
                   'src/sbs/webapp/static/index.html', 'src/sbs/webapp/static/app.js',
                   'src/sbs/app133/runtime.py', 'src/sbs/app133/lifecycle210.py',
                   'config/app-integration-133.json'}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError('APP210_' + message)


def durable(path, raw):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw if isinstance(raw, bytes) else canonical(raw))
        stream.flush()
        os.fsync(stream.fileno())
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def read(path):
    return json.loads(Path(path).read_bytes())


def safe(name):
    p = PurePosixPath(name)
    require(isinstance(name, str) and str(p) == name and not p.is_absolute()
            and '..' not in p.parts and bool(p.parts), 'PATH')
    return name


def prepare(changes, *, root=ROOT):
    """Snapshot only changed bytes; no credentials/network/window created."""
    root = Path(root)
    base = read(root / BASE / 'manifest.json')['files_sha256']
    require(set(changes) == PATCH_ALLOWLIST, 'PATCH_SCOPE')
    changes = {safe(n): raw for n, raw in changes.items()}
    chunks = read(root / BASE / 'source/chunks163-manifest.json')
    for name, raw in changes.items():
        require(isinstance(raw, bytes) and len(raw) < 8 * 1024 * 1024, 'PATCH_SIZE')
        require(not name.startswith('chunks163/'), 'MODEL_IMMUTABLE')
        chunks['logical_files_sha256'][name] = digest(raw)
    changes['chunks163-manifest.json'] = canonical(chunks) + b'\n'
    delta = {}
    package = root / PACKAGE
    require(not package.exists(), 'PACKAGE_EXISTS')
    for name, raw in changes.items():
        if base.get(name) == digest(raw):
            continue
        before = None
        if name in base:
            original = (root / BASE / 'source' / name).read_bytes()
            require(digest(original) == base[name], 'BASE_DRIFT')
            durable(package / 'originals' / name, original)
            before = base[name]
        durable(package / 'delta' / name, raw)
        delta[name] = {'before': before, 'after': digest(raw), 'bytes': len(raw)}
    files = dict(base)
    files.update({n: item['after'] for n, item in delta.items()})
    plan = {'version': 210, 'app': APP, 'source_path': SOURCE,
            'expected_deployment': OLD_DEPLOYMENT, 'delta': delta,
            'result_files_sha256': files, 'result_source_sha256': digest(canonical(files)),
            'base_manifest_sha256': digest((root / BASE / 'manifest.json').read_bytes()),
            'source_directory_is_mutable': True, 'old_path_hash_is_historical': True,
            'runtime_activation': 'after_readiness_signed_epoch', 'automatic_stop': False,
            'numeric_equivalence': 'failed', 'final_release_authorized': False}
    durable(package / 'plan.json', plan)
    return plan


class API:
    def __init__(self, cfg, state):
        import requests
        require(cfg.host.rstrip('/') == HOST, 'HOST')
        self.cfg, self.state, self.count = cfg, Path(state), 0
        self.session = requests.Session()
        self.session.trust_env = False
        require(all(a.max_retries.total == 0 for a in self.session.adapters.values()), 'RETRY')

    def __call__(self, method, path, body=None, query=None):
        self.count += 1
        require(self.count <= 300, 'HTTP_CAP')
        durable(self.state / f'http-{self.count:03}.json', {'method': method, 'path': path})
        response = self.session.request(method, HOST + path, json=body, params=query,
                                        headers=self.cfg.authenticate(), timeout=(15, 60),
                                        allow_redirects=False)
        try:
            require(response.status_code in (200, 201, 202), 'HTTP_' + str(response.status_code))
            return response.json() if response.content else {}
        finally:
            response.close()


def identity(app):
    require(app.get('name') == APP and app.get('id') == CLIENT
            and app.get('service_principal_client_id') == CLIENT
            and app.get('service_principal_id') == 77041447522099
            and app.get('creator') == OWNER and app.get('url') == ORIGIN, 'IDENTITY')
    require(app.get('default_source_code_path') == SOURCE, 'SOURCE')


def verify_plan(root):
    root = Path(root)
    plan_path = root / PACKAGE / 'plan.json'
    plan = read(plan_path)
    review = read(root / REVIEW)
    require(review.get('status') == 'PASS_INCREMENTAL_210_CODE_ONLY'
            and review.get('plan_sha256') == digest(plan_path.read_bytes()), 'REVIEW')
    for name, pin in review['files_sha256'].items():
        require(digest((root / safe(name)).read_bytes()) == pin, 'REVIEW_DRIFT')
    require(review['files_sha256'].get('deployment/incremental_app210.py') == digest(Path(__file__).read_bytes()), 'RUNNER_REVIEW')
    require(plan['source_path'] == SOURCE and plan['expected_deployment'] == OLD_DEPLOYMENT
            and plan['app'] == APP and plan['automatic_stop'] is False, 'PLAN_SCOPE')
    for name, item in plan['delta'].items():
        require(digest((root / PACKAGE / 'delta' / safe(name)).read_bytes()) == item['after'], 'DELTA_DRIFT')
    return plan


def stage(api, plan, package, state):
    """Validate all before-images before any overwrite; never retry an ambiguous import."""
    package, state = Path(package), Path(state)
    # New files must be demonstrably absent using directory listing, not a swallowed error.
    parents = {}
    for name, item in plan['delta'].items():
        path = SOURCE + '/' + name
        if item['before'] is None:
            parent = str(PurePosixPath(path).parent)
            if parent not in parents:
                listing = api('GET', '/api/2.0/workspace/list', query={'path': parent})
                require(not listing.get('next_page_token'), 'LIST_PAGINATED')
                parents[parent] = {o['path'] for o in listing.get('objects', [])}
            require(path not in parents[parent], 'NEW_FILE_EXISTS')
        else:
            value = api('GET', '/api/2.0/workspace/export', query={'path': path, 'format': 'AUTO'})
            raw = base64.b64decode(value['content'], validate=True)
            require(digest(raw) == item['before'], 'REMOTE_DRIFT')
        durable(state / 'before' / (name + '.json'), item)
    # Manifest last, so partially staged source cannot pass reassembly.
    for name in sorted(plan['delta'], key=lambda n: (n == 'chunks163-manifest.json', n)):
        item = plan['delta'][name]
        raw = (package / 'delta' / name).read_bytes()
        require(digest(raw) == item['after'], 'DELTA_DRIFT')
        durable(state / 'imports' / (name + '.json'), item)
        api('POST', '/api/2.0/workspace/import', body={'path': SOURCE + '/' + name,
            'format': 'AUTO', 'overwrite': item['before'] is not None,
            'content': base64.b64encode(raw).decode()})
        value = api('GET', '/api/2.0/workspace/export', query={'path': SOURCE + '/' + name, 'format': 'AUTO'})
        require(digest(base64.b64decode(value['content'], validate=True)) == item['after'], 'READBACK')
        durable(state / 'verified' / (name + '.json'), item)



def stopped_guard(api, app, state, label):
    """STOPPED responses can omit active_deployment; deployment history is authoritative."""
    from datetime import datetime
    identity(app)
    require(app.get('compute_status', {}).get('state') == 'STOPPED'
            and not app.get('pending_deployment'), label + '_STATE')
    active = app.get('active_deployment')
    require(not active or active.get('deployment_id') == OLD_DEPLOYMENT, label + '_DEPLOYMENT')
    require(app.get('last_deployment_id') in (None, OLD_DEPLOYMENT), label + '_LAST_DEPLOYMENT')
    app_path = '/api/2.0/apps/' + APP
    expected = api('GET', app_path + '/deployments/' + OLD_DEPLOYMENT)
    require(expected.get('deployment_id') == OLD_DEPLOYMENT
            and expected.get('source_code_path') == SOURCE
            and expected.get('creator') == OWNER
            and expected.get('status', {}).get('state') == 'SUCCEEDED', label + '_DEPLOYMENT')
    values, token, tokens = [], None, set()
    for _ in range(3):
        query = {'page_size': 100}
        if token:
            query['page_token'] = token
        page = api('GET', app_path + '/deployments', query=query)
        values.extend(page.get('app_deployments', []))
        token = page.get('next_page_token')
        if not token:
            break
        require(token not in tokens, label + '_HISTORY_TOKEN')
        tokens.add(token)
    else:
        raise ValueError('APP210_' + label + '_HISTORY_LIMIT')
    require(values, label + '_HISTORY_EMPTY')
    def timestamp(value):
        return datetime.fromisoformat(value['create_time'].replace('Z', '+00:00')).timestamp()
    latest_time = max(timestamp(value) for value in values)
    latest = [value for value in values if timestamp(value) == latest_time]
    require(len(latest) == 1 and latest[0].get('deployment_id') == OLD_DEPLOYMENT
            and latest[0].get('source_code_path') == SOURCE
            and latest[0].get('creator') == OWNER
            and latest[0].get('status', {}).get('state') == 'SUCCEEDED', label + '_LATEST_DEPLOYMENT')
    durable(Path(state) / (label.lower() + '-stopped-binding.json'),
            {'app': app, 'expected_deployment': expected, 'history': values})


def execution_state(root):
    state = Path(root) / STATE
    if not state.exists():
        state.mkdir(parents=True)
        return state, None
    prior = read(state / 'result.json')
    require(prior.get('error_code') == 'APP210_INITIAL_STATE'
            and prior.get('http_reserved') == 2
            and all(prior.get(k) == 0 for k in ('additional_upload_intents', 'additional_start_intents', 'additional_deploy_intents')),
            'ATTEMPT2_PRIOR_EFFECTS')
    require({p.name for p in state.iterdir()} == {'http-001.json', 'http-002.json', 'result.json'}, 'ATTEMPT2_JOURNAL')
    for name, path in [('http-001.json', '/api/2.0/preview/scim/v2/Me'), ('http-002.json', '/api/2.0/apps/' + APP)]:
        require(read(state / name) == {'method': 'GET', 'path': path}, 'ATTEMPT2_PRIOR_CALL')
    attempt = state / 'attempt2'
    attempt.mkdir(exist_ok=False)
    retained = {'http': 2, 'upload': 0, 'start': 0, 'deploy': 0,
                'result_sha256': digest((state / 'result.json').read_bytes())}
    durable(attempt / 'prior-attempt.json', retained)
    return attempt, retained


def execute(*, cfg, root=ROOT, api_factory=API, sleep=time.sleep, clock=time.time):
    root = Path(root)
    plan = verify_plan(root)
    state, retained = execution_state(root)
    api = api_factory(cfg, state)
    app_path = '/api/2.0/apps/' + APP
    result = {'prior_attempt210': retained, 'prior_attempts_191_to_207': {'deploy': 3, 'http': 1818, 'mkdir': 84, 'start': 3, 'upload': 469},
              'delta_files': len(plan['delta']), 'delta_bytes': sum(x['bytes'] for x in plan['delta'].values()),
              'status': 'incomplete', 'automatic_stop': False, 'activation_started': False,
              'numeric_equivalence': 'failed', 'final_release_authorized': False}
    try:
        me = api('GET', '/api/2.0/preview/scim/v2/Me')
        require(me.get('id') == '76826984571984' and me.get('userName') == OWNER and me.get('active') is True, 'OPERATOR')
        app = api('GET', app_path)
        stopped_guard(api, app, state, 'INITIAL')
        durable(state / 'app-before.json', app)
        stage(api, plan, root / PACKAGE, state)
        app = api('GET', app_path)
        stopped_guard(api, app, state, 'PRESTART')
        started = clock()
        durable(state / 'start-intent.json', {'at_unix': started})
        api('POST', app_path + '/start', body={})
        for i in range(90):
            app = api('GET', app_path)
            identity(app)
            active = app.get('active_deployment') or {}
            pending = app.get('pending_deployment')
            if pending:
                require(pending.get('source_code_path') == SOURCE and pending.get('creator') == OWNER, 'RESTORE_PENDING_SOURCE')
            if not active:
                require(app.get('compute_status', {}).get('state') in ('STOPPED', 'STARTING', 'UPDATING', 'ACTIVE', 'RUNNING'), 'RESTORE_STATE')
                sleep(3)
                continue
            require(active.get('source_code_path') == SOURCE and active.get('creator') == OWNER, 'RESTORE_SOURCE')
            if active.get('deployment_id') != OLD_DEPLOYMENT:
                from datetime import datetime
                when = datetime.fromisoformat(active['create_time'].replace('Z', '+00:00')).timestamp()
                require(started - 2 <= when <= clock() + 5, 'RESTORE_TIME')
            terminal = active.get('status', {}).get('state') in ('SUCCEEDED', 'FAILED', 'CANCELLED')
            if terminal and not app.get('pending_deployment') and app.get('compute_status', {}).get('state') in ('ACTIVE', 'RUNNING'):
                fresh = api('GET', app_path + '/deployments/' + active['deployment_id'])
                require(fresh.get('status', {}).get('state') in ('SUCCEEDED', 'FAILED', 'CANCELLED'), 'RESTORE_NOT_TERMINAL')
                break
            sleep(3)
        else:
            raise ValueError('APP210_RESTORE_TIMEOUT')
        durable(state / 'deploy-intent.json', {'source_code_path': SOURCE, 'mode': 'SNAPSHOT'})
        deployment = api('POST', app_path + '/deployments', body={'source_code_path': SOURCE, 'mode': 'SNAPSHOT'})
        require(deployment.get('source_code_path') == SOURCE and deployment.get('deployment_id'), 'DEPLOY_RECEIPT')
        durable(state / 'deploy-receipt.json', deployment)
        for i in range(90):
            observed = api('GET', app_path + '/deployments/' + deployment['deployment_id'])
            phase = observed.get('status', {}).get('state')
            if phase == 'SUCCEEDED':
                app = api('GET', app_path)
                identity(app)
                require(app.get('active_deployment', {}).get('deployment_id') == deployment['deployment_id']
                        and not app.get('pending_deployment')
                        and app.get('compute_status', {}).get('state') in ('ACTIVE', 'RUNNING'), 'ACTIVE_BINDING')
                durable(state / 'app-active.json', app)
                result.update(status='deployed_inactive_pending_real_ui', deployment_id=deployment['deployment_id'],
                              source_sha256=plan['result_source_sha256'])
                break
            require(phase not in ('FAILED', 'CANCELLED'), 'DEPLOY_FAILED')
            sleep(3)
        else:
            raise ValueError('APP210_DEPLOY_TIMEOUT')
    except Exception as error:
        result['error_type'] = type(error).__name__
        message = str(error)
        result['error_code'] = message if message.startswith('APP210_') else 'APP210_REMOTE_FAILURE'
        result['recovery'] = 'Inspect journal and real App state; never retry a mutation or stop automatically.'
    finally:
        result['http_reserved'] = getattr(api, 'count', None)
        result['additional_upload_intents'] = len(list((state / 'imports').rglob('*.json')))
        result['additional_start_intents'] = int((state / 'start-intent.json').exists())
        result['additional_deploy_intents'] = int((state / 'deploy-intent.json').exists())
        durable(state / 'result.json', result)
        if hasattr(api, 'session'):
            api.session.close()
    return result
