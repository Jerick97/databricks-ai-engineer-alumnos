"""Single-admission canary executor reusing080 scoped RAW transport; no chat."""
from pathlib import Path
from types import SimpleNamespace
import argparse,hashlib,importlib.util,io,json,time
ROOT=Path(__file__).resolve().parents[1]
BASE='runs/sk12-linux-canary-141-source-v2';STATE='deployment/state/linux-canary-145'
FREEZE='runs/sk12-canary-145-freeze.json';REVIEW='runs/sk09-canary-145-review.json'
PREFIX='/Workspace/Users/sociosdosmilveintiseis@gmail.com/sbs-radar/releases/'
def module(root,path,name):
 s=importlib.util.spec_from_file_location(name,Path(root)/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
base=module(ROOT,'deployment/app_deploy_080.py','canary145transport080')
require=base.require;read=base.read;durable=base.durable;sha=lambda p:base.sha(Path(p).read_bytes())
def preflight(root=ROOT):
 root=Path(root)
 from importlib.metadata import version
 require(version('databricks-sdk')=='0.102.0','CANARY145_SDK_VERSION_CHANGED')
 require(sha(root/'runs/sk12-linux-141-freeze.json')=='4789c11f74dab27e6f02fb2e8dbad6b045cf1495611481e03e202b02e8707583','CANARY145_141_FREEZE_CHANGED')
 for p,h in read(root/'runs/sk12-linux-141-freeze.json')['files_sha256'].items():require(sha(root/p)==h,'CANARY145_141_INPUT_DRIFT')
 manifest=read(root/BASE/'manifest.json');files=manifest['files_sha256']
 require(manifest['source_sha256']=='61af512439687ec4d7a1d8fcfa17288cba70cc1155e3ebec4f42193a59292b43' and len(files)==218 and manifest['expires_at_unix']==0,'CANARY145_BASE_CHANGED')
 for p,h in files.items():
  target=root/BASE/'source'/p
  require(not Path(p).is_absolute() and '..' not in Path(p).parts and not target.is_symlink() and target.resolve().is_relative_to((root/BASE/'source').resolve()) and sha(target)==h,'CANARY145_SOURCE_DRIFT')
 require(sha(root/base.AUTONOMY)==base.AUTONOMY_SHA,'CANARY145_AUTONOMY_CHANGED')
 return dict(status='prepared_canary_review_required',files=218,uploads_max=218,start_max=1,deploy_max=1,provider_calls=0,sql=0,new_resources=0,base_manifest_sha256=sha(root/BASE/'manifest.json'),quality_accepted=False)
def check_review(root):
 f=read(root/FREEZE);r=read(root/REVIEW)
 require(r.get('status')=='PASS_CANARY_EXECUTOR_145' and r.get('freeze_sha256')==sha(root/FREEZE),'CANARY145_REVIEW_REQUIRED')
 for p,h in f['files_sha256'].items():require(sha(root/p)==h,'CANARY145_REVIEW_INPUT_DRIFT')

class CappedApi:
 def __init__(self,delegate,*,uploads,mkdirs):
  self.delegate=delegate;self.maximum={'upload':uploads,'mkdir':mkdirs,'start':1,'deploy':1};self.counts=dict.fromkeys(self.maximum,0);self.total=0
 def __getattr__(self,name):return getattr(self.delegate,name)
 def do(self,method,path=None,**kwargs):
  require(self.total<1600,'CANARY145_HTTP_CAP')
  kind=('upload' if path.endswith('/workspace/import') else 'mkdir' if path.endswith('/workspace/mkdirs') else 'start' if path.endswith('/start') else 'deploy' if path.endswith('/deployments') else None) if method=='POST' else None
  if kind:
   require(self.counts[kind]<self.maximum[kind],'CANARY145_EFFECT_CAP');self.counts[kind]+=1
  self.total+=1
  return self.delegate.do(method,path,**kwargs)

def services(cfg,prefix,admit,*,uploads,mkdirs):
 original=base.services(cfg,prefix,admit)
 from databricks.sdk.mixins.workspace import WorkspaceExt
 from databricks.sdk.service.apps import AppsAPI
 api=CappedApi(original.api,uploads=uploads,mkdirs=mkdirs)
 return SimpleNamespace(workspace=WorkspaceExt(api),apps=AppsAPI(api),api=api)

def identity(app):
 require(app.get('name')==base.APP and app.get('service_principal_id')==77041447522099 and app.get('service_principal_client_id')=='a947eccf-5f94-4369-a3d4-8f83b4ea98a1','CANARY145_APP_IDENTITY_CHANGED')

def execute(root=ROOT,*,config_factory=None,services_factory=services,clock=lambda:int(time.time()*1000),sleep=time.sleep):
 root=Path(root);p=preflight(root);check_review(root)
 if config_factory is None:
  from databricks.sdk.core import Config
  config_factory=Config
 cfg=config_factory(profile='databricks-ai-engineer-aws')
 require(cfg.host.rstrip('/')==base.HOST,'CANARY145_HOST_CHANGED')
 headers=cfg.authenticate();require(bool(headers),'CANARY145_AUTH_UNAVAILABLE');del headers
 state=root/STATE;expires=int(clock()/1000)+1800
 durable(state/'admission.json',dict(phase='145',freeze_sha256=sha(root/FREEZE),review_sha256=sha(root/REVIEW),base_manifest_sha256=p['base_manifest_sha256'],expires_at_unix=expires,scope='diagnosticcanaryonly; no release promotion',uploads_max=218,start_max=1,deploy_max=1,provider_calls=0))
 result={'status':'incomplete','quality_accepted':False,'release_authorized':False,'provider_calls':0,'sql_calls':0,'new_resources':0,'stop_required_by_coordinator':False};server=None
 try:
  def admit():require(clock()<expires*1000,'CANARY145_WINDOW_EXPIRED')
  builder=module(root,'deployment/prepare_canary_141.py','builder141for145')
  package=state/'package';manifest=builder.prepare(package,root=root,expires_at=expires);files=manifest['files_sha256']
  original=read(root/BASE/'manifest.json')['files_sha256']
  require(set(files)==set(original) and all(h==original[n] for n,h in files.items() if n!='canary141-config.json'),'CANARY145_UNREVIEWED_OVERLAY')
  require(read(package/'source/canary141-config.json')=={'kind':'diagnostic_only_not_release','expires_at_unix':expires,'provider_calls':0,'source133_sha256':manifest['source133_sha256']},'CANARY145_EXPIRY_OVERLAY_CHANGED')
  prefix=PREFIX+'canary145-'+manifest['source_sha256'];durable(state/'source-binding.json',dict(source_code_path=prefix,source_sha256=manifest['source_sha256'],manifest_sha256=sha(package/'manifest.json'),expires_at_unix=expires))
  directories=sorted({prefix,*[prefix+'/'+str(Path(n).parent) for n in files if str(Path(n).parent)!='.']},key=lambda p:(p.count('/'),p))
  server=services_factory(cfg,prefix,admit,uploads=len(files),mkdirs=len(directories))
  app=base.obj(server.apps.get(base.APP));identity(app);durable(state/'app-before.json',app)
  require(not app.get('active_deployment'),'CANARY145_ACTIVE_DEPLOYMENT_REQUIRES_SEPARATE_ROLLBACK_PLAN')
  from databricks.sdk.service.workspace import ImportFormat,ExportFormat
  def status(path):
   try:return base.obj(server.workspace.get_status(path))
   except Exception as e:
    if getattr(e,'error_code',None)=='RESOURCE_DOES_NOT_EXIST':return None
    raise
  for directory in directories:
   admit();require(status(directory) is None,'CANARY145_REMOTE_DIRECTORY_EXISTS');durable(state/('mkdir-'+base.sha(directory.encode())+'.json'),{'path':directory})
   try:server.workspace.mkdirs(directory)
   except Exception:
    observed=status(directory);require(observed and observed.get('object_type')=='DIRECTORY','CANARY145_MKDIR_UNCONFIRMED')
  for name,h in sorted(files.items()):
   admit();remote=prefix+'/'+name;key=base.sha(name.encode());payload=(package/'source'/name).read_bytes();require(base.sha(payload)==h,'CANARY145_SOURCE_CHANGED_BEFORE_UPLOAD')
   require(status(remote) is None,'CANARY145_REMOTE_FILE_EXISTS');durable(state/('upload-'+key+'.json'),{'path':remote,'sha256':h})
   try:
    with io.BytesIO(payload) as stream:server.workspace.upload(remote,stream,format=ImportFormat.RAW,overwrite=False)
   except Exception:pass
   with server.workspace.download(remote,format=ExportFormat.RAW) as stream:observed=base.sha(stream.read(500000001))
   require(observed==h,'CANARY145_UPLOAD_READBACK_FAILED');durable(state/('uploaded-'+key+'.json'),{'path':remote,'sha256':h})
  durable(state/'source-verified.json',{'source_sha256':manifest['source_sha256'],'files':len(files)})
  current=base.obj(server.apps.get(base.APP));identity(current);durable(state/'app-prestart.json',current)
  require(not current.get('active_deployment'),'CANARY145_ACTIVE_DEPLOYMENT_CHANGED')
  phase=current.get('compute_status',{}).get('state');require(phase in ('STOPPED','ACTIVE','RUNNING'),'CANARY145_COMPUTE_STATE_UNSUPPORTED')
  if phase=='STOPPED':
   durable(state/'start-intent.json',{'app':base.APP});result['stop_required_by_coordinator']=True
   try:server.apps.start(base.APP)
   except Exception:pass
  else:result['stop_required_by_coordinator']=True
  for i in range(20):
   admit();current=base.obj(server.apps.get(base.APP));identity(current);durable(state/f'start-observation-{i:02}.json',current)
   if current.get('compute_status',{}).get('state') in ('ACTIVE','RUNNING'):break
   sleep(5)
  else:raise ValueError('CANARY145_START_UNCONFIRMED')
  durable(state/'deploy-intent.json',{'source_code_path':prefix,'mode':'SNAPSHOT'})
  from databricks.sdk.service.apps import AppDeployment,AppDeploymentMode
  try:deployment=base.obj(server.apps.deploy(base.APP,AppDeployment(source_code_path=prefix,mode=AppDeploymentMode.SNAPSHOT)).response)
  except Exception:
   from itertools import islice
   matches=[base.obj(x) for x in islice(server.apps.list_deployments(base.APP,page_size=20),20) if base.obj(x).get('source_code_path')==prefix]
   require(len(matches)==1,'CANARY145_DEPLOY_UNCONFIRMED_NO_RETRY');deployment=matches[0]
  durable(state/'deploy-receipt.json',deployment);deployment_id=deployment['deployment_id']
  for i in range(20):
   admit();observed=base.obj(server.apps.get_deployment(base.APP,deployment_id));durable(state/f'deploy-observation-{i:02}.json',observed)
   state_name=observed.get('status',{}).get('state')
   if state_name=='SUCCEEDED':result.update(status='deployed_linux_evidence_pending',deployment_id=deployment_id,source_sha256=manifest['source_sha256'],source_code_path=prefix);break
   require(state_name not in ('FAILED','CANCELLED'),'CANARY145_DEPLOY_FAILED');sleep(5)
  else:raise ValueError('CANARY145_DEPLOY_PENDING')
 except Exception as error:result.update(error_type=type(error).__name__,error_code=str(error) if str(error).startswith('CANARY145_') else 'CANARY145_BOUNDED_EXECUTION_FAILED')
 finally:
  if server:
   result['http_calls']=server.api.calls;result['effects']=server.api.counts;server.api.session.close()
  durable(state/'result.json',result)
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');a=p.parse_args();print(json.dumps(execute() if a.execute else preflight(),indent=2))
