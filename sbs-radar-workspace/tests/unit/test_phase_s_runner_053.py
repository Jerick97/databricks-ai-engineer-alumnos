"""053 runner tests: local inputs and injected activity; no SDK/auth/cloud."""
from pathlib import Path
import importlib.util,json,hashlib
import pytest
ROOT=Path(__file__).resolve().parents[2]


def load():
    path=ROOT/'runs/sk12-phase-s-053.py'
    assert path.is_file(), 'Missing reviewable renewal053 runner'
    spec=importlib.util.spec_from_file_location('runner053',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def test_preflight_pure_exposes_drift_and_preserves_budget():
    m=load();targets=[ROOT/'deployment/phase-s-017.json',ROOT/'deployment/state/phase-s-017/sql-budget-050.json',ROOT/'deployment/state/phase-s-017/journal/binding.json']
    before={str(p):p.read_bytes() for p in targets}
    out=m.preflight(ROOT)
    assert out['remote_calls']==0 and out['starts_warehouse'] is False
    assert out['sql_budget']['reserved']==3 and out['sql_budget']['limit']==112
    assert out['configuration_updates']
    assert out['status']=='ready_for_independent_review_not_executed'
    assert {str(p):p.read_bytes() for p in targets}==before


def test_fresh_authorization_created_only_from_execute_clock_and_actual_phase_authorize():
    m=load();c=json.loads((ROOT/'deployment/phase-s-017.json').read_bytes())
    a,cfg=m.fresh_authorization(c,'a'*64,1234000)
    assert a['issued_at_ms']==1234000 and a['expires_at_ms']==3034000
    assert cfg.policy['issued_at_ms']==a['issued_at_ms']
    assert a['allow_start_if_stopped'] is True
    assert cfg.max_http_calls==512


class Activity:
    id='828756322bedff37'
    def __init__(self,states,ambiguous=False):self.states=iter(states);self.calls=[];self.ambiguous=ambiguous
    def call(self,method):
        self.calls.append(method)
        if method=='POST':
            if self.ambiguous:raise ValueError('unconfirmed')
            return {}
        return {'id':self.id,'state':next(self.states)}


def test_restart_requires_confirmed_prior_running_and_new_stopped(tmp_path):
    m=load();a=Activity(['STOPPED','RUNNING'])
    with pytest.raises(ValueError,match='PRIOR_RUNNING_REQUIRED'):
        m.reconcile_start(a,tmp_path,prior_running=False,admit=lambda:None,clock=lambda:1000,sleep=lambda _:None)
    assert a.calls==[]
    a=Activity(['STOPPED','STARTING','RUNNING'],ambiguous=True)
    out=m.reconcile_start(a,tmp_path,prior_running=True,admit=lambda:None,clock=lambda:1000,sleep=lambda _:None)
    assert a.calls==['GET','POST','GET','GET'] and out['state']=='RUNNING'
    assert out['post_status']=='unconfirmed'
    b=Activity(['STOPPED'])
    with pytest.raises(FileExistsError):m.reconcile_start(b,tmp_path,prior_running=True,admit=lambda:None,clock=lambda:1000,sleep=lambda _:None)
    assert b.calls==['GET']


def test_review_missing_or_wrong_never_updates_configuration(tmp_path):
    m=load()
    with pytest.raises(ValueError,match='REVIEW_REQUIRED'):m.execute(ROOT,None)
    report=m.preflight(ROOT);bad=tmp_path/'review.json';bad.write_text(json.dumps({'status':'PASS'}))
    with pytest.raises(ValueError,match='REVIEW_SHAPE'):m.execute(ROOT,bad)


def test_expiration_blocks_post_and_sql_delegate(tmp_path):
    m=load();phase=m.phase(ROOT);a=Activity(['STOPPED']);calls=[]
    def expired():raise ValueError('PHASE_EFFECT_ADMISSION_CLOSED')
    with pytest.raises(ValueError,match='ADMISSION_CLOSED'):
        m.reconcile_start(a,tmp_path,prior_running=True,admit=expired,clock=lambda:1000,sleep=lambda _:None)
    assert a.calls==[] and list(tmp_path.iterdir())==[]
    class SQL:
        def execute_statement(self,**kw):calls.append(kw)
    gated=phase.AdmissionStatements(SQL(),1000,lambda:1000)
    with pytest.raises(ValueError,match='PHASE_SQL_ADMISSION_CLOSED'):gated.execute_statement(statement='SELECT 1')
    assert calls==[]
    class Config:
        def authenticate(self):calls.append('auth');return {'Authorization':'fixture'}
    wrapper=phase.AdmissionConfig(Config(),expired)
    with pytest.raises(ValueError,match='ADMISSION_CLOSED'):wrapper.authenticate()
    assert calls==['auth']


def test_valid_review_still_requires_explicit_config_apply_before_writes(tmp_path):
    m=load();report=m.preflight(ROOT);review=tmp_path/'review.json'
    review.write_text(json.dumps({**report['review_contract'],'status':'PASS'}))
    with pytest.raises(ValueError,match='EXPLICIT_CONFIG_APPLICATION_REQUIRED'):
        m.execute(ROOT,review)
    assert not (ROOT/'deployment/state/phase-s-017/runner-053-intent.json').exists()


def test_execute_fixture_archives_config_renews_append_only_and_keeps_budget(tmp_path,monkeypatch):
    """Fixture wiring only: real authorize/renewal/persistence, fake SDK/warehouse/writer."""
    from types import SimpleNamespace
    from copy import copy
    m=load();report=m.preflight(ROOT);p=m.phase(ROOT)
    plan=p.load_write_plan(ROOT,publication_id='pilot002-016')
    for name in ['deployment/phase-s-017.json','deployment/state/phase-s-017/sql-budget-050.json','deployment/state/phase-s-017/journal/binding.json']:
        dest=tmp_path/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((ROOT/name).read_bytes())
    (tmp_path/'runs').mkdir()
    before=(tmp_path/'deployment/phase-s-017.json').read_bytes()
    state=tmp_path/'deployment/state/phase-s-017';binding=(state/'journal/binding.json').read_bytes();budget=(state/'sql-budget-050.json').read_bytes()
    review=tmp_path/'review.json';review.write_text(json.dumps({**report['review_contract'],'status':'PASS'}))
    proxy=SimpleNamespace(**{k:getattr(p,k) for k in ['authorize','AdmissionConfig','AdmissionStatements']})
    proxy.load=lambda root:(root,report['proposed_configuration'],report['approved_configuration_sha256'],plan)
    monkeypatch.setattr(m,'preflight',lambda root:report);monkeypatch.setattr(m,'phase',lambda root:proxy)
    calls=[]
    class Writer:
        def __init__(self):self.original=SimpleNamespace();self.statements=self.original;self.reader=SimpleNamespace(sdk=self.original)
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def publish(self,**kw):
            assert isinstance(self.statements,p.AdmissionStatements)
            assert self.statements.delegate is self.original # no second cumulative budget wrapper
            calls.append('fixture_publish');return {'status':'published','evidence_mode':'fixture'}
    activity=Activity(['RUNNING']);activity.close=lambda:None
    out=m.execute(tmp_path,review,apply_reviewed_config=True,
                  config_factory=lambda **kw:SimpleNamespace(host=report['proposed_configuration']['writer']['host']),
                  activity_factory=lambda *a:activity,writer_factory=lambda *a,**kw:Writer(),
                  clock=lambda:report['old_policy']['expires_at_ms']+1000,sleep=lambda _:None)
    assert out['status']=='published' and calls==['fixture_publish']
    assert (state/'journal/binding.json').read_bytes()==binding
    assert (state/'sql-budget-050.json').read_bytes()==budget
    assert (state/'journal/window-renewal-000001.json').is_file()
    assert (tmp_path/'runs/sk12-phase-s-053-config-before.json').read_bytes()==before
    assert hashlib.sha256((tmp_path/'deployment/phase-s-017.json').read_bytes()).hexdigest()==report['approved_configuration_sha256']
    auth=json.loads((tmp_path/m.NEW_AUTH).read_bytes())
    assert auth['expires_at_ms']-auth['issued_at_ms']==1800000
    assert not (state/'warehouse-restart-053-intent.json').exists()
    with pytest.raises(FileExistsError):m.execute(tmp_path,review,apply_reviewed_config=True)
