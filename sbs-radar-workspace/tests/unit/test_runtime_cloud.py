"""Checkpoint15: offline reader boundaries; no actual cloud calls."""
import json
from pathlib import Path
import pytest
from sbs.runtime import LocalService
ROOT=Path(__file__).resolve().parents[2]

def test_reader_connector_absent_disabled_never_builds_sdk(tmp_path):
    from sbs.operations.runtime_cloud import attach_cloud_refresh
    def forbidden(*a,**k):raise AssertionError('SDK_CONSTRUCTED')
    service=LocalService();attach_cloud_refresh(service,ROOT,config_path=tmp_path/'absent',reader_factory=forbidden)
    assert service.catalog()['runtime_refresh']['status']=='disabled'
    config=tmp_path/'disabled.json';config.write_text('{"enabled":false}')
    attach_cloud_refresh(service,ROOT,config_path=config,reader_factory=forbidden)
    assert service.catalog()['snapshot']==service.snapshot

def test_invalid_active_config_fails_before_credentials(tmp_path):
    from sbs.operations.runtime_cloud import attach_cloud_refresh
    p=tmp_path/'active';p.write_text('{"enabled":true}')
    with pytest.raises(ValueError):attach_cloud_refresh(LocalService(),ROOT,config_path=p,reader_factory=lambda *_:pytest.fail('SDK_CONSTRUCTED'))

def configuration(cache='runs/runtime-reader-fixture'):
    from sbs.operations.cloud_dispatch import digest
    c=dict(version=1,enabled=True,workspace_host='https://fixture.cloud.databricks.com',client_id='11111111-1111-1111-1111-111111111111',executor_id=123,control_table='catalog.sbs_radar.control',control_table_id='observed-uc-id',warehouse_id='observed-warehouse',volume_prefix='/Volumes/catalog/sbs_radar/artifacts/sbs-refresh',poll_seconds=10,max_polls=8,max_promotions=4,max_http_calls=100,max_sql_statements=8,max_files_calls=1000,cache_root=cache)
    c['backend_sha256']=digest({k:c[k] for k in ('control_table','control_table_id','warehouse_id','volume_prefix')})
    c['policy']={'trusted_administrators':['admin'],'maintenance':'Trusted admins coordinate changes','singleton_control':'Preseed row; no external DML','reader_access':'App SELECT + READ VOLUME only; backend grants required','issued_at_ms':0,'expires_at_ms':1000}
    c['policy_sha256']=digest(c['policy']);return c

def reader(c,files=None):
    from types import SimpleNamespace
    from test_shared_control import SQL
    from test_volume_artifacts import Files
    from sbs.operations.runtime_cloud import CloudSnapshotReader
    from databricks.sdk.service.catalog import TableInfo
    from databricks.sdk.service.iam import User
    table={'full_name':c['control_table'],'table_id':c['control_table_id'],'data_source_format':'DELTA','table_type':'MANAGED','owner':'admin','properties':{'delta.isolationLevel':'Serializable'},'columns':[{'name':'control_id'}]}
    services=SimpleNamespace(statement_execution=SQL(),files=files or Files(),current_user=SimpleNamespace(me=lambda:User(active=True,id=str(c['executor_id']),user_name=c['client_id'])),tables=SimpleNamespace(get=lambda *a,**k:TableInfo.from_dict(table)),warehouses=SimpleNamespace(get=lambda id:{'id':id,'state':'RUNNING'}))
    return CloudSnapshotReader(c,services,evidence_mode='fixture',clock_ms=lambda:50),services,table

@pytest.mark.parametrize('kind',['warehouse','owner','mask','principal','policy'])
def test_reader_refuses_metadata_before_select(kind):
    c=configuration();r,s,t=reader(c)
    if kind=='warehouse':s.warehouses.get=lambda id:{'id':id,'state':'STOPPED'}
    if kind=='owner':t['owner']='other'
    if kind=='mask':t['columns']=[{'name':'control_id','mask':{'function_name':'mask'}}]
    if kind=='principal':s.current_user.me=lambda:{'active':True,'id':'123','userName':'other'}
    if kind=='policy':r.clock_ms=lambda:1001
    with pytest.raises(ValueError):r.current()
    assert s.statement_execution.calls==[] and s.files.calls==[]

def test_read_only_transport_disallows_writes_before_auth():
    from sbs.operations.runtime_cloud import ReadOnlyApi,select_statement
    class Config:
        host='https://fixture.cloud.databricks.com'
        def authenticate(self):pytest.fail('AUTH_NOT_ALLOWED')
    c=configuration();api=ReadOnlyApi(Config(),c)
    for method,path,body in [('PUT','/api/2.0/fs/files'+c['volume_prefix']+'/runs/99/x',None),('POST','/api/2.0/sql/statements',{'warehouse_id':c['warehouse_id'],'statement':'UPDATE table SET x=1'}),('POST','/api/2.0/sql/statements',{'warehouse_id':'other','statement':select_statement(c)}),('POST','/api/2.0/sql/warehouses/id/start',None)]:
        with pytest.raises(ValueError,match='READER_WRITE_FORBIDDEN'):api.do(method,path,body=body)
    assert api.calls==0

def test_bad_host_pin_before_sdk_constructor(monkeypatch):
    import databricks.sdk.core
    from sbs.operations.runtime_cloud import sdk_reader
    monkeypatch.setattr(databricks.sdk.core,'Config',lambda **k:pytest.fail('CREDENTIAL_CONSTRUCTION'))
    c=configuration();c['workspace_host']='https://external.example'
    with pytest.raises(ValueError):sdk_reader(c)
    c=configuration();c['backend_sha256']='0'*64
    with pytest.raises(ValueError):sdk_reader(c)

@pytest.fixture(scope='module')
def releases(tmp_path_factory):
    from dataclasses import replace
    from sbs.operations import load_sealed_plan,RefreshRunner,sha,canonical
    from sbs.operations.preparers import build_real_hooks
    plan=load_sealed_plan(ROOT);config=json.loads((ROOT/'config/genie-pilot-002.json').read_text());pairs={x['pair']['pair_id']:x['pair'] for x in config['contexts']}
    plan=replace(plan,pairs=tuple(pairs.values()));out=[]
    for family in ('cybersecurity',None):
        p=plan
        if family:
            entries=[x for x in plan.manifest['sources'] if x['family']==family];urls={x['url'] for x in entries};m={**plan.manifest,'sources':entries}
            p=replace(plan,manifest=m,originals={k:v for k,v in plan.originals.items() if k in urls},hashes={k:v for k,v in plan.hashes.items() if k in urls},identity=sha(canonical(m)),pairs=tuple(x for x in pairs.values() if x['family']==family))
        runner=RefreshRunner(p,tmp_path_factory.mktemp('cloud-release')/'state')
        assert runner.run(run_id='offline-reader-fixture',force_revalidate=True,hooks=build_real_hooks(ROOT))['status']=='published'
        loaded=LocalService.from_release(runner.root,pointer=runner.current())
        out.append((runner,loaded.release_metadata['closure']))
    return out

def publish_fixture(backend,volume,run,release):
    from sbs.operations.shared_control import SharedLedger,SnapshotWriter
    from sbs.operations.cloud_dispatch import digest
    runner,closure=release;staged=volume.stage(str(run),runner.root,closure)
    SharedLedger(backend).reserve(digest(run),{'request_hash':digest(run),'job_id':7,'run_id':run,'status':'submitted'})
    w=SnapshotWriter(backend,job_id=7,writer_guard=lambda *a:True,artifact_validator=volume.verify,artifact_prefix=volume.prefix)
    current=w.current();w.publish(run,w.claim(run),previous=current['release_id'] if current else None,release_id=staged['release_id'],artifacts=staged['artifacts'])
    return w.current()

def test_factory_and_requests_promote_actual_family_with_failure_throttle_and_quota(releases,tmp_path,monkeypatch):
    from copy import deepcopy
    import sbs.runtime as runtime
    from test_shared_control import Backend
    from test_volume_artifacts import Files,store
    from sbs.operations.runtime_cloud import attach_cloud_refresh
    f=Files();v=store(f);b=Backend();first=publish_fixture(b,v,99,releases[0]);second=publish_fixture(b,v,100,releases[1]);c=configuration(cache='cache');r,s,_=reader(c,f)
    path=tmp_path/'runtime-cloud.json';path.write_text(json.dumps(c));tick=[0];calls=[]
    def factory(config):calls.append('factory');return r
    # Factory is genuinely create_service; remap only connector's server cache root.
    original=attach_cloud_refresh
    monkeypatch.setattr('sbs.operations.runtime_cloud.attach_cloud_refresh',lambda service,root,**kw:original(service,tmp_path,**kw))
    service=runtime.create_service(mode='cloud',cloud_config_path=path,cloud_reader_factory=factory,cloud_clock=lambda:tick[0])
    assert calls==[] and s.statement_execution.calls==[]
    actor={'authenticated':True,'subject':'reader','role':'reader','families':['cybersecurity','market_conduct']}
    s.statement_execution.revision=b.revision;s.statement_execution.state=deepcopy(b.state);s.statement_execution.state['current']=deepcopy(first)
    view=service.for_actor(actor);catalog=view.catalog();before=service.snapshot
    assert [p['family_id'] for p in catalog['pairs']]==['cybersecurity'] and catalog['runtime_refresh']['status']=='current'
    sql_count=len(s.statement_execution.calls);view.catalog();assert len(s.statement_execution.calls)==sql_count
    s.statement_execution.state=deepcopy(b.state)
    path2=second['manifest_path'];prefix=path2.rsplit('/',1)[0];pdf=next(p for p in f.data if p.startswith(prefix) and p.endswith('.pdf'));saved=f.data[pdf];f.data[pdf]=b'corrupt'
    tick[0]=11;failed=view.catalog()
    assert failed['runtime_refresh']['status']=='unavailable' and service.snapshot==before
    f.data[pdf]=saved;writes=list(f.calls);tick[0]=22
    after=view.catalog();assert service.snapshot!=before and len(after['pairs'])==2 and after['runtime_refresh']['evidence_mode']=='fixture'
    market=next(p for p in after['pairs'] if p['family_id']=='market_conduct');focus=market['provisions'][0]['id'];comparison=view.comparison(market['id'],focus)
    assert comparison['snapshot']==after['snapshot'] and comparison['after']['text']
    context=service.entry(market['id'],focus)['context'];result=service.rag(next(iter(service.query_cache)),context)
    assert result['snapshot']==after['snapshot'] and result['evidence']['citations']
    assert all(x.startswith('SELECT control_id, revision, state_json FROM ') for x in s.statement_execution.calls) and f.calls==writes
    assert calls==['factory'] and service.generator is None
    for n in range(4,11):tick[0]=n*11;view.catalog()
    assert view.catalog()['runtime_refresh']['status']=='quota_exhausted'

def test_real_sdk_factory_uses_m2m_pinned_identity_and_exact_select(monkeypatch):
    import databricks.sdk.core
    import sbs.operations.runtime_cloud as cloud
    from types import SimpleNamespace
    from test_shared_control import SQL
    from io import BytesIO
    c=configuration();calls=[];auth=[];sql=SQL();OriginalApi=cloud.ReadOnlyApi
    class Config:
        host=c['workspace_host'];client_id=c['client_id'];auth_type='oauth-m2m';workspace_id=None
        def __init__(self,**kw):assert kw['host']==self.host and kw['auth_type']=='oauth-m2m'
        def authenticate(self):auth.append(1);return {'Authorization':'fixture'}
    class Response:
        status_code=200;headers={}
        def __init__(self,value):self.raw=SimpleNamespace(read=lambda *a,**k:json.dumps(value).encode())
        def close(self):pass
    class Session:
        def request(self,method,url,**kw):
            calls.append((method,url,kw.get('json')))
            if '/Me' in url:value={'active':True,'id':'123','userName':c['client_id']}
            elif '/unity-catalog/tables/' in url:value={'full_name':c['control_table'],'table_id':c['control_table_id'],'table_type':'MANAGED','data_source_format':'DELTA','owner':'admin','properties':{'delta.isolationLevel':'Serializable'},'columns':[{'name':'control_id'}]}
            elif '/warehouses/' in url:value={'id':c['warehouse_id'],'state':'RUNNING'}
            else:
                assert method=='POST' and kw['json']['statement']==cloud.select_statement(c)
                value=sql.execute_statement(kw['json']['statement'],kw['json']['warehouse_id'])
                value['manifest']['schema']['columns'][1]['type_name']='LONG'
            return Response(value)
    monkeypatch.setattr(databricks.sdk.core,'Config',Config)
    monkeypatch.setattr(cloud,'ReadOnlyApi',lambda cfg,c:OriginalApi(cfg,c,session=Session()))
    r=cloud.sdk_reader(c);r.clock_ms=lambda:50
    assert calls==[] and auth==[]
    assert r.current() is None and len(calls)==4 and len(auth)==4
    assert calls[-1][0]=='POST' and sql.calls==[cloud.select_statement(c)]
    # Observed OAuth client mismatch rejects before any request/authentication.
    Config.client_id='different'
    with pytest.raises(ValueError,match='OAUTH_IDENTITY'):cloud.sdk_reader(c)
    assert len(calls)==4

def test_pending_and_factory_failure_are_explicit_preserve_bootstrap(tmp_path):
    from sbs.operations.runtime_cloud import attach_cloud_refresh
    c=configuration('cache');path=tmp_path/'active.json';path.write_text(json.dumps(c));r,s,_=reader(c);tick=[0]
    service=LocalService(mode='cloud');old=service.snapshot
    attach_cloud_refresh(service,tmp_path,config_path=path,reader_factory=lambda c:r,clock=lambda:tick[0])
    catalog=service.catalog();assert catalog['runtime_refresh']['reason']=='NO_PUBLISHED_RELEASE' and catalog['snapshot']==old
    def broken(c):raise RuntimeError('secret provider details')
    attach_cloud_refresh(service,tmp_path,config_path=path,reader_factory=broken,clock=lambda:tick[0])
    catalog=service.catalog();assert catalog['runtime_refresh']['reason']=='CLOUD_REFRESH_FAILED' and 'secret' not in json.dumps(catalog) and catalog['snapshot']==old
