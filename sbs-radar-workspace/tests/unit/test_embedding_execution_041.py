"""Fixtures only: no network, SDK client or real vectors."""
from pathlib import Path
import pytest
from sbs.retrieval.embedding_execution import execute, seal, digest

class Adapter:
    identity='model'; dimension=2
    calls=0
    def embed(self, texts, role):
        self.calls+=1
        return dict(embeddings=[[1.,2.]],bundle_hash='model',model='response',server_usage_exceeds_reserve=False,usage={'prompt_tokens':1},cost=None)

def setup(tmp_path):
    plan=dict(version='embedding-execution-041-v1',output='new',host='https://example.test',model_identity='model',dimension=2,expected_response_model='response',requests=2,inputs=2,reserved_tokens=18,local_input_tokens=2,batches=[{'index':i,'passage_id':str(i),'text':'x','input_sha256':digest(b'x'),'tokens':1,'reserved_tokens':9} for i in range(2)])
    auth=dict(plan_sha256=digest(plan),approved=True,expires_at=1000,requests=2,inputs=2,reserved_tokens=18)
    return plan,auth

def test_missing_authority_never_constructs(tmp_path):
    p,a=setup(tmp_path)
    with pytest.raises(ValueError): execute(tmp_path,p,None,adapter_factory=lambda:pytest.fail('constructed'),clock=lambda:1)
    assert not (tmp_path/'new').exists()

def test_success_resume_no_calls_and_tamper_rejected(tmp_path):
    p,a=setup(tmp_path); adapter=Adapter()
    execute(tmp_path,p,a,adapter_factory=lambda:adapter,clock=lambda:1)
    assert adapter.calls==2
    execute(tmp_path,p,a,adapter_factory=lambda:pytest.fail('resume constructed'),clock=lambda:1)
    f=tmp_path/'new/result-0000.json';f.write_text('{}')
    with pytest.raises(ValueError):execute(tmp_path,p,a,adapter_factory=lambda:pytest.fail('tamper constructed'),clock=lambda:1)

def test_ambiguous_attempt_never_retried(tmp_path):
    p,a=setup(tmp_path)
    class Broken(Adapter):
        def embed(self,*args,**kw):raise RuntimeError('secret body')
    with pytest.raises(ValueError,match='ATTEMPT_FAILED'):execute(tmp_path,p,a,adapter_factory=Broken,clock=lambda:1)
    assert 'secret body' not in ''.join(f.read_text() for f in (tmp_path/'new').glob('*.json'))
    with pytest.raises(ValueError,match='UNRESOLVED_ATTEMPT'):execute(tmp_path,p,a,adapter_factory=lambda:pytest.fail('retry'),clock=lambda:1)

@pytest.mark.parametrize('change',[{'requests':True},{'reserved_tokens':17},{'plan_sha256':'wrong'},{'expires_at':0}])
def test_authority_caps(tmp_path,change):
    p,a=setup(tmp_path);a.update(change)
    with pytest.raises(ValueError):execute(tmp_path,p,a,adapter_factory=lambda:pytest.fail('constructed'),clock=lambda:1)

def test_excess_server_usage_stops_next(tmp_path):
    p,a=setup(tmp_path)
    class Excess(Adapter):
        def embed(self,*args,**kw):
            r=super().embed(*args,**kw);r['server_usage_exceeds_reserve']=True;return r
    ad=Excess()
    with pytest.raises(ValueError,match='SERVER_USAGE_EXCEEDED'):execute(tmp_path,p,a,adapter_factory=lambda:ad,clock=lambda:1)
    assert ad.calls==1
    with pytest.raises(ValueError):execute(tmp_path,p,a,adapter_factory=lambda:pytest.fail('retry'),clock=lambda:1)

def test_input_drift_before_factory(tmp_path):
    p,a=setup(tmp_path);f=tmp_path/'input';f.write_bytes(b'old');p['closure']={'input':digest(b'old')};a['plan_sha256']=digest(p);f.write_bytes(b'new')
    with pytest.raises(ValueError,match='INPUT_DRIFT'):execute(tmp_path,p,a,adapter_factory=lambda:pytest.fail('constructed'),clock=lambda:1)

def test_intent_persistence_failure_blocks_embed(tmp_path,monkeypatch):
    import sbs.retrieval.embedding_execution as m
    p,a=setup(tmp_path);ad=Adapter();original=m.append
    def fail(path,value):
        if path.name.startswith('intent-'):raise OSError('fixture fsync')
        return original(path,value)
    monkeypatch.setattr(m,'append',fail)
    with pytest.raises(OSError):execute(tmp_path,p,a,adapter_factory=lambda:ad,clock=lambda:1)
    assert ad.calls==0

def test_invalid_vectors_terminal_not_retried(tmp_path):
    p,a=setup(tmp_path)
    class Bad(Adapter):
        def embed(self,*args,**kw):
            r=super().embed(*args,**kw);r['embeddings']=[[float('nan'),1.]];return r
    with pytest.raises(ValueError,match='ATTEMPT_FAILED'):execute(tmp_path,p,a,adapter_factory=Bad,clock=lambda:1)
    with pytest.raises(ValueError,match='UNRESOLVED_ATTEMPT'):execute(tmp_path,p,a,adapter_factory=lambda:pytest.fail('retry'),clock=lambda:1)

def test_expiry_after_factory_prevents_post(tmp_path):
    p,a=setup(tmp_path);now=[1];ad=Adapter()
    def factory():now[0]=1001;return ad
    with pytest.raises(ValueError,match='EXPIRED'):execute(tmp_path,p,a,adapter_factory=factory,clock=lambda:now[0])
    assert ad.calls==0

def test_metadata_auth_expiry_no_get(tmp_path,monkeypatch):
    import databricks.sdk
    import requests
    from types import SimpleNamespace
    from sbs.retrieval.embedding_execution import production_factory
    p,a=setup(tmp_path);p.update(profile='fixture',endpoint_gets_max_per_run=3);a['plan_sha256']=digest(p)
    now=[1]
    def authenticate():now[0]=1001;return {'Authorization':'fixture-never-persist'}
    monkeypatch.setattr(databricks.sdk,'WorkspaceClient',lambda **kw:SimpleNamespace(config=SimpleNamespace(host=p['host'],authenticate=authenticate)))
    monkeypatch.setattr(requests.Session,'get',lambda *args,**kw:pytest.fail('GET after expired auth'))
    with pytest.raises(ValueError,match='EXPIRED'):execute(tmp_path,p,a,adapter_factory=production_factory(tmp_path,p,a,clock=lambda:now[0]),clock=lambda:now[0])
    assert 'fixture-never-persist' not in ''.join(f.read_text() for f in (tmp_path/'new').glob('*.json'))

def test_frozen_real_preflight_offline():
    from sbs.retrieval.embedding_execution import prepare_plan
    root=Path(__file__).resolve().parents[2]
    p=prepare_plan(root,host='https://example.test')
    assert (p['inputs'],p['requests'],p['local_input_tokens'],p['reserved_tokens'])==(231,29,106278,108126)
    assert [len(b['items']) for b in p['batches']]==[8]*28+[7]
    assert all(r['text']==''.join(r['input_parts']) for b in p['batches'] for r in b['items'])

def test_real_transport_gate_after_auth_before_post(tmp_path,monkeypatch):
    import databricks.sdk
    import requests
    from types import SimpleNamespace
    import sbs.retrieval.embedding_execution as m
    # Real local tokenizer+adapter/SingleShotTransport; fake HTTP and SDK auth.
    root=Path(__file__).resolve().parents[2]
    plan=m.prepare_plan(root,host='https://example.test');plan['output']='out';plan['closure']={}
    auth=dict(approved=True,plan_sha256=digest(plan),expires_at=1000,requests=29,inputs=231,reserved_tokens=108126)
    now=[1];calls=[0]
    def authenticate():
        calls[0]+=1
        if calls[0]==2:now[0]=1001
        return {'Authorization':'fixture'}
    monkeypatch.setattr(databricks.sdk,'WorkspaceClient',lambda **kw:SimpleNamespace(config=SimpleNamespace(host=plan['host'],authenticate=authenticate)))
    class Response:
        status_code=200
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def iter_content(self,*args):
            import json
            yield json.dumps({'task':'llm/v1/embeddings','config':{'config_version':1,'served_entities':[{'foundation_model':{'name':'system.ai.qwen3-embedding-0-6b'}}]}}).encode()
    monkeypatch.setattr(requests.Session,'get',lambda *args,**kw:Response())
    monkeypatch.setattr(requests.Session,'post',lambda *args,**kw:pytest.fail('POST after auth deadline'))
    original=m.load_local
    monkeypatch.setattr(m,'load_local',lambda ignored:original(root))
    with pytest.raises(ValueError,match='ATTEMPT_FAILED'):
        execute(tmp_path,plan,auth,adapter_factory=m.production_factory(tmp_path,plan,auth,clock=lambda:now[0]),clock=lambda:now[0])
    assert calls[0]==2
    assert not (tmp_path/'out/vectors.json').exists()

# Resolution of independent E41-01/02; all transports remain fixtures.
def test_nonprefix_journal_rejected_before_factory(tmp_path):
    p,a=setup(tmp_path)
    execute(tmp_path,p,a,adapter_factory=Adapter,clock=lambda:1)
    for name in ('intent-0000.json','result-0000.json','vectors.json'):
        (tmp_path/'new'/name).unlink()
    with pytest.raises(ValueError,match='JOURNAL_NONPREFIX'):
        execute(tmp_path,p,a,adapter_factory=lambda:pytest.fail('gap constructed adapter'),clock=lambda:1)
    assert not (tmp_path/'new/intent-0000.json').exists()

def test_failure_diagnostics_allowlist(tmp_path):
    from sbs.retrieval.embedding_execution import unseal
    p,a=setup(tmp_path)
    class Failure(Adapter):
        last_attempt={'stage':'transport','http_status':403,'error_code':'PERMISSION_DENIED',
                      'calls_attempted':1,'reserved_tokens':9,'expected_response_model':'response',
                      'response_model':'response','usage':{'prompt_tokens':1,'total_tokens':2,'secret':'secret-value'},
                      'headers':{'Authorization':'secret-value'},'body':'secret-value'}
        def embed(self,*args,**kw):raise RuntimeError('secret-value')
    with pytest.raises(ValueError,match='ATTEMPT_FAILED'):
        execute(tmp_path,p,a,adapter_factory=Failure,clock=lambda:1)
    raw=(tmp_path/'new/result-0000.json').read_text();diag=unseal(tmp_path/'new/result-0000.json')['diagnostics']
    assert diag=={'stage':'transport','http_status':403,'error_code':'PERMISSION_DENIED','calls_attempted':1,'reserved_tokens':9,'expected_response_model':'response','response_model':'response','usage':{'prompt_tokens':1,'total_tokens':2}}
    assert 'secret-value' not in raw and 'Authorization' not in raw

@pytest.mark.parametrize('bad',[True,1.0,-1,'secret-value',None,{},[403]])
def test_failure_diagnostics_invalid_types_do_not_leak(tmp_path,bad):
    from sbs.retrieval.embedding_execution import unseal
    p,a=setup(tmp_path)
    class Failure(Adapter):
        last_attempt={'http_status':bad,'calls_attempted':bad,'reserved_tokens':bad,
                      'stage':'secret-value','error_code':'secret-value','response_model':'secret-value',
                      'usage':{'prompt_tokens':bad,'total_tokens':bad,'secret':'secret-value'}}
        def embed(self,*args,**kw):raise RuntimeError('secret-value')
    with pytest.raises(ValueError,match='ATTEMPT_FAILED'):execute(tmp_path,p,a,adapter_factory=Failure,clock=lambda:1)
    diag=unseal(tmp_path/'new/result-0000.json')['diagnostics']
    assert 'http_status' not in diag and 'calls_attempted' not in diag and 'reserved_tokens' not in diag
    assert 'secret-value' not in str(diag)
    assert diag.get('usage',{})=={}
