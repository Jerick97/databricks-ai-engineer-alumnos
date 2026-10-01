from fastapi.testclient import TestClient
import pytest
from sbs.webapp import create_app
from sbs.runtime import create_service
from sbs.guardrails.identity import DatabricksUserIdentity

ORIGIN='https://sbs-radar-pilot.example.test'
@pytest.fixture(scope='module')
def service():return create_service(mode='cloud')

def identity():
    return DatabricksUserIdentity({'principals':{'one':{'role':'reader','families':['cybersecurity']},'two':{'role':'reader','families':['market_conduct']}}},lambda t:{'id':t,'active':True})

def client(service):return TestClient(create_app(service,mode='cloud',identity_adapter=identity(),public_origin=ORIGIN),base_url=ORIGIN)

def test_cloud_requires_complete_backend_identity_configuration(service):
    with pytest.raises(ValueError):create_app(service,mode='cloud')
    with pytest.raises(ValueError):create_app(service,mode='cloud',identity_adapter=identity(),public_origin='http://bad.test')

def test_cloud_auth_scope_sources_and_revocation(service):
    c=client(service)
    assert c.get('/api/catalog').status_code==401
    r=c.get('/api/catalog',headers={'x-forwarded-access-token':'one'})
    assert r.status_code==200 and 'Secure' in r.headers['set-cookie']
    assert [p['id'] for p in r.json()['pairs']]==['cyber-504']
    assert c.get('/api/comparison?pair_id=market-3274&provision_id=art27',headers={'x-forwarded-access-token':'one'}).status_code==404
    src=service.entry('market-3274','art27')['before']['version_id']
    assert c.get('/api/sources/'+src,headers={'x-forwarded-access-token':'one'}).status_code==403
    assert c.get('/api/catalog',headers={'x-forwarded-access-token':'revoked'}).status_code==401

def test_subject_switch_rotates_session_and_rejects_csrf_and_cross_origin(service):
    c=client(service)
    a=c.get('/api/catalog',headers={'x-forwarded-access-token':'one'}).json();old_cookie=c.cookies.get('sbs_session')
    b=c.get('/api/catalog',headers={'x-forwarded-access-token':'two'}).json()
    assert old_cookie!=c.cookies.get('sbs_session') and a['csrf_token']!=b['csrf_token']
    body={'pair_id':'market-3274','provision_id':'art27','question':'antes'}
    assert c.post('/api/ask',json=body,headers={'x-forwarded-access-token':'two','x-csrf-token':a['csrf_token']}).status_code==403
    assert c.post('/api/ask',json=body,headers={'x-forwarded-access-token':'two','x-csrf-token':b['csrf_token'],'origin':'https://evil.test'}).status_code==403
    assert service.generator is None

def test_cloud_cannot_bind_personal_profile_local_runtime():
    with pytest.raises(ValueError,match='cloud'):
        create_app(create_service(),mode='cloud',identity_adapter=identity(),public_origin=ORIGIN)
