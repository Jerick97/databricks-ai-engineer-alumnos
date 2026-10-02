import json
from pathlib import Path
import pytest
from sbs.operations.cloud_driver import DriverConfig,preflight,SingleAttemptApi,bind_driver

def test_preflight_missing_is_actionable_no_network():
 r=preflight(None)
 assert r['status']=='pending_configuration' and r['cloud_executed'] is False and r['missing']

def test_config_rejects_extra_and_placeholder():
 with pytest.raises(ValueError):DriverConfig.from_dict({'secret':'never'})

def test_transport_never_retries_post_and_sanitizes():
 class Config:
  host='https://workspace.example';workspace_id=None
  def authenticate(self):return {'Authorization':'secret'}
 class Response:
  status_code=503;content=b'';headers={}
  def close(self):pass
 class Session:
  def __init__(self):self.calls=[]
  def request(self,*a,**kw):self.calls.append((a,kw));return Response()
 session=Session();api=SingleAttemptApi(Config(),session=session,max_calls=1)
 with pytest.raises(ValueError,match='^SDK_HTTP_FAILED$'):api.do('POST','/api/2.0/sql/statements',body={})
 assert len(session.calls)==1 and session.calls[0][1]['allow_redirects'] is False
 with pytest.raises(ValueError):api.do('POST','/api/2.0/sql/statements',body={})
 assert len(session.calls)==1

def test_transport_rejects_remote_url_and_job_mutations_without_auth():
 class Config:
  host='https://workspace.example';workspace_id=None
  def authenticate(self):raise AssertionError('no auth')
 api=SingleAttemptApi(Config())
 for method,path in [('POST','/api/2.1/jobs/run-now'),('GET','https://other'),('DELETE','/api/2.0/fs/files/x')]:
  with pytest.raises(ValueError):api.do(method,path)

from types import SimpleNamespace
from copy import deepcopy
from dataclasses import asdict,replace
from sbs.operations.cloud_dispatch import WriterConfig,job_settings,digest
from sbs.operations.cloud_driver import sha,sdk_services
from test_shared_control import SQL
from test_volume_artifacts import Files

def config(release_id='a'*64,manifest='release.json',serverless=False):
 policy={'trusted_administrators':['admin'],'maintenance':'Trusted admins coordinate changes','exclusive_writer':'Only pinned Job writer; admins trusted','singleton_control':'Preseed one row; no outside DML','storage_authorized':'Dedicated writable namespace','issued_at_ms':0,'expires_at_ms':1000}
 backend=dict(control_table='catalog.sbs_radar.control',control_table_id='uc-control',warehouse_id='warehouse',volume_prefix='/Volumes/catalog/sbs_radar/artifacts/sbs-refresh')
 w=WriterConfig(7,'writer-sp',None if serverless else 'cluster','/Shared/writer',release_id,digest(backend),digest(policy),compute_mode='serverless' if serverless else 'existing_cluster',environment_version='4' if serverless else None,environment_dependencies=('databricks-sdk==0.102.0',) if serverless else ())
 return DriverConfig(writer=w,**backend,expected_acl={'object_id':'/jobs/7','access_control_list':[]},policy=policy,release_manifest=manifest)

def services(c):
 class Jobs:
  def __init__(self):self.settings=job_settings(c.writer);self.run_mutation=lambda r:None
  def get(self,job_id):return dict(job_id=7,run_as_user_name='writer-sp',settings=deepcopy(self.settings))
  def get_permissions(self,job_id):return deepcopy(c.expected_acl)
  def get_run(self,run_id,**kw):
   task=deepcopy(self.settings['tasks'][0]);values=dict(request_id=str(run_id),release_id=c.writer.release_id,job_id='7',run_id=str(run_id),snapshot_backend_id=c.writer.snapshot_backend_id)
   task['resolved_values']={'notebook_task':{'base_parameters':values}}
   r=dict(job_id=7,run_id=run_id,state={'life_cycle_state':'RUNNING'},trigger='PERIODIC',tasks=[task],job_parameters=[{'name':'release_id','value':c.writer.release_id},{'name':'request_id','value':str(run_id)}]);self.run_mutation(r);return r
  def run_now(self,**kw):raise AssertionError('never starts a job')
 table={'full_name':c.control_table,'table_id':c.control_table_id,'table_type':'MANAGED','data_source_format':'DELTA','owner':'admin','properties':{'delta.isolationLevel':'Serializable'},'columns':[{'name':'control_id'}]}
 from databricks.sdk.service.catalog import TableInfo
 from databricks.sdk.service.iam import User
 return SimpleNamespace(jobs=Jobs(),tables=SimpleNamespace(get=lambda *a,**kw:TableInfo.from_dict(table)),table=table,warehouses=SimpleNamespace(get=lambda id:{'id':id,'state':'RUNNING'}),clusters=SimpleNamespace(get=lambda id:{'cluster_id':id,'state':'RUNNING'}),current_user=SimpleNamespace(me=lambda:User(active=True,user_name='writer-sp')),statement_execution=SQL(),files=Files())

def test_bind_no_io_and_closed_config_serverless_roundtrip():
 c=config(serverless=True);assert DriverConfig.from_dict(json.loads(json.dumps(asdict(c))))==c
 s=services(c);d=bind_driver(c,s,evidence_mode='fixture',clock=lambda:50)
 assert s.statement_execution.calls==[] and s.files.calls==[]
 assert preflight(c)['compute_mode']=='serverless'
 assert d.identity()['isolation']=='Serializable'

@pytest.mark.parametrize('mutation',[lambda s:s.table['properties'].clear(),lambda s:s.table.update(table_id='different'),lambda s:s.table.update(owner='untrusted'),lambda s:s.table.update(row_filter={'function_name':'f'}),lambda s:setattr(s.warehouses,'get',lambda id:{'id':id,'state':'STOPPED'})])
def test_metadata_rejection_before_statement(mutation):
 c=config();s=services(c);mutation(s);d=bind_driver(c,s,evidence_mode='fixture',clock=lambda:50)
 with pytest.raises(ValueError):d.control.read()
 assert not s.statement_execution.calls

def test_policy_expiry_not_expected_observation():
 c=config();s=services(c);d=bind_driver(c,s,evidence_mode='fixture',clock=lambda:1001)
 with pytest.raises(ValueError):d.identity()
 assert not s.statement_execution.calls

def test_daily_registration_guard_and_serverless_no_cluster_call():
 c=config(serverless=True);s=services(c);s.clusters.get=lambda *a:(_ for _ in ()).throw(AssertionError('no invented cluster'))
 d=bind_driver(c,s,evidence_mode='fixture',clock=lambda:50)
 d.dispatcher.observe_daily(99)
 assert d.writer_guard(7,99)
 assert d.observations['run']['historical_run_as']=='not_exposed_by_SDK'
 s.jobs.run_mutation=lambda r:r['tasks'][0].update(environment_key='other')
 with pytest.raises(ValueError):d.writer_guard(7,99)

def test_identity_and_duplicate_control_reject():
 c=config();s=services(c);d=bind_driver(c,s,evidence_mode='fixture',clock=lambda:50);d.dispatcher.observe_daily(99)
 s.current_user.me=lambda:{'active':True,'userName':'wrong'}
 with pytest.raises(ValueError):d.writer_guard(7,99)
 s.statement_execution.duplicate=True
 with pytest.raises(ValueError):d.control.read()

def test_real_six_pdf_prepare_with_assembled_fixture_boundaries(tmp_path):
 import tempfile
 from sbs.operations import load_sealed_plan
 root=Path(__file__).resolve().parents[2]
 # Fresh local test-only pinned manifest; no production manifest change.
 fd,path=tempfile.mkstemp(prefix='sk11-cloud-driver-014-test-',suffix='.json',dir=root/'runs')
 import os;os.close(fd);p=Path(path)
 try:
  raw=json.dumps({'files':{'config/genie-pilot-002.json':sha((root/'config/genie-pilot-002.json').read_bytes())}}).encode();p.write_bytes(raw)
  c=config(sha(raw),str(p.relative_to(root)),serverless=True);s=services(c);d=bind_driver(c,s,evidence_mode='fixture',clock=lambda:50)
  cfg=json.load(open(root/'config/genie-pilot-002.json'));pairs={x['pair']['pair_id']:x['pair'] for x in cfg['contexts']};plan=replace(load_sealed_plan(root),pairs=tuple(pairs.values()))
  out=d.execute(root,plan,run_id=99,local_parent=tmp_path)
  assert out['status']=='published' and out['counts']['sources']==6 and out['counts']['records']==135 and out['counts']['embedding_calls']==0
  assert out['evidence_mode']=='fixture' and out['cloud_acceptance'] is False
  again=d.execute(root,plan,run_id=99,local_parent=tmp_path)
  assert again['recovered'] is True
 finally:p.unlink()

def test_generated_sdk_serializers_single_attempt_and_files_false():
 from io import BytesIO
 class Config:
  host='https://workspace.example';workspace_id=None
  def authenticate(self):return {'Authorization':'never-recorded'}
 class Response:
  status_code=200;headers={}
  def __init__(self,raw):self.raw=SimpleNamespace(read=lambda *a,**kw:raw)
  def close(self):pass
 class Session:
  def __init__(self):self.calls=[]
  def request(self,method,url,**kwargs):
   self.calls.append((method,url,kwargs))
   return Response(b'{"statement_id":"statement","status":{"state":"SUCCEEDED"}}' if method=='POST' else b'')
 session=Session();s=sdk_services(Config(),session=session)
 r=s.statement_execution.execute_statement(statement='SELECT 1',warehouse_id='warehouse',row_limit=2)
 assert r.statement_id=='statement'
 s.files.upload('/Volumes/catalog/sbs_radar/artifacts/sbs-refresh/runs/99/x',BytesIO(b'x'),overwrite=False)
 assert len(session.calls)==2 and session.calls[-1][2]['params']['overwrite']=='false'
 assert session.calls[0][2]['json']['statement']=='SELECT 1'


def test_config_pin_and_unknown_fields_fail_without_sdk(tmp_path):
 from sbs.operations.cloud_driver import load_config
 p=tmp_path/'config.json';p.write_text(json.dumps(asdict(config())))
 assert load_config(p,sha(p.read_bytes())).writer.job_id==7
 with pytest.raises(ValueError):load_config(p,'b'*64)
 data=json.loads(p.read_text());data['token']='secret';p.write_text(json.dumps(data))
 with pytest.raises(ValueError):load_config(p,sha(p.read_bytes()))


def test_release_pin_failure_before_any_metadata_or_sql(tmp_path):
 (tmp_path/'release.json').write_text('{}');c=config();s=services(c)
 s.tables.get=lambda *a,**k:(_ for _ in ()).throw(AssertionError('metadata not reached'))
 d=bind_driver(c,s,evidence_mode='fixture',clock=lambda:50)
 with pytest.raises(ValueError,match='PIN'):d.execute(tmp_path,None,run_id=99)
 assert not s.statement_execution.calls and not s.files.calls

@pytest.mark.parametrize('read_fails,close_fails,expected',[(True,False,'SDK_RESPONSE_READ_UNCONFIRMED'),(False,True,'SDK_RESPONSE_CLOSE_UNCONFIRMED'),(True,True,'SDK_RESPONSE_READ_UNCONFIRMED')])
def test_cd01_stream_close_errors_safe_one_attempt(read_fails,close_fails,expected):
 api,response,session=error_transport(read_fails=read_fails,close_fails=close_fails)
 with pytest.raises(ValueError,match='^'+expected+'$') as exc:api.do('GET','/api/2.0/clusters/get')
 assert 'fixture-sensitive-response-marker' not in str(exc.value)
 assert response.closed==1 and session.calls==1 and api.calls==1


def error_transport(*,read_fails=False,close_fails=False,status=200,content=b'{}',cap=1024):
 class Config:
  host='https://workspace.example';workspace_id=None
  def authenticate(self):return {}
 class Response:
  status_code=status;headers={}
  def __init__(self):self.closed=0;self.raw=SimpleNamespace(read=self.read)
  def read(self,*a,**k):
   if read_fails:raise RuntimeError('fixture-sensitive-response-marker')
   return content
  def close(self):
   self.closed+=1
   if close_fails:raise RuntimeError('fixture-sensitive-close-marker')
 class Session:
  def __init__(self):self.calls=0
  def request(self,*a,**kw):self.calls+=1;return response
 response=Response();session=Session()
 return SingleAttemptApi(Config(),session=session,max_response_bytes=cap),response,session


def test_cd01_close_failure_preserves_http_conflict():
 from sbs.operations.cloud_driver import SafeHttpError
 api,response,session=error_transport(status=409,close_fails=True)
 with pytest.raises(SafeHttpError) as exc:api.do('PUT','/api/2.0/fs/files/Volumes/catalog/sbs_radar/artifacts/sbs-refresh/runs/99/x')
 assert exc.value.error_code=='RESOURCE_ALREADY_EXISTS' and str(exc.value)=='SDK_HTTP_FAILED'
 assert session.calls==1 and response.closed==1


@pytest.mark.parametrize('content,cap,code',[(b'{',1024,'SDK_JSON_INVALID'),(b'12345',4,'SDK_RESPONSE_CAP_EXCEEDED')])
def test_cd01_close_failure_preserves_json_and_cap(content,cap,code):
 api,response,session=error_transport(content=content,cap=cap,close_fails=True)
 with pytest.raises(ValueError,match='^'+code+'$'):api.do('GET','/api/2.0/clusters/get')
 assert session.calls==1 and response.closed==1

def test_cd01_stream_error_remains_safe_through_writer_guard():
 from databricks.sdk.service.compute import ClustersAPI
 c=config();s=services(c);d=bind_driver(c,s,evidence_mode='fixture',clock=lambda:50)
 d.dispatcher.observe_daily(99)
 api,response,session=error_transport(read_fails=True);s.clusters=ClustersAPI(api)
 with pytest.raises(ValueError,match='^SDK_RESPONSE_READ_UNCONFIRMED$'):d.writer_guard(7,99)
 assert session.calls==1 and response.closed==1

def test_remote_mode_reaches_coordinator_from_pinned_driver(tmp_path,monkeypatch):
 import sbs.operations.cloud_driver as module
 raw=b'{"files":{}}'
 # At least one file is required by the driver release validator.
 (tmp_path/'input').write_bytes(b'input');raw=json.dumps({'files':{'input':sha(b'input')}}).encode();(tmp_path/'release.json').write_bytes(raw)
 c=replace(config(sha(raw)),capture_mode='remote',capture_state_root=str(tmp_path/'capture-state'))
 c=DriverConfig.from_dict(json.loads(json.dumps(asdict(c))));s=services(c);d=bind_driver(c,s,evidence_mode='fixture',clock=lambda:50);observed={}
 def prepare(*args,**kwargs):observed.update(kwargs);return {'status':'pending_validation'}
 monkeypatch.setattr(module,'prepare_and_publish',prepare)
 d.execute(tmp_path,None,run_id=99)
 assert observed['capture_mode']=='remote' and observed['capture_state_root']==str(tmp_path/'capture-state')
