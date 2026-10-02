"""Recovery of145: same immutable source/window; AUTO readback, no resend."""
from pathlib import Path
from types import SimpleNamespace
import argparse,base64,io,json,time
ROOT=Path(__file__).resolve().parents[1]
import importlib.util
def module(path,name):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
prior=module('deployment/canary_deploy_145.py','recovery151prior145')
base=prior.base;require=base.require;read=base.read;durable=base.durable;sha=prior.sha;identity=prior.identity
STATE='deployment/state/linux-canary-recovery-151'
FREEZE='runs/sk12-canary-recovery-151-freeze.json';REVIEW='runs/sk09-canary-recovery-151-review.json'
def preflight(root=ROOT):
 root=Path(root);prior.preflight(root);prior.check_review(root)
 old=root/prior.STATE;binding=read(old/'source-binding.json');manifest=read(old/'package/manifest.json');result=read(old/'result.json')
 require(result['effects']=={'upload':1,'mkdir':40,'start':0,'deploy':0} and result['status']=='incomplete','CANARY151_PRIOR_EFFECTS_CHANGED')
 require(not (old/'start-intent.json').exists() and not (old/'deploy-intent.json').exists(),'CANARY151_PRIOR_START_OR_DEPLOY')
 require(binding['manifest_sha256']==sha(old/'package/manifest.json') and binding['source_sha256']==manifest['source_sha256'] and binding['expires_at_unix']==manifest['expires_at_unix'],'CANARY151_BINDING_CHANGED')
 require(binding['source_code_path']==prior.PREFIX+'canary145-'+manifest['source_sha256'],'CANARY151_PREFIX_CHANGED')
 files=manifest['files_sha256'];require(len(files)==218,'CANARY151_FILE_COUNT')
 original=read(root/prior.BASE/'manifest.json')['files_sha256']
 require(set(files)==set(original) and all(h==original[n] for n,h in files.items() if n!='canary141-config.json'),'CANARY151_OVERLAY_CHANGED')
 require(read(old/'package/source/canary141-config.json')=={'kind':'diagnostic_only_not_release','expires_at_unix':binding['expires_at_unix'],'provider_calls':0,'source133_sha256':manifest['source133_sha256']},'CANARY151_WINDOW_CHANGED')
 for n,h in files.items():require(sha(old/'package/source'/n)==h,'CANARY151_SOURCE_CHANGED')
 intents=list(old.glob('upload-*.json'));require(len(intents)==1 and read(intents[0])=={'path':binding['source_code_path']+'/app.yaml','sha256':files['app.yaml']},'CANARY151_PRIOR_UPLOAD_CHANGED')
 auto=read(root/'runs/sk12-canary-auto-150.json');require(auto['matches'] is True and auto['sha256']==files['app.yaml'] and auto['path']==binding['source_code_path']+'/app.yaml','CANARY151_AUTO_PROOF_CHANGED')
 return dict(status='prepared_recovery_review_required',files=218,uploads_max=217,aggregate_uploads_max=218,start_max=1,deploy_max=1,expires_at_unix=binding['expires_at_unix'],source_code_path=binding['source_code_path'],provider_calls=0,sql_calls=0,new_window=False)
def check_review(root):
 f=read(root/FREEZE);r=read(root/REVIEW)
 require(r.get('status')=='PASS_CANARY_RECOVERY_151' and r.get('freeze_sha256')==sha(root/FREEZE),'CANARY151_REVIEW_REQUIRED')
 for p,h in f['files_sha256'].items():require(sha(root/p)==h,'CANARY151_REVIEW_INPUT_DRIFT')

class ErrorSession:
 """Preserve bounded non-2xx body before frozen080 parses it; no headers."""
 def __init__(self,session,state):self.session=session;self.state=state;self.sequence=0
 def __getattr__(self,name):return getattr(self.session,name)
 @property
 def trust_env(self):return self.session.trust_env
 @trust_env.setter
 def trust_env(self,value):self.session.trust_env=value
 def request(self,method,url,**kwargs):
  response=self.session.request(method,url,**kwargs)
  if not 200<=response.status_code<300:
   raw=response.raw;self.sequence+=1;path=self.state/f'http-error-{self.sequence:04}.json'
   class Raw:
    def read(inner,amount,**options):
     content=raw.read(min(amount,1048577),**options)
     durable(path,{'method':method,'url':url,'status':response.status_code,'body_base64':base64.b64encode(content[:1048576]).decode(),'truncated':len(content)>1048576})
     require(len(content)<=1048576,'CANARY151_ERROR_BODY_CAP');return content
   response.raw=Raw()
  return response

def services(cfg,prefix,admit,*,uploads,mkdirs,state):
 import requests
 from databricks.sdk.mixins.workspace import WorkspaceExt
 from databricks.sdk.service.apps import AppsAPI
 delegate=base.ScopedApi(cfg,prefix,admit,ErrorSession(requests.Session(),state))
 api=prior.CappedApi(delegate,uploads=uploads,mkdirs=mkdirs)
 return SimpleNamespace(workspace=WorkspaceExt(api),apps=AppsAPI(api),api=api)

def execute(root=ROOT,*,config_factory=None,services_factory=services,clock=lambda:int(time.time()*1000),sleep=time.sleep):
 root=Path(root);p=preflight(root);check_review(root);expires=p['expires_at_unix']
 def admit():require(clock()<expires*1000,'CANARY151_WINDOW_EXPIRED')
 admit()
 if config_factory is None:
  from databricks.sdk.core import Config
  config_factory=Config
 cfg=config_factory(profile='databricks-ai-engineer-aws');require(cfg.host.rstrip('/')==base.HOST,'CANARY151_HOST_CHANGED')
 headers=cfg.authenticate();require(bool(headers),'CANARY151_AUTH_UNAVAILABLE');del headers;admit()
 state=root/STATE;state.mkdir(parents=True,exist_ok=False)
 durable(state/'admission.json',dict(phase='151',freeze_sha256=sha(root/FREEZE),review_sha256=sha(root/REVIEW),prior_admission_sha256=sha(root/prior.STATE/'admission.json'),**p))
 result={'status':'incomplete','quality_accepted':False,'release_authorized':False,'provider_calls':0,'sql_calls':0,'new_resources':0,'stop_required_by_coordinator':False};server=None
 try:
  old=root/prior.STATE;package=old/'package';manifest=read(package/'manifest.json');files=manifest['files_sha256'];prefix=p['source_code_path']
  server=services_factory(cfg,prefix,admit,uploads=217,mkdirs=0,state=state)
  app=base.obj(server.apps.get(base.APP));identity(app);durable(state/'app-before.json',app)
  require(not app.get('active_deployment') and not app.get('pending_deployment'),'CANARY151_OTHER_DEPLOYMENT')
  require(app.get('compute_status',{}).get('state')=='STOPPED','CANARY151_INITIAL_COMPUTE_CHANGED')
  from databricks.sdk.service.workspace import ImportFormat,ExportFormat
  def status(path):
   try:return base.obj(server.workspace.get_status(path))
   except Exception as e:
    if getattr(e,'error_code',None)=='RESOURCE_DOES_NOT_EXIST':return None
    raise
  directories=sorted({prefix,*[prefix+'/'+str(Path(n).parent) for n in files if str(Path(n).parent)!='.']})
  require(len(directories)==40,'CANARY151_DIRECTORY_COUNT')
  for directory in directories:
   admit();require(read(old/('mkdir-'+base.sha(directory.encode())+'.json'))=={'path':directory},'CANARY151_DIRECTORY_INTENT')
   observed=status(directory);require(observed and observed.get('object_type')=='DIRECTORY','CANARY151_DIRECTORY_MISSING')
  for name,h in sorted(files.items()):
   admit();remote=prefix+'/'+name;key=base.sha(name.encode());payload=(package/'source'/name).read_bytes();require(base.sha(payload)==h,'CANARY151_SOURCE_CHANGED_BEFORE_UPLOAD')
   if name=='app.yaml':
    observed=status(remote);require(observed and observed.get('object_type')=='FILE','CANARY151_PRIOR_FILE_MISSING')
   else:
    require(status(remote) is None,'CANARY151_REMOTE_FILE_EXISTS');durable(state/('upload-'+key+'.json'),{'path':remote,'sha256':h})
    try:
     with io.BytesIO(payload) as stream:server.workspace.upload(remote,stream,format=ImportFormat.RAW,overwrite=False)
    except Exception:pass
   with server.workspace.download(remote,format=ExportFormat.AUTO) as stream:observed=base.sha(stream.read(500000001))
   require(observed==h,'CANARY151_UPLOAD_READBACK_FAILED');durable(state/('uploaded-'+key+'.json'),{'path':remote,'sha256':h,'export_format':'AUTO','reconciles_phase145':name=='app.yaml'})
  durable(state/'source-verified.json',{'source_sha256':manifest['source_sha256'],'files':len(files)})
  current=base.obj(server.apps.get(base.APP));identity(current);durable(state/'app-prestart.json',current)
  require(not current.get('active_deployment') and not current.get('pending_deployment'),'CANARY151_ACTIVE_DEPLOYMENT_CHANGED')
  phase=current.get('compute_status',{}).get('state');require(phase in ('STOPPED','ACTIVE','RUNNING'),'CANARY151_COMPUTE_STATE_UNSUPPORTED')
  if phase=='STOPPED':
   durable(state/'start-intent.json',{'app':base.APP});result['stop_required_by_coordinator']=True
   try:server.apps.start(base.APP)
   except Exception:pass
  else:result['stop_required_by_coordinator']=True
  for i in range(20):
   admit();current=base.obj(server.apps.get(base.APP));identity(current);durable(state/f'start-observation-{i:02}.json',current)
   if current.get('compute_status',{}).get('state') in ('ACTIVE','RUNNING'):break
   sleep(5)
  else:raise ValueError('CANARY151_START_UNCONFIRMED')
  durable(state/'deploy-intent.json',{'source_code_path':prefix,'mode':'SNAPSHOT'})
  from databricks.sdk.service.apps import AppDeployment,AppDeploymentMode
  try:deployment=base.obj(server.apps.deploy(base.APP,AppDeployment(source_code_path=prefix,mode=AppDeploymentMode.SNAPSHOT)).response)
  except Exception:
   from itertools import islice
   matches=[base.obj(x) for x in islice(server.apps.list_deployments(base.APP,page_size=20),20) if base.obj(x).get('source_code_path')==prefix]
   require(len(matches)==1,'CANARY151_DEPLOY_UNCONFIRMED_NO_RETRY');deployment=matches[0]
  durable(state/'deploy-receipt.json',deployment);deployment_id=deployment['deployment_id']
  for i in range(20):
   admit();observed=base.obj(server.apps.get_deployment(base.APP,deployment_id));durable(state/f'deploy-observation-{i:02}.json',observed)
   state_name=observed.get('status',{}).get('state')
   if state_name=='SUCCEEDED':result.update(status='deployed_linux_evidence_pending',deployment_id=deployment_id,source_sha256=manifest['source_sha256'],source_code_path=prefix);break
   require(state_name not in ('FAILED','CANCELLED'),'CANARY151_DEPLOY_FAILED');sleep(5)
  else:raise ValueError('CANARY151_DEPLOY_PENDING')
 except Exception as error:result.update(error_type=type(error).__name__,error_code=str(error) if str(error).startswith('CANARY151_') else 'CANARY151_BOUNDED_EXECUTION_FAILED')
 finally:
  if server:
   result['http_calls']=server.api.calls;result['effects']=server.api.counts;result['aggregate_effects_145_151']={k:v+({'upload':1,'mkdir':40}.get(k,0)) for k,v in server.api.counts.items()};server.api.session.close()
  durable(state/'result.json',result)
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');a=p.parse_args();print(json.dumps(execute() if a.execute else preflight(),indent=2))
