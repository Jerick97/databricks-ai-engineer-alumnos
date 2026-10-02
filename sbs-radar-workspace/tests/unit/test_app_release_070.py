"""Local reproducible assembly only; no deployment or provider calls."""
from pathlib import Path
import importlib.util,tarfile,io,json,hashlib
import pytest
ROOT=Path(__file__).resolve().parents[2]
def load():
    s=importlib.util.spec_from_file_location('app070',ROOT/'deployment/app_release_070.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def test_archive_deterministic_and_no_path_escape():
    m=load();a=m.archive_bytes({'b.txt':b'b','a.txt':b'a'});assert a==m.archive_bytes({'a.txt':b'a','b.txt':b'b'})
    with tarfile.open(fileobj=io.BytesIO(a),mode='r:gz') as t:
        assert t.getnames()==['a.txt','b.txt'] and all(x.mtime==0 and x.uid==0 for x in t)
    with pytest.raises(ValueError):m.archive_bytes({'../escape':b'x'})

def test_snapshot_offline_models_state_exclusions_and_concrete_config():
    m=load();b,manifest,c,o=m.snapshot()
    assert any(n.endswith('.onnx') for n in b)
    assert not any(n.startswith('deployment/state/') or (n.startswith('deployment/') and n.count('/')==1 and n.endswith('-authorization.json')) for n in b)
    assert json.loads(b['config/genie-server.json'])['enabled'] is False
    assert c['command']==['python','app.py'] and {'name':'SBS_MODE','value':'cloud'} in c['env']
    assert not any('SECRET' in e['name'] or 'TOKEN'==e['name'] for e in c['env'])
    assert manifest['structural_049_activated'] is False
    assert all(hashlib.sha256(b[n]).hexdigest()==h for n,h in manifest['files_sha256'].items())

def test_plan_limits_existing_resources_and_no_false_e2e():
    m=load();b,manifest,c,o=m.snapshot();p=m.operation_plan(manifest,c,o)
    assert p['app_name']=='sbs-radar-pilot' and p['effects']['app_start_max']==p['effects']['app_deploy_max']==1
    assert p['effects']['sql']==0 and p['effects']['endpoint_permission_changes'] is False
    assert p['user_api_scope_changes']==[] and 'iam.current-user:read' in p['user_api_scopes_observed']
    assert p['acceptance']['e2e']=='not accepted' and 'rate limit0' in p['blockers']['generation']
    names=[r['name'] for r in p['resource_bindings_proposed']]
    assert len(names)==len(set(names)) and 'sbs-evidence-volume' in names and 'sbs-evidence' in names
    assert 'smoke072 passed' in p['blockers']['generation'] and '073' in p['blockers']['generation']
    from databricks.sdk.service.apps import AppResource,AppDeployment
    for resource in p['resource_bindings_proposed']:assert AppResource.from_dict(resource).as_dict()==resource
    assert AppDeployment.from_dict(p['deployment_request']).as_dict()==p['deployment_request']
