"""Operator167: reviewed config + PENDING core, original dispatcher, bound authority.

Existing Job stays PAUSED. Only existing configVolume and privateNotebook writes.
No permission mutation, retries, rerun or fake ACL. Default offline preflight.
"""
from pathlib import Path
from types import SimpleNamespace
from io import BytesIO
import base64,json,time,re
from .provision_106 import HOST,OWNER,OWNER_ID,PRINCIPAL,TABLE,WAREHOUSE,VOLUME,PREFIX,DriverConfig,validate_table,safe_json,normalize_source
from .job_recovery_126 import ROOT,original,bounded_text
from .provision_105 import _write_new,step_once,DEPENDENCIES
from .policy_binding_137 import separate_journal
from .cloud_dispatch import job_settings,CloudDispatcher
from .cloud_driver import CloudDriver
from .job_defaults_146 import DefaultsApi146
from .writer_authority_167 import require,sha,digest,canonical,parse_source,trusted_acls,NOTEBOOK_ID,MAX_TTL
from .writer_delivery_167 import build_delivery,render
from . import atomic,exclusive_lock
JOB=989326861421503
NOTEBOOK='/Users/sociosdosmilveintiseis@gmail.com/sbs-radar-writer118-5af111bd1d790c6c'
LIMITS={'http':128,'sql':24,'config_put':1,'notebook_import':2,'run_now':1}
REQUEST='sbs-writer-first-167'
def review_inputs(root=ROOT):
 root=Path(root);names=set(safe_json(root/'runs/sk11-dispatch-146-imports.json')['modules'])|set(safe_json(root/'runs/sk11-writer-167-imports.json')['modules'])|{'src/sbs/operations/writer_authority_167.py','src/sbs/operations/writer_delivery_167.py','src/sbs/operations/writer_operator_167.py','runs/sk09-writer-authority-164-review.json','runs/sk12-writer-portable-105.json','deployment/state/policy-binding146/driver-config146.json','deployment/writer_diagnostic_158_notebook.py'}
 names.add(str(original(root)[0].relative_to(root)));return {p:sha((root/p).read_bytes()) for p in sorted(names)}
class OperatorApi167:
 def __init__(self,cfg,state,authorize,*,session=None):
  import requests
  require(cfg.host.rstrip('/')=='https://'+HOST,'OPERATOR167_HOST');self._cfg=cfg;self.state=Path(state);self.authorize=authorize;self.session=session or requests.Session()
  require(all(a.max_retries.total==0 for a in self.session.adapters.values()),'OPERATOR167_RETRIES');self.config_path=None;self.config_sha=None;self.import_pin=None
  token=digest({'job_id':JOB,'request_id':REQUEST});self.run_body={'job_id':JOB,'idempotency_token':token,'job_parameters':{'request_id':token,'release_id':'c2e2b29394d3796e2753fbe1d4c3df44137a88391a118044b16c51a74dab2f32'},'queue':{'enabled':True}}
 def do(self,method,path=None,*,query=None,body=None,headers=None,data=None,raw=False,response_headers=None,**extra):
  require(not extra and isinstance(path,str) and path.startswith('/api/') and not any(x in path for x in ('?','#','..')),'OPERATOR167_PATH')
  kind=None
  if method=='GET':kind='http'
  elif method=='POST' and path=='/api/2.0/sql/statements':
   table='.'.join('`'+x+'`' for x in TABLE.split('.'));require(isinstance(body,dict) and body.get('warehouse_id')==WAREHOUSE and body.get('statement') in {'SELECT control_id, revision, state_json FROM '+table,'UPDATE '+table+' SET revision = revision + 1, state_json = :state WHERE control_id = :control AND revision = :revision'},'OPERATOR167_SQL_SCOPE');kind='sql'
  elif method=='PUT' and self.config_path and path=='/api/2.0/fs/files'+self.config_path:
   require(query=={'overwrite':False} and body is None and hasattr(data,'read'),'OPERATOR167_CONFIG_UPLOAD');content=data.read();require(len(content)<=65536 and sha(content)==self.config_sha,'OPERATOR167_CONFIG_PIN');data=BytesIO(content);kind='config_put'
  elif method=='POST' and path=='/api/2.0/workspace/import':
   require(isinstance(body,dict) and set(body)=={'path','content','format','language','overwrite'} and body['path']==NOTEBOOK and body['format']=='SOURCE' and body['language']=='PYTHON' and body['overwrite'] is True and sha(normalize_source(base64.b64decode(body['content'],validate=True)))==self.import_pin,'OPERATOR167_NOTEBOOK_SCOPE');kind='notebook_import'
  elif method=='POST' and path=='/api/2.2/jobs/run-now':require(canonical(body)==canonical(self.run_body),'OPERATOR167_RUN_SCOPE');kind='run_now'
  require(kind is not None,'OPERATOR167_MUTATION_FORBIDDEN');self.authorize();bp=self.state/'budget.json';b=safe_json(bp) if bp.exists() else dict.fromkeys(LIMITS,0)
  require(set(b)==set(LIMITS) and all(type(b[k]) is int and 0<=b[k]<=LIMITS[k] for k in b),'OPERATOR167_BUDGET_INVALID');b['http']+=1
  if kind!='http':b[kind]+=1
  require(all(b[k]<=LIMITS[k] for k in b),'OPERATOR167_BUDGET_EXCEEDED');atomic(bp,b)
  auth=self._cfg.authenticate();self.authorize();prefix=self.state/('http-%03d'%b['http'])
  _write_new(Path(str(prefix)+'-intent.json'),{'method':method,'path':path,'body_sha256':digest(body) if body is not None else None})
  try:r=self.session.request(method,'https://'+HOST+path,params={k:str(v).lower() if type(v) is bool else v for k,v in (query or {}).items()},json=body,data=data,headers={**(headers or {}),**auth},timeout=(10,60),allow_redirects=False,stream=True)
  except Exception:raise ValueError('OPERATOR167_TRANSPORT_UNKNOWN') from None
  try:
   _write_new(Path(str(prefix)+'-status.json'),{'status':r.status_code,'path':path,'method':method,'request_id':bounded_text(r.headers.get('x-request-id'),256)})
   content=r.raw.read(33554433,decode_content=True);require(len(content)<=33554432,'OPERATOR167_RESPONSE_CAP')
   if not 200<=r.status_code<300:
    try:error=json.loads(content)
    except Exception:error={}
    _write_new(Path(str(prefix)+'-error.json'),{'status':r.status_code,'error_code':bounded_text(error.get('error_code'),100),'message':bounded_text(error.get('message'),1000)})
    if r.status_code==404 and error.get('error_code') in ('NOT_FOUND','RESOURCE_DOES_NOT_EXIST'):raise FileNotFoundError('OPERATOR167_ABSENT')
    raise ValueError('OPERATOR167_HTTP_REJECTED')
   self.authorize()
   if raw:return {'contents':BytesIO(content),**{k:r.headers.get(k) for k in response_headers or []}}
   value=json.loads(content) if content else {};require(isinstance(value,dict),'OPERATOR167_RESPONSE_OBJECT');return value
  finally:r.close()

class Operator167:
 def __init__(self,root,state,review,*,profile=None,config_factory=None,session=None,clock=None):
  import importlib.metadata
  require(importlib.metadata.version('databricks-sdk')=='0.102.0','SDK_VERSION');self.root=Path(root).resolve();self.state=Path(state).resolve();self.review=review;self.clock=clock or(lambda:int(time.time()*1000))
  separate_journal(root,state)
  for old in ('policy-binding146','dispatch146','writer-diagnostic158','diagnostic-monitor162'):
   historical=(self.root/'deployment/state'/old).resolve();require(self.state!=historical and historical not in self.state.parents and self.state not in historical.parents,'OPERATOR167_HISTORICAL_OVERLAP')
  require(review.get('files')==review_inputs(root),'OPERATOR167_REVIEW_INPUTS');self.authorize()
  from databricks.sdk.core import Config
  from databricks.sdk.service import jobs,catalog,sql,files,iam,workspace
  cfg=config_factory() if config_factory else Config(profile=profile) if profile else Config();self.api=OperatorApi167(cfg,self.state,self.authorize,session=session)
  self.expected={k:v for k,v in original(self.root)[2].items() if k!='access_control_list'}
  self.services=SimpleNamespace(api=self.api,jobs=jobs.JobsAPI(DefaultsApi146(self.api,self.expected,JOB,lambda r:atomic(self.state/('job-raw-'+digest(r)+'.json'),r))),tables=catalog.TablesAPI(self.api),warehouses=sql.WarehousesAPI(self.api),statement_execution=sql.StatementExecutionAPI(self.api),files=files.FilesAPI(self.api),current_user=iam.CurrentUserAPI(self.api),workspace=workspace.WorkspaceAPI(self.api))
 def authorize(self):
  r=self.review;now=self.clock();require(r.get('approved') is True and r.get('scope')=='writer_operator167_two_phase' and r.get('limits')==LIMITS and r.get('request_id')==REQUEST,'OPERATOR167_REVIEW_REQUIRED')
  require(type(r.get('issued_at_ms')) is int and type(r.get('expires_at_ms')) is int and r['issued_at_ms']<=now<r['expires_at_ms'] and 0<r['expires_at_ms']-r['issued_at_ms']<=1800000,'OPERATOR167_REVIEW_EXPIRED')
  for p,h in r['files'].items():require(sha((self.root/p).read_bytes())==h,'OPERATOR167_INPUT_DRIFT')
  pp=self.state/'policy167.json'
  if pp.exists():policy=safe_json(pp)['policy'];require(policy['issued_at_ms']<=now<policy['expires_at_ms'],'OPERATOR167_POLICY_EXPIRED')
  ap=self.state/'authority167.json'
  if ap.exists():a=safe_json(ap);require(a['issued_at_ms']<=now<a['expires_at_ms'],'OPERATOR167_ATTESTATION_EXPIRED')
 def snapshot(self):
  from .writer_authority_167 import strict_settings,obj
  me=obj(self.services.current_user.me());require(me.get('id')==OWNER_ID and me.get('userName')==OWNER and me.get('active') is True,'OPERATOR167_IDENTITY')
  raw=self.api.do('GET','/api/2.2/jobs/get',query={'job_id':JOB});require(raw.get('job_id')==JOB and raw.get('run_as_user_name')==PRINCIPAL,'OPERATOR167_JOB_IDENTITY');settings_pin=strict_settings(raw,self.expected)
  acl=self.api.do('GET','/api/2.0/permissions/jobs/'+str(JOB));nb_acl=self.api.do('GET','/api/2.0/permissions/notebooks/'+str(NOTEBOOK_ID));trusted_acls(acl,nb_acl,JOB,PRINCIPAL)
  nb=self.api.do('GET','/api/2.0/workspace/get-status',query={'path':NOTEBOOK});require(nb.get('path')==NOTEBOOK and nb.get('object_id')==NOTEBOOK_ID and nb.get('object_type')=='NOTEBOOK','OPERATOR167_NOTEBOOK_IDENTITY')
  table=validate_table(obj(self.services.tables.get(TABLE,include_browse=False)),owner=OWNER);prior=safe_json(self.root/'deployment/state/policy-binding146/driver-config146.json');require(table['table_id']==prior['control_table_id'],'OPERATOR167_TABLE_CHANGED')
  wh=obj(self.services.warehouses.get(WAREHOUSE));require(wh.get('id')==WAREHOUSE and wh.get('state')=='RUNNING','OPERATOR167_WAREHOUSE_NOT_RUNNING')
  return {'observed_at_ms':self.clock(),'settings_sha256':settings_pin,'job_acl':acl,'notebook_acl':nb_acl,'notebook_id':NOTEBOOK_ID,'notebook_path':NOTEBOOK,'operator':{'id':OWNER_ID,'userName':OWNER}}
 def export(self):return normalize_source(base64.b64decode(self.api.do('GET','/api/2.0/workspace/export',query={'path':NOTEBOOK,'format':'SOURCE'})['content'],validate=True))
 def one(self,name,step_id,payload,observe,effect):
  folder=self.state/name;folder.mkdir(exist_ok=True);step={'step_id':step_id,'operation':'operator167_'+name,'payload':payload,'precondition':'reviewed167 protected authority and current policy'}
  result=step_once(folder,step,authorize=self.authorize,observe=observe,effect=effect);require(result['status']=='confirmed_by_readback','OPERATOR167_RECONCILE_REQUIRED');return result['observation']
 def import_source(self,name,source,allowed_previous):
  pin=sha(normalize_source(source.encode()));self.api.import_pin=pin
  def observe():
   raw=self.export();current=sha(raw)
   if current==pin:return {'notebook_id':NOTEBOOK_ID,'source_sha256':pin}
   require(current in allowed_previous,'OPERATOR167_SOURCE_CHANGED');return None
  payload={'path':NOTEBOOK,'content':base64.b64encode(source.encode()).decode(),'format':'SOURCE','language':'PYTHON','overwrite':True}
  return self.one(name,'import_notebook',payload,observe,lambda _:self.api.do('POST','/api/2.0/workspace/import',body=payload))
 def run(self):
  from .writer_authority_167 import obj
  before=self.snapshot();old=safe_json(self.root/'deployment/state/policy-binding146/driver-config146.json');package=safe_json(self.root/'runs/sk12-writer-portable-105.json')
  pp=self.state/'policy167.json'
  if not pp.exists():
   issued=self.clock();policy={**old['policy'],'issued_at_ms':issued,'expires_at_ms':issued+1800000};_write_new(pp,{'policy':policy,'supersedes146_sha256':sha((self.root/'deployment/state/policy-binding146/driver-config146.json').read_bytes())})
  policy=safe_json(pp)['policy'];config={**old,'writer':{**old['writer'],'boundary_policy_id':digest(policy)},'expected_acl':before['job_acl'],'policy':policy};parsed=DriverConfig.from_dict(config);require(job_settings(parsed.writer)==self.expected,'OPERATOR167_SETTINGS_CHANGED')
  raw=(canonical(config)+'\n').encode();config_pin=sha(raw);config_path=PREFIX+'/bootstrap106/'+package['archive_sha256']+'/driver-operator167-'+config_pin+'.json';self.api.config_path=config_path;self.api.config_sha=config_pin
  def config_observe():
   try:response=self.services.files.download(config_path)
   except FileNotFoundError:return None
   data=response.contents.read();response.contents.close();require(sha(data)==config_pin,'OPERATOR167_REMOTE_CONFIG_CHANGED');return {'path':config_path,'sha256':config_pin}
  self.one('config167','upload_config',{'path':config_path,'sha256':config_pin},config_observe,lambda _:self.services.files.upload(config_path,BytesIO(raw),overwrite=False))
  delivery=build_delivery(archive_path=PREFIX+'/bootstrap106/'+package['archive_sha256']+'/code.tar.gz',archive_sha=package['archive_sha256'],manifest_path=package['release_manifest'],release_id=package['release_id'],config_path=config_path,config_sha=config_pin,job_id=JOB,request_id=REQUEST)
  pending=render(delivery);pending_pin=sha(normalize_source(pending.encode()));ap=self.state/'authority167.json'
  if not ap.exists():self.import_source('pending167',pending,{sha(normalize_source((self.root/'deployment/writer_diagnostic_158_notebook.py').read_bytes()))})
  if not (self.state/'prelaunch.json').exists():_write_new(self.state/'prelaunch.json',self.snapshot())
  pre=safe_json(self.state/'prelaunch.json')
  # Existing operator dispatcher retains real ACLGET + SharedLedger/CAS fencing.
  driver=CloudDriver(parsed,self.services,evidence_mode='real');record=driver.dispatcher.request(REQUEST)
  atomic(self.state/'dispatch167.json',{'request':record,'budget':safe_json(self.state/'budget.json')})
  require(record.get('status')=='submitted' and type(record.get('run_id')) is int and record['run_id']>0,'OPERATOR167_SUBMISSION_NOT_CONFIRMED')
  rid=record['run_id'];run=self.api.do('GET','/api/2.2/jobs/runs/get',query={'run_id':rid,'include_resolved_values':True});require(run.get('job_id')==JOB and run.get('run_id')==rid and run.get('state',{}).get('life_cycle_state') in ('PENDING','RUNNING','QUEUED','BLOCKED'),'OPERATOR167_RUN_NOT_ACTIVE')
  post=self.snapshot()
  require(pre['settings_sha256']==post['settings_sha256'] and pre['job_acl']==post['job_acl'] and pre['notebook_acl']==post['notebook_acl'],'OPERATOR167_PRE_POST_DRIFT')
  if not ap.exists():
   issued=self.clock();a={'version':'writer-authority167','state':'AUTHORIZED','issuer':{'id':OWNER_ID,'userName':OWNER},'issued_at_ms':issued,'expires_at_ms':min(issued+MAX_TTL,policy['expires_at_ms']),'job_id':JOB,'run_id':rid,'request_token':delivery['request_token'],'request_id':REQUEST,'writer_principal':PRINCIPAL,'release_id':parsed.writer.release_id,'snapshot_backend_id':parsed.writer.snapshot_backend_id,'policy_id':parsed.writer.boundary_policy_id,'notebook_id':NOTEBOOK_ID,'notebook_path':NOTEBOOK,'delivery_sha256':digest(delivery),'pre':pre,'post':post};require(issued-pre['observed_at_ms']<=MAX_TTL,'OPERATOR167_PRELAUNCH_TOO_OLD');_write_new(ap,a)
  a=safe_json(ap);require(a['run_id']==rid and a['delivery_sha256']==digest(delivery),'OPERATOR167_AUTHORITY_BINDING_CHANGED')
  bound=render(delivery,a);self.import_source('authorized167',bound,{pending_pin});final=self.snapshot();self.authorize()
  require(all(final[k]==post[k] for k in ('settings_sha256','job_acl','notebook_acl')),'OPERATOR167_FINAL_DRIFT')
  atomic(self.state/'driver-config167.json',config);atomic(self.state/'delivery167.json',delivery)
  result={'status':'operator_attestation_delivered_not_writer_accepted','job_id':JOB,'run_id':rid,'authority_sha256':digest(a),'authority_expires_at_ms':a['expires_at_ms'],'budget':safe_json(self.state/'budget.json'),'writer_acceptance':False,'publication_readback_required':True,'cost':None};atomic(self.state/'result.json',result);return result

def main():
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');p.add_argument('--review-file',type=Path);p.add_argument('--profile');a=p.parse_args()
 if not a.execute:print(json.dumps({'status':'operator167_offline_preflight','limits':LIMITS,'request_id':REQUEST,'files':review_inputs(),'cloud_executed':False}));return
 require(a.review_file is not None,'OPERATOR167_REVIEW_FILE');state=ROOT/'deployment/state/writer-operator167';state.mkdir(parents=True,exist_ok=True)
 with exclusive_lock(state):
  runner=Operator167(ROOT,state,safe_json(a.review_file),profile=a.profile)
  try:print(json.dumps(runner.run()))
  finally:runner.api.session.close()
if __name__=='__main__':main()
