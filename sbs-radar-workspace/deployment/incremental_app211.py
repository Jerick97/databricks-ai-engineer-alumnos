"""Display-only delta on ACTIVE210; one deploy, no start/stop or runtime changes."""
import importlib.util
from pathlib import Path
import time
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('incremental210_util', ROOT / 'deployment/incremental_app210.py')
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)
EXPECTED = '01f1bc545d091be18851c8ff1754cd9f'
PACKAGE = 'deployment/state/incremental-package211'
STATE = 'deployment/state/incremental-app211'
REVIEW = 'runs/sk09-incremental-211-review.json'
UI_FILES = {'src/sbs/webapp/static/app.js', 'src/sbs/webapp/static/index.html'}


def prepare(root=ROOT):
    root = Path(root)
    prior = u.read(root / u.PACKAGE / 'plan.json')
    chunks = u.read(root / u.PACKAGE / 'delta/chunks163-manifest.json')
    changes = {n: (root / 'deployment/overlay211' / n).read_bytes() for n in UI_FILES}
    for name, raw in changes.items():
        chunks['logical_files_sha256'][name] = u.digest(raw)
    changes['chunks163-manifest.json'] = u.canonical(chunks) + b'\n'
    package = root / PACKAGE
    u.require(not package.exists(), '211_PACKAGE_EXISTS')
    delta = {}
    for name, raw in changes.items():
        old = (root / u.PACKAGE / 'delta' / name).read_bytes()
        u.require(u.digest(old) == prior['result_files_sha256'][name], '211_PRIOR_DRIFT')
        u.durable(package / 'originals' / name, old)
        u.durable(package / 'delta' / name, raw)
        delta[name] = {'before': u.digest(old), 'after': u.digest(raw), 'bytes': len(raw)}
    files = dict(prior['result_files_sha256'])
    files.update({n: item['after'] for n, item in delta.items()})
    plan = {'version': 211, 'app': u.APP, 'source_path': u.SOURCE,
            'expected_deployment': EXPECTED, 'delta': delta, 'result_files_sha256': files,
            'result_source_sha256': u.digest(u.canonical(files)), 'source_directory_is_mutable': True,
            'old_path_hash_is_historical': True, 'automatic_stop': False,
            'new_start': False, 'new_deploy_max': 1, 'display_only': True,
            'runtime210_unchanged': True, 'numeric_equivalence': 'failed', 'final_release_authorized': False,
            'additional_process_allocation': {'generation_posts': 8, 'embedding_posts': 8, 'embedding_tokens': 80000}}
    u.durable(package / 'plan.json', plan)
    return plan


def review(root=ROOT):
    root = Path(root)
    plan = u.read(root / PACKAGE / 'plan.json')
    record = u.read(root / REVIEW)
    u.require(record.get('status') == 'PASS_INCREMENTAL_211_CODE_ONLY'
              and record.get('plan_sha256') == u.digest((root / PACKAGE / 'plan.json').read_bytes()), '211_REVIEW')
    for name, pin in record['files_sha256'].items():
        u.require(u.digest((root / u.safe(name)).read_bytes()) == pin, '211_REVIEW_DRIFT')
    for name in ('deployment/incremental_app211.py', 'deployment/incremental_app210.py', 'deployment/activation211.py'):
        u.require(name in record['files_sha256'], '211_REVIEW_SCOPE')
    u.require(plan['expected_deployment'] == EXPECTED and plan['source_path'] == u.SOURCE
              and set(plan['delta']) == UI_FILES | {'chunks163-manifest.json'}
              and plan['runtime210_unchanged'] is True and plan['new_start'] is False, '211_PLAN_SCOPE')
    for name, item in plan['delta'].items():
        u.require(u.digest((root / PACKAGE / 'delta' / name).read_bytes()) == item['after'], '211_DELTA_DRIFT')
    return plan


def active_guard(api, app):
    u.identity(app)
    active = app.get('active_deployment') or {}
    u.require(app.get('compute_status', {}).get('state') in ('ACTIVE', 'RUNNING')
              and active.get('deployment_id') == EXPECTED
              and active.get('source_code_path') == u.SOURCE and active.get('creator') == u.OWNER
              and active.get('status', {}).get('state') == 'SUCCEEDED'
              and not app.get('pending_deployment'), '211_ACTIVE_BINDING')
    actual = api('GET', '/api/2.0/apps/' + u.APP + '/deployments/' + EXPECTED)
    u.require(actual.get('deployment_id') == EXPECTED and actual.get('source_code_path') == u.SOURCE
              and actual.get('creator') == u.OWNER and actual.get('status', {}).get('state') == 'SUCCEEDED', '211_DEPLOYMENT_BINDING')


def execute(*, cfg, root=ROOT, api_factory=u.API, sleep=time.sleep):
    root = Path(root)
    plan = review(root)
    state = root / STATE
    state.mkdir(parents=True, exist_ok=False)
    api = api_factory(cfg, state)
    path = '/api/2.0/apps/' + u.APP
    result = {'status': 'incomplete', 'automatic_stop': False, 'new_start': False,
              'runtime210_unchanged': True, 'activation_started': False,
              'delta_files': len(plan['delta']), 'delta_bytes': sum(x['bytes'] for x in plan['delta'].values()),
              'prior210_result_sha256': u.digest((root / u.STATE / 'attempt2/result.json').read_bytes()),
              'prior210_result': u.read(root / u.STATE / 'attempt2/result.json')}
    try:
        me = api('GET', '/api/2.0/preview/scim/v2/Me')
        u.require(me.get('id') == '76826984571984' and me.get('userName') == u.OWNER and me.get('active') is True, '211_OPERATOR')
        app = api('GET', path)
        active_guard(api, app)
        u.durable(state / 'app-before.json', app)
        u.stage(api, plan, root / PACKAGE, state)
        active_guard(api, api('GET', path))
        u.durable(state / 'deploy-intent.json', {'source_code_path': u.SOURCE, 'mode': 'SNAPSHOT'})
        deployment = api('POST', path + '/deployments', body={'source_code_path': u.SOURCE, 'mode': 'SNAPSHOT'})
        u.require(deployment.get('source_code_path') == u.SOURCE and deployment.get('deployment_id'), '211_DEPLOY_RECEIPT')
        u.durable(state / 'deploy-receipt.json', deployment)
        for _ in range(90):
            actual = api('GET', path + '/deployments/' + deployment['deployment_id'])
            phase = actual.get('status', {}).get('state')
            if phase == 'SUCCEEDED':
                app = api('GET', path)
                u.identity(app)
                u.require(app.get('active_deployment', {}).get('deployment_id') == deployment['deployment_id']
                          and not app.get('pending_deployment')
                          and app.get('compute_status', {}).get('state') in ('ACTIVE', 'RUNNING'), '211_NEW_ACTIVE')
                u.durable(state / 'app-active.json', app)
                result.update(status='deployed_inactive_pending_real_ui', deployment_id=deployment['deployment_id'],
                              source_sha256=plan['result_source_sha256'])
                break
            u.require(phase not in ('FAILED', 'CANCELLED'), '211_DEPLOY_FAILED')
            sleep(3)
        else:
            raise ValueError('APP210_211_DEPLOY_TIMEOUT')
    except Exception as error:
        result['error_type'] = type(error).__name__
        text = str(error)
        result['error_code'] = text if text.startswith('APP210_') else 'APP210_211_REMOTE_FAILURE'
    finally:
        result['http_reserved'] = getattr(api, 'count', None)
        result['additional_upload_intents'] = len(list((state / 'imports').rglob('*.json')))
        result['additional_deploy_intents'] = int((state / 'deploy-intent.json').exists())
        u.durable(state / 'result.json', result)
        if hasattr(api, 'session'):
            api.session.close()
    return result
