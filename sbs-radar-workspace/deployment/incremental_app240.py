"""Publish explicit catalog-count/Genie comparison profile237 and UI239 on exact ACTIVE236; limits preserved. One deployment, zero App start/stop; identities and process caps unchanged."""
import importlib.util
from pathlib import Path
import time
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('incremental210_util', ROOT / 'deployment/incremental_app210.py')
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)
EXPECTED = '01f1bca36d231c9e82bd1d7d369a3fa2'
PACKAGE = 'deployment/state/incremental-package240'
STATE = 'deployment/state/incremental-app240'
REVIEW = 'runs/sk09-incremental-240-review.json'
OVERLAY = 'runs/sk12-composed240-overlay/source'
PATCH_FILES = {'src/sbs/genie/cache_transport227.py', 'src/sbs/genie/diagnostics220.py', 'src/sbs/genie/cache228.py', 'src/sbs/genie/server_rotation.py', 'config/genie-bootstrap-098.json', 'src/sbs/conversation/__init__.py', 'src/sbs/genie/provenance.py', 'src/sbs/genie/__init__.py', 'src/sbs/webapp/static/app.js', 'config/genie-rotation-098.json', 'src/sbs/genie/count237.py'}
PRIOR_PACKAGE = 'deployment/state/incremental-package236'
PRIOR_RESULT = 'deployment/state/incremental-app236/result.json'
PROTECTED_RECEIPT = 'runs/sk06-protected-evidence-217-cloud-verified.json'
OVERLAY_MANIFEST = 'runs/sk12-composed240-overlay/manifest240.json'


def prepare(root=ROOT):
    root = Path(root)
    prior = u.read(root / PRIOR_PACKAGE / 'plan.json')
    chunks = u.read(root / PRIOR_PACKAGE / 'delta/chunks163-manifest.json')
    overlay = u.read(root / OVERLAY_MANIFEST)
    u.require(bool(PATCH_FILES),'240_PATCHSET_NOT_FROZEN')
    changes = {}
    for n in sorted(PATCH_FILES):
        changes[n]=(root/OVERLAY/n).read_bytes()
        u.require(overlay['files_sha256'][n]==u.digest(changes[n]),'240_OVERLAY_DRIFT')
    for name, raw in changes.items():
        chunks['logical_files_sha256'][name] = u.digest(raw)
    changes['chunks163-manifest.json'] = u.canonical(chunks) + b'\n'
    package = root / PACKAGE
    u.require(not package.exists(), '240_PACKAGE_EXISTS')
    delta = {}
    for name, raw in changes.items():
        old=None
        if name in prior['result_files_sha256']:
            candidates=[root/prefix/'delta'/name for prefix in (PRIOR_PACKAGE,'deployment/state/incremental-package234','deployment/state/incremental-package232','deployment/state/incremental-package229','deployment/state/incremental-package225','deployment/state/incremental-package223','deployment/state/incremental-package221','deployment/state/incremental-package218','deployment/state/incremental-package214',u.PACKAGE)]
            candidates.append(root/u.BASE/'source'/name)
            old=next(p for p in candidates if p.exists()).read_bytes()
            u.require(u.digest(old)==prior['result_files_sha256'][name],'240_PRIOR_DRIFT')
            u.durable(package/'originals'/name,old)
        u.durable(package/'delta'/name,raw)
        delta[name]={'before':u.digest(old) if old is not None else None,'after':u.digest(raw),'bytes':len(raw)}
    files = dict(prior['result_files_sha256'])
    files.update({n: item['after'] for n, item in delta.items()})
    plan = {'overlay240_sha256': u.digest((root / OVERLAY_MANIFEST).read_bytes()),
            'protected_volume_receipt_required': PROTECTED_RECEIPT, 'version': 240, 'app': u.APP, 'source_path': u.SOURCE,
            'expected_deployment': EXPECTED, 'delta': delta, 'result_files_sha256': files,
            'result_source_sha256': u.digest(u.canonical(files)), 'source_directory_is_mutable': True,
            'old_path_hash_is_historical': True, 'automatic_stop': False,
            'new_start': False, 'new_deploy_max': 1, 'display_only': False, 'proposal_policy224_changed': False, 'proposal_policy224_preserved': True, 'protected_evidence217': True, 'safe_generation_diagnostics': True, 'historical_counts221':True,'platform_authorization223':True,'typed_result225':True,'cache_chain228':True,'diagnostic231_preserved':True,'trace233_preserved':True,'published_count_profile237':True,'count_ui239':True,'genie_polling_seconds':2,'genie_max_polls':23,'genie_acceptance_deadline_seconds':45,
            'runtime_identity210_unchanged': True, 'signed_process_limits_unchanged': True, 'numeric_equivalence': 'failed', 'final_release_authorized': False,
            'additional_process_allocation': {'generation_posts': 6, 'embedding_posts': 5, 'embedding_tokens': 50000}}
    u.durable(package / 'plan.json', plan)
    return plan


def review(root=ROOT):
    root = Path(root)
    plan = u.read(root / PACKAGE / 'plan.json')
    record = u.read(root / REVIEW)
    u.require(record.get('status') == 'PASS_INCREMENTAL_240_CODE_ONLY'
              and record.get('plan_sha256') == u.digest((root / PACKAGE / 'plan.json').read_bytes()), '240_REVIEW')
    for name, pin in record['files_sha256'].items():
        u.require(u.digest((root / u.safe(name)).read_bytes()) == pin, '240_REVIEW_DRIFT')
    u.require(PROTECTED_RECEIPT in record['files_sha256'], '240_PROTECTED_VOLUME_REVIEW')
    for name in ('deployment/incremental_app240.py', 'deployment/incremental_app210.py', 'deployment/activation240.py'):
        u.require(name in record['files_sha256'], '240_REVIEW_SCOPE')
    u.require(plan['expected_deployment'] == EXPECTED and plan['source_path'] == u.SOURCE
              and set(plan['delta']) == PATCH_FILES | {'chunks163-manifest.json'}
              and plan['runtime_identity210_unchanged'] is True and plan['signed_process_limits_unchanged'] is True and plan['new_start'] is False
              and plan['display_only'] is False and plan['proposal_policy224_changed'] is False and plan['proposal_policy224_preserved'] is True and plan['protected_evidence217'] is True, '240_PLAN_SCOPE')
    for name, item in plan['delta'].items():
        u.require(u.digest((root / PACKAGE / 'delta' / name).read_bytes()) == item['after'], '240_DELTA_DRIFT')
    return plan


def active_guard(api, app):
    u.identity(app)
    active = app.get('active_deployment') or {}
    u.require(app.get('compute_status', {}).get('state') in ('ACTIVE', 'RUNNING')
              and active.get('deployment_id') == EXPECTED
              and active.get('source_code_path') == u.SOURCE and active.get('creator') == u.OWNER
              and active.get('status', {}).get('state') == 'SUCCEEDED'
              and not app.get('pending_deployment'), '240_ACTIVE_BINDING')
    actual = api('GET', '/api/2.0/apps/' + u.APP + '/deployments/' + EXPECTED)
    u.require(actual.get('deployment_id') == EXPECTED and actual.get('source_code_path') == u.SOURCE
              and actual.get('creator') == u.OWNER and actual.get('status', {}).get('state') == 'SUCCEEDED', '240_DEPLOYMENT_BINDING')


def execute(*, cfg, root=ROOT, api_factory=u.API, sleep=time.sleep):
    root = Path(root)
    plan = review(root)
    state = root / STATE
    state.mkdir(parents=True, exist_ok=False)
    api = api_factory(cfg, state)
    path = '/api/2.0/apps/' + u.APP
    result = {'status': 'incomplete', 'automatic_stop': False, 'new_start': False,
              'runtime_identity210_unchanged': True, 'signed_process_limits_unchanged': True, 'activation_started': False,
              'delta_files': len(plan['delta']), 'delta_bytes': sum(x['bytes'] for x in plan['delta'].values()),
              'prior236_result_sha256': u.digest((root / PRIOR_RESULT).read_bytes()),
              'prior236_result': u.read(root / PRIOR_RESULT)}
    try:
        me = api('GET', '/api/2.0/preview/scim/v2/Me')
        u.require(me.get('id') == '76826984571984' and me.get('userName') == u.OWNER and me.get('active') is True, '240_OPERATOR')
        app = api('GET', path)
        active_guard(api, app)
        u.durable(state / 'app-before.json', app)
        u.stage(api, plan, root / PACKAGE, state)
        active_guard(api, api('GET', path))
        u.durable(state / 'deploy-intent.json', {'source_code_path': u.SOURCE, 'mode': 'SNAPSHOT'})
        deployment = api('POST', path + '/deployments', body={'source_code_path': u.SOURCE, 'mode': 'SNAPSHOT'})
        u.require(deployment.get('source_code_path') == u.SOURCE and deployment.get('deployment_id'), '240_DEPLOY_RECEIPT')
        u.durable(state / 'deploy-receipt.json', deployment)
        for _ in range(90):
            actual = api('GET', path + '/deployments/' + deployment['deployment_id'])
            phase = actual.get('status', {}).get('state')
            if phase == 'SUCCEEDED':
                app = api('GET', path)
                u.identity(app)
                u.require(app.get('active_deployment', {}).get('deployment_id') == deployment['deployment_id']
                          and not app.get('pending_deployment')
                          and app.get('compute_status', {}).get('state') in ('ACTIVE', 'RUNNING'), '240_NEW_ACTIVE')
                u.durable(state / 'app-active.json', app)
                result.update(status='deployed_inactive_pending_real_ui', deployment_id=deployment['deployment_id'],
                              source_sha256=plan['result_source_sha256'])
                break
            u.require(phase not in ('FAILED', 'CANCELLED'), '240_DEPLOY_FAILED')
            sleep(3)
        else:
            raise ValueError('APP210_240_DEPLOY_TIMEOUT')
    except Exception as error:
        result['error_type'] = type(error).__name__
        text = str(error)
        result['error_code'] = text if text.startswith('APP210_') else 'APP210_240_REMOTE_FAILURE'
    finally:
        result['http_reserved'] = getattr(api, 'count', None)
        result['additional_upload_intents'] = len(list((state / 'imports').rglob('*.json')))
        result['additional_deploy_intents'] = int((state / 'deploy-intent.json').exists())
        u.durable(state / 'result.json', result)
        if hasattr(api, 'session'):
            api.session.close()
    return result
