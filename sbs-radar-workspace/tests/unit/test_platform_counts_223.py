"""223 offline contracts; authentic App M2M and Genie E2E remain separate."""
import os,json,shutil,subprocess,sys
from pathlib import Path
from types import SimpleNamespace
from copy import deepcopy
import pytest
ROOT=Path(__file__).resolve().parents[2]
INNER=os.environ.get('SBS_TEST_OVERLAY223')=='1'
only=pytest.mark.skipif(not INNER,reason='isolated223 overlay')

def test_isolated_overlay223(tmp_path):
    if INNER:pytest.skip('outer launcher')
    shutil.copytree(ROOT/'contracts',tmp_path/'contracts');(tmp_path/'config').mkdir();shutil.copy2(ROOT/'config/permissions.json',tmp_path/'config/permissions.json')
    shutil.copytree(ROOT/'src',tmp_path/'src');shutil.copytree(ROOT/'runs/sk06-platform-counts-223-overlay/source/src',tmp_path/'src',dirs_exist_ok=True)
    files=[str(Path(__file__).resolve()),str(ROOT/'tests/unit/test_immutable_snapshot_221.py'),str(ROOT/'tests/unit/test_genie_governance.py'),str(ROOT/'tests/unit/test_genie_delta_runtime.py'),str(ROOT/'tests/unit/test_publication_rotation_078.py')]
    r=subprocess.run([sys.executable,'-m','pytest',*files,'-q','-o','pythonpath='+str(tmp_path/'src'),'-k','not isolated_overlay'],cwd=ROOT,
        env={**os.environ,'SBS_TEST_OVERLAY223':'1','SBS_TEST_OVERLAY221':'1','PYTHONPATH':str(tmp_path/'src')+os.pathsep+str(ROOT/'tests/unit')},capture_output=True,text=True,timeout=120)
    print(r.stdout);assert r.returncode==0,r.stdout+r.stderr


def fixture():
    from sbs.genie.platform_counts import PlatformReads,PlatformCountProbe,PlatformPermissionProbe
    from sbs.genie.governance import StandingAdminPolicy
    state={'time':100,'status':'active','calls':[]}
    tables=['catalog.sbs_radar.documents','catalog.sbs_radar.provisions']
    values={'me':{'id':'17','active':True},'warehouse':{'id':'w','warehouse_type':'PRO','state':'STOPPED'},'space':{'space_id':'s','warehouse_id':'w'},'history':{'res':[]}}
    for table in tables:values['table:'+table]={'full_name':table,'table_id':'uc-'+table,'metastore_id':'meta','storage_location':'s3://'+table,'table_type':'MANAGED','data_source_format':'DELTA','columns':[{'name':'id'}]}
    class Reads(PlatformReads):
        def get(self,op,table=None):
            assert self.calls<self.max_calls;self.calls+=1;state['calls'].append((op,table))
            v=values[op+(':'+table if table else '')]
            if isinstance(v,Exception):raise v
            return deepcopy(v)
    reads=Reads(SimpleNamespace(),executor_id=17,warehouse_id='w',space_id='s',tables=tables,prefix='/Volumes/c/sbs_radar/v/registry',generation='a'*64,binding='b'*64)
    policy=StandingAdminPolicy('p','catalog.sbs_radar',('owner',),'trusted maintenance','ABAC not observed',0,60000,lambda **k:state['status'])
    p=PlatformCountProbe(reads,policy,clock=lambda:state['time']);kw=dict(source_tables=[tables[0]],executor_id=17,warehouse_id='w',space_id='s',started_at_ms=100,ended_at_ms=100)
    return state,values,reads,p,kw

@only
def test_no_privileged_enumeration_and_honest_assurance():
    state,values,reads,p,kw=fixture();session=p.new_session();a=session(**kw)
    state['time']=200;b=session(**{**kw,'started_at_ms':120,'ended_at_ms':180})
    assert [op for op,t in state['calls']]==['me','table','me','table']
    assert b['read_only_basis']=='genie_product_contract' and b['principal_select_only']=='not_observed'
    assert b['effective_privileges_enumerated'] is False and 'backend_select_only' not in b
    assert b['identity_continuity']=='not_proven' and b['aba_prevented'] is False

@only
@pytest.mark.parametrize('bad',[{}, {'id':'18'},{'id':17},{'id':'017'},{'id':'17','active':False},{'id':'17','active':None},{'id':'17','active':1},PermissionError('secret')])
def test_me_mismatch_denied_or_malformed_rejects(bad):
    state,values,reads,p,kw=fixture();values['me']=bad
    with pytest.raises((ValueError,PermissionError)):p.new_session()(**kw)
    assert all(op!='table' for op,t in state['calls'])

@only
def test_active_absent_is_not_invented():
    state,values,reads,p,kw=fixture();values['me']={'id':'17'}
    assert p.new_session()(**kw)['observation']['caller']['active_observed'] is None

@only
@pytest.mark.parametrize('change',['identity','table','filter','mask','revoke','ttl','future','actor'])
def test_current_proof_required_after_execution(change):
    state,values,reads,p,kw=fixture();s=p.new_session();s(**kw);state['time']=200
    call={**kw,'started_at_ms':120,'ended_at_ms':180}
    if change=='identity':values['me']['id']='18'
    elif change=='table':values['table:'+kw['source_tables'][0]]['table_id']='changed'
    elif change=='filter':values['table:'+kw['source_tables'][0]]['row_filter']={'function_name':'x'}
    elif change=='mask':values['table:'+kw['source_tables'][0]]['columns'][0]['mask']={'function_name':'x'}
    elif change=='revoke':state['status']='revoked'
    elif change=='ttl':state['time']=60101
    elif change=='future':call['ended_at_ms']=201
    else:call['executor_id']=18
    with pytest.raises(ValueError):s(**call)

@only
@pytest.mark.parametrize('state_name',['RUNNING','STOPPED','STARTING'])
def test_stopped_warehouse_allows_only_platform_attempt(state_name):
    from sbs.genie.platform_counts import PlatformPermissionProbe
    from sbs.genie import GenieAdapter
    state,values,reads,p,kw=fixture();values['warehouse']['state']=state_name
    cfg={'namespace':'sbs_radar','warehouse_id':'w','space_id':'s','snapshot':'snapshot'}
    a=GenieAdapter(None,cfg,PlatformPermissionProbe(reads,snapshot='snapshot'))
    assert a.preflight() is None
    assert [op for op,t in state['calls']]==['warehouse','space']

@only
@pytest.mark.parametrize('denied',[False,True])
@pytest.mark.parametrize('history',[{'res':[]},{'has_next_page':False}])
def test_diagnostic_exactly_eight_gets_all_layers_even_first_denial(denied,history):
    from sbs.genie.platform_counts import diagnose,PlatformCountProbe
    from test_immutable_snapshot_221 import historical_fixture
    reader,data,now,e,op,_,_,_=historical_fixture()
    state,values,reads,p,kw=fixture();reads.max_calls=8
    # Diagnostic metadata data bindings are separately verified; historical219 is genuine.
    values['status']=data[reader.binding+'.status.json'];values['generation']=data[reader.pin+'.json']
    values['history']=history
    if denied:values['me']=PermissionError('secret sentinel')
    result=diagnose(reads,reader,p)
    assert reads.calls==8 and len(state['calls'])==8 and len(result['operations'])==8
    assert result['status']==('capabilities_incomplete' if denied else 'capabilities_observed')
    assert result['genie_posts']==result['sql_statements']==0
    assert result['query_history_evidence']=='endpoint_response_only_not_future_query_proof'
    assert 'secret sentinel' not in json.dumps(result)

@only
def test_transport_eight_attempts_no_redirect_retry_or_extra_resource():
    from sbs.genie.platform_counts import PlatformReads
    calls=[];secrets='DO_NOT_LOG_BEARER'
    class Response:
        status_code=403
        def iter_content(self,n):yield b'{}'
    class Session:
        def mount(self,*a):pass
        def request(self,*a,**kw):calls.append((a,kw));return Response()
        def close(self):pass
    cfg=SimpleNamespace(host='https://fixed.example',authenticate=lambda:{'Authorization':secrets})
    r=PlatformReads(cfg,executor_id=17,warehouse_id='w',space_id='s',tables=['c.sbs_radar.documents','c.sbs_radar.provisions'],prefix='/Volumes/c/sbs_radar/v/registry',generation='a'*64,binding='b'*64,max_calls=8,session_factory=Session)
    for _ in range(8):
        with pytest.raises(PermissionError,match='^PLATFORM_GET_DENIED$'):r.get('me')
    with pytest.raises(ValueError,match='CAP'):r.get('me')
    with pytest.raises(ValueError):r.get('table','foreign.table')
    assert len(calls)==8 and all(x[0][0]=='GET' and x[1]['allow_redirects'] is False for x in calls)

@only
def test_scope_typed_before_snapshot_conflict():
    from sbs.conversation import Conversation,Session,Tool
    import inspect
    # Source-order regression supplements actual branch test in existing runtime tests.
    source=inspect.getsource(Conversation.ask)
    assert source.index("status=='scope_not_answered'")<source.index("status=='conflict'")

@only
def test_explicit_polling_configuration_and_deadline():
    from sbs.genie.server import GenieTransport
    cfg=json.loads((ROOT/'runs/sk06-platform-counts-223-overlay/source/config/genie-runtime-068.json').read_bytes())
    assert cfg['max_polls']==23 and cfg['poll_seconds']==2
    t=GenieTransport(SimpleNamespace(host='https://dbc-0410b264-20c7.cloud.databricks.com'),space_id='s',max_seconds=45)
    t.deadline=0
    with pytest.raises(TimeoutError):t.do('GET','/api/2.0/genie/spaces/s/conversations/c/messages/m')
    assert t.calls==1

@only
def test_administrative_diagnostic_identity_csrf_and_closed_body():
    from fastapi.testclient import TestClient
    from sbs.webapp import create_app
    class Service:
        mode='cloud'
        calls=0
        def for_actor(self,actor):return self
        def catalog(self):return {'pairs':[]}
        def initialize_genie(self):return self
        def check_capabilities(self):self.calls+=1;return {'get_attempts':8,'genie_posts':0}
    service=Service();identity=SimpleNamespace(authenticate=lambda h:{'subject':'76826984571984'})
    app=create_app(service,mode='cloud',identity_adapter=identity,public_origin='https://testserver')
    with TestClient(app,base_url='https://testserver') as client:
        csrf=client.get('/api/catalog').json()['csrf_token']
        assert client.post('/api/genie/capabilities',json={}).status_code==403
        headers={'x-csrf-token':csrf,'origin':'https://testserver'}
        assert client.post('/api/genie/capabilities',json={'path':'/secret'},headers=headers).status_code==400
        assert client.post('/api/genie/capabilities?table=other',json={},headers=headers).status_code==400
        assert service.calls==0
        response=client.post('/api/genie/capabilities',json={},headers=headers)
        assert response.status_code==200 and response.json()=={'get_attempts':8,'genie_posts':0} and service.calls==1
        identity.authenticate=lambda h:{'subject':'other-verified-user'}
        new=client.get('/api/catalog').json()['csrf_token'];headers['x-csrf-token']=new
        assert client.post('/api/genie/capabilities',json={},headers=headers).status_code==403
        assert service.calls==1

@only
def test_platform_delta_capability_checks_real_historical_proof_and_metadata():
    from sbs.genie.delta import DeltaPublication
    from sbs.genie.platform_counts import PROFILE,PlatformCountProbe
    from sbs.genie.publication import NAMED_IDENTITY_PROFILE
    from test_immutable_snapshot_221 import historical_fixture
    reader,data,now,e,op,_,_,_=historical_fixture();selected=reader.select()
    state,values,reads,p,kw=fixture();t=selected.certificate.as_dict()['tables'][0]
    # Only the collector transport is a local double. The219 registry and proof remain unchanged.
    reads.tables=(t['full_name'],);p.policy=__import__('dataclasses').replace(p.policy,namespace=t['full_name'].rsplit('.',1)[0])
    values['table:'+t['full_name']]={'full_name':t['full_name'],'table_id':t['uc_table_id'],'metastore_id':t['metastore_id'],'storage_location':'fixture-location','table_type':'MANAGED','data_source_format':'DELTA','columns':[{'name':'id'}]}
    original=p.table
    def mapped(value,name):return {**original(value,name),'location_sha256':t['location_sha256']}
    p.table=mapped
    cap=DeltaPublication(selected.certificate,selected.certificate.sha256,e['registry']['mapping_sha256'],selected.registry,p,
        assurance_profile=PROFILE,certificate_identity_profile=NAMED_IDENTITY_PROFILE,evidence_temporality='historical')
    # The real class's per-request session is isolated and type checked.
    assert isinstance(cap.for_request().identity_access_probe,PlatformCountProbe)
    p._session=True;state['time']=now[0]
    kw.update(source_tables=[t['full_name']],started_at_ms=now[0],ended_at_ms=now[0])
    result=cap.verify(**kw)
    assert result['publication_evidence_temporality']=='historical' and result['assurance_profile']==PROFILE
    assert result['access_assurance']['principal_select_only']=='not_observed'
    state['time']+=100
    cap.verify(**{**kw,'started_at_ms':now[0]+1,'ended_at_ms':now[0]+99})
    values['table:'+t['full_name']]['table_id']='replaced'
    with pytest.raises(ValueError):cap.verify(**{**kw,'started_at_ms':now[0]+1,'ended_at_ms':now[0]+99})

@only
def test_query_history_wire_uses_sdk_dot_notation():
    from sbs.genie.platform_counts import PlatformReads
    calls=[]
    class Response:
        status_code=200
        def iter_content(self,n):yield b'{"has_next_page":false}'
    class Session:
        def mount(self,*a):pass
        def request(self,*a,**kw):calls.append((a,kw));return Response()
        def close(self):pass
    cfg=SimpleNamespace(host='https://fixed.example',authenticate=lambda:{})
    r=PlatformReads(cfg,executor_id=17,warehouse_id='w',space_id='s',tables=[],prefix='p',generation='a'*64,binding='b'*64,session_factory=Session)
    assert r.get('history')=={'has_next_page':False}
    query=calls[0][1]['params']
    assert set(query)=={'filter_by.user_ids','filter_by.warehouse_ids','filter_by.query_start_time_range.start_time_ms','filter_by.query_start_time_range.end_time_ms','max_results','include_metrics'}
    assert query['filter_by.user_ids']==[17] and query['filter_by.warehouse_ids']==['w'] and query['max_results']==1
    assert query['filter_by.query_start_time_range.end_time_ms']-query['filter_by.query_start_time_range.start_time_ms']==86400000

@only
def test_late_genie_response_rejected_without_post_retry(monkeypatch):
    from sbs.genie.server import GenieTransport
    import time
    now=[0.0];calls=[]
    monkeypatch.setattr(time,'monotonic',lambda:now[0])
    class Response:
        status_code=200
        def json(self):return {'conversation_id':'c','message_id':'m'}
    class Session:
        def mount(self,*a):pass
        def request(self,*a,**kw):calls.append((a,kw));now[0]=46;return Response()
        def close(self):pass
    cfg=SimpleNamespace(host='https://dbc-0410b264-20c7.cloud.databricks.com',authenticate=lambda:{})
    transport=GenieTransport(cfg,space_id='s',session_factory=Session,max_seconds=45)
    with pytest.raises(TimeoutError):transport.do('POST','/api/2.0/genie/spaces/s/start-conversation',body={'content':'closed question'})
    assert len(calls)==1 and calls[0][1]['timeout']==30
