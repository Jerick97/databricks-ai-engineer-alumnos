"""058 pure local continuation contracts; no auth/SDK/cloud."""
from pathlib import Path
import importlib.util,json
import pytest
ROOT=Path(__file__).resolve().parents[2]
def load():
    p=ROOT/'runs/sk12-phase-s-058.py'
    assert p.exists(),'Missing058runner'
    spec=importlib.util.spec_from_file_location('runner058',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def test_preflight_preserves_real_state_and_uses_current_renewal():
    m=load();files=[ROOT/m.CONFIG,ROOT/m.OLD_AUTH,*list((ROOT/'deployment/state/phase-s-017').rglob('*.json'))]
    before={str(p):p.read_bytes() for p in files};r=m.preflight(ROOT)
    assert r['sql_budget']['reserved']==51 and r['sql_budget']['limit']==112
    assert r['remote_calls']==0 and r['identity_profile']=='uc_managed_named_detail_v1'
    assert r['insert_receipts']==8 and r['expected_additional_sql']==48
    assert {str(p):p.read_bytes() for p in files}==before

def test_window_selection_reuses_live_and_renews_expired():
    m=load();r=m.preflight(ROOT);c=r['proposed_configuration'];old=r['old_policy'];h=r['approved_configuration_sha256']
    for now,renewed in [(old['expires_at_ms']-600000,False),(old['expires_at_ms'],True)]:
        auth,cfg,renew=m.authorization_for_window(c,h,old,now)
        assert renew is renewed
        assert cfg.policy['issued_at_ms']==(now if renewed else old['issued_at_ms'])
        assert auth['expires_at_ms']==(now+1800000 if renewed else old['expires_at_ms'])

def test_read_only_blocks_mutations_before_delegate():
    m=load();calls=[]
    class SQL:
        def execute_statement(self,**kw):calls.append(kw)
    s=m.ReadOnlyStatements(SQL())
    for sql in ['INSERT INTO x VALUES (1)','CREATE TABLE x(a INT)','DROP TABLE x','SELECT 1; DROP TABLE x']:
        with pytest.raises(ValueError,match='CONTINUATION_READ_ONLY'):s.execute_statement(statement=sql)
    assert calls==[]
    s.execute_statement(statement='DESCRIBE HISTORY `a`.`b`.`c`');assert len(calls)==1

def test_review_required_before_any_write():
    m=load()
    with pytest.raises(ValueError,match='REVIEW_REQUIRED'):m.execute(ROOT,None)


@pytest.mark.parametrize('expired',[False,True])
def test_execute_fixture_preserves_budget_and_binding_and_selects_profile(tmp_path,monkeypatch,expired):
    from types import SimpleNamespace
    from dataclasses import asdict
    from sbs.genie.publication_writer import WriterConfig
    from sbs.genie import digest
    m=load();r=m.preflight(ROOT);p=m.phase(ROOT);plan=p.load_write_plan(ROOT,publication_id='pilot002-016')
    state=tmp_path/'deployment/state/phase-s-017';(state/'journal').mkdir(parents=True);(tmp_path/'runs').mkdir()
    (tmp_path/m.CONFIG).write_bytes((ROOT/m.CONFIG).read_bytes())
    cfg=WriterConfig(**r['proposed_configuration']['writer'],policy=r['old_policy'])
    binding=json.dumps({'plan_sha256':cfg.plan_sha256,'config_sha256':digest(asdict(cfg))}).encode()
    (state/'journal/binding.json').write_bytes(binding)
    budget=json.dumps(r['sql_budget']).encode();(state/'sql-budget-050.json').write_bytes(budget)
    review=tmp_path/'review.json';review.write_text(json.dumps({**r['review_contract'],'status':'PASS'}))
    proxy=SimpleNamespace(**{k:getattr(p,k) for k in ['authorize','AdmissionConfig','AdmissionStatements']})
    proxy.load=lambda root:(root,r['proposed_configuration'],r['approved_configuration_sha256'],plan)
    monkeypatch.setattr(m,'preflight',lambda root:r);monkeypatch.setattr(m,'phase',lambda root:proxy)
    calls=[]
    class SQL:
        def execute_statement(self,**kw):calls.append(kw)
    class Writer:
        def __init__(self):self.statements=SQL();self.reader=SimpleNamespace()
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def publish(self,**kw):
            assert isinstance(self.statements,m.ReadOnlyStatements)
            assert isinstance(self.statements.delegate,p.AdmissionStatements)
            with pytest.raises(ValueError):self.statements.execute_statement(statement='INSERT INTO x VALUES (1)')
            self.statements.execute_statement(statement='SELECT 1')
            return {'status':'published','evidence_mode':'fixture'}
    def factory(*a,**kw):assert kw['identity_profile']==m.IDENTITY_PROFILE;return Writer()
    class Activity:
        def call(self,method):assert method=='GET';return {'state':'RUNNING'}
        def close(self):pass
    out=m.execute(tmp_path,review,apply_reviewed_config=True,config_factory=lambda **kw:SimpleNamespace(host=cfg.host),activity_factory=lambda *a:Activity(),writer_factory=factory,clock=lambda:r['old_policy']['expires_at_ms']+(1 if expired else -600000),sleep=lambda _:None)
    assert out['status']=='published' and out['window_reused'] is not expired
    assert len(calls)==1 and calls[0]['statement']=='SELECT 1'
    assert (state/'journal/binding.json').read_bytes()==binding and (state/'sql-budget-050.json').read_bytes()==budget
    assert bool(list((state/'journal').glob('window-renewal-*'))) is expired
    assert (tmp_path/'runs/sk12-phase-s-058-config-before.json').is_file()
    with pytest.raises(FileExistsError):m.execute(tmp_path,review,apply_reviewed_config=True,clock=lambda:r['old_policy']['expires_at_ms']+1)


def test_live_window_expiry_still_blocks_sql_and_warehouse(tmp_path):
    from test_phase_s_runner_053 import Activity
    m=load();p=m.phase(ROOT);calls=[]
    class SQL:
        def execute_statement(self,**kw):calls.append(kw)
    gated=m.ReadOnlyStatements(p.AdmissionStatements(SQL(),1000,lambda:1000))
    with pytest.raises(ValueError,match='ADMISSION_CLOSED'):gated.execute_statement(statement='SELECT 1')
    a=Activity(['STOPPED'])
    def expired():raise ValueError('PHASE_EFFECT_ADMISSION_CLOSED')
    with pytest.raises(ValueError,match='ADMISSION_CLOSED'):m.reconcile_start(a,tmp_path,prior_running=True,admit=expired,clock=lambda:1000,sleep=lambda _:None)
    assert calls==[] and a.calls==[]


def test_near_expiry_rejected_before_any_execute_write_or_sdk(tmp_path,monkeypatch):
    m=load();r=m.preflight(ROOT);review=tmp_path/'review.json'
    review.write_text(json.dumps({**r['review_contract'],'status':'PASS'}))
    monkeypatch.setattr(m,'preflight',lambda root:r)
    before={str(p):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    calls=[]
    for remaining in (1,300000):
        with pytest.raises(ValueError,match='LIVE_WINDOW_INSUFFICIENT_BUFFER'):
            m.execute(tmp_path,review,apply_reviewed_config=True,config_factory=lambda **kw:calls.append('sdk'),clock=lambda:r['old_policy']['expires_at_ms']-remaining)
    assert calls==[]
    assert {str(p):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}==before
