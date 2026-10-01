from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sbs.webapp import create_app

class Service:
    def __init__(self,tmp): self.tmp=tmp; self.calls=[]
    def catalog(self): return {'families':[{'id':'a','label':'A'},{'id':'b','label':'B'}], 'pairs':[{'id':'p','family_id':'a','title':'Par A','provisions':[{'id':'art','label':'Artículo'}]},{'id':'q','family_id':'b','title':'Par B','provisions':[{'id':'artb','label':'Artículo B'}]}]}
    def comparison(self,pair_id,provision_id=None): return {'pair_id':pair_id,'provision_id':provision_id,'before':{'text':'<script>alert(1)</script>'},'after':{'text':'Texto'}}
    def ask(self,session_id,question,pair_id,provision_id=None,cross_family=False): self.calls.append((session_id,question,pair_id,provision_id,cross_family)); return {'answer':'<img src=x onerror=alert(1)>','status':'unreviewed'}
    def source(self,source_id):
        if source_id!='doc': raise KeyError(source_id)
        return self.tmp

@pytest.fixture
def setup(tmp_path):
    path=tmp_path/'source.pdf'; path.write_bytes(b'%PDF-test'); service=Service(path)
    return TestClient(create_app(service)),service

def payload(**kw): return dict(question='Qué cambió',pair_id='p',provision_id='art',cross_family=False,**kw)
def test_catalog_cookie_and_mutation_protection(setup):
    c,s=setup; r=c.get('/api/catalog'); token=r.json()['csrf_token']
    assert 'httponly' in r.headers['set-cookie'].lower() and 'samesite=strict' in r.headers['set-cookie'].lower()
    assert c.post('/api/ask',json=payload()).status_code==403
    assert c.post('/api/ask',headers={'X-CSRF-Token':token},json=payload(actor_role='expert')).status_code==422
    assert c.post('/api/ask',headers={'X-CSRF-Token':token},json=payload()).status_code==200
    assert len(s.calls)==1

def test_selection_context_and_isolation(setup):
    c,s=setup; token=c.get('/api/catalog').json()['csrf_token']
    for pair,article in [('p','art'),('q','artb')]:
        r=c.post('/api/ask',headers={'X-CSRF-Token':token},json={'question':'hola','pair_id':pair,'provision_id':article})
        assert r.status_code==200
    assert s.calls[0][0]==s.calls[1][0] and s.calls[1][2]=='q' and s.calls[1][3]=='artb'
    other=TestClient(c.app); tok=other.get('/api/catalog').json()['csrf_token']; other.post('/api/ask',headers={'X-CSRF-Token':tok},json=payload())
    assert s.calls[-1][0]!=s.calls[0][0]
    assert c.get('/api/comparison',params={'pair_id':'q','provision_id':'art'}).status_code==404

def test_source_mapping_and_untrusted_content(setup):
    c,s=setup
    assert c.get('/api/sources/doc').content==b'%PDF-test'
    assert c.get('/api/sources/%2e%2e%2fetc%2fpasswd').status_code==404
    assert c.get('/api/sources/unknown').status_code==404
    r=c.get('/api/comparison',params={'pair_id':'p','provision_id':'art'})
    assert r.headers['content-type'].startswith('application/json')
    assert r.json()['before']['text']=='<script>alert(1)</script>'
    assert "default-src 'self'" in c.get('/').headers['content-security-policy']

def test_cloud_fails_closed(setup):
    with pytest.raises(ValueError): create_app(setup[1],mode='cloud')

def test_missing_selection_and_blank_question(setup):
    c,s=setup; token=c.get('/api/catalog').json()['csrf_token']; headers={'X-CSRF-Token':token}
    assert c.post('/api/ask',headers=headers,json={'question':'x','pair_id':'nonexistent'}).status_code==404
    assert c.post('/api/ask',headers=headers,json={'question':'  ','pair_id':'p','provision_id':'art'}).status_code==422
    assert not s.calls

def test_failure_is_explicit_and_no_invented_answer(setup):
    c,s=setup
    def failure(*args,**kwargs): raise RuntimeError('sensitive internal config')
    s.ask=failure
    client=TestClient(c.app,raise_server_exceptions=False)
    token=client.get('/api/catalog').json()['csrf_token']
    response=client.post('/api/ask',headers={'X-CSRF-Token':token},json=payload())
    assert response.status_code==503
    assert 'answer' not in response.json() and 'sensitive' not in response.text

def test_unknown_source_cannot_request_redirect(setup):
    c,s=setup; s.source=lambda sid:{'url':'javascript:alert(1)'}
    assert c.get('/api/sources/doc').status_code==404


def test_missing_provision_cannot_silently_select_first(setup):
    c,s=setup; token=c.get('/api/catalog').json()['csrf_token']
    assert c.get('/api/comparison',params={'pair_id':'p'}).status_code==404
    assert c.post('/api/ask',headers={'X-CSRF-Token':token},json={'question':'Explica','pair_id':'p'}).status_code==404
    assert not s.calls
