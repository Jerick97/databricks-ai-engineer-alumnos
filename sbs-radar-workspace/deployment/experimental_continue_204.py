"""Continuation204 adopts explicitly observed user-started App; zero starts, same199 deadline."""
from pathlib import Path
from types import SimpleNamespace
import argparse,importlib.util,json,time
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('continue204prior199',ROOT/'deployment/experimental_app_199.py');prior=importlib.util.module_from_spec(s);s.loader.exec_module(prior)
base=prior.base;require=prior.require;read=prior.read;durable=prior.durable;sha=prior.sha;CAPS=prior.CAPS;known=prior.known;config=prior.config;operator_identity=prior.operator_identity;control=prior.control
STATE='deployment/state/experimental-continue204';FREEZE='runs/sk12-experimental-204-freeze.json';REVIEW='runs/sk09-experimental-204-review.json';OBSERVATION='deployment/state/auth-observation204/app.json'
LIMITS={'http':1599,'upload':234,'mkdir':50,'start':0,'deploy':1};PRIOR_COUNTS={'http':905,'upload':234,'mkdir':42,'start':2,'deploy':2}
END=1790719123;SOURCE='24687d1435c9b7dbbd0a0689ff02328556031122a37b2fa4cf4b4cbfe789ec98'

def adopted(app,root):
 old=read(Path(root)/prior.OLD);source=old['source_code_path'];allowed={}
 for key in ('active_deployment','pending_deployment'):
  d=app.get(key)
  if d:
   require(d.get('creator')==prior.prior.OWNER and d.get('source_code_path')==source and isinstance(d.get('deployment_id'),str),'EXPERIMENT204_ADOPTION_OWNER_SOURCE')
   when=datetime.fromisoformat(d['create_time'].replace('Z','+00:00')).timestamp();lower=datetime.fromisoformat(old['create_time'].replace('Z','+00:00')).timestamp()
   require(lower<=when<END,'EXPERIMENT204_ADOPTION_TIME');allowed[d['deployment_id']]=source
 require(app.get('active_deployment') and app.get('last_deployment_id') in (None,*allowed) and app.get('default_source_code_path')==source,'EXPERIMENT204_ADOPTION_BINDING')
 require(known(app,allowed) in ('ACTIVE','RUNNING'),'EXPERIMENT204_NOT_ACTIVE');return allowed,app['active_deployment']

def preflight(root=ROOT):
 root=Path(root);prior.preflight(root);prior.review(root);package,m,p=prior.ready(root);state=root/prior.STATE;result=read(state/'result.json')
 require(result['aggregate_191_194_199']==PRIOR_COUNTS and result['api_reserved']=={'http':1,'upload':0,'mkdir':0,'start':0,'deploy':0} and result['error_code']=='EXPERIMENT191_FOREIGN_DEPLOYMENT','EXPERIMENT204_PRIOR_ATTEMPTS')
 require(not (state/'deploy-intent.json').exists() and not (state/'start-intent.json').exists() and not (state/'deploy-receipt.json').exists() and not (state/'demo-ledger').exists(),'EXPERIMENT204_PRIOR_EFFECTS')
 require(p['expires_at_unix']==END and m['source_sha256']==SOURCE,'EXPERIMENT204_SOURCE_WINDOW')
 app=read(root/OBSERVATION);allowed,old=adopted(app,root)
 return package,m,p,allowed,old

def review(root):
 value=read(root/REVIEW);require(value.get('status')=='PASS_EXPERIMENTAL_CONTINUE_204' and value.get('freeze_sha256')==sha(root/FREEZE) and value.get('user_started_app_adoption_authorized') is True,'EXPERIMENT204_REVIEW')
 for n,h in read(root/FREEZE)['files_sha256'].items():require(sha(root/n)==h,'EXPERIMENT204_INPUT_DRIFT')

def services(cfg,prefix,admit,*,state):
 from databricks.sdk.mixins.workspace import WorkspaceExt
 from databricks.sdk.service.apps import AppsAPI
 original=prior.prior.transport.services(cfg,prefix,admit,uploads=234,mkdirs=50,state=state);original.api.maximum['start']=0
 api=prior.prior.LedgerAPI(original.api,state,LIMITS);return SimpleNamespace(workspace=WorkspaceExt(api),apps=AppsAPI(api),api=api)

def reconcile_cleanup(app,state,allowed,history,*,clock=time.time):
 from datetime import datetime
 require(not history.get('next_page_token'),'EXPERIMENT191_CLEANUP_HISTORY_PAGINATED')
 items=history.get('app_deployments');require(isinstance(items,list),'EXPERIMENT191_CLEANUP_HISTORY')
 start=read(state/'adoption-intent.json');before=read(state/'app-before.json');prior_source=before['default_source_code_path'];new=read(state/'deploy-intent.json') if (state/'deploy-intent.json').exists() else None
 ids={app.get('last_deployment_id')}|{app[k].get('deployment_id') for k in ('active_deployment','pending_deployment') if app.get(k)};ids.discard(None)
 found=[]
 for ident in ids-set(allowed):
  matches=[x for x in items if x.get('deployment_id')==ident];require(len(matches)==1,'EXPERIMENT191_CLEANUP_ID_UNKNOWN');d=matches[0]
  require(d.get('creator')==prior.prior.OWNER,'EXPERIMENT191_CLEANUP_FOREIGN_prior.prior.OWNER');when=datetime.fromisoformat(d['create_time'].replace('Z','+00:00')).timestamp()
  source=d.get('source_code_path');is_restore=source==prior_source and when>=start['at_unix']-2;is_candidate=bool(new and source==new['source_code_path'] and when>=new['at_unix']-2)
  require((is_restore or is_candidate) and when<=clock()+5,'EXPERIMENT191_CLEANUP_FOREIGN_SOURCE_TIME');found.append(d)
 for d in found:allowed[d['deployment_id']]=d['source_code_path']
 require(sum(v==prior_source for v in allowed.values())<=2 and (not new or sum(v==new['source_code_path'] for v in allowed.values())<=1),'EXPERIMENT191_CLEANUP_AMBIGUOUS_IDS')
 known(app,allowed);durable(state/'cleanup/reconciled-deployments.json',{'allowed':allowed,'observed':found});return allowed

def cleanup(cfg,state,allowed,*,sleep=time.sleep,session_factory=None):
 import requests
 directory=state/'cleanup';directory.mkdir(exist_ok=False);api=control.Transport(cfg,directory,(session_factory or requests.Session)());out={'status':'incomplete'}
 try:
  app=api.request('workspace_get',control.APP_PATH)
  try:phase=known(app,allowed)
  except ValueError:
   history=api.request('workspace_get',control.APP_PATH+'/deployments');reconcile_cleanup(app,state,allowed,history);phase=known(app,allowed)
  if phase=='STOPPED':out['status']='stopped_observed';return out
  require(phase in ('ACTIVE','RUNNING','STARTING','UPDATING'),'EXPERIMENT191_CLEANUP_STATE')
  app=api.request('workspace_get',control.APP_PATH);known(app,allowed)
  durable(directory/'stop-intent.json',{'app':base.APP,'allowed_deployments':allowed})
  try:api.request('stop',control.APP_PATH+'/stop')
  except Exception:durable(directory/'stop-unknown.json',{'retry':False})
  for i in range(10):
   app=api.request('workspace_get',control.APP_PATH);phase=known(app,allowed)
   if phase=='STOPPED':out['status']='stopped_observed';break
   sleep(5)
  else:out['status']='stop_unconfirmed_no_retry'
 except Exception as e:out.update(error_type=type(e).__name__,error_code=str(e) if str(e).startswith('EXPERIMENT191_') else 'EXPERIMENT191_CLEANUP_UNCONFIRMED')
 finally:out['reserved']=api.counts;api.session.close();durable(directory/'result.json',out)
 return out

def execute(root=ROOT,*,config_factory=config,services_factory=services,clock=time.time,sleep=time.sleep,identity_fn=operator_identity,cfg=None):
 root=Path(root);package,m,p,allowed,old=preflight(root);review(root);end=p['expires_at_unix']
 require(type(end)is int and 0<end-clock()<=1800,'EXPERIMENT204_WINDOW')
 cfg=cfg if cfg is not None else config_factory();require(cfg.host.rstrip('/')==base.HOST,'EXPERIMENT204_HOST');headers=cfg.authenticate();require(bool(headers),'EXPERIMENT204_AUTH');del headers
 state=root/STATE;state.mkdir(parents=True,exist_ok=False);identity_fn(cfg,state)
 def admit():require(clock()<end,'EXPERIMENT191_EXPIRED')
 require(type(end) is int and 0<end-clock()<=1800,'EXPERIMENT191_WINDOW');admit()
 durable(state/'admission.json',{'freeze_sha256':sha(root/FREEZE),'exact_review_sha256':sha(root/prior.REVIEW),'expires_at_unix':end,'numeric_equivalence':'failed','final_release_authorized':False,'model_caps':CAPS})
 server=None;effect=False;handoff=False;result={'status':'incomplete','final_release_authorized':False,'numeric_equivalence':'failed','provider_calls_by_executor':0}
 try:
  admit()
  server=services_factory(cfg,p['source_code_path'],admit,state=state)
  app=base.obj(server.apps.get(base.APP));require(known(app,allowed) in ('ACTIVE','RUNNING') and app.get('default_source_code_path')==old['source_code_path'],'EXPERIMENT204_INITIAL_CHANGED');durable(state/'app-before.json',app)
  start_at=datetime.fromisoformat(old['create_time'].replace('Z','+00:00')).timestamp();durable(state/'adoption-intent.json',{'at_unix':start_at,'observed_app_sha256':sha(root/OBSERVATION),'user_started':True,'executor_starts':0});effect=True
  prior.prior.shipping.upload(server,state,package,m['files_sha256'],p['source_code_path'],admit)
  for i in range(60):
   admit();app=base.obj(server.apps.get(base.APP));phase=known(app,allowed);durable(state/f'active-observation-{i:02}.json',app)
   if prior.fix.restoration_ready(server,app,old,allowed,start_at,state,i):break
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
    binding={'deployment_id':d['deployment_id'],'source_code_path':p['source_code_path'],'source_sha256':m['source_sha256'],'expires_at_unix':end,'caps':CAPS,'scope':'external_coordinator_only_not_server_global','process_epoch':None,'candidate_kind':'experimental_linux199','numeric_equivalence':'failed','final_release_authorized':False};durable(root/prior.STATE/'deploy-receipt.json',d);prior.migrate_ledger(root,root/prior.STATE,binding);durable(root/prior.STATE/'continuation204.json',{'state':STATE,'deploy_receipt_sha256':sha(state/'deploy-receipt.json'),'review_sha256':sha(root/REVIEW)});result.update(status='experimental_ui_evaluation_pending',binding=binding,cleanup_required_before_or_at_unix=end);handoff=True;break
   require(phase not in ('FAILED','CANCELLED'),'EXPERIMENT191_DEPLOY_FAILED');sleep(5)
  else:raise ValueError('EXPERIMENT191_DEPLOY_PENDING')
 except Exception as e:result.update(error_type=type(e).__name__,error_code=str(e) if str(e).startswith(('EXPERIMENT191_','EXPERIMENT194_','EXPERIMENT199_','EXPERIMENT204_','FINAL168_')) else 'EXPERIMENT191_EXECUTION_FAILED')
 finally:
  if server:
   result['api_reserved']=server.api.counts;result['aggregate_191_194_199_204']={k:PRIOR_COUNTS[k]+server.api.counts[k] for k in LIMITS};server.api.session.close()
  if effect and not handoff:result['cleanup']=cleanup(cfg,state,allowed,sleep=sleep)
  durable(state/'result.json',result)
 return result

def stop(root=ROOT,*,cfg=None):
 root=Path(root);review(root);state=root/STATE;require((state/'adoption-intent.json').exists(),'EXPERIMENT204_NOT_ADOPTED')
 allowed=read(state/'allowed-deployments.json') if (state/'allowed-deployments.json').exists() else adopted(read(root/OBSERVATION),root)[0]
 return cleanup(cfg if cfg is not None else config(),state,allowed)

def supervised_execute(root=ROOT,*,config_factory=config,cfg=None):
 retained=[cfg]
 def provider():
  if retained[0] is None:retained[0]=config_factory()
  return retained[0]
 result=execute(root,config_factory=provider);print(json.dumps(result,indent=2),flush=True)
 if result.get('status')=='experimental_ui_evaluation_pending':
  end=result['cleanup_required_before_or_at_unix'];state=Path(root)/STATE
  try:
   while time.time()<end:
    if (state/'cleanup/result.json').exists():return
    if (Path(root)/prior.STATE/'demo-ledger/ui-failed.json').exists():break
    time.sleep(min(5,max(.01,end-time.time())))
  finally:
   if not (state/'cleanup').exists():print(json.dumps(stop(root,cfg=retained[0]),indent=2),flush=True)

if __name__=='__main__':
 parser=argparse.ArgumentParser();g=parser.add_mutually_exclusive_group();g.add_argument('--execute',action='store_true');g.add_argument('--stop',action='store_true');a=parser.parse_args()
 if a.execute:supervised_execute()
 elif a.stop:print(json.dumps(stop(),indent=2))
 else:
  _,m,p,allowed,_=preflight();print(json.dumps({'status':'prepared204_existing_window','source_sha256':m['source_sha256'],'expires_at_unix':p['expires_at_unix'],'adopted':allowed,'additional_limits':LIMITS,'prior_aggregate':PRIOR_COUNTS},indent=2))
