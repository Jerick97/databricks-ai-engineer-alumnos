"""064 runner local tests; no SDK authentication or cloud."""
from pathlib import Path
import importlib.util,json
from types import SimpleNamespace
import pytest
ROOT=Path(__file__).resolve().parents[2]
def load():
    p=ROOT/'runs/sk06-recovery-064-finalize.py';s=importlib.util.spec_from_file_location('runner064',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def test_preflight_pure_and_pins_recovery_scope():
    m=load();state=ROOT/'deployment/state/phase-s-017';paths=[ROOT/m.CONFIG,ROOT/m.AUTH,*state.rglob('*.json')];before={str(p):p.read_bytes() for p in paths}
    r=m.preflight();assert r['sql_submissions']==r['post_requests']==r['remote_calls']==0 and r['expected_gets']==45
    assert r['max_readback_age_ms']==7200000 and r['configuration_delta']
    assert {str(p):p.read_bytes() for p in paths}==before


def test_requires_review_before_state():
    m=load()
    with pytest.raises(ValueError,match='REVIEW_REQUIRED'):m.execute(ROOT,None)


def test_get_transport_only_allowed_paths_bounded_private_capture(tmp_path):
    import io
    m=load();calls=[];admissions=[]
    class Raw(io.BytesIO):
        def read(self,n,**kw):return super().read(n)
    class Session:
        def request(self,*a,**kw):calls.append((a,kw));return SimpleNamespace(status_code=200,raw=Raw(b'{"ok":true}'),close=lambda:None)
    cfg=SimpleNamespace(host='https://fixture',authenticate=lambda:{'Authorization':'fixture-secret'})
    t=m.GetOnly(cfg,['/allowed'],tmp_path,lambda:admissions.append(1),Session())
    assert t.get('/allowed')=={'ok':True};assert calls[0][0]==('GET','https://fixture/allowed') and len(admissions)==2
    assert 'fixture-secret' not in (tmp_path/'get-001.json').read_text()
    with pytest.raises(ValueError,match='PATH_FORBIDDEN'):t.get('/api/2.0/sql/statements')
    t.calls=45
    with pytest.raises(ValueError,match='GET_CAP'):t.get('/allowed')
    assert len(calls)==1


def test_window_no_renewal_and_current_time():
    m=load();p={'issued_at_ms':1,'expires_at_ms':900000}
    for now in (0,600000,900000):
        with pytest.raises(ValueError,match='WINDOW_INSUFFICIENT'):m.admit_window(p,now)
    m.admit_window(p,599999)


def test_expiry_between_authentication_and_get_blocks_request(tmp_path):
    m=load();calls=[];now=[0]
    def auth():now[0]=2;return {}
    def admit():
        if now[0]>1:raise ValueError('EXPIRED')
    t=m.GetOnly(SimpleNamespace(host='https://fixture',authenticate=auth),['/allowed'],tmp_path,admit,SimpleNamespace(request=lambda *a,**kw:calls.append(1)))
    with pytest.raises(ValueError,match='EXPIRED'):t.get('/allowed')
    assert calls==[]


def test_execute_rejects_late_window_before_any_state_or_sdk(tmp_path,monkeypatch):
    m=load();r=m.preflight();review=tmp_path/'review.json';review.write_text(json.dumps({**r['review_contract'],'status':'PASS'}))
    original=m.read
    library={'status':'PASS','code_sha256':{p:m.sha((ROOT/p).read_bytes()) for p in m.CODE}}
    monkeypatch.setattr(m,'read',lambda p:library if Path(p)==ROOT/m.REVIEW else original(p))
    monkeypatch.setattr(m,'preflight',lambda root:r)
    before=(ROOT/m.CONFIG).read_bytes();calls=[]
    with pytest.raises(ValueError,match='WINDOW_INSUFFICIENT'):
        m.execute(ROOT,review,clock=lambda:r['policy']['expires_at_ms']-1,config_factory=lambda **kw:calls.append(1))
    assert calls==[] and (ROOT/m.CONFIG).read_bytes()==before
    assert not (ROOT/'runs/sk06-recovery-064-finalization').exists()
