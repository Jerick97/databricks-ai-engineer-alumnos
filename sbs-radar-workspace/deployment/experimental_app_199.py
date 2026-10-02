"""Experimental199: reviewed proxy197 overlay, renewed bounded run, retained192 reservations."""
from pathlib import Path
from types import SimpleNamespace
import argparse,fcntl,importlib.util,json,os,shutil,time
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('experiment199prior191',ROOT/'deployment/experimental_app_191.py');prior=importlib.util.module_from_spec(s);s.loader.exec_module(prior)
s=importlib.util.spec_from_file_location('experiment199fix194',ROOT/'deployment/experimental_continue_194.py');fix=importlib.util.module_from_spec(s);s.loader.exec_module(fix)
base=prior.base;builder=prior.builder;require=prior.require;read=prior.read;durable=prior.durable;sha=prior.sha
control=prior.control;CAPS=prior.CAPS;known=prior.known;cleanup=prior.cleanup;config=prior.config;operator_identity=prior.operator_identity
STATE='deployment/state/experimental-app199';PACKAGE='deployment/state/experimental-materialized199'
FREEZE='runs/sk12-experimental-199-freeze.json';REVIEW='runs/sk09-experimental-199-review.json'
OVERLAY='runs/sk10-proxy-host-197-overlay';OLD='deployment/state/experimental-continue194/deploy-receipt.json'
OLD_LEDGER='deployment/state/experimental-app191/demo-ledger';PREFIX=prior.PREFIX.replace('experiment191-','experiment199-')
LIMITS={'http':1600,'upload':234,'mkdir':50,'start':1,'deploy':1}
PRIOR_COUNTS={'http':904,'upload':234,'mkdir':42,'start':2,'deploy':2};TURNS=('turn0','turn1','turn2','turn3')
ACTIONS='runs/sk10-demo-170-actions.json'

def preflight(root=ROOT):
 root=Path(root);prior.preflight(root);prior.review(root);_,m,p=prior.ready(root);fix.review(root)
 review197=read(root/'runs/sk09-proxy-host-197-review.json');freeze197=root/'runs/sk10-proxy-host-197-freeze.json'
 require(review197['status']=='PASS_HOST_PATCH_CODE_ONLY' and review197['freeze_sha256']==sha(freeze197),'EXPERIMENT199_HOST_REVIEW')
 for n,h in read(freeze197)['files_sha256'].items():require(sha(root/n)==h,'EXPERIMENT199_HOST_DRIFT')
 overlay=read(root/OVERLAY/'manifest.json');require(set(overlay['files_sha256'])=={'src/sbs/webapp/__init__.py','app133.py','app.yaml'},'EXPERIMENT199_OVERLAY_SCOPE')
 for n,h in overlay['base_files_sha256'].items():require(m['files_sha256'][n]==h,'EXPERIMENT199_BASE_DRIFT')
 for n,h in overlay['files_sha256'].items():require(sha(root/OVERLAY/n)==h,'EXPERIMENT199_OVERLAY_DRIFT')
 old=read(root/OLD);result=read(root/fix.STATE/'result.json');stopped=read(root/fix.STATE/'cleanup/result.json')
 require(result['aggregate_191_194']==PRIOR_COUNTS and result['status']=='experimental_ui_evaluation_pending' and stopped['status']=='stopped_observed' and stopped['latest_deployment_id']==old['deployment_id'],'EXPERIMENT199_PRIOR_STATE')
 require(old['source_code_path']==p['source_code_path'] and old['deployment_id']=='01f1bc4879681762b1f396de3f79c7aa','EXPERIMENT199_OLD_DEPLOYMENT')
 ledger=root/OLD_LEDGER;binding=read(ledger/'binding.json');require(binding==result['binding'] and binding['caps']==CAPS,'EXPERIMENT199_PRIOR_BINDING')
 require({x.name for x in ledger.iterdir()}=={'binding.json',*(f'turn-{a}-intent.json' for a in TURNS)},'EXPERIMENT199_PRIOR_LEDGER_CHANGED')
 actions=read(root/ACTIONS)
 for a in TURNS:
  intent=read(ledger/f'turn-{a}-intent.json')
  require(intent['turn_id']==a and intent['deployment_id']==old['deployment_id'] and intent['source_sha256']==m['source_sha256'] and intent['reserved']==actions[a]['reserved'] and intent['action_sha256']==base.sha(base.rawjson(actions[a])),'EXPERIMENT199_PRIOR_INTENT')
 require({k:sum(read(ledger/f'turn-{a}-intent.json')['reserved'][k] for a in TURNS) for k in CAPS}=={'generation_posts':1,'embedding_posts':1,'embedding_tokens':20000},'EXPERIMENT199_PRIOR_QUOTA')
 return {'status':'prepared199_no_deadline','overlay_manifest_sha256':sha(root/OVERLAY/'manifest.json'),'prior_aggregate':PRIOR_COUNTS,'additional_limits':LIMITS,'model_caps':CAPS,'deadline_emitted':False,'numeric_equivalence':'failed','final_release_authorized':False}

def review(root):
 value=read(root/REVIEW);require(value.get('status')=='PASS_EXPERIMENTAL_199' and value.get('freeze_sha256')==sha(root/FREEZE) and value.get('operator_attests_no_192_actions_sent') is True,'EXPERIMENT199_REVIEW')
 for p,h in read(root/FREEZE)['files_sha256'].items():require(sha(root/p)==h,'EXPERIMENT199_INPUT_DRIFT')

def transformed_files(root,end):
 root=Path(root);require(type(end)is int and end>0,'EXPERIMENT199_DEADLINE')
 source=root/prior.PACKAGE/'source';cfg=read(source/'config/app-integration-133.json');cfg['deadline_unix']=end
 changes={n:(root/OVERLAY/n).read_bytes() for n in read(root/OVERLAY/'manifest.json')['files_sha256']}
 changes['config/app-integration-133.json']=(json.dumps(cfg,sort_keys=True,separators=(',',':'))+'\n').encode()
 chunks=read(source/'chunks163-manifest.json')
 for n,raw in changes.items():chunks['logical_files_sha256'][n]=base.sha(raw)
 changes['chunks163-manifest.json']=(json.dumps(chunks,indent=2)+'\n').encode()
 return changes

def materialize(destination,*,root=ROOT,clock=time.time):
 root=Path(root);dest=Path(destination);require(not dest.exists(),'EXPERIMENT199_PACKAGE_EXISTS')
 end=int(clock())+1800;changes=transformed_files(root,end);shutil.copytree(root/prior.PACKAGE/'source',dest/'source')
 for n,raw in changes.items():(dest/'source'/n).write_bytes(raw)
 files=builder.files(dest/'source');m={'kind':'experimental_linux199_proxy197','deadline_unix':end,'base_source133_sha256':builder.BASE_SHA,'prior191_manifest_sha256':sha(root/prior.PACKAGE/'manifest.json'),'overlay197_manifest_sha256':sha(root/OVERLAY/'manifest.json'),'files_sha256':files,'source_sha256':builder.sha(builder.encoded(files)),'model_caps':CAPS,'worker_count':1,'numeric_equivalence':'failed','final_release_authorized':False}
 durable(dest/'manifest.json',m);durable(dest/'deployment-payload.json',{'app_name':base.APP,'host':base.HOST,'source_code_path':PREFIX+m['source_sha256'],'source_sha256':m['source_sha256'],'expires_at_unix':end,'mode':'SNAPSHOT','limits':LIMITS,'numeric_equivalence':'failed','final_release_authorized':False});return ready(root,package=dest)

def ready(root,*,package=None):
 root=Path(root);package=Path(package) if package else root/PACKAGE;m=builder.verify(package);p=read(package/'deployment-payload.json');end=m['deadline_unix']
 require(m['prior191_manifest_sha256']==sha(root/prior.PACKAGE/'manifest.json') and m['overlay197_manifest_sha256']==sha(root/OVERLAY/'manifest.json') and m['base_source133_sha256']==builder.BASE_SHA,'EXPERIMENT199_LINEAGE')
 require(m['kind']=='experimental_linux199_proxy197' and m['numeric_equivalence']=='failed' and m['final_release_authorized'] is False and m['model_caps']==CAPS and m['worker_count']==1,'EXPERIMENT199_MANIFEST')
 expected=dict(read(root/prior.PACKAGE/'manifest.json')['files_sha256']);expected.update({n:base.sha(raw) for n,raw in transformed_files(root,end).items()})
 require(m['files_sha256']==expected and len(expected)==234,'EXPERIMENT199_SOURCE_SCOPE')
 require(p=={'app_name':base.APP,'host':base.HOST,'source_code_path':PREFIX+m['source_sha256'],'source_sha256':m['source_sha256'],'expires_at_unix':end,'mode':'SNAPSHOT','limits':LIMITS,'numeric_equivalence':'failed','final_release_authorized':False},'EXPERIMENT199_PAYLOAD');return package,m,p

def services(cfg,prefix,admit,*,state):
 from databricks.sdk.mixins.workspace import WorkspaceExt
 from databricks.sdk.service.apps import AppsAPI
 original=prior.transport.services(cfg,prefix,admit,uploads=234,mkdirs=50,state=state);api=prior.LedgerAPI(original.api,state,LIMITS)
 return SimpleNamespace(workspace=WorkspaceExt(api),apps=AppsAPI(api),api=api)

def migrate_ledger(root,state,binding):
 ledger=state/'demo-ledger';require(not ledger.exists(),'EXPERIMENT199_LEDGER_EXISTS');old=Path(root)/OLD_LEDGER
 durable(ledger/'binding.json',binding)
 for a in TURNS:
  path=old/f'turn-{a}-intent.json';intent=read(path)
  durable(ledger/'history192'/path.name,intent)
  durable(ledger/path.name,{**intent,'deployment_id':binding['deployment_id'],'source_sha256':binding['source_sha256'],'migrated_from192_sha256':sha(path),'reservation_retained':True})
 durable(ledger/'migration.json',{'source_binding_sha256':sha(old/'binding.json'),'target_binding_sha256':sha(ledger/'binding.json'),'turn_ids':list(TURNS),'reservation_increase':{k:0 for k in CAPS},'operator_report':'root: no clickConsultar or POST/apiask for192; not universal traffic monitoring','old_ledger_unchanged':True,'review_sha256':sha(Path(root)/REVIEW)})

def execute(root=ROOT,*,config_factory=config,services_factory=services,clock=time.time,sleep=time.sleep,identity_fn=operator_identity,cfg=None):
 root=Path(root);preflight(root);review(root);old=read(root/OLD);cfg=cfg if cfg is not None else config_factory();require(cfg.host.rstrip('/')==base.HOST,'EXPERIMENT199_HOST');headers=cfg.authenticate();require(bool(headers),'EXPERIMENT199_AUTH');del headers
 state=root/STATE;state.mkdir(parents=True,exist_ok=False);identity_fn(cfg,state)
 package,m,p=materialize(root/PACKAGE,root=root,clock=clock);end=p['expires_at_unix']
 def admit():require(clock()<end,'EXPERIMENT191_EXPIRED')
 require(type(end) is int and 0<end-clock()<=1800,'EXPERIMENT191_WINDOW');admit()
 durable(state/'admission.json',{'freeze_sha256':sha(root/FREEZE),'exact_review_sha256':sha(root/prior.EXACT),'expires_at_unix':end,'numeric_equivalence':'failed','final_release_authorized':False,'model_caps':CAPS})
 allowed={old['deployment_id']:old['source_code_path']};server=None;effect=False;handoff=False;result={'status':'incomplete','final_release_authorized':False,'numeric_equivalence':'failed','provider_calls_by_executor':0}
 try:
  admit()
  server=services_factory(cfg,p['source_code_path'],admit,state=state)
  app=base.obj(server.apps.get(base.APP));require(known(app,allowed)=='STOPPED' and app.get('default_source_code_path')==old['source_code_path'],'EXPERIMENT191_INITIAL_NOT_STOPPED');durable(state/'app-before.json',app)
  prior.shipping.upload(server,state,package,m['files_sha256'],p['source_code_path'],admit)
  app=base.obj(server.apps.get(base.APP));require(known(app,allowed)=='STOPPED','EXPERIMENT191_PRESTART_CHANGED')
  start_at=clock();durable(state/'start-intent.json',{'app':base.APP,'at_unix':start_at});effect=True
  try:server.apps.start(base.APP)
  except Exception:pass
  for i in range(60):
   admit();app=base.obj(server.apps.get(base.APP));phase=prior.restored(app,old,allowed,start_at);durable(state/f'start-observation-{i:02}.json',app)
   if fix.restoration_ready(server,app,old,allowed,start_at,state,i):break
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
    binding={'deployment_id':d['deployment_id'],'source_code_path':p['source_code_path'],'source_sha256':m['source_sha256'],'expires_at_unix':end,'caps':CAPS,'scope':'external_coordinator_only_not_server_global','process_epoch':None,'candidate_kind':'experimental_linux199','numeric_equivalence':'failed','final_release_authorized':False};migrate_ledger(root,state,binding);result.update(status='experimental_ui_evaluation_pending',binding=binding,cleanup_required_before_or_at_unix=end);handoff=True;break
   require(phase not in ('FAILED','CANCELLED'),'EXPERIMENT191_DEPLOY_FAILED');sleep(5)
  else:raise ValueError('EXPERIMENT191_DEPLOY_PENDING')
 except Exception as e:result.update(error_type=type(e).__name__,error_code=str(e) if str(e).startswith(('EXPERIMENT191_','EXPERIMENT194_','EXPERIMENT199_','FINAL168_')) else 'EXPERIMENT191_EXECUTION_FAILED')
 finally:
  if server:
   result['api_reserved']=server.api.counts;result['aggregate_191_194_199']={k:PRIOR_COUNTS[k]+server.api.counts[k] for k in LIMITS};server.api.session.close()
  if effect and not handoff:result['cleanup']=cleanup(cfg,state,allowed,sleep=sleep)
  durable(state/'result.json',result)
 return result

def stop(root=ROOT,*,cfg=None):
 root=Path(root);review(root);state=root/STATE;require((state/'start-intent.json').exists(),'EXPERIMENT199_NO_OWN_EFFECT');old=read(root/OLD)
 allowed=read(state/'allowed-deployments.json') if (state/'allowed-deployments.json').exists() else read(state/'restoration-observed.json') if (state/'restoration-observed.json').exists() else {old['deployment_id']:old['source_code_path']}
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
    if (state/'demo-ledger/ui-failed.json').exists():break
    time.sleep(min(5,max(.01,end-time.time())))
  finally:
   if not (state/'cleanup').exists():print(json.dumps(stop(root,cfg=retained[0]),indent=2),flush=True)

class Coordinator:
 """Claim transferred intent once; never allocates another reservation or sends traffic."""
 def __init__(self,root=ROOT,clock=time.time):
  self.root=Path(root);review(self.root);self.path=self.root/STATE/'demo-ledger';self.clock=clock;self.binding=read(self.path/'binding.json')
  _,m,p=ready(self.root);b=self.binding
  require(b['deployment_id']==read(self.root/STATE/'deploy-receipt.json')['deployment_id'] and b['scope']=='external_coordinator_only_not_server_global' and b['process_epoch'] is None,'EXPERIMENT199_DEPLOYMENT_BINDING')
  require(b['candidate_kind']=='experimental_linux199' and b['source_sha256']==m['source_sha256'] and b['source_code_path']==p['source_code_path'] and b['expires_at_unix']==p['expires_at_unix'] and b['caps']==CAPS and b['numeric_equivalence']=='failed' and b['final_release_authorized'] is False,'EXPERIMENT199_LEDGER_BINDING')
  require(read(self.path/'migration.json')['target_binding_sha256']==sha(self.path/'binding.json'),'EXPERIMENT199_MIGRATION_BINDING')
 def claim(self,action,observation_path):
  require(action in TURNS,'EXPERIMENT199_TURN');o=read(observation_path);b=self.binding
  require(o.get('deployment_id')==b['deployment_id'] and o.get('source_sha256')==b['source_sha256'] and type(o.get('observed_at_unix'))in(int,float) and 0<=self.clock()-o['observed_at_unix']<=120 and self.clock()<b['expires_at_unix'],'EXPERIMENT199_OBSERVATION')
  fd=os.open(self.path,os.O_RDONLY);fcntl.flock(fd,fcntl.LOCK_EX)
  try:
   require(not (self.path/'ui-failed.json').exists() and not (self.path/'quota-unknown.json').exists(),'EXPERIMENT199_UI_BLOCKED')
   require(not (self.path/f'turn-{action}-claim.json').exists(),'EXPERIMENT199_NO_RESEND')
   intent=read(self.path/f'turn-{action}-intent.json');old=self.root/OLD_LEDGER/f'turn-{action}-intent.json';original=read(old)
   require(intent=={**original,'deployment_id':b['deployment_id'],'source_sha256':b['source_sha256'],'migrated_from192_sha256':sha(old),'reservation_retained':True},'EXPERIMENT199_MIGRATION_DRIFT')
   durable(self.path/f'turn-{action}-claim.json',{'turn_id':action,'intent_sha256':sha(self.path/f'turn-{action}-intent.json'),'observation_sha256':sha(Path(observation_path)),'reserved':intent['reserved'],'additional_reservation':{k:0 for k in CAPS}})
  finally:os.close(fd)
  return {'status':'transferred_intent_claimed_once_send_one_visible_action','turn_id':action,'reserved':intent['reserved']}
 def receipt(self,action,trace_path=None):
  require(action in TURNS and (self.path/f'turn-{action}-claim.json').exists(),'EXPERIMENT199_CLAIM_REQUIRED')
  coordinator=prior.module('runs/sk10-demo-coordinator-170.py','experiment199receipt170')
  return coordinator.Coordinator(self.path,clock=self.clock).receipt(action,trace_path)
 def fail(self):
  durable(self.path/'ui-failed.json',{'reason':'operator_observed_bad_UI','further_actions_allowed':False,'stop_requested':True})
  return {'status':'UI_blocked_supervisor_stop_requested'}

if __name__=='__main__':
 parser=argparse.ArgumentParser();g=parser.add_mutually_exclusive_group();g.add_argument('--execute',action='store_true');g.add_argument('--stop',action='store_true');g.add_argument('--claim',choices=TURNS);g.add_argument('--receipt',choices=TURNS);g.add_argument('--ui-failed',action='store_true');parser.add_argument('--observation',type=Path);parser.add_argument('--trace',type=Path);a=parser.parse_args()
 if a.execute:supervised_execute()
 elif a.stop:print(json.dumps(stop(),indent=2))
 elif a.claim:
  if not a.observation:parser.error('--observation required')
  print(json.dumps(Coordinator().claim(a.claim,a.observation),indent=2))
 elif a.receipt:print(json.dumps(Coordinator().receipt(a.receipt,a.trace),indent=2))
 elif a.ui_failed:print(json.dumps(Coordinator().fail(),indent=2))
 else:print(json.dumps(preflight(),indent=2))
