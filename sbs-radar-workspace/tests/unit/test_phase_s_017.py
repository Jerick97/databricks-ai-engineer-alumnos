from pathlib import Path
import importlib.util
ROOT=Path(__file__).resolve().parents[2]
def load():
    spec=importlib.util.spec_from_file_location('phase_s017',ROOT/'runs/sk12-phase-s-017.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def test_independent_local_preflight():
    m=load();out=m.preflight(ROOT)
    assert out['status']=='pending_sql_start_authorization'
    assert out['executor_id']==76826984571984
    assert not out['requires_genie_space'] and not out['requires_job'] and not out['requires_app']
    assert out['remote_calls']==0

import json
import pytest
from types import SimpleNamespace

@pytest.fixture
def m():return load()
def approved(m):
    root,c,h,plan=m.load(ROOT)
    a=dict(status='approved',phase='S',configuration_sha256=h,approved_by=c['writer']['owner'],accept_sql_cost_unknown=True,issued_at_ms=1000,expires_at_ms=1801000,warehouse_running_observation_required=True,allow_start_if_stopped=False)
    return c,h,plan,a

@pytest.mark.parametrize('field',['accept_sql_cost_unknown','warehouse_running_observation_required'])
def test_pending_assumption_or_cost_never_opens_sdk(m,field):
    c,h,p,a=approved(m);a[field]=False
    with pytest.raises(ValueError):m.authorize(c,h,a,2000)

@pytest.mark.parametrize('change',[{'configuration_sha256':'0'*64},{'issued_at_ms':True},{'expires_at_ms':1001},{'status':'pending'},{'allow_start_if_stopped':1}])
def test_authorization_exact_pins_window_and_types(m,change):
    c,h,p,a=approved(m)
    with pytest.raises(ValueError):m.authorize(c,h,a|change,2000)

class Activity:
    id='828756322bedff37'
    def __init__(self,states,ambiguous=False):self.states=iter(states);self.calls=[];self.ambiguous=ambiguous
    def call(self,method):
        self.calls.append(method)
        if method=='POST':
            if self.ambiguous:raise ValueError('unknown')
            return {}
        return dict(id=self.id,state=next(self.states),auto_stop_mins=10)
    def close(self):pass

def test_start_same_authorization_single_post_reconciles(m,tmp_path):
    a=Activity(['STOPPED','STARTING','RUNNING'],ambiguous=True)
    out=m.ensure_running(a,tmp_path,allow_start=True,sleep=lambda _:None)
    assert a.calls==['GET','POST','GET','GET'] and out['state']=='RUNNING'
    assert out['automatic_stop'] is False and out['creation_attribution']=='not_claimed'
    assert (tmp_path/'warehouse-start-intent.json').exists()

def test_pending_start_never_reissued(m,tmp_path):
    a=Activity(['STOPPED']*4)
    with pytest.raises(ValueError,match='PENDING'):m.ensure_running(a,tmp_path,allow_start=True,sleep=lambda _:None)
    b=Activity(['STOPPED'])
    with pytest.raises(FileExistsError):m.ensure_running(b,tmp_path,allow_start=True,sleep=lambda _:None)
    assert a.calls.count('POST')==1 and b.calls==['GET']

def test_existing_running_shared_warehouse_not_stopped(m,tmp_path):
    a=Activity(['RUNNING']);out=m.ensure_running(a,tmp_path,allow_start=False)
    assert a.calls==['GET'] and not out['start_requested'] and not out['automatic_stop']

def test_stopped_without_cost_start_decision_fails(m,tmp_path):
    a=Activity(['STOPPED'])
    with pytest.raises(ValueError,match='NOT_AUTHORIZED'):m.ensure_running(a,tmp_path,allow_start=False)
    assert a.calls==['GET']

def test_execute_binding_writes_local_record_and_uses_existing_owner(m,tmp_path,monkeypatch):
    c,h,p,a=approved(m);monkeypatch.setattr(m,'load',lambda root:(tmp_path,c,h,p));calls=[]
    class Writer:
        def __init__(self):self.statements=SimpleNamespace(execute_statement=lambda **k:None);self.reader=SimpleNamespace(sdk=self.statements)
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def publish(self,**kwargs):calls.append(kwargs);return dict(status='published',evidence_mode='fixture',versions={})
    def factory(plan,cfg,journal,**kwargs):
        assert cfg.executor_id==76826984571984 and cfg.policy['exclusive_maintenance']==c['server_policy_assumptions_unobserved']['exclusive_maintenance']
        return Writer()
    out=m.execute(tmp_path,a,config_factory=lambda **k:SimpleNamespace(host=c['writer']['host']),writer_factory=factory,activity_factory=lambda *a:Activity(['RUNNING']),clock=lambda:2000)
    assert out['status']=='published' and len(calls)==1
    assert out['result']['evidence_mode']=='fixture' # fixture is not cloud evidence
    path=tmp_path/c['state_root']/'attempt-initial.json';assert json.loads(path.read_text())==out
    with pytest.raises(FileExistsError):m.execute(tmp_path,a,config_factory=lambda **k:None,clock=lambda:2000)

def test_factory_failure_recorded_without_provider_text(m,tmp_path,monkeypatch):
    c,h,p,a=approved(m);monkeypatch.setattr(m,'load',lambda root:(tmp_path,c,h,p))
    def fail(**kwargs):raise RuntimeError('secret-provider-text')
    out=m.execute(tmp_path,a,config_factory=fail,clock=lambda:2000)
    assert out['status']=='incomplete' and 'secret-provider-text' not in json.dumps(out)


def test_sql_admission_closes_without_stopping_existing_work(m):
    calls=[];delegate=SimpleNamespace(execute_statement=lambda **kw:calls.append(kw))
    gate=m.AdmissionStatements(delegate,1000,lambda:1000)
    with pytest.raises(ValueError,match='ADMISSION_CLOSED'):gate.execute_statement(statement='SELECT fixture')
    assert calls==[]

def test_expiry_during_auth_blocks_actual_start_transport(m,monkeypatch):
    import requests
    calls=[];now=[1]
    session=SimpleNamespace(adapters={},request=lambda *a,**k:calls.append(a),close=lambda:None)
    monkeypatch.setattr(requests,'Session',lambda:session)
    def auth():now[0]=10;return {'Authorization':'fixture-secret'}
    activity=m.WarehouseActivity(SimpleNamespace(host='https://fixture.invalid',authenticate=auth),'828756322bedff37')
    activity.admit=lambda:m.require(now[0]<10,'EXPIRED')
    with pytest.raises(ValueError):activity.call('POST')
    assert calls==[]

def test_expiry_during_auth_blocks_actual_sql_transport(m):
    from sbs.operations.cloud_driver import SingleAttemptApi
    now=[1];calls=[]
    def auth():now[0]=10;return {'Authorization':'fixture-secret'}
    cfg=m.AdmissionConfig(SimpleNamespace(host='https://fixture.invalid',authenticate=auth),lambda:m.require(now[0]<10,'EXPIRED'))
    api=SingleAttemptApi(cfg,session=SimpleNamespace(request=lambda *a,**kw:calls.append(a)))
    with pytest.raises(ValueError):api.do('POST','/api/2.0/sql/statements',body={'statement':'fixture only'})
    assert calls==[]

def test_directory_sync_failure_prevents_start(m,tmp_path,monkeypatch):
    activity=Activity(['STOPPED'])
    monkeypatch.setattr(m,'sync_directory',lambda _:(_ for _ in ()).throw(OSError('fixture persistence error')))
    with pytest.raises(OSError):m.ensure_running(activity,tmp_path,allow_start=True,sleep=lambda _:None)
    assert activity.calls==['GET']

def test_result_sync_failure_prevents_auth(m,tmp_path,monkeypatch):
    c,h,p,a=approved(m);monkeypatch.setattr(m,'load',lambda root:(tmp_path,c,h,p));calls=[]
    original=m.sync_directory
    def sync(path):
        if (tmp_path/c['state_root']/'attempt-initial.json').exists():raise OSError('fixture sync failed')
        original(path)
    monkeypatch.setattr(m,'sync_directory',sync)
    with pytest.raises(OSError):m.execute(tmp_path,a,config_factory=lambda **kw:calls.append(kw),clock=lambda:2000)
    assert calls==[]

def test_technical_profile_is_not_user_attestation(m):
    c,h,p,a=approved(m)
    assert 'accept_administrative_declarations' not in a
    assert c['policy_user_attestation'] is False and c['policy_selected_by']=='server_executor'
    assert m.authorize(c,h,a,2000).policy['no_inherited_abac']==c['server_policy_assumptions_unobserved']['no_inherited_abac']


def test_real_sdk_config_import_without_authentication():
    """Execute the actual runtime import, without constructing/authenticating Config."""
    import ast
    from databricks.sdk.core import Config
    tree=ast.parse((ROOT/'runs/sk12-phase-s-017.py').read_text())
    imports=[n for n in ast.walk(tree) if isinstance(n,ast.ImportFrom) and any(a.name=='Config' for a in n.names)]
    assert len(imports)==1
    namespace={}
    exec(compile(ast.Module(body=imports,type_ignores=[]),'runtime-config-import','exec'),namespace)
    assert namespace['Config'] is Config
