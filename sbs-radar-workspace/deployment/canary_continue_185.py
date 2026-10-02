"""Continue178 without uploads/start; accept only observed166 restoration."""
from pathlib import Path
import argparse,importlib.util,json,time
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('continue185prior178',ROOT/'deployment/canary_recovery_178.py');prior=importlib.util.module_from_spec(s);s.loader.exec_module(prior)
base=prior.base;require=prior.require;read=prior.read;durable=prior.durable;sha=prior.sha
FREEZE='runs/sk12-canary-continue-185-freeze.json';REVIEW='runs/sk09-canary-continue-185-review.json';STATE='deployment/state/linux-canary-continue-185';OLD166='deployment/state/linux-canary-integrated-166'
def preflight(root=ROOT):
 root=Path(root);prior.preflight(root);prior.check_review(root);old=root/prior.STATE;result=read(old/'result.json');binding=read(old/'source-binding.json')
 require(result['effects']=={'upload':237,'mkdir':42,'start':1,'deploy':0} and result['cleanup']['reserved_http_attempts']['stop']==0,'CANARY185_PRIOR_EFFECTS')
 require(not (old/'deploy-intent.json').exists() and read(old/'start-intent.json')=={'app':base.APP},'CANARY185_PRIOR_INTENT')
 manifest=read(old/'package/manifest.json');require(binding['manifest_sha256']==sha(old/'package/manifest.json') and binding['source_sha256']==manifest['source_sha256'] and binding['expires_at_unix']==manifest['expires_at_unix'],'CANARY185_SOURCE_BINDING')
 require(read(old/'source-verified.json')=={'files':237,'source_sha256':binding['source_sha256']},'CANARY185_SOURCE_VERIFIED')
 for n,h in manifest['files_sha256'].items():require(read(old/('uploaded-'+base.sha(n.encode())+'.json'))=={'path':binding['source_code_path']+'/'+n,'sha256':h},'CANARY185_READBACK_CHANGED')
 previous=read(root/OLD166/'deploy-receipt.json');restored=read(old/'start-observation-10.json')['pending_deployment'];before=read(old/'app-before.json')
 require(before['compute_status']['state']=='STOPPED' and before['default_source_code_path']==previous['source_code_path']==restored['source_code_path'],'CANARY185_RESTORE_SOURCE')
 require(restored['deployment_id']=='01f1bc423d1a1c5c81d7de749ad20cce' and restored['create_time']=='2026-09-29T20:13:30Z' and restored['creator']=='sociosdosmilveintiseis@gmail.com','CANARY185_RESTORE_IDENTITY')
 return {**binding,'status':'prepared_continuation','upload_max':0,'start_max':0,'deploy_max':1,'old_source':previous['source_code_path'],'old_ids':[previous['deployment_id'],restored['deployment_id']],'pending_wait_seconds':300,'deployment_wait_seconds':300}
def check_review(root):
 r=read(root/REVIEW);require(r.get('status')=='PASS_CANARY_CONTINUE_185' and r.get('freeze_sha256')==sha(root/FREEZE),'CANARY185_REVIEW_REQUIRED')
 for p,h in read(root/FREEZE)['files_sha256'].items():require(sha(root/p)==h,'CANARY185_INPUT_DRIFT')
def known(app,p,expected=None):
 prior.runner.transport.history.identity(app)
 for key in ('active_deployment','pending_deployment'):
  item=app.get(key)
  if item:
   old=item.get('source_code_path')==p['old_source'] and item.get('deployment_id') in p['old_ids']
   new=bool(expected and item.get('source_code_path')==expected['source_code_path'] and (not expected.get('deployment_id') or item.get('deployment_id')==expected['deployment_id']))
   require(old or new,'CANARY185_OTHER_DEPLOYMENT')
 require(app.get('compute_status',{}).get('state') in ('ACTIVE','RUNNING','STOPPING','STOPPED'),'CANARY185_COMPUTE_STATE')

def cleanup(cfg,state,p,expected,*,sleep=time.sleep,session_factory=None):
 import requests
 directory=state/'cleanup';directory.mkdir(exist_ok=False);control=prior.runner.control;api=control.Transport(cfg,directory,(session_factory or requests.Session)());out={'status':'incomplete'}
 try:
  app=api.request('workspace_get',control.APP_PATH);known(app,p,expected)
  if app.get('compute_status',{}).get('state')=='STOPPED':out['status']='stopped_observed';return out
  require(app['compute_status']['state'] in ('ACTIVE','RUNNING'),'CANARY185_CLEANUP_NOT_ACTIVE')
  history=api.request('workspace_get',control.APP_PATH+'/deployments');require(not history.get('next_page_token'),'CANARY185_HISTORY_INCOMPLETE');items=history.get('app_deployments');require(isinstance(items,list) and items,'CANARY185_HISTORY_EMPTY')
  from datetime import datetime
  times=[datetime.fromisoformat(x['create_time'].replace('Z','+00:00')) for x in items];latest=[x for x,t in zip(items,times) if t==max(times)];require(len(latest)==1,'CANARY185_HISTORY_AMBIGUOUS')
  probe=dict(app,active_deployment=latest[0],pending_deployment=None);known(probe,p,expected)
  app=api.request('workspace_get',control.APP_PATH);known(app,p,expected);require(app['compute_status']['state'] in ('ACTIVE','RUNNING'),'CANARY185_CLEANUP_STATE_CHANGED')
  allowed={*p['old_ids'],expected.get('deployment_id')};require(app.get('last_deployment_id') in allowed,'CANARY185_CLEANUP_LAST_CHANGED')
  durable(directory/'stop-intent.json',{'app':base.APP,'expected':expected,'accepted_old_ids':p['old_ids']})
  try:api.request('stop',control.APP_PATH+'/stop')
  except Exception as e:durable(directory/'ambiguous.json',{'error_type':type(e).__name__,'retry':False})
  for i in range(10):
   app=api.request('workspace_get',control.APP_PATH);known(app,p,expected)
   if app['compute_status']['state']=='STOPPED':out['status']='stopped_observed';break
   sleep(5)
  else:out['status']='stop_unconfirmed_no_retry'
 except Exception as e:out.update(error_type=type(e).__name__,error_code=str(e) if str(e).startswith(('CANARY185_','CANARY148_')) else 'CANARY185_CLEANUP_FAILED')
 finally:out['reserved_http_attempts']=api.counts;api.session.close();durable(directory/'result.json',out)
 return out

def execute(root=ROOT,*,config_factory=None,services_factory=prior.runner.transport.services,clock=time.time,sleep=time.sleep,capture_fn=prior.capture,cleanup_fn=cleanup):
 root=Path(root);p=preflight(root);check_review(root)
 def admit():require(clock()<p['expires_at_unix'],'CANARY185_EXPIRED')
 admit()
 if config_factory is None:
  from databricks.sdk.core import Config
  config_factory=Config
 cfg=config_factory(profile='databricks-ai-engineer-aws');require(cfg.host.rstrip('/')==base.HOST,'CANARY185_HOST');headers=cfg.authenticate();require(bool(headers),'CANARY185_AUTH');del headers;admit()
 state=root/STATE;state.mkdir(parents=True,exist_ok=False);durable(state/'admission.json',{'phase':'185','freeze_sha256':sha(root/FREEZE),'review_sha256':sha(root/REVIEW),**p})
 durable(state/'source-binding.json',{'source_code_path':p['source_code_path'],'source_sha256':p['source_sha256'],'source_binding178_sha256':sha(root/prior.STATE/'source-binding.json')})
 expected={'source_code_path':p['source_code_path'],'source_sha256':p['source_sha256'],'deployment_id':None};server=None;observed_owned=False;handoff=False;result={'status':'incomplete','provider_calls':0,'sql_calls':0,'linux_verified':False}
 try:
  server=services_factory(cfg,p['source_code_path'],admit,uploads=0,mkdirs=0,state=state);server.api.maximum['start']=0
  for i in range(60):
   admit();app=base.obj(server.apps.get(base.APP));known(app,p);require(app['compute_status']['state'] in ('ACTIVE','RUNNING'),'CANARY185_NOT_ACTIVE');observed_owned=True;durable(state/f'prior-observation-{i:02}.json',app)
   require(app.get('last_deployment_id') in (None,*p['old_ids']),'CANARY185_LAST_CHANGED')
   if not app.get('pending_deployment'):break
   sleep(5)
  else:raise ValueError('CANARY185_RESTORE_PENDING')
  admit();durable(state/'deploy-intent.json',{'source_code_path':p['source_code_path'],'mode':'SNAPSHOT'})
  from databricks.sdk.service.apps import AppDeployment,AppDeploymentMode
  try:deployment=base.obj(server.apps.deploy(base.APP,AppDeployment(source_code_path=p['source_code_path'],mode=AppDeploymentMode.SNAPSHOT)).response)
  except Exception:
   from itertools import islice
   matches=[base.obj(x) for x in islice(server.apps.list_deployments(base.APP,page_size=20),20) if base.obj(x).get('source_code_path')==p['source_code_path']];require(len(matches)==1,'CANARY185_DEPLOY_UNKNOWN');deployment=matches[0]
  expected['deployment_id']=deployment['deployment_id'];durable(state/'deploy-receipt.json',deployment)
  for i in range(60):
   admit();value=base.obj(server.apps.get_deployment(base.APP,deployment['deployment_id']));durable(state/f'deploy-observation-{i:02}.json',value);phase=value.get('status',{}).get('state')
   if phase=='SUCCEEDED':
    result.update(status='deployed_capture_pending',**expected)
    try:
     result['evidence']=capture_fn(cfg,state,expected,root=root)
     handoff=result['evidence'].get('status')=='captured_linux_report153_pass'
     if handoff:
      durable(state/'active-handoff.json',{**expected,'expires_at_unix':p['expires_at_unix'],'report_sha256':result['evidence']['report_sha256'],'root_cleanup_required_if_final_not_launched':True});result['status']='linux_pass_active_handoff_to_final186'
    except Exception as e:durable(state/'capture-failure.json',{'error_type':type(e).__name__,'cleanup_required':True});result['evidence']={'status':'capture_failed'}
    break
   require(phase not in ('FAILED','CANCELLED'),'CANARY185_DEPLOY_FAILED');sleep(5)
  else:raise ValueError('CANARY185_DEPLOY_PENDING')
 except Exception as e:result.update(error_type=type(e).__name__,error_code=str(e) if str(e).startswith('CANARY185_') else 'CANARY185_BOUNDED_FAILURE')
 finally:
  if server:result['effects']=server.api.counts;result['http_calls']=server.api.calls;server.api.session.close()
  if handoff:result['cleanup']={'status':'deferred_active_handoff','root_required_before_or_at_unix':p['expires_at_unix'],'reason':'avoid implicit restore on anotherstart; final1860start'}
  elif observed_owned:
   try:result['cleanup']=cleanup_fn(cfg,state,p,expected,sleep=sleep)
   except Exception as e:result['cleanup']={'status':'coordinator_required','error_type':type(e).__name__}
  durable(state/'result.json',result)
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');a=p.parse_args();print(json.dumps(execute() if a.execute else preflight(),indent=2))
