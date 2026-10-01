"""Continue observed154 start, no repeated uploads/start; deploy once."""
from pathlib import Path
import argparse,importlib.util,json,time
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('continue159prior154',ROOT/'deployment/canary_recovery_154.py');prior=importlib.util.module_from_spec(s);s.loader.exec_module(prior)
base=prior.base;require=base.require;read=base.read;durable=base.durable;sha=prior.sha
FREEZE='runs/sk12-canary-continue-159-freeze.json';REVIEW='runs/sk09-canary-continue-159-review.json';STATE='deployment/state/linux-canary-continue-159'
def preflight(root=ROOT):
 root=Path(root);prior.preflight(root);prior.check_review(root)
 state=root/prior.STATE;old=root/prior.history.prior.STATE;binding=read(old/'source-binding.json');result=read(state/'result.json')
 require(result.get('effects')=={'upload':217,'mkdir':0,'start':1,'deploy':0},'CANARY159_EFFECTS_CHANGED')
 require(read(state/'start-intent.json')=={'app':base.APP} and not (state/'deploy-intent.json').exists(),'CANARY159_PRIOR_INTENT')
 require(read(state/'source-verified.json')=={'source_sha256':binding['source_sha256'],'files':218},'CANARY159_SOURCE_NOT_VERIFIED')
 files=read(old/'package/manifest.json')['files_sha256']
 for n,h in files.items():require(read(state/('uploaded-'+base.sha(n.encode())+'.json'))=={'path':binding['source_code_path']+'/'+n,'sha256':h,'export_format':'AUTO','reconciles_phase145':n=='app.yaml'},'CANARY159_RECEIPT_CHANGED')
 return {'status':'prepared_continue_review_required','expires_at_unix':binding['expires_at_unix'],'source_code_path':binding['source_code_path'],'source_sha256':binding['source_sha256'],'uploads_max':0,'start_max':0,'deploy_max':1,'compute_get_max':60,'deployment_get_max':20}
def check_review(root):
 r=read(root/REVIEW);require(r.get('status')=='PASS_CANARY_CONTINUE_159' and r.get('freeze_sha256')==sha(root/FREEZE),'CANARY159_REVIEW_REQUIRED')
 for p,h in read(root/FREEZE)['files_sha256'].items():require(sha(root/p)==h,'CANARY159_INPUT_DRIFT')
def execute(root=ROOT,*,config_factory=None,services_factory=prior.services,clock=time.time,sleep=time.sleep):
 root=Path(root);p=preflight(root);check_review(root)
 def admit():require(clock()<p['expires_at_unix'],'CANARY159_WINDOW_EXPIRED')
 admit()
 if config_factory is None:
  from databricks.sdk.core import Config
  config_factory=Config
 cfg=config_factory(profile='databricks-ai-engineer-aws');require(cfg.host.rstrip('/')==base.HOST,'CANARY159_HOST');headers=cfg.authenticate();require(bool(headers),'CANARY159_AUTH');del headers;admit()
 state=root/STATE;state.mkdir(parents=True,exist_ok=False);durable(state/'admission.json',{'phase':'159','freeze_sha256':sha(root/FREEZE),'review_sha256':sha(root/REVIEW),**p})
 server=None;result={'status':'incomplete','stop_required_by_coordinator':True,'quality_accepted':False,'provider_calls':0,'sql_calls':0}
 try:
  server=services_factory(cfg,p['source_code_path'],admit,uploads=0,mkdirs=0,state=state);server.api.maximum['start']=0
  for i in range(60):
   admit();app=base.obj(server.apps.get(base.APP));prior.history.identity(app);durable(state/f'compute-observation-{i:02}.json',app)
   require(not app.get('active_deployment') and not app.get('pending_deployment'),'CANARY159_OTHER_DEPLOYMENT')
   phase=app.get('compute_status',{}).get('state')
   if phase in ('ACTIVE','RUNNING'):break
   require(phase in ('STARTING','UPDATING'),'CANARY159_COMPUTE_NOT_STARTING');sleep(10)
  else:raise ValueError('CANARY159_START_UNCONFIRMED')
  admit();durable(state/'deploy-intent.json',{'source_code_path':p['source_code_path'],'mode':'SNAPSHOT'})
  from databricks.sdk.service.apps import AppDeployment,AppDeploymentMode
  try:deployed=base.obj(server.apps.deploy(base.APP,AppDeployment(source_code_path=p['source_code_path'],mode=AppDeploymentMode.SNAPSHOT)).response)
  except Exception:
   from itertools import islice
   matches=[base.obj(x) for x in islice(server.apps.list_deployments(base.APP,page_size=20),20) if base.obj(x).get('source_code_path')==p['source_code_path']]
   require(len(matches)==1,'CANARY159_DEPLOY_UNCONFIRMED_NO_RETRY');deployed=matches[0]
  durable(state/'deploy-receipt.json',deployed)
  for i in range(20):
   admit();observed=base.obj(server.apps.get_deployment(base.APP,deployed['deployment_id']));durable(state/f'deploy-observation-{i:02}.json',observed);phase=observed.get('status',{}).get('state')
   if phase=='SUCCEEDED':result.update(status='deployed_linux_evidence_pending',deployment_id=deployed['deployment_id'],source_code_path=p['source_code_path'],source_sha256=p['source_sha256']);break
   require(phase not in ('FAILED','CANCELLED'),'CANARY159_DEPLOY_FAILED');sleep(5)
  else:raise ValueError('CANARY159_DEPLOY_PENDING')
 except Exception as e:result.update(error_type=type(e).__name__,error_code=str(e) if str(e).startswith('CANARY159_') else 'CANARY159_BOUNDED_FAILURE')
 finally:
  if server:result['effects']=server.api.counts;result['http_calls']=server.api.calls;server.api.session.close()
  durable(state/'result.json',result)
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');a=p.parse_args();print(json.dumps(execute() if a.execute else preflight(),indent=2))
