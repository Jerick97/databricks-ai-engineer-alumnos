"""Concrete, bounded provisioning106. Default CLI is offline preflight.

Execute requires an independent review capability tied to exact input hashes and
an unexpired window. Creates only the dedicated control table and paused Job;
never starts compute, runs a Job, deletes objects or touches eight data tables.
"""
from pathlib import Path
from types import SimpleNamespace
from io import BytesIO
import base64,hashlib,json,time,os,re,sys
from . import atomic,exclusive_lock
from .cloud_dispatch import require,digest,canonical,obj
from .cloud_driver import DriverConfig,load_config
from .provision_105 import TABLE,WAREHOUSE,PRINCIPAL,control_steps,creation_settings,step_once

HOST='dbc-0410b264-20c7.cloud.databricks.com'
OWNER='sociosdosmilveintiseis@gmail.com'
OWNER_ID='76826984571984'
VOLUME='neptuno_manuel_arguelles.sbs_radar.release_artifacts'
PREFIX='/Volumes/neptuno_manuel_arguelles/sbs_radar/release_artifacts/sbs-refresh'
SELECT=f'SELECT control_id, revision, state_json FROM {TABLE}'
LIMITS={'http':120,'sql':12,'mutations':12}
def sha(raw):return hashlib.sha256(raw).hexdigest()
def safe_json(path):
 p=Path(path);require(p.is_file() and not p.is_symlink(),'INPUT_FILE_INVALID');return json.loads(p.read_bytes())

class RemoteError(ValueError):
 def __init__(self,status,code):super().__init__('REMOTE_REQUEST_FAILED');self.status=status;self.code=code

def validate_table(t,*,owner):
 require(isinstance(t,dict) and t.get('full_name')==TABLE and isinstance(t.get('table_id'),str) and bool(t['table_id']) and t.get('table_type')=='MANAGED' and t.get('data_source_format')=='DELTA' and t.get('owner')==owner and t.get('browse_only') is not True,'TABLE_METADATA_INVALID')
 require(t.get('properties',{}).get('delta.isolationLevel')=='Serializable' and not t.get('row_filter'),'TABLE_POLICY_INVALID')
 cols=t.get('columns');require(isinstance(cols,list) and len(cols)==3,'TABLE_SCHEMA_INVALID')
 require([(c.get('name'),'LONG' if c.get('type_name')=='BIGINT' else c.get('type_name'),c.get('nullable')) for c in cols]==[('control_id','STRING',False),('revision','LONG',False),('state_json','STRING',False)] and all(not c.get('mask') for c in cols),'TABLE_SCHEMA_INVALID')
 return {'table_id':t['table_id'],'metadata_sha256':digest(t),'owner':owner}

def validate_rows(r,*,empty):
 from .shared_control import initial_state
 m=r.get('manifest',{});v=r.get('result',{});n=0 if empty else 1
 require(m.get('format')=='JSON_ARRAY' and m.get('truncated') is False and m.get('total_row_count')==n and m.get('total_chunk_count') in ((0,1) if empty else (1,)),'SINGLETON_MANIFEST_INVALID')
 require([(c.get('name'),'LONG' if c.get('type_name')=='BIGINT' else c.get('type_name')) for c in m.get('schema',{}).get('columns',[])]==[('control_id','STRING'),('revision','LONG'),('state_json','STRING')],'SINGLETON_SCHEMA_INVALID')
 if empty and m.get('total_chunk_count')==0:
  require(v in ({},{'data_array':[]}), 'EMPTY_RESULT_INVALID');return {'rows':0,'readback_sha256':digest(r)}
 require(not v.get('external_links') and v.get('next_chunk_index') is None and v.get('next_chunk_internal_link') is None and v.get('chunk_index')==0 and v.get('row_offset')==0 and v.get('row_count')==n,'SINGLETON_RESULT_INVALID')
 rows=v.get('data_array',[]);require(isinstance(rows,list) and len(rows)==n,'SINGLETON_ROWS_INVALID')
 if not empty:require(len(rows[0])==3 and rows[0][:2]==['control','0'] and json.loads(rows[0][2])==initial_state(),'SINGLETON_SEED_INVALID')
 return {'rows':n,'readback_sha256':digest(r)}

def notebook_source(*,archive_path,archive_sha,manifest_path,release_id,config_path,config_sha,mode):
 require(mode in ('preflight','execute'),'WRITER_MODE_INVALID')
 values=dict(archive_path=archive_path,archive_sha=archive_sha,manifest_path=manifest_path,release_id=release_id,config_path=config_path,config_sha=config_sha,mode=mode)
 return '# Databricks notebook source\n'+'''# Bound106: static server-reviewed delivery; widgets supply only observed Job context.
import hashlib, json, pathlib, tarfile, tempfile, sys
B = '''+repr(values)+'''
def checked(v, code):
    if not v: raise ValueError(code)
archive=pathlib.Path(B['archive_path']);raw=archive.read_bytes()
checked(hashlib.sha256(raw).hexdigest()==B['archive_sha'],'ARCHIVE_PIN_MISMATCH')
with tempfile.TemporaryDirectory(prefix='sbs-writer106-') as tmp:
    root=pathlib.Path(tmp)/'sbs-radar'
    with tarfile.open(archive) as tar:
        members=tar.getmembers();names=[m.name for m in members]
        checked(len(names)==len(set(names)) and len(names)<=2000 and sum(m.size for m in members)<=134217728,'ARCHIVE_LIMIT')
        checked(all(m.isfile() and m.name.startswith('sbs-radar/') and '..' not in pathlib.PurePosixPath(m.name).parts for m in members),'ARCHIVE_PATH_INVALID')
        tar.extractall(tmp,filter='data')
    manifest_raw=(root/B['manifest_path']).read_bytes()
    checked(hashlib.sha256(manifest_raw).hexdigest()==B['release_id'],'MANIFEST_PIN_MISMATCH')
    for name,pin in json.loads(manifest_raw)['files'].items():
        p=root/name
        checked(not pathlib.PurePosixPath(name).is_absolute() and '..' not in pathlib.PurePosixPath(name).parts and hashlib.sha256(p.read_bytes()).hexdigest()==pin,'SNAPSHOT_CLOSURE_INVALID')
    sys.path.insert(0,str(root/'src'))
    from sbs.operations.cloud_driver import load_config,preflight,execute_from_config
    config=load_config(B['config_path'],B['config_sha'])
    checked(config.writer.release_id==B['release_id'],'CONFIG_RELEASE_MISMATCH')
    if B['mode']=='preflight':
        print(json.dumps(preflight(config)))
    else:
        job_id=dbutils.widgets.get('job_id');run_id=dbutils.widgets.get('run_id');release_id=dbutils.widgets.get('release_id')
        checked(job_id.isdecimal() and run_id.isdecimal(),'JOB_CONTEXT_INVALID')
        result=execute_from_config(config,root,job_id=int(job_id),run_id=int(run_id),release_id=release_id)
        print(json.dumps({k:result[k] for k in ('status','evidence_mode','cloud_acceptance','cost') if k in result}))
'''

def normalize_source(raw):return raw.replace(b'\r\n',b'\n').rstrip()+b'\n'

class ScopedApi:
 """SDK serializer target; one request, no retries, durable cumulative quota."""
 def __init__(self,config,*,journal,authorize,prefix,session=None):
  from urllib.parse import urlsplit
  import requests
  u=urlsplit(config.host);require(u.scheme=='https' and u.hostname==HOST and not any((u.username,u.password,u.query,u.fragment)) and u.path in ('','/'),'HOST_INVALID')
  self._cfg=config;self.journal=Path(journal);self.authorize=authorize;self.prefix=prefix;self.permit=None
  self.notebook_ids=set()
  self.session=session or requests.Session()
  for a in self.session.adapters.values():require(a.max_retries.total==0,'RETRIES_FORBIDDEN')
 def reserve(self,*,sql,mutation):
  p=self.journal/'budget.json';b=safe_json(p) if p.exists() else {k:0 for k in LIMITS}
  b['http']+=1;b['sql']+=int(sql);b['mutations']+=int(mutation)
  require(all(type(b[k]) is int and 0<=b[k]<=LIMITS[k] for k in LIMITS),'PROVISION_BUDGET_EXCEEDED');atomic(p,b)
 def with_permit(self,method,path,body,call,*,data_sha=None):
  require(self.permit is None,'NESTED_WRITE_FORBIDDEN');self.permit=(method,path,digest(body),data_sha)
  try:return call()
  finally:self.permit=None
 def do(self,method,path=None,*,query=None,body=None,headers=None,data=None,raw=False,response_headers=None,**extra):
  require(not extra and isinstance(path,str) and '..' not in path,'API_REQUEST_INVALID')
  read_paths={'/api/2.0/preview/scim/v2/Me','/api/2.0/preview/scim/v2/ServicePrincipals/72803555975940','/api/2.0/sql/warehouses/'+WAREHOUSE,'/api/2.1/unity-catalog/volumes/'+VOLUME,'/api/2.1/unity-catalog/tables/'+TABLE,'/api/2.2/jobs/list','/api/2.2/jobs/get','/api/2.0/workspace/get-status','/api/2.0/workspace/export'}
  permitted_read=method=='GET' and (path in read_paths or re.fullmatch(r'/api/2.0/permissions/(jobs|notebooks)/[0-9]+',path) or re.fullmatch(r'/api/2.0/sql/statements/[A-Za-z0-9-]+',path) or path.startswith('/api/2.0/fs/files'+self.prefix+'/') or path=='/api/2.1/unity-catalog/permissions/table/'+TABLE)
  sql=method=='POST' and path=='/api/2.0/sql/statements'
  read_sql=sql and isinstance(body,dict) and body.get('statement')==SELECT and body.get('warehouse_id')==WAREHOUSE
  permitted_read=permitted_read or (method=='HEAD' and path=='/api/2.0/fs/directories'+self.prefix)
  mutation=not(permitted_read or read_sql)
  if mutation:
   namespace='/Shared/sbs-radar/writer106-'+self.prefix.rsplit('/',1)[-1][:16]
   allowed=(sql and isinstance(body,dict) and body.get('statement') in [s['payload']['statement'] for s in control_steps()] and body.get('warehouse_id')==WAREHOUSE) or (method=='PUT' and path=='/api/2.0/fs/directories'+self.prefix and body is None) or (method=='PUT' and path.startswith('/api/2.0/fs/files'+self.prefix+'/') and query=={'overwrite':False}) or (method=='POST' and path=='/api/2.0/workspace/mkdirs' and body=={'path':'/Shared/sbs-radar'}) or (method=='POST' and path=='/api/2.0/workspace/import' and body.get('path')==namespace and body.get('format')=='SOURCE' and body.get('language')=='PYTHON') or (method=='PATCH' and path=='/api/2.1/unity-catalog/permissions/table/'+TABLE and body=={'changes':[{'principal':PRINCIPAL,'add':['SELECT','MODIFY']}]}) or (method=='PATCH' and any(path=='/api/2.0/permissions/notebooks/'+str(i) for i in self.notebook_ids) and body=={'access_control_list':[{'service_principal_name':PRINCIPAL,'permission_level':'CAN_READ'}]}) or (method=='POST' and path=='/api/2.2/jobs/create' and body.get('name')=='sbs-radar-single-writer' and body.get('schedule',{}).get('pause_status')=='PAUSED' and body.get('run_as')=={'service_principal_name':PRINCIPAL} and body.get('max_concurrent_runs')==1)
   require(allowed,'MUTATION_OUTSIDE_SCOPE')
   data_pin=None
   if data is not None:
    require(hasattr(data,'read'),'FILE_STREAM_REQUIRED');content=data.read();require(len(content)<=33554432,'UPLOAD_LIMIT');data=BytesIO(content);data_pin=sha(content)
   require(self.permit==(method,path,digest(body),data_pin),'WRITE_NOT_APPROVED');self.permit=None
  else:require(permitted_read or read_sql,'API_NOT_ALLOWED')
  self.authorize();self.reserve(sql=sql,mutation=mutation)
  auth=self._cfg.authenticate();self.authorize() # authentication may consume time
  try:r=self.session.request(method,self._cfg.host.rstrip('/')+path,params={k:str(v).lower() if type(v) is bool else v for k,v in (query or {}).items()},json=body,data=data,headers={**(headers or {}),**auth},timeout=(10,60),allow_redirects=False,stream=True)
  except Exception:raise ValueError('TRANSPORT_OUTCOME_UNKNOWN') from None
  try:
   content=r.raw.read(33554433,decode_content=True);require(len(content)<=33554432,'RESPONSE_LIMIT')
   if not 200<=r.status_code<300:
    try:code=json.loads(content).get('error_code')
    except Exception:code=None
    raise RemoteError(r.status_code,code if code in ('TABLE_DOES_NOT_EXIST','RESOURCE_DOES_NOT_EXIST','NOT_FOUND','RESOURCE_ALREADY_EXISTS') else 'UNCLASSIFIED')
   if raw:return {'contents':BytesIO(content),**{k:r.headers.get(k) for k in response_headers or []}}
   return json.loads(content) if content else {}
  finally:r.close()

class Provisioner:
 def __init__(self,root,journal,review,*,profile=None,writer_mode='preflight',config_factory=None,session=None):
  from databricks.sdk.core import Config
  from databricks.sdk.service import jobs,workspace,catalog,sql,files,iam
  import importlib.metadata
  require(importlib.metadata.version('databricks-sdk')=='0.102.0','SDK_VERSION_MISMATCH')
  self.root=Path(root).resolve();self.journal=Path(journal).resolve();self.review=review;self.mode=writer_mode
  require(review.get('files')==review_inputs(self.root),'EXACT_REVIEW_INPUTS_REQUIRED')
  self.package=safe_json(self.root/'runs/sk12-writer-portable-105.json');self.bundle=self.root/self.package['archive'];self.pin=sha(self.bundle.read_bytes());require(self.pin==self.package['archive_sha256'],'BUNDLE_DRIFT')
  self.prefix=PREFIX+'/bootstrap106/'+self.pin;self.notebook='/Shared/sbs-radar/writer106-'+self.pin[:16];self.owner=None;self.table_id=None
  self.authorize()
  cfg=config_factory() if config_factory else (Config(profile=profile) if profile else Config())
  self.api=ScopedApi(cfg,journal=self.journal,authorize=self.authorize,prefix=self.prefix,session=session)
  self.jobs=jobs.JobsAPI(self.api);self.workspace=workspace.WorkspaceAPI(self.api);self.tables=catalog.TablesAPI(self.api);self.grants=catalog.GrantsAPI(self.api);self.sql=sql.StatementExecutionAPI(self.api);self.files=files.FilesAPI(self.api);self.me=iam.CurrentUserAPI(self.api);self.warehouses=sql.WarehousesAPI(self.api);self.volumes=catalog.VolumesAPI(self.api)
 def authorize(self):
  now=int(time.time()*1000);r=self.review
  require(r.get('approved') is True and r.get('scope')=='provision106' and type(r.get('issued_at_ms')) is int and type(r.get('expires_at_ms')) is int and r['issued_at_ms']<=now<r['expires_at_ms'] and 0<r['expires_at_ms']-r['issued_at_ms']<=1800000,'REVIEW_WINDOW_REQUIRED')
  require(r.get('writer_mode')==self.mode and r.get('limits')==LIMITS,'REVIEW_SCOPE_MISMATCH')
  for name,pin in r['files'].items():require(sha((self.root/name).read_bytes())==pin,'REVIEW_INPUT_DRIFT')
 def one(self,name,step_id,payload,observe,effect):
  folder=self.journal/name;folder.mkdir(exist_ok=True)
  step={'step_id':step_id,'operation':name,'payload':payload,'precondition':'review106_exact_inputs_current_identity_and_scoped_readbacks'}
  result=step_once(folder,step,authorize=self.authorize,observe=observe,effect=effect)
  require(result['status']=='confirmed_by_readback','PROVISION_RECONCILE_REQUIRED');return result['observation']
 def table(self):
  try:t=obj(self.tables.get(TABLE,include_browse=False))
  except RemoteError as e:
   if e.status==404 and e.code=='TABLE_DOES_NOT_EXIST':return None
   raise
  observed=validate_table(t,owner=self.owner)
  if self.table_id is not None:require(observed['table_id']==self.table_id,'TABLE_ID_DRIFT')
  return observed
 def statement(self,statement,*,mutation=False):
  from databricks.sdk.service.sql import Disposition,Format
  kwargs=dict(statement=statement,warehouse_id=WAREHOUSE,disposition=Disposition.INLINE,format=Format.JSON_ARRAY,wait_timeout='10s',row_limit=2,byte_limit=1000000)
  body={'statement':statement,'warehouse_id':WAREHOUSE,'disposition':'INLINE','format':'JSON_ARRAY','wait_timeout':'10s','row_limit':2,'byte_limit':1000000}
  call=lambda:self.sql.execute_statement(**kwargs)
  response=self.api.with_permit('POST','/api/2.0/sql/statements',body,call) if mutation else call()
  r=obj(response);sid=r.get('statement_id');require(isinstance(sid,str) and sid,'STATEMENT_ID_REQUIRED')
  for _ in range(3):
   if r.get('status',{}).get('state')=='SUCCEEDED':break
   require(r.get('status',{}).get('state') in ('PENDING','RUNNING'),'SQL_FAILED');r=obj(self.sql.get_statement(sid))
  require(r.get('statement_id')==sid and r.get('status',{}).get('state')=='SUCCEEDED' and not r.get('status',{}).get('error'),'SQL_NOT_CONFIRMED');return r
 def rows(self,*,want_empty=False):
  require(self.table() is not None,'CONTROL_TABLE_REQUIRED');r=self.statement(SELECT)
  n=r.get('manifest',{}).get('total_row_count')
  if n==0:
   result=validate_rows(r,empty=True);return result if want_empty else None
  require(not want_empty,'CONTROL_NOT_EMPTY');return validate_rows(r,empty=False)
 def file_readback(self,path,pin):
  try:response=self.files.download(path)
  except RemoteError as e:
   if e.status==404 and e.code in ('RESOURCE_DOES_NOT_EXIST','NOT_FOUND'):return None
   raise
  try:raw=response.contents.read(33554433)
  finally:response.contents.close()
  require(sha(raw)==pin,'REMOTE_FILE_DRIFT');return {'path':path,'sha256':pin,'bytes':len(raw)}
 def upload(self,name,path,raw):
  pin=sha(raw)
  return self.one(name,'upload_config' if name=='config' else 'upload_bundle',{'path':path,'sha256':pin,'bytes':len(raw)},lambda:self.file_readback(path,pin),lambda _:self.api.with_permit('PUT','/api/2.0/fs/files'+path,None,lambda:self.files.upload(path,BytesIO(raw),overwrite=False),data_sha=pin))
 def notebook_readback(self,source,*,allow_initial=False,previous_source=None):
  from databricks.sdk.service.workspace import ExportFormat
  try:status=obj(self.workspace.get_status(self.notebook))
  except RemoteError as e:
   if e.status==404 and e.code=='RESOURCE_DOES_NOT_EXIST':return None
   raise
  require(status.get('path')==self.notebook and status.get('object_type')=='NOTEBOOK' and type(status.get('object_id')) is int and status['object_id']>0,'NOTEBOOK_METADATA_INVALID')
  self.api.notebook_ids.add(status['object_id'])
  exported=obj(self.workspace.export(self.notebook,format=ExportFormat.SOURCE));raw=base64.b64decode(exported.get('content',''),validate=True)
  if allow_initial and normalize_source(raw)==normalize_source(self.bootstrap.encode()):return None
  if previous_source is not None and normalize_source(raw)==normalize_source(previous_source.encode()):return None
  require(normalize_source(raw)==normalize_source(source.encode()),'NOTEBOOK_CONTENT_DRIFT');return {'object_id':status['object_id'],'path':self.notebook,'source_sha256':sha(normalize_source(raw))}
 def import_notebook(self,name,source,*,overwrite=False,previous_source=None):
  from databricks.sdk.service.workspace import ImportFormat,Language
  payload={'path':self.notebook,'content':base64.b64encode(source.encode()).decode(),'format':'SOURCE','language':'PYTHON','overwrite':overwrite}
  return self.one(name,'import_notebook',payload,lambda:self.notebook_readback(source,allow_initial=overwrite,previous_source=previous_source),lambda _:self.api.with_permit('POST','/api/2.0/workspace/import',payload,lambda:self.workspace.import_(self.notebook,content=payload['content'],format=ImportFormat.SOURCE,language=Language.PYTHON,overwrite=overwrite)))
 def job_observation(self,settings):
  listing=self.api.do('GET','/api/2.2/jobs/list',query={'name':'sbs-radar-single-writer','limit':25,'expand_tasks':True})
  require(not listing.get('has_more') and not listing.get('next_page_token'),'JOBS_PAGINATION_UNSUPPORTED');items=listing.get('jobs',[]);require(isinstance(items,list) and len(items)<=1,'JOB_NAME_CONFLICT')
  if not items:return None
  candidate=items[0].get('job_id');require(type(candidate) is int and candidate>0,'JOB_ID_INVALID')
  job=obj(self.jobs.get(candidate));require(job.get('job_id')==candidate and not job.get('next_page_token') and job.get('run_as_user_name')==PRINCIPAL,'JOB_IDENTITY_INVALID')
  actual=job.get('settings',{});require(all(actual.get(k)==v for k,v in settings.items()),'JOB_SETTINGS_MISMATCH');require(not any(actual.get(k) for k in ('continuous','trigger','git_source','job_clusters')),'JOB_EXTRA_EXECUTION_SETTINGS')
  return {'job_id':candidate,'settings_sha256':digest(settings),'job_sha256':digest(job)}
 def run(self):
  from databricks.sdk.service.jobs import JobSettings,JobAccessControlRequest,JobPermissionLevel
  from databricks.sdk.service.catalog import PermissionsChange,Privilege
  from databricks.sdk.service.workspace import WorkspaceObjectAccessControlRequest,WorkspaceObjectPermissionLevel
  self.authorize()
  user=obj(self.me.me());require(user.get('userName')==OWNER and user.get('id')==OWNER_ID and user.get('active') is True,'OPERATOR_IDENTITY_INVALID');self.owner=user['userName']
  sp=self.api.do('GET','/api/2.0/preview/scim/v2/ServicePrincipals/72803555975940');require(sp.get('id')=='72803555975940' and sp.get('applicationId')==PRINCIPAL and sp.get('active') is True,'WRITER_PRINCIPAL_INVALID')
  require(obj(self.warehouses.get(WAREHOUSE)).get('state')=='RUNNING','WAREHOUSE_NOT_RUNNING')
  volume=obj(self.volumes.read(VOLUME));require(volume.get('full_name')==VOLUME,'VOLUME_IDENTITY_INVALID')
  policy={'trusted_administrators':[self.owner],'maintenance':'Only the reviewed provision106 operator mutates dedicated control DDL/seed under exclusive maintenance. Workspace administrators remain trusted.','exclusive_writer':'Only the named paused Job runs as the existing writer principal; privileged administrators remain trusted.','singleton_control':'No parallel DDL/INSERT/DELETE into dedicated control table during provisioning or operation.','storage_authorized':'Existing UC Volume is SBS-owned; effective writer privileges must be observed before first run.','issued_at_ms':self.review['issued_at_ms'],'expires_at_ms':self.review['expires_at_ms']}
  policy_path=self.journal/'policy.json'
  if policy_path.exists():policy=safe_json(policy_path)
  else:atomic(policy_path,policy)
  require(policy['trusted_administrators']==[self.owner],'POLICY_OPERATOR_DRIFT')
  # No existing resource is adopted without a prior local durable intent.
  if not list((self.journal/'table').glob('*.intent.json')):require(self.table() is None,'EXISTING_TABLE_REQUIRES_RECONCILIATION')
  table_step=control_steps()[0]
  self.table_id=self.one('table','create_control',table_step['payload'],self.table,lambda _:self.statement(table_step['payload']['statement'],mutation=True))['table_id']
  def seed_effect(_):
   self.rows(want_empty=True);return self.statement(control_steps()[1]['payload']['statement'],mutation=True)
  self.one('seed','seed_control',control_steps()[1]['payload'],self.rows,seed_effect)
  # Add exactly two privileges to the new dedicated table; no data-table ACLs.
  grant_payload={'changes':[{'principal':PRINCIPAL,'add':['SELECT','MODIFY']}]}
  def grant_observe():
   require(self.table() is not None,'CONTROL_TABLE_REQUIRED');g=obj(self.grants.get('table',TABLE,principal=PRINCIPAL));require(not g.get('next_page_token'),'GRANT_PAGINATION_UNSUPPORTED')
   matches=[p for p in g.get('privilege_assignments',[]) if p.get('principal')==PRINCIPAL]
   if not matches:return None
   require(len(matches)==1,'GRANT_IDENTITY_AMBIGUOUS');priv=set(matches[0].get('privileges',[]));require(priv<={'SELECT','MODIFY'},'EXCESS_WRITER_CONTROL_GRANT')
   return {'principal':PRINCIPAL,'privileges':sorted(priv),'sha256':digest(g)} if priv=={'SELECT','MODIFY'} else None
  self.one('control_acl','set_job_acl',grant_payload,grant_observe,lambda _:self.api.with_permit('PATCH','/api/2.1/unity-catalog/permissions/table/'+TABLE,grant_payload,lambda:self.grants.update('table',TABLE,changes=[PermissionsChange(principal=PRINCIPAL,add=[Privilege.SELECT,Privilege.MODIFY])])))
  def directory_observe():
   try:self.files.get_directory_metadata(self.prefix)
   except RemoteError as e:
    if e.status==404 and e.code in ('RESOURCE_DOES_NOT_EXIST','NOT_FOUND'):return None
    raise
   return {'directory':self.prefix}
  self.one('volume_directory','upload_bundle',{'path':self.prefix},directory_observe,lambda _:self.api.with_permit('PUT','/api/2.0/fs/directories'+self.prefix,None,lambda:self.files.create_directory(self.prefix)))
  def workspace_directory():
   try:info=obj(self.workspace.get_status('/Shared/sbs-radar'))
   except RemoteError as e:
    if e.status==404 and e.code=='RESOURCE_DOES_NOT_EXIST':return None
    raise
   require(info.get('path')=='/Shared/sbs-radar' and info.get('object_type')=='DIRECTORY','WORKSPACE_DIRECTORY_INVALID');return {'path':info['path'],'object_id':info.get('object_id')}
  self.one('workspace_directory','import_notebook',{'path':'/Shared/sbs-radar'},workspace_directory,lambda _:self.api.with_permit('POST','/api/2.0/workspace/mkdirs',{'path':'/Shared/sbs-radar'},lambda:self.workspace.mkdirs('/Shared/sbs-radar')))
  archive_path=self.prefix+'/code.tar.gz';self.upload('bundle',archive_path,self.bundle.read_bytes())
  self.bootstrap='# Databricks notebook source\nprint("SBS106 provisioning preflight: final server configuration pending; no cloud writer execution")\n'
  if not list((self.journal/'notebook_bootstrap').glob('*.intent.json')):require(self.notebook_readback(self.bootstrap) is None,'EXISTING_NOTEBOOK_FORBIDDEN')
  if any(self.journal.glob('notebook_bound_*')):
   receipts=list((self.journal/'notebook_bootstrap').glob('*.observed.json'));require(len(receipts)==1,'BOOTSTRAP_RECEIPT_REQUIRED')
   nb=safe_json(receipts[0])['observation'];current=obj(self.workspace.get_status(self.notebook))
   require(current.get('object_id')==nb['object_id'] and current.get('path')==self.notebook and current.get('object_type')=='NOTEBOOK','NOTEBOOK_ID_DRIFT');self.api.notebook_ids.add(nb['object_id'])
  else:nb=self.import_notebook('notebook_bootstrap',self.bootstrap)
  acl_payload={'access_control_list':[{'service_principal_name':PRINCIPAL,'permission_level':'CAN_READ'}]}
  def notebook_acl():
   permissions=obj(self.workspace.get_permissions('notebooks',str(nb['object_id'])))
   entries=permissions.get('access_control_list',[]);require(isinstance(entries,list),'NOTEBOOK_ACL_INVALID')
   for entry in entries:
    levels={p.get('permission_level') for p in entry.get('all_permissions',[])}
    if levels&{'CAN_EDIT','CAN_MANAGE'}:require(entry.get('user_name')==self.owner or entry.get('group_name')=='admins','UNTRUSTED_NOTEBOOK_WRITER')
   for entry in entries:
    if entry.get('service_principal_name')==PRINCIPAL:
     levels={p.get('permission_level') for p in entry.get('all_permissions',[])};require(levels<={'CAN_READ','CAN_RUN'},'WRITER_NOTEBOOK_WRITE_FORBIDDEN')
     if levels:return {'object_id':nb['object_id'],'acl_sha256':digest(permissions)}
   return None
  self.one('notebook_acl','set_job_acl',acl_payload,notebook_acl,lambda _:self.api.with_permit('PATCH','/api/2.0/permissions/notebooks/'+str(nb['object_id']),acl_payload,lambda:self.workspace.update_permissions('notebooks',str(nb['object_id']),access_control_list=[WorkspaceObjectAccessControlRequest(service_principal_name=PRINCIPAL,permission_level=WorkspaceObjectPermissionLevel.CAN_READ)])))
  backend={'control_table':TABLE,'control_table_id':self.table_id,'warehouse_id':WAREHOUSE,'volume_prefix':PREFIX}
  settings=creation_settings(notebook_path=self.notebook,release_id=self.package['release_id'],snapshot_backend_id=digest(backend),boundary_policy_id=digest(policy))
  if not list((self.journal/'job').glob('*.intent.json')):require(self.job_observation(settings) is None,'EXISTING_JOB_REQUIRES_RECONCILIATION')
  access=[{'user_name':self.owner,'permission_level':'IS_OWNER'},{'service_principal_name':PRINCIPAL,'permission_level':'CAN_MANAGE_RUN'}];create_payload={**settings,'access_control_list':access}
  def create_job(_):
   require(self.job_observation(settings) is None,'JOB_APPEARED_BEFORE_CREATE')
   parsed=JobSettings.from_dict(settings);kwargs={k:getattr(parsed,k) for k in settings}
   kwargs['access_control_list']=[JobAccessControlRequest.from_dict(v) for v in access]
   return self.api.with_permit('POST','/api/2.2/jobs/create',create_payload,lambda:self.jobs.create(**kwargs))
  job=self.one('job','create_job',create_payload,lambda:self.job_observation(settings),create_job);job_id=job['job_id']
  acl=obj(self.jobs.get_permissions(str(job_id)));require(acl.get('object_id')=='/jobs/'+str(job_id) and isinstance(acl.get('access_control_list'),list),'JOB_ACL_INVALID')
  writer_permission=False;owner_permission=False
  for entry in acl['access_control_list']:
   principal=entry.get('service_principal_name');user_name=entry.get('user_name');group=entry.get('group_name');levels={p.get('permission_level') for p in entry.get('all_permissions',[])}
   if principal==PRINCIPAL:require(levels<={'CAN_VIEW','CAN_MANAGE_RUN'},'WRITER_ACL_EXCESS');writer_permission='CAN_MANAGE_RUN' in levels
   elif user_name==self.owner:owner_permission='IS_OWNER' in levels
   elif levels&{'CAN_MANAGE_RUN','CAN_MANAGE','IS_OWNER'}:require(group=='admins','UNTRUSTED_JOB_ACL')
  require(writer_permission and owner_permission,'JOB_ACL_BINDING_REQUIRED')
  config={'writer':{'job_id':job_id,'writer_principal':PRINCIPAL,'cluster_id':None,'notebook_path':self.notebook,'release_id':self.package['release_id'],'snapshot_backend_id':digest(backend),'boundary_policy_id':digest(policy),'schedule_enabled':False,'compute_mode':'serverless','environment_version':'4','environment_dependencies':list(__import__('sbs.operations.provision_105',fromlist=['DEPENDENCIES']).DEPENDENCIES)},**backend,'expected_acl':acl,'policy':policy,'release_manifest':self.package['release_manifest'],'capture_mode':'sealed','capture_state_root':None}
  # backend's keys map exactly to DriverConfig; its snapshot hash includes same identity.
  DriverConfig.from_dict(config);config_raw=(canonical(config)+'\n').encode();config_pin=sha(config_raw);config_path=self.prefix+'/driver-'+config_pin+'.json'
  self.upload('config',config_path,config_raw)
  final=notebook_source(archive_path=archive_path,archive_sha=self.pin,manifest_path=self.package['release_manifest'],release_id=self.package['release_id'],config_path=config_path,config_sha=config_pin,mode=self.mode)
  previous_source=None
  if self.mode=='execute':
   require(policy['issued_at_ms']<=int(time.time()*1000)<policy['expires_at_ms'],'WRITER_POLICY_RENEWAL_REQUIRED')
   if (self.journal/'notebook_bound_preflight').exists():
    previous_source=notebook_source(archive_path=archive_path,archive_sha=self.pin,manifest_path=self.package['release_manifest'],release_id=self.package['release_id'],config_path=config_path,config_sha=config_pin,mode='preflight')
  bound=self.import_notebook('notebook_bound_'+self.mode,final,overwrite=True,previous_source=previous_source)
  require(self.job_observation(settings)['job_id']==job_id,'FINAL_JOB_DRIFT');require(obj(self.jobs.get_permissions(str(job_id)))==acl,'FINAL_ACL_DRIFT');self.rows()
  result={'status':'provisioned_paused_not_run','job_id':job_id,'control_table_id':self.table_id,'notebook':bound,'config_path':config_path,'config_sha256':config_pin,'archive_sha256':self.pin,'writer_mode':self.mode,'schedule':'PAUSED 08:00 America/Lima','cloud_acceptance':False,'cost':None,'remaining':['effective USE CATALOG/SCHEMA, warehouse CAN_USE and Volume READ/WRITE for writer','first real writer run via CloudDispatcher, output readback and recovery','sealed bootstrap does not establish live daily capture; remote capture needs separately bound config/recovery','writer administrative policy renewal before expiry','Genie certificate separate TTL5min renewal','independent E2E acceptance before enabling schedule']}
  atomic(self.journal/'result.json',result);atomic(self.journal/'driver-config.json',config);return result

def preflight(root):
 root=Path(root).resolve();record=safe_json(root/'runs/sk12-writer-portable-105.json');bundle=root/record['archive'];require(sha(bundle.read_bytes())==record['archive_sha256'],'BUNDLE_DRIFT')
 import inspect,importlib.metadata
 require(importlib.metadata.version('databricks-sdk')=='0.102.0','SDK_VERSION_MISMATCH')
 from databricks.sdk.service.jobs import JobsAPI
 from databricks.sdk.core import Config
 require('access_control_list' in inspect.signature(JobsAPI.create).parameters,'SDK_CONTRACT_INVALID')
 return {'status':'offline_preflight_passed','default_mode':'preflight','archive_sha256':record['archive_sha256'],'limits':LIMITS,'create_job_pause_status':'PAUSED','observed_job_id':None,'observed_table_id':None,'cloud_executed':False,'cost':None}

def main():
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path.cwd());p.add_argument('--execute',action='store_true');p.add_argument('--review-file',type=Path);p.add_argument('--journal',type=Path);p.add_argument('--profile');p.add_argument('--writer-mode',choices=['preflight','execute'],default='preflight');a=p.parse_args()
 if not a.execute:print(json.dumps(preflight(a.root)));return
 require(a.review_file is not None and a.journal is not None,'REVIEW_AND_JOURNAL_REQUIRED')
 review=safe_json(a.review_file);expected=review_inputs(a.root);require(review.get('files')==expected,'EXACT_REVIEW_INPUTS_REQUIRED')
 a.journal.mkdir(parents=True,exist_ok=True)
 with exclusive_lock(a.journal):
  executor=Provisioner(a.root,a.journal,review,profile=a.profile,writer_mode=a.writer_mode)
  try:print(json.dumps(executor.run()))
  finally:executor.api.session.close()

def review_inputs(root):
 root=Path(root);names=['src/sbs/operations/provision_106.py','src/sbs/operations/__init__.py','src/sbs/operations/provision_105.py','src/sbs/operations/cloud_driver.py','src/sbs/operations/cloud_dispatch.py','src/sbs/operations/shared_control.py','runs/sk12-writer-portable-105.json','runs/sk12-writer-portable-105.tar.gz']
 return {p:sha((root/p).read_bytes()) for p in names}
if __name__=='__main__':main()
