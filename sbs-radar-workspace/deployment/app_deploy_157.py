"""Reviewed App153 materialization/deploy and external demonstration ledger."""
from pathlib import Path
import argparse,fcntl,importlib.util,io,json,re,time
ROOT=Path(__file__).resolve().parents[1]
def module(path,name):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
transport=module('deployment/canary_recovery_154.py','final157transport154');builder=module('deployment/app_candidate_153.py','final157builder153')
base=transport.base;require=base.require;read=base.read;durable=base.durable;sha=transport.sha
FREEZE='runs/sk12-app-deploy-157-freeze.json';REVIEW='runs/sk09-app-deploy-157-review.json';MATERIALIZED='deployment/state/app-materialized-157';STATE='deployment/state/app-deploy-157'
TEMPLATE='runs/sk12-app-candidate-153-source';FINAL_REVIEW='runs/sk09-app-materialized-157-review.json'
def preflight(root=ROOT):
 root=Path(root);m=builder.verify(root/TEMPLATE)
 require(len(m['files_sha256'])==214 and m['deadline_unix']==0,'APP157_TEMPLATE_CHANGED')
 review=read(root/'runs/sk09-app-candidate-153-review.json');require(review['status']=='PASS_CODE_ONLY' and review['freeze_sha256']==sha(root/'runs/sk12-app-candidate-153-freeze.json'),'APP157_SOURCE_REVIEW')
 for p,h in read(root/'runs/sk12-app-candidate-153-freeze.json')['files'].items():require(sha(root/p)==h,'APP157_SOURCE_DRIFT')
 return {'status':'prepared_linux_materialization_pending','uploads_max':214,'start_max':0,'deploy_max':1,'generation_calls':0,'embedding_calls':0,'deadline_emitted':False}
def check_review(root):
 r=read(root/REVIEW);require(r.get('status')=='PASS_APP_DEPLOY_157' and r.get('freeze_sha256')==sha(root/FREEZE),'APP157_REVIEW_REQUIRED')
 for p,h in read(root/FREEZE)['files_sha256'].items():require(sha(root/p)==h,'APP157_INPUT_DRIFT')
def materialize(linux_evidence,linux_sha,*,root=ROOT,clock=time.time):
 root=Path(root);preflight(root);check_review(root)
 # Gate before emitting the absolute deadline or creating any new state.
 builder.gates(root,linux_evidence,linux_sha)
 return builder.materialize(root/TEMPLATE,root/MATERIALIZED,linux_evidence=linux_evidence,linux_sha=linux_sha,expires_at=int(clock())+1800,root=root,clock=clock)
def ready(root):
 package=root/MATERIALIZED;m=builder.verify(package);payload=read(package/'deployment-payload.json');review=read(root/FINAL_REVIEW)
 require(review.get('status')=='PASS_EXACT_MATERIALIZATION_157' and review.get('manifest_sha256')==sha(package/'manifest.json') and review.get('payload_sha256')==sha(package/'deployment-payload.json') and review.get('executor_freeze_sha256')==sha(root/FREEZE),'APP157_EXACT_RELEASE_REVIEW_REQUIRED')
 require(m.get('template_sha256')==sha(root/TEMPLATE/'manifest.json') and m['deadline_unix']==payload['expires_at_unix'] and len(m['files_sha256'])==214,'APP157_MATERIALIZED_CHANGED')
 require(payload['source_sha256']==m['source_sha256'] and payload['source_code_path']==transport.history.prior.PREFIX+'app153-'+m['source_sha256'] and payload['limits']=={'upload_max':214,'deploy_max':1,'start_max':0,'model_calls_by_publisher':0},'APP157_PAYLOAD_CHANGED')
 return package,m,payload

def owned_canary(app,source,receipt):
 transport.history.identity(app);require(not app.get('pending_deployment'),'APP157_PENDING_DEPLOYMENT')
 active=app.get('active_deployment') or {}
 require(active.get('deployment_id')==receipt['deployment_id'] and active.get('source_code_path')==source['source_code_path'],'APP157_CURRENT_DEPLOYMENT_NOT_OWNED')
 require(app.get('compute_status',{}).get('state') in ('ACTIVE','RUNNING'),'APP157_COMPUTE_NOT_ACTIVE')

class Api(transport.history.prior.CappedApi):
 def __init__(self,delegate,*,mkdirs):
  super().__init__(delegate,uploads=214,mkdirs=mkdirs);self.maximum['start']=0

def services(cfg,prefix,admit,state,mkdirs):
 import requests
 from databricks.sdk.mixins.workspace import WorkspaceExt
 from databricks.sdk.service.apps import AppsAPI
 api=Api(base.ScopedApi(cfg,prefix,admit,transport.ErrorSession(requests.Session(),state)),mkdirs=mkdirs)
 return type('Services',(),{'workspace':WorkspaceExt(api),'apps':AppsAPI(api),'api':api})()

def execute(root=ROOT,*,config_factory=None,services_factory=services,clock=time.time,sleep=time.sleep):
 root=Path(root);preflight(root);check_review(root);package,manifest,payload=ready(root);expires=payload['expires_at_unix']
 def admit():require(clock()<expires,'APP157_DEADLINE_EXPIRED')
 admit()
 if config_factory is None:
  from databricks.sdk.core import Config
  config_factory=Config
 cfg=config_factory(profile='databricks-ai-engineer-aws');require(cfg.host.rstrip('/')==base.HOST,'APP157_HOST');headers=cfg.authenticate();require(bool(headers),'APP157_AUTH');del headers;admit()
 state=root/STATE;state.mkdir(parents=True,exist_ok=False);durable(state/'admission.json',{'freeze_sha256':sha(root/FREEZE),'materialized_review_sha256':sha(root/FINAL_REVIEW),'manifest_sha256':sha(package/'manifest.json'),'expires_at_unix':expires,'uploads_max':214,'start_max':0,'deploy_max':1})
 result={'status':'incomplete','quality_accepted':False,'m2m_verified':False,'ui_verified':False,'stop_required':True};server=None
 try:
  source=read(root/transport.history.prior.STATE/'source-binding.json');receipt=read(root/'deployment/state/linux-canary-continue-159/deploy-receipt.json')
  intent=read(root/'deployment/state/linux-canary-continue-159/deploy-intent.json');require(intent=={'source_code_path':source['source_code_path'],'mode':'SNAPSHOT'},'APP157_PRIOR_INTENT_CHANGED')
  prefix=payload['source_code_path'];files=manifest['files_sha256'];directories=sorted({prefix,*[prefix+'/'+str(Path(n).parent) for n in files if str(Path(n).parent)!='.']},key=lambda p:(p.count('/'),p))
  server=services_factory(cfg,prefix,admit,state,len(directories));app=base.obj(server.apps.get(base.APP));owned_canary(app,source,receipt);durable(state/'app-before.json',app)
  from databricks.sdk.service.workspace import ImportFormat,ExportFormat
  def status(path):
   try:return base.obj(server.workspace.get_status(path))
   except Exception as e:
    if getattr(e,'error_code',None)=='RESOURCE_DOES_NOT_EXIST':return None
    raise
  for directory in directories:
   admit();require(status(directory) is None,'APP157_DIRECTORY_EXISTS');durable(state/('mkdir-'+base.sha(directory.encode())+'.json'),{'path':directory})
   try:server.workspace.mkdirs(directory)
   except Exception:require((status(directory) or {}).get('object_type')=='DIRECTORY','APP157_MKDIR_UNKNOWN')
  for name,h in sorted(files.items()):
   admit();path=prefix+'/'+name;key=base.sha(name.encode());raw=(package/'source'/name).read_bytes();require(base.sha(raw)==h,'APP157_SOURCE_CHANGED');require(status(path) is None,'APP157_FILE_EXISTS')
   durable(state/('upload-'+key+'.json'),{'path':path,'sha256':h})
   try:
    with io.BytesIO(raw) as stream:server.workspace.upload(path,stream,format=ImportFormat.RAW,overwrite=False)
   except Exception:pass
   with server.workspace.download(path,format=ExportFormat.AUTO) as stream:observed=base.sha(stream.read(500000001))
   require(observed==h,'APP157_READBACK_MISMATCH');durable(state/('uploaded-'+key+'.json'),{'path':path,'sha256':h})
  durable(state/'source-verified.json',{'manifest_sha256':sha(package/'manifest.json'),'files':214})
  app=base.obj(server.apps.get(base.APP));owned_canary(app,source,receipt);durable(state/'app-predeploy.json',app);admit()
  durable(state/'deploy-intent.json',{'source_code_path':prefix,'mode':'SNAPSHOT'})
  from databricks.sdk.service.apps import AppDeployment,AppDeploymentMode
  try:deployed=base.obj(server.apps.deploy(base.APP,AppDeployment(source_code_path=prefix,mode=AppDeploymentMode.SNAPSHOT)).response)
  except Exception:
   from itertools import islice
   matches=[base.obj(x) for x in islice(server.apps.list_deployments(base.APP,page_size=20),20) if base.obj(x).get('source_code_path')==prefix]
   require(len(matches)==1,'APP157_DEPLOY_UNCONFIRMED_NO_RETRY');deployed=matches[0]
  durable(state/'deploy-receipt.json',deployed)
  for i in range(20):
   admit();observed=base.obj(server.apps.get_deployment(base.APP,deployed['deployment_id']));durable(state/f'deploy-observation-{i:02}.json',observed);phase=observed.get('status',{}).get('state')
   if phase=='SUCCEEDED':
    binding={'deployment_id':deployed['deployment_id'],'source_code_path':prefix,'source_sha256':manifest['source_sha256'],'expires_at_unix':expires}
    durable(state/'demo-ledger/binding.json',{**binding,'caps':{'generation_posts':4,'embedding_posts':2,'embedding_tokens':20000},'scope':'external_coordinator_only_not_server_global','process_epoch':None})
    result.update(status='deployed_demo_admission_pending',**binding);break
   require(phase not in ('FAILED','CANCELLED'),'APP157_DEPLOY_FAILED');sleep(5)
  else:raise ValueError('APP157_DEPLOY_PENDING')
 except Exception as e:result.update(error_type=type(e).__name__,error_code=str(e) if str(e).startswith('APP157_') else 'APP157_BOUNDED_FAILURE')
 finally:
  if server:result['effects']=server.api.counts;result['http_calls']=server.api.calls;server.api.session.close()
  durable(state/'result.json',result)
 return result

class DemoLedger:
 """External reservations: no automatic app traffic, no claim of global enforcement."""
 def __init__(self,path,clock=time.time):self.path=Path(path);self.clock=clock;self.binding=read(self.path/'binding.json')
 def reserve(self,turn_id,*,process_epoch,deployment_id,source_sha256,costs,observation_path,observation_sha256):
  require(re.fullmatch(r'[A-Za-z0-9_-]{1,80}',turn_id) and re.fullmatch(r'process-[0-9a-f]{32}',process_epoch),'APP157_TURN_OR_EPOCH')
  require(sha(Path(observation_path))==observation_sha256,'APP157_OBSERVATION_DRIFT')
  observation=read(observation_path);require(observation.get('deployment_id')==deployment_id and observation.get('source_sha256')==source_sha256 and observation.get('capture_process')==process_epoch and isinstance(observation.get('observed_at_unix'),(int,float)) and 0<=self.clock()-observation['observed_at_unix']<=30,'APP157_FRESH_PROCESS_OBSERVATION_REQUIRED')
  require(self.clock()<self.binding['expires_at_unix'] and deployment_id==self.binding['deployment_id'] and source_sha256==self.binding['source_sha256'],'APP157_DEMO_BINDING_CHANGED')
  caps=self.binding['caps'];require(set(costs)==set(caps) and all(type(v)is int and v>=0 for v in costs.values()),'APP157_COSTS')
  fd=__import__('os').open(self.path,__import__('os').O_RDONLY);fcntl.flock(fd,fcntl.LOCK_EX)
  try:
   entries=[read(p) for p in self.path.glob('turn-*-intent.json')]
   require(all(x['process_epoch']==process_epoch for x in entries),'APP157_RESTART_BLOCKED')
   require(not (self.path/f'turn-{turn_id}-intent.json').exists(),'APP157_DUPLICATE_TURN')
   require(all(sum(x['reserved'][k] for x in entries)+costs[k]<=caps[k] for k in caps),'APP157_DEMO_CAP')
   durable(self.path/f'turn-{turn_id}-intent.json',{'turn_id':turn_id,'process_epoch':process_epoch,'reserved':costs,'observation_sha256':observation_sha256,'deployment_id':deployment_id,'source_sha256':source_sha256})
  finally:__import__('os').close(fd)
 def record(self,turn_id,*,actual,unknown,capture_ids):
  require(re.fullmatch(r'[A-Za-z0-9_-]{1,80}',turn_id),'APP157_TURN');intent=read(self.path/f'turn-{turn_id}-intent.json');caps=intent['reserved']
  require(set(actual)==set(caps) and set(unknown)==set(caps) and all(type(actual[k])is int and type(unknown[k])is int and 0<=actual[k]+unknown[k]<=caps[k] and actual[k]>=0 and unknown[k]>=0 for k in caps),'APP157_ACTUAL_COUNTS')
  require(isinstance(capture_ids,list) and all(isinstance(x,str) and x for x in capture_ids),'APP157_CAPTURE_IDS')
  durable(self.path/f'turn-{turn_id}-receipt.json',{'turn_id':turn_id,'actual':actual,'unknown':unknown,'capture_ids':capture_ids,'reservation_retained':True})
def stop(root=ROOT,*,config_factory=None,session_factory=None,sleep=time.sleep):
 """Separate teardown; no renewal and no inference that watchdog stopped compute."""
 root=Path(root);preflight(root);check_review(root);package,manifest,payload=ready(root)
 control=module('deployment/canary_observe_stop_148.py','final157stoptransport148')
 deploy=root/STATE;require(read(deploy/'deploy-intent.json')=={'source_code_path':payload['source_code_path'],'mode':'SNAPSHOT'},'APP157_STOP_INTENT_NOT_OWNED')
 receipt=read(deploy/'deploy-receipt.json') if (deploy/'deploy-receipt.json').exists() else {}
 expected={'deployment_id':receipt.get('deployment_id'),'source_code_path':payload['source_code_path'],'source_sha256':manifest['source_sha256']}
 if config_factory is None:
  from databricks.sdk.core import Config
  config_factory=Config
 if session_factory is None:
  import requests
  session_factory=requests.Session
 cfg=config_factory(profile='databricks-ai-engineer-aws');require(cfg.host.rstrip('/')==base.HOST,'APP157_HOST');headers=cfg.authenticate();require(bool(headers),'APP157_AUTH');del headers
 state=root/'deployment/state/app-stop-157';state.mkdir(parents=True,exist_ok=False);durable(state/'admission.json',{'freeze_sha256':sha(root/FREEZE),'binding':expected,'stop_max':1,'readback_max':10})
 api=control.Transport(cfg,state,session_factory());result={'status':'incomplete'}
 try:
  app=api.request('workspace_get',control.APP_PATH);phase=control.owned(app,expected,allow_unbound=True)
  if phase=='STOPPED':result['status']='already_stopped_observed'
  else:
   require(phase in ('ACTIVE','RUNNING'),'APP157_STOP_COMPUTE_STATE');control.latest_owned(api.request('workspace_get',control.APP_PATH+'/deployments'),expected)
   app=api.request('workspace_get',control.APP_PATH);require(control.owned(app,expected,allow_unbound=True) in ('ACTIVE','RUNNING'),'APP157_STOP_STATE_CHANGED')
   durable(state/'stop-intent.json',expected)
   try:api.request('stop',control.APP_PATH+'/stop')
   except Exception as e:durable(state/'ambiguous.json',{'error_type':type(e).__name__,'retry':False})
   for i in range(10):
    app=api.request('workspace_get',control.APP_PATH);phase=control.owned(app,expected,allow_unbound=True)
    if phase=='STOPPED':result['status']='stopped_observed';break
    sleep(2)
   else:result['status']='stop_unconfirmed_no_retry'
 except Exception as e:result.update(error_type=type(e).__name__,error_code=str(e) if str(e).startswith(('APP157_','CANARY148_')) else 'APP157_STOP_BOUNDED_FAILURE')
 finally:result['reserved_http_attempts']=api.counts;api.session.close();durable(state/'result.json',result)
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--materialize',type=Path);p.add_argument('--linux-sha256');p.add_argument('--execute',action='store_true');p.add_argument('--stop',action='store_true');a=p.parse_args()
 print(json.dumps(materialize(a.materialize,a.linux_sha256) if a.materialize else stop() if a.stop else execute() if a.execute else preflight(),indent=2))
