"""One new bounded canary mission: chunked upload/start/deploy/evidence/cleanup."""
from pathlib import Path
import argparse,importlib.util,io,json,time
ROOT=Path(__file__).resolve().parents[1]
def module(path,name):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
transport=module('deployment/canary_recovery_154.py','integrated166transport154');builder=module('deployment/prepare_chunked_canary_163.py','integrated166builder163');control=module('deployment/canary_observe_stop_148.py','integrated166control148')
base=transport.base;require=base.require;read=base.read;durable=base.durable;sha=transport.sha
FREEZE='runs/sk12-canary-integrated-166-freeze.json';REVIEW='runs/sk09-canary-integrated-166-review.json';STATE='deployment/state/linux-canary-integrated-166';TEMPLATE='runs/sk12-chunked-canary-163-source-v2'
def preflight(root=ROOT):
 root=Path(root);review=read(root/'runs/sk09-chunked-canary-163-review.json');require(review.get('status')=='PASS_CODE_ONLY' and review.get('freeze_sha256')==sha(root/'runs/sk12-chunked-canary-163-freeze.json'),'CANARY166_SOURCE_REVIEW')
 for p,h in read(root/'runs/sk12-chunked-canary-163-freeze.json')['files_sha256'].items():require(sha(root/p)==h,'CANARY166_SOURCE_DRIFT')
 require(sha(root/base.AUTONOMY)==base.AUTONOMY_SHA,'CANARY166_AUTONOMY_CHANGED')
 return {'status':'prepared_review_required','upload_max':237,'start_max':1,'deploy_max':1,'stop_max':1,'provider_calls':0,'sql_calls':0,'start_wait_max_seconds':600,'deploy_wait_max_seconds':300,'window_seconds':1800}
def check_review(root):
 review=read(root/REVIEW);require(review.get('status')=='PASS_CANARY_INTEGRATED_166' and review.get('freeze_sha256')==sha(root/FREEZE),'CANARY166_REVIEW_REQUIRED')
 for p,h in read(root/FREEZE)['files_sha256'].items():require(sha(root/p)==h,'CANARY166_INPUT_DRIFT')
def verify_package(root,package,expires):
 m=read(package/'manifest.json');held=read(root/TEMPLATE/'manifest.json');files=m['files_sha256'];before=held['files_sha256'];allowed={'canary141-config.json','chunks163-manifest.json'}
 require(set(files)==set(before) and len(files)==237 and all(files[n]==before[n] for n in files if n not in allowed),'CANARY166_UNREVIEWED_PACKAGE')
 config=read(package/'source/canary141-config.json');expected=read(root/TEMPLATE/'source/canary141-config.json');expected['expires_at_unix']=expires;require(config==expected,'CANARY166_EXPIRY_DELTA')
 chunks=read(package/'source/chunks163-manifest.json');original=read(root/TEMPLATE/'source/chunks163-manifest.json');original['logical_files_sha256']['canary141-config.json']=sha(package/'source/canary141-config.json');require(chunks==original,'CANARY166_CHUNK_MANIFEST_DELTA')
 require(m['expires_at_unix']==expires and all((package/'source'/n).stat().st_size<=8388608 and sha(package/'source'/n)==h for n,h in files.items()),'CANARY166_TRANSPORT_SOURCE')
 return m

def cleanup(cfg,state,expected,before,*,session_factory=None,sleep=time.sleep):
 import requests
 directory=state/'cleanup';directory.mkdir(exist_ok=False);api=control.Transport(cfg,directory,(session_factory or requests.Session)());out={'status':'incomplete'}
 try:
  app=api.request('workspace_get',control.APP_PATH);transport.history.identity(app)
  for key in ('active_deployment','pending_deployment'):
   item=app.get(key)
   require(not item or item.get('source_code_path')==expected['source_code_path'],'CANARY166_CLEANUP_OTHER_DEPLOYMENT')
  phase=app.get('compute_status',{}).get('state')
  if phase=='STOPPED':out['status']='stopped_observed';return out
  require(phase in ('ACTIVE','RUNNING'),'CANARY166_CLEANUP_NOT_ACTIVE')
  history=api.request('workspace_get',control.APP_PATH+'/deployments');require(not history.get('next_page_token'),'CANARY166_CLEANUP_HISTORY_INCOMPLETE')
  items=history.get('app_deployments');require(isinstance(items,list),'CANARY166_CLEANUP_HISTORY_SHAPE')
  if items:
   from datetime import datetime
   stamps=[datetime.fromisoformat(x['create_time'].replace('Z','+00:00')) for x in items];require(all(x.tzinfo for x in stamps),'CANARY166_CLEANUP_TIMESTAMP');latest=[x for x,t in zip(items,stamps) if t==max(stamps)]
   require(len(latest)==1 and (latest[0].get('source_code_path')==expected['source_code_path'] or latest[0].get('deployment_id')==before.get('last_deployment_id')),'CANARY166_CLEANUP_REPLACEMENT')
  else:require(not before.get('last_deployment_id') and not expected.get('deployment_id'),'CANARY166_CLEANUP_HISTORY_MISSING')
  # Recheck current App immediately before stop; same ownsource or untouched priorlast.
  app=api.request('workspace_get',control.APP_PATH);transport.history.identity(app);require(app.get('compute_status',{}).get('state') in ('ACTIVE','RUNNING'),'CANARY166_CLEANUP_STATE_CHANGED')
  for key in ('active_deployment','pending_deployment'):
   item=app.get(key);require(not item or item.get('source_code_path')==expected['source_code_path'],'CANARY166_CLEANUP_REPLACEMENT')
  last=app.get('last_deployment_id');owned_ids={before.get('last_deployment_id'),expected.get('deployment_id'),*(x.get('deployment_id') for x in items if x.get('source_code_path')==expected['source_code_path'])};require(last in owned_ids,'CANARY166_CLEANUP_LAST_CHANGED')
  durable(directory/'stop-intent.json',{'app':base.APP,**expected})
  try:api.request('stop',control.APP_PATH+'/stop')
  except Exception as e:durable(directory/'stop-ambiguous.json',{'error_type':type(e).__name__,'retry':False})
  for i in range(10):
   app=api.request('workspace_get',control.APP_PATH);transport.history.identity(app)
   for key in ('active_deployment','pending_deployment'):
    require(not app.get(key) or app[key].get('source_code_path')==expected['source_code_path'],'CANARY166_CLEANUP_REPLACEMENT')
   if app.get('compute_status',{}).get('state')=='STOPPED':out['status']='stopped_observed';break
   sleep(5)
  else:out['status']='stop_unconfirmed_no_retry'
 except Exception as e:out.update(error_type=type(e).__name__,error_code=str(e) if str(e).startswith(('CANARY166_','CANARY148_')) else 'CANARY166_CLEANUP_BOUNDED_FAILURE')
 finally:out['reserved_http_attempts']=api.counts;api.session.close();durable(directory/'result.json',out)
 return out

def evidence(cfg,state,expected,*,session_factory=None):
 import requests
 directory=state/'evidence';directory.mkdir(exist_ok=False);api=control.Transport(cfg,directory,(session_factory or requests.Session)())
 try:
  app=api.request('workspace_get',control.APP_PATH);require(control.owned(app,expected) in ('ACTIVE','RUNNING'),'CANARY166_EVIDENCE_NOT_ACTIVE')
  for path in ('/health','/evidence'):durable(directory/(path[1:]+'-parsed.json'),api.request('app_get',path))
  return {'status':'captured_not_semantically_validated'}
 except Exception as e:return {'status':'capture_failed_use_cli_logs_handoff','error_type':type(e).__name__}
 finally:api.session.close()

def execute(root=ROOT,*,config_factory=None,services_factory=transport.services,clock=time.time,sleep=time.sleep,evidence_fn=evidence,cleanup_fn=cleanup):
 root=Path(root);p=preflight(root);check_review(root)
 if config_factory is None:
  from databricks.sdk.core import Config
  config_factory=Config
 cfg=config_factory(profile='databricks-ai-engineer-aws');require(cfg.host.rstrip('/')==base.HOST,'CANARY166_HOST');headers=cfg.authenticate();require(bool(headers),'CANARY166_AUTH');del headers
 expires=int(clock())+1800;state=root/STATE;state.mkdir(parents=True,exist_ok=False);durable(state/'admission.json',{'phase':'166','freeze_sha256':sha(root/FREEZE),'review_sha256':sha(root/REVIEW),'expires_at_unix':expires,'authorization_sha256':base.AUTONOMY_SHA,**p})
 result={'status':'incomplete','quality_accepted':False,'linux_verified':False,'provider_calls':0,'sql_calls':0};server=None;started=False;before=None;expected=None
 try:
  def admit():require(clock()<expires,'CANARY166_DEADLINE')
  package=state/'package';builder.prepare(package,root=root,expires_at=expires);manifest=verify_package(root,package,expires);files=manifest['files_sha256'];prefix=transport.history.prior.PREFIX+'canary166-'+manifest['source_sha256'];expected={'source_code_path':prefix,'source_sha256':manifest['source_sha256'],'deployment_id':None};durable(state/'source-binding.json',{**expected,'expires_at_unix':expires,'manifest_sha256':sha(package/'manifest.json')})
  directories=sorted({prefix,*[prefix+'/'+str(Path(n).parent) for n in files if str(Path(n).parent)!='.']},key=lambda p:(p.count('/'),p));server=services_factory(cfg,prefix,admit,uploads=237,mkdirs=len(directories),state=state)
  before=base.obj(server.apps.get(base.APP));transport.history.identity(before);require(before.get('compute_status',{}).get('state')=='STOPPED' and not before.get('active_deployment') and not before.get('pending_deployment'),'CANARY166_INITIAL_NOT_STOPPED');durable(state/'app-before.json',before)
  from databricks.sdk.service.workspace import ImportFormat,ExportFormat
  def status(path):
   try:return base.obj(server.workspace.get_status(path))
   except Exception as e:
    if getattr(e,'error_code',None)=='RESOURCE_DOES_NOT_EXIST':return None
    raise
  for directory in directories:
   admit();require(status(directory) is None,'CANARY166_DIRECTORY_EXISTS');durable(state/('mkdir-'+base.sha(directory.encode())+'.json'),{'path':directory})
   try:server.workspace.mkdirs(directory)
   except Exception:require((status(directory) or {}).get('object_type')=='DIRECTORY','CANARY166_MKDIR_UNCONFIRMED')
  for name,h in sorted(files.items()):
   admit();path=prefix+'/'+name;key=base.sha(name.encode());raw=(package/'source'/name).read_bytes();require(base.sha(raw)==h and len(raw)<=8388608,'CANARY166_FILE_DRIFT');require(status(path) is None,'CANARY166_FILE_EXISTS');durable(state/('upload-'+key+'.json'),{'path':path,'sha256':h})
   try:
    with io.BytesIO(raw) as stream:server.workspace.upload(path,stream,format=ImportFormat.RAW,overwrite=False)
   except Exception:pass
   with server.workspace.download(path,format=ExportFormat.AUTO) as stream:observed=base.sha(stream.read(8388609))
   require(observed==h,'CANARY166_READBACK_MISMATCH');durable(state/('uploaded-'+key+'.json'),{'path':path,'sha256':h})
  durable(state/'source-verified.json',{'files':237,'source_sha256':manifest['source_sha256']});app=base.obj(server.apps.get(base.APP));transport.history.identity(app);require(app.get('compute_status',{}).get('state')=='STOPPED' and not app.get('active_deployment') and not app.get('pending_deployment') and app.get('last_deployment_id')==before.get('last_deployment_id'),'CANARY166_PRESTART_CHANGED')
  durable(state/'start-intent.json',{'app':base.APP});started=True
  try:server.apps.start(base.APP)
  except Exception:pass
  for i in range(60):
   admit();app=base.obj(server.apps.get(base.APP));transport.history.identity(app);durable(state/f'start-observation-{i:02}.json',app);require(not app.get('active_deployment') and not app.get('pending_deployment') and app.get('last_deployment_id')==before.get('last_deployment_id'),'CANARY166_PREDEPLOY_CHANGED')
   phase=app.get('compute_status',{}).get('state')
   if phase in ('ACTIVE','RUNNING'):break
   require(phase in ('STARTING','UPDATING'),'CANARY166_START_FAILED');sleep(10)
  else:raise ValueError('CANARY166_START_UNCONFIRMED')
  admit();durable(state/'deploy-intent.json',{'source_code_path':prefix,'mode':'SNAPSHOT'})
  from databricks.sdk.service.apps import AppDeployment,AppDeploymentMode
  try:deployed=base.obj(server.apps.deploy(base.APP,AppDeployment(source_code_path=prefix,mode=AppDeploymentMode.SNAPSHOT)).response)
  except Exception:
   from itertools import islice
   matches=[base.obj(x) for x in islice(server.apps.list_deployments(base.APP,page_size=20),20) if base.obj(x).get('source_code_path')==prefix];require(len(matches)==1,'CANARY166_DEPLOY_UNCONFIRMED_NO_RETRY');deployed=matches[0]
  expected['deployment_id']=deployed['deployment_id'];durable(state/'deploy-receipt.json',deployed)
  for i in range(60):
   admit();observed=base.obj(server.apps.get_deployment(base.APP,deployed['deployment_id']));durable(state/f'deploy-observation-{i:02}.json',observed);phase=observed.get('status',{}).get('state')
   if phase=='SUCCEEDED':result.update(status='deployed_evidence_pending',**expected);result['evidence']=evidence_fn(cfg,state,expected);break
   require(phase not in ('FAILED','CANCELLED'),'CANARY166_DEPLOY_FAILED');sleep(5)
  else:raise ValueError('CANARY166_DEPLOY_PENDING')
 except Exception as e:result.update(error_type=type(e).__name__,error_code=str(e) if str(e).startswith('CANARY166_') else 'CANARY166_BOUNDED_FAILURE')
 finally:
  if server:result['effects']=server.api.counts;result['http_calls']=server.api.calls;server.api.session.close()
  if started:
   try:result['cleanup']=cleanup_fn(cfg,state,expected,before,sleep=sleep)
   except Exception as e:result['cleanup']={'status':'cleanup_failed_coordinator_required','error_type':type(e).__name__}
  else:result['cleanup']={'status':'no_start_attempt_no_stop'}
  durable(state/'result.json',result)
 return result
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true');a=parser.parse_args();print(json.dumps(execute() if a.execute else preflight(),indent=2))
