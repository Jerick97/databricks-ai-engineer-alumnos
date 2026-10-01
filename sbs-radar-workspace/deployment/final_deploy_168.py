"""Final234file App runner, conditional start; no automatic demo inference."""
from pathlib import Path
import argparse,base64,io,json,time
import importlib.util
ROOT=Path(__file__).resolve().parents[1]
def module(path,name):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
packager=module('deployment/final_chunked_168.py','final168packager');prior=module('deployment/app_deploy_157.py','final168ledger157');mission=module('deployment/canary_integrated_166.py','final168cleanup166')
base=prior.base;require=base.require;read=base.read;durable=base.durable;sha=prior.sha
FREEZE='runs/sk12-final-chunked-168-freeze.json';REVIEW='runs/sk09-final-chunked-168-review.json';EXACT_REVIEW='runs/sk09-final-materialized-168-review.json';STATE='deployment/state/final-app-168';MATERIALIZED='deployment/state/final-materialized-168'
def preflight(root=ROOT):
 root=Path(root);prior.preflight(root);held=read(root/'runs/sk12-final-chunked-168-source/manifest.json');require(held['deadline_unix']==0 and held['transport_files']==234,'FINAL168_HELD_CHANGED')
 for p,h in held['files_sha256'].items():require(sha(root/'runs/sk12-final-chunked-168-source/source'/p)==h,'FINAL168_HELD_DRIFT')
 return {'status':'held_linux_actual_required','files':234,'start_max':1,'deploy_max':1,'provider_calls':0,'deadline_emitted':False}
def review(root):
 r=read(root/REVIEW);require(r.get('status')=='PASS_FINAL_CHUNKED_168' and r.get('freeze_sha256')==sha(root/FREEZE),'FINAL168_REVIEW_REQUIRED')
 for p,h in read(root/FREEZE)['files_sha256'].items():require(sha(root/p)==h,'FINAL168_REVIEW_DRIFT')
def materialize(report,report_sha,root=ROOT,clock=time.time):
 root=Path(root);preflight(root);review(root);packager.base.gates(root,report,report_sha);require(not (root/MATERIALIZED).exists(),'FINAL168_MATERIALIZED_EXISTS')
 return packager.materialize(root/MATERIALIZED,linux_evidence=report,linux_sha=report_sha,expires_at=int(clock())+1800,root=root,clock=clock)
def ready(root):
 package=root/MATERIALIZED;m=read(package/'manifest.json');payload=read(package/'deployment-payload.json');r=read(root/EXACT_REVIEW)
 require(r.get('status')=='PASS_EXACT_FINAL_168' and r.get('manifest_sha256')==sha(package/'manifest.json') and r.get('payload_sha256')==sha(package/'deployment-payload.json') and r.get('executor_freeze_sha256')==sha(root/FREEZE),'FINAL168_EXACT_REVIEW')
 require(m['kind']=='materialized168_exactreviewrequired' and len(m['files_sha256'])==234 and packager.base.sha(packager.base.encoded(m['files_sha256']))==m['source_sha256'],'FINAL168_MANIFEST')
 require(payload['source_code_path']==prior.transport.history.prior.PREFIX+'app168-'+m['source_sha256'] and payload['source_sha256']==m['source_sha256'] and payload['expires_at_unix']==m['deadline_unix'] and payload['limits']=={'upload_max':234,'start_max':1,'deploy_max':1,'provider_calls':0},'FINAL168_PAYLOAD')
 for p,h in m['files_sha256'].items():require(not Path(p).is_absolute() and '..' not in Path(p).parts and not (package/'source'/p).is_symlink() and sha(package/'source'/p)==h and (package/'source'/p).stat().st_size<=8388608,'FINAL168_SOURCE_DRIFT')
 return package,m,payload

def upload(server,state,package,files,prefix,admit):
 from databricks.sdk.service.workspace import ImportFormat,ExportFormat
 def status(path):
  try:return base.obj(server.workspace.get_status(path))
  except Exception as e:
   if getattr(e,'error_code',None)=='RESOURCE_DOES_NOT_EXIST':return None
   raise
 directories=sorted({prefix,*[prefix+'/'+str(Path(n).parent) for n in files if str(Path(n).parent)!='.']},key=lambda x:(x.count('/'),x))
 for path in directories:
  admit();require(status(path) is None,'FINAL168_DIRECTORY_EXISTS');durable(state/('mkdir-'+base.sha(path.encode())+'.json'),{'path':path})
  try:server.workspace.mkdirs(path)
  except Exception:require((status(path) or {}).get('object_type')=='DIRECTORY','FINAL168_MKDIR_UNKNOWN')
 for n,h in sorted(files.items()):
  admit();path=prefix+'/'+n;key=base.sha(n.encode());raw=(package/'source'/n).read_bytes();require(base.sha(raw)==h and len(raw)<=8388608,'FINAL168_FILE_CHANGED');require(status(path) is None,'FINAL168_FILE_EXISTS');durable(state/('upload-'+key+'.json'),{'path':path,'sha256':h})
  try:
   with io.BytesIO(raw) as stream:server.workspace.upload(path,stream,format=ImportFormat.RAW,overwrite=False)
  except Exception:pass
  with server.workspace.download(path,format=ExportFormat.AUTO) as stream:got=base.sha(stream.read(8388609))
  require(got==h,'FINAL168_READBACK');durable(state/('uploaded-'+key+'.json'),{'path':path,'sha256':h})
 durable(state/'source-verified.json',{'files':len(files),'source_code_path':prefix})
def current(app,old):
 prior.transport.history.identity(app);require(not app.get('pending_deployment'),'FINAL168_PENDING_DEPLOYMENT')
 active=app.get('active_deployment')
 require(not active or (active.get('source_code_path')==old['source_code_path'] and active.get('deployment_id')==old['deployment_id']),'FINAL168_OTHER_ACTIVE_DEPLOYMENT')
 require(app.get('last_deployment_id') in (None,old['deployment_id']),'FINAL168_LAST_DEPLOYMENT_CHANGED')
 phase=app.get('compute_status',{}).get('state');require(phase in ('STOPPED','ACTIVE','RUNNING','STARTING','UPDATING'),'FINAL168_COMPUTE_STATE');return phase

def readiness(cfg,state,*,session_factory=None):
 import requests
 session=(session_factory or requests.Session)();session.trust_env=False;require(all(a.max_retries.total==0 for a in session.adapters.values()),'FINAL168_RETRIES')
 url=packager.base.ORIGIN+'/api/catalog';durable(state/'readiness-intent.json',{'method':'GET','url':url,'provider_calls':0})
 try:
  response=session.get(url,headers=cfg.authenticate(),allow_redirects=False,timeout=(15,30),stream=True)
  try:
   raw=response.raw.read(1048577,decode_content=True);durable(state/'readiness-response.json',{'status':response.status_code,'body_base64':base64.b64encode(raw[:1048576]).decode(),'truncated':len(raw)>1048576,'route':'/api/catalog'})
   require(len(raw)<=1048576,'FINAL168_READINESS_CAP');return {'http_status':response.status_code,'accepted':False,'scope':'catalog reachability only; no M2M/UI acceptance'}
  finally:response.close()
 except Exception as e:return {'status':'readiness_unknown','error_type':type(e).__name__,'accepted':False}
 finally:session.close()

def execute(root=ROOT,*,config_factory=None,services_factory=prior.transport.services,clock=time.time,sleep=time.sleep,readiness_fn=readiness):
 root=Path(root);preflight(root);review(root);package,m,payload=ready(root)
 def admit():require(clock()<payload['expires_at_unix'],'FINAL168_EXPIRED')
 admit()
 if config_factory is None:
  from databricks.sdk.core import Config
  config_factory=Config
 cfg=config_factory(profile='databricks-ai-engineer-aws');require(cfg.host.rstrip('/')==base.HOST,'FINAL168_HOST');headers=cfg.authenticate();require(bool(headers),'FINAL168_AUTH');del headers;admit()
 state=root/STATE;state.mkdir(parents=True,exist_ok=False);durable(state/'admission.json',{'freeze_sha256':sha(root/FREEZE),'exact_review_sha256':sha(root/EXACT_REVIEW),'manifest_sha256':sha(package/'manifest.json'),'expires_at_unix':payload['expires_at_unix'],'files':234,'start_max':1,'deploy_max':1})
 server=None;result={'status':'incomplete','stop_required':False,'provider_calls':0,'m2m_verified':False,'ui_verified':False};old=None
 try:
  oldbinding=read(root/mission.STATE/'source-binding.json');oldreceipt=read(root/mission.STATE/'deploy-receipt.json');old={**oldbinding,'deployment_id':oldreceipt['deployment_id']}
  prefix=payload['source_code_path'];files=m['files_sha256'];dirs={prefix,*[prefix+'/'+str(Path(n).parent) for n in files if str(Path(n).parent)!='.']};server=services_factory(cfg,prefix,admit,uploads=234,mkdirs=len(dirs),state=state)
  app=base.obj(server.apps.get(base.APP));require(current(app,old) in ('STOPPED','ACTIVE','RUNNING'),'FINAL168_INITIAL_TRANSITION');durable(state/'app-before.json',app)
  upload(server,state,package,files,prefix,admit);app=base.obj(server.apps.get(base.APP));phase=current(app,old);require(phase in ('STOPPED','ACTIVE','RUNNING'),'FINAL168_PRESTART_TRANSITION');durable(state/'app-prestart.json',app)
  result['stop_required']=True
  if phase=='STOPPED':
   durable(state/'start-intent.json',{'app':base.APP})
   try:server.apps.start(base.APP)
   except Exception:pass
  for i in range(60):
   admit();app=base.obj(server.apps.get(base.APP));phase=current(app,old);durable(state/f'start-observation-{i:02}.json',app)
   if phase in ('ACTIVE','RUNNING'):break
   require(phase in ('STARTING','UPDATING'),'FINAL168_START_FAILED');sleep(10)
  else:raise ValueError('FINAL168_START_PENDING')
  admit();durable(state/'deploy-intent.json',{'source_code_path':prefix,'mode':'SNAPSHOT'})
  from databricks.sdk.service.apps import AppDeployment,AppDeploymentMode
  try:deployed=base.obj(server.apps.deploy(base.APP,AppDeployment(source_code_path=prefix,mode=AppDeploymentMode.SNAPSHOT)).response)
  except Exception:
   from itertools import islice
   matches=[base.obj(x) for x in islice(server.apps.list_deployments(base.APP,page_size=20),20) if base.obj(x).get('source_code_path')==prefix];require(len(matches)==1,'FINAL168_DEPLOY_UNCONFIRMED');deployed=matches[0]
  durable(state/'deploy-receipt.json',deployed)
  for i in range(60):
   admit();app=base.obj(server.apps.get_deployment(base.APP,deployed['deployment_id']));durable(state/f'deploy-observation-{i:02}.json',app);phase=app.get('status',{}).get('state')
   if phase=='SUCCEEDED':
    binding={'deployment_id':deployed['deployment_id'],'source_code_path':prefix,'source_sha256':m['source_sha256'],'expires_at_unix':payload['expires_at_unix']};durable(state/'demo-ledger/binding.json',{**binding,'caps':{'generation_posts':4,'embedding_posts':2,'embedding_tokens':20000},'scope':'external_coordinator_only_not_server_global','process_epoch':None});result.update(status='deployed_demo_admission_pending',**binding);result['readiness']=readiness_fn(cfg,state);break
   require(phase not in ('FAILED','CANCELLED'),'FINAL168_DEPLOY_FAILED');sleep(5)
  else:raise ValueError('FINAL168_DEPLOY_PENDING')
 except Exception as e:result.update(error_type=type(e).__name__,error_code=str(e) if str(e).startswith('FINAL168_') else 'FINAL168_BOUNDED_FAILURE')
 finally:
  if server:result['effects']=server.api.counts;result['http_calls']=server.api.calls;server.api.session.close()
  durable(state/'result.json',result)
 return result

def stop(root=ROOT,*,config_factory=None,sleep=time.sleep):
 root=Path(root);preflight(root);review(root);package,m,payload=ready(root);state=root/STATE
 # Intent to start or replace own166 source authorizes cleanup; no success-onlygate.
 require((state/'start-intent.json').exists() or (state/'deploy-intent.json').exists(),'FINAL168_NO_EFFECT_TO_CLEANUP')
 before=read(state/'app-before.json');receipt=read(state/'deploy-receipt.json') if (state/'deploy-receipt.json').exists() else {};expected={'source_code_path':payload['source_code_path'],'source_sha256':m['source_sha256'],'deployment_id':receipt.get('deployment_id')}
 if config_factory is None:
  from databricks.sdk.core import Config
  config_factory=Config
 cfg=config_factory(profile='databricks-ai-engineer-aws');require(cfg.host.rstrip('/')==base.HOST,'FINAL168_HOST');headers=cfg.authenticate();require(bool(headers),'FINAL168_AUTH');del headers
 return mission.cleanup(cfg,state,expected,before,sleep=sleep)
DemoLedger=prior.DemoLedger
if __name__=='__main__':
 p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group();g.add_argument('--materialize',type=Path);g.add_argument('--execute',action='store_true');g.add_argument('--stop',action='store_true');p.add_argument('--linux-sha256');a=p.parse_args()
 print(json.dumps(materialize(a.materialize,a.linux_sha256) if a.materialize else execute() if a.execute else stop() if a.stop else preflight(),indent=2))
