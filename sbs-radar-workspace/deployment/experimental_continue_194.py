"""Continuation194: same reviewed191 bytes/window, zero uploads, additional start/deploy."""
from pathlib import Path
from types import SimpleNamespace
import argparse,importlib.util,json,time
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('continue194prior191',ROOT/'deployment/experimental_app_191.py');prior=importlib.util.module_from_spec(s);s.loader.exec_module(prior)
base=prior.base;require=prior.require;read=prior.read;durable=prior.durable;sha=prior.sha
control=prior.control;CAPS=prior.CAPS;known=prior.known;cleanup=prior.cleanup;config=prior.config;operator_identity=prior.operator_identity
STATE='deployment/state/experimental-continue194';FREEZE='runs/sk12-experimental-194-freeze.json';REVIEW='runs/sk09-experimental-194-review.json'
END=1790716194;SOURCE='694605f5c11d9bcb82d75424db7e7cda83068ad07c64a8ec5318d9dd7f205f89'
LIMITS={'http':771,'upload':0,'mkdir':0,'start':1,'deploy':1}
PRIOR_COUNTS={'http':829,'upload':234,'mkdir':42,'start':1,'deploy':1}

def preflight(root=ROOT):
 root=Path(root);prior.preflight(root);prior.review(root);package,m,p=prior.ready(root)
 require(m['source_sha256']==SOURCE and m['deadline_unix']==END and p['expires_at_unix']==END,'EXPERIMENT194_SOURCE_WINDOW')
 state=root/prior.STATE;result=read(state/'result.json')
 require(result['api_reserved']==PRIOR_COUNTS and result['error_code']=='EXPERIMENT191_DEPLOY_UNKNOWN' and result['cleanup']['status']=='stopped_observed','EXPERIMENT194_PRIOR_EFFECTS')
 require(read(state/'cleanup/result.json')['status']=='stopped_observed' and not (state/'deploy-receipt.json').exists() and not (state/'demo-ledger/binding.json').exists(),'EXPERIMENT194_PRIOR_HANDOFF')
 require(read(state/'source-verified.json')=={'files':234,'source_code_path':p['source_code_path']},'EXPERIMENT194_PRIOR_VERIFIED')
 for n,h in m['files_sha256'].items():
  require(read(state/('uploaded-'+base.sha(n.encode())+'.json'))=={'path':p['source_code_path']+'/'+n,'sha256':h},'EXPERIMENT194_PRIOR_FILE')
 old=read(state/'start-observation-37.json')['active_deployment']
 require(old['deployment_id']=='01f1bc46cf3311e19cff9e89270bd7ec' and old['source_code_path']==read(root/prior.OLD)['source_code_path'] and old['creator']==prior.OWNER and old['create_time']=='2026-09-29T20:46:13Z','EXPERIMENT194_OLD_BINDING')
 return package,m,p,old

def review(root):
 value=read(root/REVIEW);require(value.get('status')=='PASS_EXPERIMENTAL_CONTINUE_194' and value.get('freeze_sha256')==sha(root/FREEZE),'EXPERIMENT194_REVIEW')
 for p,h in read(root/FREEZE)['files_sha256'].items():require(sha(root/p)==h,'EXPERIMENT194_INPUT_DRIFT')

def services(cfg,prefix,admit,*,state):
 from databricks.sdk.mixins.workspace import WorkspaceExt
 from databricks.sdk.service.apps import AppsAPI
 original=prior.transport.services(cfg,prefix,admit,uploads=0,mkdirs=0,state=state)
 api=prior.LedgerAPI(original.api,state,LIMITS)
 return SimpleNamespace(workspace=WorkspaceExt(api),apps=AppsAPI(api),api=api)

def restoration_ready(server,app,old,allowed,start_at,state,index):
 phase=prior.restored(app,old,allowed,start_at)
 if phase not in ('ACTIVE','RUNNING') or app.get('pending_deployment'):return False
 active=app.get('active_deployment');require(isinstance(active,dict),'EXPERIMENT194_ACTIVE_MISSING')
 ident=active['deployment_id'];fresh=base.obj(server.apps.get_deployment(base.APP,ident));durable(state/f'restoration-deployment-{index:02}.json',fresh)
 require(fresh.get('deployment_id')==ident and fresh.get('source_code_path')==old['source_code_path'] and fresh.get('creator')==prior.OWNER and fresh.get('create_time')==active.get('create_time'),'EXPERIMENT194_FRESH_RESTORE_BINDING')
 terminal={'SUCCEEDED','FAILED','CANCELLED'}
 return active.get('status',{}).get('state') in terminal and fresh.get('status',{}).get('state') in terminal

def execute(root=ROOT,*,config_factory=config,services_factory=services,clock=time.time,sleep=time.sleep,identity_fn=operator_identity):
 root=Path(root);package,m,p,old=preflight(root);review(root);end=p['expires_at_unix']
 def admit():require(clock()<end,'EXPERIMENT191_EXPIRED')
 require(type(end) is int and 0<end-clock()<=1800,'EXPERIMENT191_WINDOW');admit();cfg=config_factory();require(cfg.host.rstrip('/')==base.HOST,'EXPERIMENT191_HOST')
 state=root/STATE;state.mkdir(parents=True,exist_ok=False);durable(state/'admission.json',{'freeze_sha256':sha(root/FREEZE),'exact_review_sha256':sha(root/prior.EXACT),'expires_at_unix':end,'numeric_equivalence':'failed','final_release_authorized':False,'model_caps':CAPS})
 allowed={old['deployment_id']:old['source_code_path']};server=None;effect=False;handoff=False;result={'status':'incomplete','final_release_authorized':False,'numeric_equivalence':'failed','provider_calls_by_executor':0}
 try:
  identity_fn(cfg,state);admit()
  server=services_factory(cfg,p['source_code_path'],admit,state=state)
  app=base.obj(server.apps.get(base.APP));require(known(app,allowed)=='STOPPED' and app.get('default_source_code_path')==old['source_code_path'],'EXPERIMENT191_INITIAL_NOT_STOPPED');durable(state/'app-before.json',app)
  durable(state/'source-verified-reused.json',{'source_sha256':m['source_sha256'],'files':234,'prior_verification_sha256':sha(root/prior.STATE/'source-verified.json'),'remote_uploads':0})
  app=base.obj(server.apps.get(base.APP));require(known(app,allowed)=='STOPPED','EXPERIMENT191_PRESTART_CHANGED')
  start_at=clock();durable(state/'start-intent.json',{'app':base.APP,'at_unix':start_at});effect=True
  try:server.apps.start(base.APP)
  except Exception:pass
  for i in range(60):
   admit();app=base.obj(server.apps.get(base.APP));phase=prior.restored(app,old,allowed,start_at);durable(state/f'start-observation-{i:02}.json',app)
   if restoration_ready(server,app,old,allowed,start_at,state,i):break
   require(phase in ('STARTING','UPDATING','ACTIVE','RUNNING'),'EXPERIMENT191_START_FAILED');sleep(5)
  else:raise ValueError('EXPERIMENT191_RESTORE_PENDING')
  durable(state/'restoration-observed.json',allowed);admit();durable(state/'deploy-intent.json',{'source_code_path':p['source_code_path'],'mode':'SNAPSHOT','at_unix':clock()})
  from databricks.sdk.service.apps import AppDeployment,AppDeploymentMode
  try:d=base.obj(server.apps.deploy(base.APP,AppDeployment(source_code_path=p['source_code_path'],mode=AppDeploymentMode.SNAPSHOT)).response)
  except Exception:
   values=base.obj(server.api.do('GET',control.APP_PATH+'/deployments',query={'page_size':20}));require(not values.get('next_page_token'),'EXPERIMENT191_HISTORY_PAGINATED');matches=[x for x in values.get('app_deployments',[]) if x.get('source_code_path')==p['source_code_path']];require(len(matches)==1,'EXPERIMENT191_DEPLOY_UNKNOWN');d=matches[0]
  require(d.get('source_code_path')==p['source_code_path'] and isinstance(d.get('deployment_id'),str),'EXPERIMENT191_DEPLOY_RECEIPT');durable(state/'deploy-receipt.json',d);allowed[d['deployment_id']]=p['source_code_path'];durable(state/'allowed-deployments.json',allowed)
  for i in range(60):
   admit();observed=base.obj(server.apps.get_deployment(base.APP,d['deployment_id']));durable(state/f'deploy-observation-{i:02}.json',observed);phase=observed.get('status',{}).get('state')
   if phase=='SUCCEEDED':
    app=base.obj(server.apps.get(base.APP));require(known(app,allowed) in ('ACTIVE','RUNNING') and app.get('active_deployment',{}).get('deployment_id')==d['deployment_id'] and not app.get('pending_deployment'),'EXPERIMENT191_ACTIVE_BINDING');durable(state/'app-active.json',app)
    binding={'deployment_id':d['deployment_id'],'source_code_path':p['source_code_path'],'source_sha256':m['source_sha256'],'expires_at_unix':end,'caps':CAPS,'scope':'external_coordinator_only_not_server_global','process_epoch':None,'candidate_kind':'experimental_linux191','numeric_equivalence':'failed','final_release_authorized':False};durable(root/prior.STATE/'demo-ledger/binding.json',binding);result.update(status='experimental_ui_evaluation_pending',binding=binding,cleanup_required_before_or_at_unix=end);handoff=True;break
   require(phase not in ('FAILED','CANCELLED'),'EXPERIMENT191_DEPLOY_FAILED');sleep(5)
  else:raise ValueError('EXPERIMENT191_DEPLOY_PENDING')
 except Exception as e:result.update(error_type=type(e).__name__,error_code=str(e) if str(e).startswith(('EXPERIMENT191_','EXPERIMENT194_','FINAL168_')) else 'EXPERIMENT191_EXECUTION_FAILED')
 finally:
  if server:
   result['api_reserved']=server.api.counts;result['aggregate_191_194']={k:PRIOR_COUNTS[k]+server.api.counts[k] for k in LIMITS};server.api.session.close()
  if effect and not handoff:result['cleanup']=cleanup(cfg,state,allowed,sleep=sleep)
  durable(state/'result.json',result)
 return result

def stop(root=ROOT):
 root=Path(root);review(root);state=root/STATE;require((state/'start-intent.json').exists(),'EXPERIMENT194_NO_OWN_EFFECT')
 allowed=read(state/'allowed-deployments.json') if (state/'allowed-deployments.json').exists() else read(state/'restoration-observed.json') if (state/'restoration-observed.json').exists() else {'01f1bc46cf3311e19cff9e89270bd7ec':read(root/prior.OLD)['source_code_path']}
 return cleanup(config(),state,allowed)

def supervised_execute():
 result=execute();print(json.dumps(result,indent=2),flush=True)
 if result.get('status')=='experimental_ui_evaluation_pending':
  end=result['cleanup_required_before_or_at_unix'];state=ROOT/STATE
  try:
   while time.time()<end:
    if (state/'cleanup/result.json').exists():return
    time.sleep(min(10,max(.01,end-time.time())))
  finally:
   if not (state/'cleanup').exists():print(json.dumps(stop(),indent=2),flush=True)

if __name__=='__main__':
 parser=argparse.ArgumentParser();g=parser.add_mutually_exclusive_group();g.add_argument('--execute',action='store_true');g.add_argument('--stop',action='store_true');a=parser.parse_args()
 if a.execute:supervised_execute()
 elif a.stop:print(json.dumps(stop(),indent=2))
 else:
  _,m,p,old=preflight();print(json.dumps({'status':'prepared_continuation194','source_sha256':m['source_sha256'],'expires_at_unix':p['expires_at_unix'],'additional_limits':LIMITS,'prior_reserved':PRIOR_COUNTS,'final_release_authorized':False},indent=2))
