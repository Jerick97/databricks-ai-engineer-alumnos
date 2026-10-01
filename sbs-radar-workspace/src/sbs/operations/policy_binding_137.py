"""Additive137 correction of frozen130. Fresh policy130 plus config file and private notebook; maximum two writes.

No time window is emitted by preflight. Original106 policy/journal and unknown
create intent remain immutable. No Jobs mutation/run, SQL, grants or compute.
"""
from pathlib import Path
from io import BytesIO
import base64,json,time,re
from .cloud_dispatch import require,obj,digest,canonical
from .provision_105 import _write_new,step_once,DEPENDENCIES
from .provision_106 import HOST,OWNER,OWNER_ID,PRINCIPAL,TABLE,WAREHOUSE,VOLUME,PREFIX,DriverConfig,validate_table,notebook_source,normalize_source,safe_json,sha
from .job_recovery_126 import ROOT,original,bounded_text,policy_settings_unchanged
from . import atomic,exclusive_lock
LIMITS={'http':64,'writes':2}
POLICY_TTL_MS=1800000

def separate_journal(root,state):
 old=(Path(root)/'deployment/state/provision106').resolve();state=Path(state).resolve()
 require(state!=old and old not in state.parents and state not in old.parents,'JOURNAL_OVERLAP_FORBIDDEN')

def prior_observation(root,stage):
 files=list((Path(root)/'deployment/state/provision106'/stage).glob('*.observed.json'))
 require(len(files)==1,'PRIOR_OBSERVATION_REQUIRED');return files[0],safe_json(files[0])['observation']

def trusted_job_acl(acl,job_id):
 require(acl.get('object_id')=='/jobs/'+str(job_id) and isinstance(acl.get('access_control_list'),list),'JOB_ACL_IDENTITY_INVALID')
 owner=False;writer=False
 for entry in acl['access_control_list']:
  permissions=entry.get('all_permissions');require(isinstance(permissions,list),'JOB_ACL_PERMISSIONS_INVALID')
  levels={p.get('permission_level') for p in permissions}
  if entry.get('service_principal_name')==PRINCIPAL:
   require(levels<={'CAN_VIEW','CAN_MANAGE_RUN'},'WRITER_JOB_ACL_EXCESS');writer='CAN_MANAGE_RUN' in levels
  elif entry.get('user_name')==OWNER:owner='IS_OWNER' in levels
  elif levels&{'CAN_MANAGE_RUN','CAN_MANAGE','IS_OWNER'}:require(entry.get('group_name')=='admins','UNTRUSTED_JOB_RUNNER')
 require(owner and writer,'JOB_OWNER_AND_WRITER_REQUIRED')
 return acl

def trusted_notebook_acl(acl,object_id):
 require(acl.get('object_id')=='/notebooks/'+str(object_id) and isinstance(acl.get('access_control_list'),list),'NOTEBOOK_ACL_IDENTITY_INVALID')
 writer=False
 for entry in acl['access_control_list']:
  permissions=entry.get('all_permissions');require(isinstance(permissions,list),'NOTEBOOK_ACL_PERMISSIONS_INVALID')
  levels={p.get('permission_level') for p in permissions}
  if levels&{'CAN_EDIT','CAN_MANAGE'}:require(entry.get('user_name')==OWNER or entry.get('group_name')=='admins','UNTRUSTED_NOTEBOOK_WRITER')
  if entry.get('service_principal_name')==PRINCIPAL:
   require(levels<={'CAN_READ','CAN_RUN'},'WRITER_NOTEBOOK_WRITE_FORBIDDEN');writer=bool(levels)
 require(writer,'WRITER_NOTEBOOK_READ_REQUIRED')
 return acl

def review_inputs(root=ROOT):
 root=Path(root);names=['src/sbs/operations/policy_binding_137.py','runs/sk11-policy130-dependency.json','runs/sk12-writer-portable-105.json','deployment/state/provision106/policy.json','runs/sk11-policy-binding-137-imports.json']
 names += [str(prior_observation(root,s)[0].relative_to(root)) for s in ('table','notebook_bootstrap118')]
 names.append(str(original(root)[0].relative_to(root)))
 imports=safe_json(root/'runs/sk11-policy-binding-137-imports.json')['modules']
 require(isinstance(imports,dict) and all(p.startswith('src/sbs/') and p.endswith('.py') and '..' not in Path(p).parts for p in imports),'IMPORT_CLOSURE_INVALID')
 return {p:sha((root/p).read_bytes()) for p in sorted(set(names)|set(imports)|{'src/sbs/operations/job_recovery_126.py'})}

class BindingApi:
 def __init__(self,cfg,*,state,authorize,prefix,notebook,session=None):
  import requests
  from urllib.parse import urlsplit
  u=urlsplit(cfg.host);require(u.scheme=='https' and u.hostname==HOST and u.port is None and u.path in ('','/') and not any((u.username,u.password,u.query,u.fragment)),'HOST_INVALID')
  self._cfg=cfg;self.state=Path(state);self.authorize=authorize;self.prefix=prefix;self.notebook=notebook;self.config_path=None;self.config_pin=None;self.notebook_pin=None
  self.session=session or requests.Session();require(all(a.max_retries.total==0 for a in self.session.adapters.values()),'RETRIES_FORBIDDEN')
 def do(self,method,path=None,*,query=None,body=None,headers=None,data=None,raw=False,response_headers=None,**extra):
  reads={'/api/2.0/preview/scim/v2/Me','/api/2.0/preview/scim/v2/ServicePrincipals/72803555975940','/api/2.2/jobs/list','/api/2.2/jobs/get','/api/2.1/unity-catalog/tables/'+TABLE,'/api/2.1/unity-catalog/volumes/'+VOLUME,'/api/2.0/sql/warehouses/'+WAREHOUSE,'/api/2.0/workspace/get-status','/api/2.0/workspace/export'}
  read=method=='GET' and (path in reads or re.fullmatch('/api/2.0/permissions/(jobs|notebooks)/[0-9]+',path or '') or path=='/api/2.0/fs/files'+self.prefix+'/code.tar.gz' or (self.config_path is not None and path=='/api/2.0/fs/files'+self.config_path))
  write=not read
  require(not extra,'API_EXTRA_FORBIDDEN')
  if write:
   if method=='PUT' and self.config_path and path=='/api/2.0/fs/files'+self.config_path:
    require(body is None and query=={'overwrite':False} and hasattr(data,'read'),'CONFIG_UPLOAD_INVALID');content=data.read();require(len(content)<=65536 and sha(content)==self.config_pin,'CONFIG_BYTES_INVALID');data=BytesIO(content)
   elif method=='POST' and path=='/api/2.0/workspace/import':
    require(isinstance(body,dict) and set(body)=={'path','content','format','language','overwrite'} and body['path']==self.notebook and body['format']=='SOURCE' and body['language']=='PYTHON' and body['overwrite'] is True,'NOTEBOOK_IMPORT_INVALID')
    require(sha(normalize_source(base64.b64decode(body['content'],validate=True)))==self.notebook_pin,'NOTEBOOK_CONTENT_INVALID')
   else:raise ValueError('BINDING_MUTATION_FORBIDDEN')
  self.authorize();bp=self.state/'budget.json';b=safe_json(bp) if bp.exists() else {'http':0,'writes':0}
  require(set(b)==set(LIMITS) and all(type(b[k]) is int and 0<=b[k]<=LIMITS[k] for k in LIMITS),'BUDGET_INVALID');b['http']+=1;b['writes']+=int(write);require(all(b[k]<=LIMITS[k] for k in LIMITS),'BINDING_BUDGET_EXCEEDED');atomic(bp,b)
  auth=self._cfg.authenticate();self.authorize()
  try:r=self.session.request(method,'https://'+HOST+path,params={k:str(v).lower() if type(v) is bool else v for k,v in (query or {}).items()},json=body,data=data,headers={**(headers or {}),**auth},timeout=(10,60),allow_redirects=False,stream=True)
  except Exception:raise ValueError('BINDING_TRANSPORT_UNKNOWN') from None
  receipt={'method':method,'path':path,'status':r.status_code,'request_ids':{k:bounded_text(r.headers.get(k),256) for k in ('x-databricks-request-id','x-request-id') if r.headers.get(k)}}
  try:
   _write_new(self.state/('http-%03d-status.json'%b['http']),receipt)
   content=r.raw.read(33554433,decode_content=True);require(len(content)<=33554432,'RESPONSE_LIMIT');self.authorize()
   if not 200<=r.status_code<300:
    try:error=json.loads(content)
    except Exception:error={}
    if not isinstance(error,dict):error={}
    _write_new(self.state/('http-%03d-error.json'%b['http']),{**receipt,'error_code':bounded_text(error.get('error_code'),100),'message':bounded_text(error.get('message'),1000)})
    if r.status_code==404 and error.get('error_code') in ('RESOURCE_DOES_NOT_EXIST','NOT_FOUND'):raise FileNotFoundError('REMOTE_FILE_ABSENT')
    raise ValueError('BINDING_HTTP_REJECTED')
   if raw:return {'contents':BytesIO(content),**{k:r.headers.get(k) for k in response_headers or []}}
   return json.loads(content) if content else {}
  finally:r.close()

class PolicyBinder130:
 def __init__(self,root,state,review,*,profile=None,config_factory=None,session=None,clock=None):
  separate_journal(root,state)
  from databricks.sdk.service import jobs,workspace,catalog,sql,files,iam
  import importlib.metadata
  require(importlib.metadata.version('databricks-sdk')=='0.102.0','SDK_VERSION_MISMATCH')
  self.root=Path(root).resolve();self.state=Path(state).resolve();self.review=review;self.clock=clock or (lambda:int(time.time()*1000))
  require(review.get('files')==review_inputs(self.root),'BINDING_REVIEW_INPUTS_REQUIRED');self.authorize()
  self.package=safe_json(self.root/'runs/sk12-writer-portable-105.json');self.prefix=PREFIX+'/bootstrap106/'+self.package['archive_sha256']
  _,self.nb_prior=prior_observation(self.root,'notebook_bootstrap118');_,self.table_prior=prior_observation(self.root,'table');self.notebook=self.nb_prior['path']
  self.payload=original(self.root)[2];self.expected={k:v for k,v in self.payload.items() if k!='access_control_list'};policy_settings_unchanged(self.root)
  if config_factory:cfg=config_factory()
  else:
   from databricks.sdk.core import Config
   cfg=Config(profile=profile) if profile else Config()
  self.api=BindingApi(cfg,state=self.state,authorize=self.authorize,prefix=self.prefix,notebook=self.notebook,session=session)
  self.jobs=jobs.JobsAPI(self.api);self.workspace=workspace.WorkspaceAPI(self.api);self.tables=catalog.TablesAPI(self.api);self.volumes=catalog.VolumesAPI(self.api);self.warehouses=sql.WarehousesAPI(self.api);self.files=files.FilesAPI(self.api);self.me=iam.CurrentUserAPI(self.api)
 def authorize(self):
  r=self.review;now=self.clock()
  require(r.get('approved') is True and r.get('scope')=='policy_binding130' and r.get('limits')==LIMITS and r.get('policy_ttl_ms')==POLICY_TTL_MS,'BINDING_REVIEW_REQUIRED')
  require(type(now) is int and type(r.get('issued_at_ms')) is int and type(r.get('expires_at_ms')) is int and r['issued_at_ms']<=now<r['expires_at_ms'] and 0<r['expires_at_ms']-r['issued_at_ms']<=1800000,'BINDING_WINDOW_INVALID')
  policy_path=self.state/'policy130.json'
  if policy_path.exists():
   policy=safe_json(policy_path).get('policy',{})
   require(type(policy.get('issued_at_ms')) is int and type(policy.get('expires_at_ms')) is int and policy['issued_at_ms']<=now<policy['expires_at_ms'],'NEW_POLICY_VERSION_REQUIRED')
  for p,pin in r['files'].items():require(sha((self.root/p).read_bytes())==pin,'BINDING_INPUT_DRIFT')
 def snapshot(self):
  user=obj(self.me.me());require(user.get('id')==OWNER_ID and user.get('userName')==OWNER and user.get('active') is True,'OPERATOR_IDENTITY_INVALID')
  sp=self.api.do('GET','/api/2.0/preview/scim/v2/ServicePrincipals/72803555975940');require(sp.get('id')=='72803555975940' and sp.get('applicationId')==PRINCIPAL and sp.get('active') is True,'WRITER_IDENTITY_INVALID')
  listing=self.api.do('GET','/api/2.2/jobs/list',query={'name':'sbs-radar-single-writer','limit':25,'expand_tasks':True})
  require(not listing.get('next_page_token') and not listing.get('has_more') and isinstance(listing.get('jobs'),list) and len(listing['jobs'])==1,'EXACTLY_ONE_JOB_REQUIRED')
  candidate=listing['jobs'][0].get('job_id');require(type(candidate) is int and candidate>0,'JOB_ID_INVALID');job=obj(self.jobs.get(candidate))
  require(job.get('job_id')==candidate and job.get('run_as_user_name')==PRINCIPAL and not job.get('next_page_token') and all(job.get('settings',{}).get(k)==v for k,v in self.expected.items()) and not any(job.get('settings',{}).get(k) for k in ('continuous','trigger','git_source','job_clusters')),'JOB_SETTINGS_INVALID')
  acl=trusted_job_acl(obj(self.jobs.get_permissions(str(candidate))),candidate)
  table=validate_table(obj(self.tables.get(TABLE,include_browse=False)),owner=OWNER);require(table['table_id']==self.table_prior['table_id'],'CONTROL_TABLE_ID_DRIFT')
  volume=obj(self.volumes.read(VOLUME));require(volume.get('full_name')==VOLUME,'VOLUME_IDENTITY_INVALID')
  warehouse=obj(self.warehouses.get(WAREHOUSE));require(warehouse.get('id')==WAREHOUSE,'WAREHOUSE_IDENTITY_INVALID')
  nb=obj(self.workspace.get_status(self.notebook));require(nb.get('path')==self.notebook and nb.get('object_type')=='NOTEBOOK' and nb.get('object_id')==self.nb_prior['object_id'],'NOTEBOOK_IDENTITY_INVALID')
  nb_acl=trusted_notebook_acl(obj(self.workspace.get_permissions('notebooks',str(nb['object_id']))),nb['object_id'])
  return {'job_id':candidate,'job_acl':acl,'table_id':table['table_id'],'notebook_id':nb['object_id'],'notebook_acl_sha256':digest(nb_acl),'warehouse_state':warehouse.get('state'),'settings_sha256':digest(self.expected),'metadata_basis':'fresh authenticated GET; admin exclusivity remains explicit assumption'}
 def notebook_bytes(self):
  from databricks.sdk.service.workspace import ExportFormat
  out=obj(self.workspace.export(self.notebook,format=ExportFormat.SOURCE));return normalize_source(base64.b64decode(out.get('content',''),validate=True))
 def remote_file(self,path,pin):
  try:r=self.files.download(path)
  except FileNotFoundError:return None
  try:content=r.contents.read(33554433)
  finally:r.contents.close()
  require(sha(content)==pin,'REMOTE_FILE_PIN_MISMATCH');return {'path':path,'sha256':pin,'bytes':len(content)}
 def one(self,name,step_id,payload,observe,effect):
  folder=self.state/name;folder.mkdir(exist_ok=True)
  step={'step_id':step_id,'operation':'policy_binding130_'+name,'payload':payload,'precondition':'fresh GET identities/settings/trusted ACL; new immutable policy130 document'}
  result=step_once(folder,step,authorize=self.authorize,observe=observe,effect=effect);require(result['status']=='confirmed_by_readback','BINDING_RECONCILIATION_REQUIRED');return result['observation']
 def run(self):
  from databricks.sdk.service.workspace import ImportFormat,Language
  before=self.snapshot()
  require(self.remote_file(self.prefix+'/code.tar.gz',self.package['archive_sha256']) is not None,'REMOTE_ARCHIVE_REQUIRED')
  old_path=self.root/'deployment/state/provision106/policy.json';old_raw=old_path.read_bytes();old=safe_json(old_path)
  policy_path=self.state/'policy130.json'
  if policy_path.exists():
   document=safe_json(policy_path);require(document.get('version')=='writer-admin-policy130' and document.get('supersedes_sha256')==sha(old_raw),'POLICY_LINEAGE_INVALID')
   policy=document['policy'];require(policy['issued_at_ms']<=self.clock()<policy['expires_at_ms'],'NEW_POLICY_VERSION_REQUIRED')
   require(document['binding']=={'job_id':before['job_id'],'table_id':before['table_id'],'job_acl_sha256':digest(before['job_acl']),'notebook_id':before['notebook_id']},'POLICY_METADATA_DRIFT')
  else:
   # Never issue a window until fresh identity/settings/ACL/archive have succeeded.
   require(sha(self.notebook_bytes())==self.nb_prior['source_sha256'],'BOOTSTRAP_NOTEBOOK_CHANGED')
   issued=self.clock();require(type(issued) is int,'CLOCK_INVALID')
   policy={**old,'issued_at_ms':issued,'expires_at_ms':issued+POLICY_TTL_MS}
   document={'version':'writer-admin-policy130','supersedes_sha256':sha(old_raw),'policy':policy,'binding':{'job_id':before['job_id'],'table_id':before['table_id'],'job_acl_sha256':digest(before['job_acl']),'notebook_id':before['notebook_id']},'basis':before['metadata_basis']}
   _write_new(policy_path,document)
  require(policy.get('trusted_administrators')==[OWNER],'POLICY_OWNER_INVALID')
  backend={'control_table':TABLE,'control_table_id':before['table_id'],'warehouse_id':WAREHOUSE,'volume_prefix':PREFIX}
  writer={'job_id':before['job_id'],'writer_principal':PRINCIPAL,'cluster_id':None,'notebook_path':self.notebook,'release_id':self.package['release_id'],'snapshot_backend_id':digest(backend),'boundary_policy_id':digest(policy),'schedule_enabled':False,'compute_mode':'serverless','environment_version':'4','environment_dependencies':list(DEPENDENCIES)}
  config={'writer':writer,**backend,'expected_acl':before['job_acl'],'policy':policy,'release_manifest':self.package['release_manifest'],'capture_mode':'sealed','capture_state_root':None}
  parsed=DriverConfig.from_dict(config)
  from .cloud_dispatch import job_settings
  require(job_settings(parsed.writer)==self.expected,'NEW_POLICY_CHANGED_JOB_SETTINGS')
  raw=(canonical(config)+'\n').encode();pin=sha(raw);path=self.prefix+'/driver-policy130-'+pin+'.json'
  self.api.config_path=path;self.api.config_pin=pin
  config_result=self.one('config130','upload_config',{'path':path,'sha256':pin,'bytes':len(raw)},lambda:self.remote_file(path,pin),lambda _:self.files.upload(path,BytesIO(raw),overwrite=False))
  source=notebook_source(archive_path=self.prefix+'/code.tar.gz',archive_sha=self.package['archive_sha256'],manifest_path=self.package['release_manifest'],release_id=self.package['release_id'],config_path=path,config_sha=pin,mode='execute')
  compile(source,'writer-policy130','exec');source_pin=sha(normalize_source(source.encode()));self.api.notebook_pin=source_pin
  def notebook_observe():
   # ACL identity is checked again immediately before an import or reconciliation.
   status=obj(self.workspace.get_status(self.notebook));require(status.get('object_id')==before['notebook_id'] and status.get('path')==self.notebook,'NOTEBOOK_PATH_ID_DRIFT')
   trusted_notebook_acl(obj(self.workspace.get_permissions('notebooks',str(before['notebook_id']))),before['notebook_id'])
   content=self.notebook_bytes();observed=sha(content)
   if observed==source_pin:return {'object_id':before['notebook_id'],'path':self.notebook,'source_sha256':source_pin}
   require(observed==self.nb_prior['source_sha256'],'NOTEBOOK_CHANGED_BEFORE_BINDING');return None
  payload={'path':self.notebook,'content':base64.b64encode(source.encode()).decode(),'format':'SOURCE','language':'PYTHON','overwrite':True}
  nb_result=self.one('notebook130','import_notebook',payload,notebook_observe,lambda _:self.workspace.import_(self.notebook,content=payload['content'],format=ImportFormat.SOURCE,language=Language.PYTHON,overwrite=True))
  after=self.snapshot();require(all(after[k]==before[k] for k in ('job_id','job_acl','table_id','notebook_id','notebook_acl_sha256','settings_sha256')),'FINAL_BINDING_DRIFT')
  require(old_path.read_bytes()==old_raw,'OLD_POLICY_CHANGED')
  self.authorize()
  atomic(self.state/'driver-config130.json',config)
  result={'status':'fresh_policy_bound_job_paused','job_id':before['job_id'],'config':config_result,'notebook':nb_result,'policy_document_sha256':sha(policy_path.read_bytes()),'policy_issued_at_ms':policy['issued_at_ms'],'policy_expires_at_ms':policy['expires_at_ms'],'old_policy_sha256':sha(old_raw),'job_settings_unchanged':True,'warehouse_state':after['warehouse_state'],'budget':safe_json(self.state/'budget.json'),'job_run':False,'cloud_acceptance':False,'cost':None,'remaining':['first real Job run via CloudDispatcher ledger and actual subject','warehouse RUNNING before writer executes','output publication readback and failure/recovery','future operational policy renewal and separate Genie5min renewal']}
  atomic(self.state/'result.json',result);return result

def preflight(root=ROOT):
 return {'status':'offline_binding_ready','limits':LIMITS,'policy_ttl_ms':POLICY_TTL_MS,'policy_emitted':False,'current_window_emitted':False,'settings_check':policy_settings_unchanged(root),'review_inputs':review_inputs(root),'cloud_executed':False,'cost':None}

def main():
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--execute',action='store_true');p.add_argument('--review-file',type=Path);p.add_argument('--journal',type=Path);p.add_argument('--profile');a=p.parse_args()
 if not a.execute:print(json.dumps(preflight(a.root)));return
 require(a.review_file is not None and a.journal is not None,'REVIEW_AND_SEPARATE_JOURNAL_REQUIRED');separate_journal(a.root,a.journal);a.journal.mkdir(parents=True,exist_ok=True)
 with exclusive_lock(a.journal):
  runner=PolicyBinder130(a.root,a.journal,safe_json(a.review_file),profile=a.profile)
  try:print(json.dumps(runner.run()))
  finally:runner.api.session.close()
if __name__=='__main__':main()
