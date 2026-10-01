"""SK07 server-only assembly; fixture transports never establish cloud acceptance."""
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from sbs.genie.server import GenieTransport, load_server_binding, RemoteEvidence, ServerPermissionProbe

ROOT=Path(__file__).resolve().parents[2]

def test_pending_project_configuration_never_constructs_sdk():
    def forbidden():raise AssertionError('SDK created before configuration')
    b=load_server_binding(ROOT,mode='cloud',client_factory=forbidden)
    assert b.readiness()['available'] is False
    assert 'space_id_pending' in b.readiness()['reasons']

class Response:
    status_code=200
    def json(self):return {'conversation_id':'c1','message_id':'m1'}
class Session:
    def __init__(self):self.calls=[];self.closed=False
    def mount(self,*a):pass
    def request(self,*a,**kw):self.calls.append((a,kw));return Response()
    def close(self):self.closed=True

def config():return SimpleNamespace(host='https://example.cloud.databricks.com',workspace_id=None,authenticate=lambda:{'Authorization':'fixture'})

def test_genie_transport_single_post_no_redirect_and_no_unbounded_wait():
    s=Session();t=GenieTransport(config(),space_id='space1',session_factory=lambda:s)
    assert t.do('POST','/api/2.0/genie/spaces/space1/start-conversation',body={'content':'pregunta'})['message_id']=='m1'
    assert len(s.calls)==1 and s.calls[0][1]['allow_redirects'] is False and s.closed

@pytest.mark.parametrize('method,path,body',[
 ('POST','/api/2.0/genie/spaces/other/start-conversation',{'content':'x'}),
 ('DELETE','/api/2.0/genie/spaces/space1',None),
 ('POST','/api/2.0/genie/spaces/space1/start-conversation',{'content':'x','role':'admin'}),
 ('GET','/api/2.0/genie/spaces/space1/conversations/../messages/m',None)])
def test_transport_rejects_out_of_scope_before_network(method,path,body):
    def forbidden():raise AssertionError('network')
    with pytest.raises(ValueError):GenieTransport(config(),space_id='space1',session_factory=forbidden).do(method,path,body=body)

def test_transport_error_hides_remote_body_and_does_not_retry():
    s=Session()
    class Error(Response):
        status_code=403
        def json(self):raise AssertionError('Error body not needed')
    def request(*a,**kw):s.calls.append((a,kw));return Error()
    s.request=request
    with pytest.raises(PermissionError):GenieTransport(config(),space_id='space1',session_factory=lambda:s).do('POST','/api/2.0/genie/spaces/space1/start-conversation',body={'content':'x'})
    assert len(s.calls)==1

def test_remote_evidence_bounds_stream_and_preserves_missing_vs_denied():
    import io
    class Files:
        def download(self,path):return SimpleNamespace(contents=io.BytesIO(b'x'*12))
    store=RemoteEvidence(Files(),'/Volumes/c/sbs_radar/v/registry',max_bytes=10)
    with pytest.raises(ValueError,match='EVIDENCE_BYTES_EXCEEDED'):store.read('a.json')
    with pytest.raises(ValueError):store.read('../a.json')

def test_permission_probe_does_not_promote_view_to_query_permission():
    collector=SimpleNamespace(collect=lambda **kw:{'subject':{'principals':['app-id']}})
    client=SimpleNamespace(warehouses=SimpleNamespace(get=lambda wid:SimpleNamespace(as_dict=lambda:{'id':wid,'state':'RUNNING','warehouse_type':'PRO'})),
      genie=SimpleNamespace(get_space=lambda sid:SimpleNamespace(as_dict=lambda:{'space_id':sid,'warehouse_id':'wh'})),
      permissions=SimpleNamespace(get=lambda *a:SimpleNamespace(as_dict=lambda:{'object_id':'/genie/987','object_type':'genie','access_control_list':[{'service_principal_name':'app-id','all_permissions':[{'permission_level':'CAN_VIEW'}]}]})))
    p=ServerPermissionProbe(client,collector,executor_id=1,warehouse_id='wh',space_id='space',snapshot='a'*64,tables=['c.sbs_radar.provisions'],expected_acl_object_id='/genie/987')
    assert p()['genie_access'] is False

def enabled_inputs(tmp_path):
    import hashlib
    from test_genie_delta_runtime import setup_delta
    binding,*rest=setup_delta(tmp_path);deps=rest[-1]
    cert=deps.delta_publication.certificate
    (tmp_path/'config/cert.json').write_bytes(cert.payload)
    policy=dict(policy_id='test-policy',namespace='fixture.sbs_radar',trusted_administrators=['fixture-owner'],maintenance_assumption='TEST ONLY',abac_assumption='TEST ONLY',issued_at_ms=1,expires_at_ms=9999999999999,observation_ttl_ms=60000)
    runtime_path=tmp_path/'config/genie-pilot-002.json';r=json.loads(runtime_path.read_text());policy['namespace']=r['table_prefix']
    pp=tmp_path/'config/policy.json';pp.write_text(json.dumps(policy))
    c=dict(version=1,enabled=True,genie_acl_object_id='/genie/987',workspace_host='https://example.cloud.databricks.com',executor_id=1,client_id='app-id',runtime_config_path='config/genie-pilot-002.json',runtime_config_sha256=hashlib.sha256(runtime_path.read_bytes()).hexdigest(),certificate_path='config/cert.json',certificate_sha256=cert.sha256,policy_path='config/policy.json',policy_sha256=hashlib.sha256(pp.read_bytes()).hexdigest(),evidence_prefix='/Volumes/'+r['catalog']+'/sbs_radar/v/registry')
    (tmp_path/'config/genie-server.json').write_text(json.dumps(c));return c,binding

def fake_client(c):
    def forbidden(*a,**k):raise AssertionError('Construction made a remote call')
    api=SimpleNamespace(get=forbidden,get_effective=forbidden,get_permissions=forbidden,download=forbidden)
    return SimpleNamespace(config=SimpleNamespace(host=c['workspace_host'],auth_type='oauth-m2m',client_id=c['client_id'],workspace_id=None),files=api,service_principals=api,groups=api,tables=api,catalogs=api,schemas=api,grants=api,warehouses=api,query_history=api)

def test_enabled_factory_builds_real_adapters_without_remote_calls(tmp_path):
    c,prior=enabled_inputs(tmp_path);client=fake_client(c)
    b=load_server_binding(tmp_path,mode='cloud',client_factory=lambda:client)
    assert b.readiness()['available'] is True and b.readiness()['remote_verified'] is False
    assert b.rag_snapshot==prior.rag_snapshot and b.genie_snapshot==prior.genie_snapshot
    assert b._dependencies.delta_publication.assurance_profile=='trusted_admin_observed_v1'

@pytest.mark.parametrize('change',[{'auth_type':'pat'},{'client_id':'other-app'},{'host':'https://other.cloud.databricks.com'}])
def test_enabled_factory_rejects_wrong_backend_identity(tmp_path,change):
    c,_=enabled_inputs(tmp_path);client=fake_client(c)
    for k,v in change.items():setattr(client.config,k,v)
    with pytest.raises(ValueError,match='APP_BACKEND_IDENTITY_MISMATCH'):load_server_binding(tmp_path,mode='cloud',client_factory=lambda:client)

def test_missing_resources_and_mutated_pins_reject_before_sdk(tmp_path):
    c,_=enabled_inputs(tmp_path)
    def forbidden():raise AssertionError('SDK must remain unavailable')
    with pytest.raises(ValueError,match='GENIE_CLOUD_BACKEND_REQUIRES_CLOUD_MODE'):load_server_binding(tmp_path,mode='local',client_factory=forbidden)
    (tmp_path/c['policy_path']).write_text('{}')
    with pytest.raises(ValueError,match='SERVER_FILE_PIN_MISMATCH'):load_server_binding(tmp_path,mode='cloud',client_factory=forbidden)

def test_app_runtime_uses_server_factory_with_mode(monkeypatch):
    import sbs.runtime as app
    import sbs.genie.server as server
    service=app.create_service();calls=[]
    fake=SimpleNamespace(rag_snapshot=service.snapshot)
    monkeypatch.setattr(server,'load_server_binding',lambda root,**kw:(calls.append((root,kw)) or fake))
    assert service.initialize_genie() is fake
    assert calls==[(app.ROOT,{'mode':'local'})]

def test_installed_genie_sdk_serializes_through_single_shot_transport():
    from databricks.sdk.service.dashboards import GenieAPI
    s=Session();transport=GenieTransport(config(),space_id='space1',session_factory=lambda:s)
    waiter=GenieAPI(transport).start_conversation('space1','fixture question')
    assert waiter.response.conversation_id=='c1' and waiter.response.message_id=='m1'
    assert len(s.calls)==1  # Never wait.result() here.
    assert s.calls[0][1]['json']=={'content':'fixture question'}

def test_remote_tombstone_denial_is_not_absence():
    class Denied(Exception):error_code='PERMISSION_DENIED'
    class Files:
        def download(self,path):raise Denied('fixture sensitive message')
    with pytest.raises(ValueError,match='REMOTE_EVIDENCE_UNAVAILABLE'):
        RemoteEvidence(Files(),'/Volumes/c/sbs_radar/v/registry').read('a.revoked.json',optional=True)

def test_explicitly_disabled_factory_stays_offline(tmp_path):
    c,_=enabled_inputs(tmp_path);c['enabled']=False
    (tmp_path/'config/genie-server.json').write_text(json.dumps(c))
    def forbidden():raise AssertionError('SDK creation')
    b=load_server_binding(tmp_path,mode='cloud',client_factory=forbidden)
    assert b.readiness()['available'] is False

def test_host_is_validated_before_client_creation(tmp_path):
    c,_=enabled_inputs(tmp_path);c['workspace_host']='http://example.invalid'
    (tmp_path/'config/genie-server.json').write_text(json.dumps(c));calls=[]
    def factory():calls.append(True);return fake_client(c)
    with pytest.raises(ValueError):load_server_binding(tmp_path,mode='cloud',client_factory=factory)
    assert calls==[]

def test_concurrent_quota_reserves_before_session_creation():
    import threading,time
    from concurrent.futures import ThreadPoolExecutor
    entered=threading.Event();release=threading.Event();sessions=[]
    def factory():
        entered.set();release.wait(timeout=.5);s=Session();sessions.append(s);return s
    t=GenieTransport(config(),space_id='s',max_calls=1,session_factory=factory)
    def call():
        try:return t.do('POST','/api/2.0/genie/spaces/s/start-conversation',body={'content':'x'})
        except ValueError:return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        first=pool.submit(call);assert entered.wait(1);second=pool.submit(call);time.sleep(.03);release.set();first.result();second.result()
    assert t.calls==1 and sum(len(s.calls) for s in sessions)==1

def test_executor_scim_application_is_bound_to_oauth_client(tmp_path):
    c,_=enabled_inputs(tmp_path);client=fake_client(c)
    client.service_principals=SimpleNamespace(get=lambda sid:dict(id=sid,active=True,applicationId='other-client',groups=[],roles=[]))
    b=load_server_binding(tmp_path,mode='cloud',client_factory=lambda:client)
    with pytest.raises(ValueError,match='APP_EXECUTOR_CLIENT_MISMATCH'):
        b._dependencies.permission_probe.collector.subject_resolver(executor_id=c['executor_id'])

def test_remote_registry_roundtrip_uses_canonical_temporary_root(tmp_path):
    import io
    from test_publication_registry import fixture
    from sbs.genie.publication_registry import RegistryAdmin
    builder,cert,*_=fixture();entry=builder.build(cert);key=RegistryAdmin(tmp_path/'registry',administrator='FIXTURE').publish(entry)
    raw=(tmp_path/'registry'/(key+'.json')).read_bytes()
    class Missing(Exception):error_code='NOT_FOUND'
    class Files:
        def download(self,path):
            if path.endswith('.revoked.json'):raise Missing()
            return SimpleNamespace(contents=io.BytesIO(raw))
    assert RemoteEvidence(Files(),'/Volumes/c/sbs_radar/v/registry').registry(certificate_sha256=key)['certificate_sha256']==key

def test_acl_object_binding_uses_observed_id_not_derived_space_id():
    collector=SimpleNamespace(collect=lambda **kw:{'subject':{'principals':['app-id']}})
    acl=dict(object_id='/genie/987',object_type='genie',access_control_list=[dict(service_principal_name='app-id',all_permissions=[dict(permission_level='CAN_RUN')])])
    client=SimpleNamespace(warehouses=SimpleNamespace(get=lambda wid:dict(id=wid,state='RUNNING',warehouse_type='PRO')),genie=SimpleNamespace(get_space=lambda sid:dict(space_id=sid,warehouse_id='wh')),permissions=SimpleNamespace(get=lambda *a:acl))
    probe=ServerPermissionProbe(client,collector,executor_id=1,warehouse_id='wh',space_id='opaque-space-uuid',snapshot='a'*64,tables=['c.sbs_radar.provisions'],expected_acl_object_id='/genie/987')
    assert probe()['genie_access'] is True
    acl['object_id']='/genie/another'
    with pytest.raises(ValueError,match='GENIE_ACL_IDENTITY_CHANGED'):probe()

@pytest.mark.parametrize('version',[True,1.0])
def test_server_version_is_exact_integer_before_sdk(tmp_path,version):
    c,_=enabled_inputs(tmp_path);c['version']=version
    (tmp_path/'config/genie-server.json').write_text(json.dumps(c))
    def forbidden():raise AssertionError('invalid config reached credentials')
    with pytest.raises(ValueError,match='SERVER_CONFIGURATION_INVALID'):load_server_binding(tmp_path,mode='cloud',client_factory=forbidden)
