"""Explicit experimental Linux191 admission; never invokes/passes153 release gates."""
from pathlib import Path
from types import SimpleNamespace
import argparse,base64,hashlib,importlib.util,json,shutil,time
ROOT=Path(__file__).resolve().parents[1]
def module(path,name):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
transport=module('deployment/canary_recovery_154.py','experimental191transport')
shipping=module('deployment/final_deploy_168.py','experimental191shipping')
control=module('deployment/canary_observe_stop_148.py','experimental191stop')
builder=shipping.packager.base;base=transport.base;require=base.require;read=base.read;durable=base.durable
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
HELD='runs/sk12-final-chunked-168-source';PACKAGE='deployment/state/experimental-materialized191';STATE='deployment/state/experimental-app191'
FREEZE='runs/sk12-experimental-191-freeze.json';REVIEW='runs/sk09-experimental-191-review.json';EXACT='runs/sk09-experimental-materialized-191-review.json'
RUNTIME='deployment/state/linux-canary-continue-185/capture178/linux-report.json';NUMERIC='runs/sk05-sk09-numeric-188-paired-result.json';MEMO='runs/sk09-linux-next-experiment-190.json'
OLD='deployment/state/linux-canary-continue-185/deploy-receipt.json';PREFIX='/Workspace/Users/sociosdosmilveintiseis@gmail.com/sbs-radar/releases/experiment191-'
OWNER='sociosdosmilveintiseis@gmail.com';CAPS={'generation_posts':4,'embedding_posts':2,'embedding_tokens':20000}

def preflight(root=ROOT):
 from importlib.metadata import version
 require(version('databricks-sdk')=='0.102.0','EXPERIMENT191_SDK_VERSION')
 root=Path(root);r=read(root/RUNTIME);n=read(root/NUMERIC);memo=read(root/MEMO);m=builder.verify(root/HELD)
 require(r['status']=='PASS_LINUX_CANARY_RUNTIME_ONLY' and r['platform']['system']=='Linux' and r['source133_sha256']==builder.BASE_SHA,'EXPERIMENT191_RUNTIME')
 require(n['status']=='FAIL_PAIRED_NUMERIC_SMOKE' and n['numeric_pass'] is False and n['same_full_input'] is True and n['full_rows_sha256']==r['smoke_input_sha256'] and n['remote_report_sha256']==sha(root/RUNTIME) and n['tolerance']==.001 and all(x>.001 for x in n['absolute_deltas']),'EXPERIMENT191_NUMERIC_EVIDENCE')
 require(memo['status']=='RECOMMEND_SEPARATE_CONTROLLED_LINUX_CANDIDATE_EXPERIMENT' and memo['production_or_final_release_approved'] is False,'EXPERIMENT191_MEMO')
 require(m['kind']=='held168_deadline0' and m['deadline_unix']==0 and m['base_source133_sha256']==builder.BASE_SHA and len(m['files_sha256'])==234,'EXPERIMENT191_HELD')
 return {'status':'experimental_candidate_only','numeric_equivalence':'failed','runtime_linux':'passed','relevance_acceptance':'not_evaluated','final_release_authorized':False,'deadline_emitted':False,'caps':CAPS}

def review(root):
 v=read(root/REVIEW);require(v.get('status')=='PASS_EXPERIMENTAL_191_CODE_ONLY' and v.get('freeze_sha256')==sha(root/FREEZE),'EXPERIMENT191_REVIEW')
 for p,h in read(root/FREEZE)['files_sha256'].items():require(sha(root/p)==h,'EXPERIMENT191_INPUT_DRIFT')

def materialize(destination=None,*,root=ROOT,clock=time.time,check_review=True):
 root=Path(root);gate=preflight(root)
 if check_review:review(root)
 dest=Path(destination) if destination else root/PACKAGE;require(not dest.exists(),'EXPERIMENT191_PACKAGE_EXISTS')
 expires=int(clock())+1800;shutil.copytree(root/HELD/'source',dest/'source');source=dest/'source';cfg=read(source/'config/app-integration-133.json')
 require(cfg['deadline_unix']==0 and cfg['generation_posts_per_process']==4 and cfg['embedding_posts_per_process']==2 and cfg['embedding_tokens_per_process']==20000 and cfg['worker_count']==1,'EXPERIMENT191_CONFIG')
 cfg['deadline_unix']=expires;(source/'config/app-integration-133.json').write_text(json.dumps(cfg,sort_keys=True,separators=(',',':'))+'\n')
 chunks=read(source/'chunks163-manifest.json');chunks['logical_files_sha256']['config/app-integration-133.json']=sha(source/'config/app-integration-133.json');(source/'chunks163-manifest.json').write_text(json.dumps(chunks,indent=2)+'\n')
 files=builder.files(source);m={'kind':'experimental_linux191_exact_review_required','deadline_unix':expires,'base_source133_sha256':builder.BASE_SHA,'held168_manifest_sha256':sha(root/HELD/'manifest.json'),'files_sha256':files,'source_sha256':builder.sha(builder.encoded(files)),'admission':{**gate,'deadline_emitted':True},'evidence_sha256':{p:sha(root/p) for p in (RUNTIME,NUMERIC,MEMO)},'packaging_changes_only':['config/app-integration-133.json:deadline','chunks163-manifest.json:config hash'],'model_caps':CAPS,'worker_count':1}
 durable(dest/'manifest.json',m);payload={'app_name':base.APP,'host':base.HOST,'source_code_path':PREFIX+m['source_sha256'],'source_sha256':m['source_sha256'],'expires_at_unix':expires,'mode':'SNAPSHOT','limits':{'http':1600,'upload':234,'mkdir':50,'start':1,'deploy':1},'numeric_equivalence':'failed','final_release_authorized':False};durable(dest/'deployment-payload.json',payload);return m

def ready(root,*,exact=True):
 package=root/PACKAGE;m=builder.verify(package);p=read(package/'deployment-payload.json')
 require(m['kind']=='experimental_linux191_exact_review_required' and m['admission']['numeric_equivalence']=='failed' and m['admission']['final_release_authorized'] is False,'EXPERIMENT191_KIND')
 require(p=={'app_name':base.APP,'host':base.HOST,'source_code_path':PREFIX+m['source_sha256'],'source_sha256':m['source_sha256'],'expires_at_unix':m['deadline_unix'],'mode':'SNAPSHOT','limits':{'http':1600,'upload':234,'mkdir':50,'start':1,'deploy':1},'numeric_equivalence':'failed','final_release_authorized':False},'EXPERIMENT191_PAYLOAD')
 held=read(root/HELD/'manifest.json')['files_sha256'];changed={n for n in held if held[n]!=m['files_sha256'].get(n)};require(set(held)==set(m['files_sha256']) and changed=={'config/app-integration-133.json','chunks163-manifest.json'},'EXPERIMENT191_SOURCE_SCOPE')
 cfg=read(package/'source/config/app-integration-133.json');old=read(root/HELD/'source/config/app-integration-133.json');require(cfg=={**old,'deadline_unix':m['deadline_unix']},'EXPERIMENT191_CONFIG_DRIFT')
 ch=read(package/'source/chunks163-manifest.json');original=read(root/HELD/'source/chunks163-manifest.json');original['logical_files_sha256']['config/app-integration-133.json']=sha(package/'source/config/app-integration-133.json');require(ch==original,'EXPERIMENT191_CHUNKS_DRIFT')
 if exact:
  v=read(root/EXACT);require(v.get('status')=='PASS_EXACT_EXPERIMENTAL_191' and v.get('manifest_sha256')==sha(package/'manifest.json') and v.get('payload_sha256')==sha(package/'deployment-payload.json') and v.get('executor_freeze_sha256')==sha(root/FREEZE),'EXPERIMENT191_EXACT_REVIEW')
 return package,m,p

class LedgerAPI:
 def __init__(self,delegate,state,limits):self.delegate=delegate;self.state=state;self.limits=limits;self.counts=dict.fromkeys(limits,0)
 def __getattr__(self,n):return getattr(self.delegate,n)
 def do(self,method,path=None,**kw):
  kind={'/api/2.0/workspace/import':'upload','/api/2.0/workspace/mkdirs':'mkdir',control.APP_PATH+'/start':'start',control.APP_PATH+'/deployments':'deploy'}.get(path) if method=='POST' else None
  self.counts['http']+=1
  if kind:self.counts[kind]+=1
  require(all(self.counts[k]<=self.limits[k] for k in self.limits),'EXPERIMENT191_API_CAP')
  durable(self.state/f'api-{self.counts["http"]:04}.json',{'method':method,'path':path,'reserved':dict(self.counts),'request_retry':False})
  return self.delegate.do(method,path,**kw)

def services(cfg,prefix,admit,*,state):
 from databricks.sdk.mixins.workspace import WorkspaceExt
 from databricks.sdk.service.apps import AppsAPI
 original=transport.services(cfg,prefix,admit,uploads=234,mkdirs=50,state=state);api=LedgerAPI(original.api,state,{'http':1600,'upload':234,'mkdir':50,'start':1,'deploy':1})
 return SimpleNamespace(workspace=WorkspaceExt(api),apps=AppsAPI(api),api=api)

def known(app,allowed):
 transport.history.identity(app);require(app.get('url')==builder.ORIGIN,'EXPERIMENT191_ORIGIN')
 for key in ('active_deployment','pending_deployment'):
  d=app.get(key)
  if d:require(allowed.get(d.get('deployment_id'))==d.get('source_code_path'),'EXPERIMENT191_FOREIGN_DEPLOYMENT')
 require(app.get('last_deployment_id') in (None,*allowed),'EXPERIMENT191_LAST_DEPLOYMENT');return app.get('compute_status',{}).get('state')

def restored(app,old,allowed,start_at):
 from datetime import datetime
 for key in ('active_deployment','pending_deployment'):
  d=app.get(key)
  if d and d.get('deployment_id') not in allowed:
   require(d.get('source_code_path')==old['source_code_path'] and d.get('creator')==OWNER and isinstance(d.get('deployment_id'),str),'EXPERIMENT191_RESTORE_OWNER_SOURCE')
   when=datetime.fromisoformat(d['create_time'].replace('Z','+00:00')).timestamp();require(start_at-2<=when<=time.time()+5,'EXPERIMENT191_RESTORE_TIME');allowed[d['deployment_id']]=d['source_code_path']
 require(len(allowed)<=2,'EXPERIMENT191_MULTIPLE_RESTORES');return known(app,allowed)

def reconcile_cleanup(app,state,allowed,history,*,clock=time.time):
 from datetime import datetime
 require(not history.get('next_page_token'),'EXPERIMENT191_CLEANUP_HISTORY_PAGINATED')
 items=history.get('app_deployments');require(isinstance(items,list),'EXPERIMENT191_CLEANUP_HISTORY')
 start=read(state/'start-intent.json');before=read(state/'app-before.json');prior_source=before['default_source_code_path'];new=read(state/'deploy-intent.json') if (state/'deploy-intent.json').exists() else None
 ids={app.get('last_deployment_id')}|{app[k].get('deployment_id') for k in ('active_deployment','pending_deployment') if app.get(k)};ids.discard(None)
 found=[]
 for ident in ids-set(allowed):
  matches=[x for x in items if x.get('deployment_id')==ident];require(len(matches)==1,'EXPERIMENT191_CLEANUP_ID_UNKNOWN');d=matches[0]
  require(d.get('creator')==OWNER,'EXPERIMENT191_CLEANUP_FOREIGN_OWNER');when=datetime.fromisoformat(d['create_time'].replace('Z','+00:00')).timestamp()
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

def operator_identity(cfg,state):
 import requests
 session=requests.Session();session.trust_env=False
 require(all(a.max_retries.total==0 for a in session.adapters.values()),'EXPERIMENT191_IDENTITY_RETRIES')
 durable(state/'identity-intent.json',{'method':'GET','path':'/api/2.0/preview/scim/v2/Me'})
 try:
  response=session.get(base.HOST+'/api/2.0/preview/scim/v2/Me',headers=cfg.authenticate(),timeout=(15,30),allow_redirects=False,stream=True)
  try:
   raw=response.raw.read(1048577,decode_content=True);require(response.status_code==200 and len(raw)<=1048576,'EXPERIMENT191_IDENTITY_HTTP');me=json.loads(raw)
   require(me.get('id')=='76826984571984' and me.get('userName')==OWNER and me.get('active') is True,'EXPERIMENT191_OPERATOR')
   durable(state/'identity-observed.json',{'id':me['id'],'userName':me['userName'],'active':True})
  finally:response.close()
 finally:session.close()

def config():
 from databricks.sdk.core import Config
 cfg=Config(profile='databricks-ai-engineer-aws');require(cfg.host.rstrip('/')==base.HOST,'EXPERIMENT191_HOST');return cfg

def execute(root=ROOT,*,config_factory=config,services_factory=services,clock=time.time,sleep=time.sleep,identity_fn=operator_identity):
 root=Path(root);preflight(root);review(root);package,m,p=ready(root);end=p['expires_at_unix']
 def admit():require(clock()<end,'EXPERIMENT191_EXPIRED')
 require(type(end) is int and 0<end-clock()<=1800,'EXPERIMENT191_WINDOW');admit();cfg=config_factory();require(cfg.host.rstrip('/')==base.HOST,'EXPERIMENT191_HOST')
 state=root/STATE;state.mkdir(parents=True,exist_ok=False);durable(state/'admission.json',{'freeze_sha256':sha(root/FREEZE),'exact_review_sha256':sha(root/EXACT),'expires_at_unix':end,'numeric_equivalence':'failed','final_release_authorized':False,'model_caps':CAPS})
 old=read(root/OLD);allowed={old['deployment_id']:old['source_code_path']};server=None;effect=False;handoff=False;result={'status':'incomplete','final_release_authorized':False,'numeric_equivalence':'failed','provider_calls_by_executor':0}
 try:
  identity_fn(cfg,state);admit()
  server=services_factory(cfg,p['source_code_path'],admit,state=state)
  app=base.obj(server.apps.get(base.APP));require(known(app,allowed)=='STOPPED' and app.get('default_source_code_path')==old['source_code_path'],'EXPERIMENT191_INITIAL_NOT_STOPPED');durable(state/'app-before.json',app)
  shipping.upload(server,state,package,m['files_sha256'],p['source_code_path'],admit)
  app=base.obj(server.apps.get(base.APP));require(known(app,allowed)=='STOPPED','EXPERIMENT191_PRESTART_CHANGED')
  start_at=clock();durable(state/'start-intent.json',{'app':base.APP,'at_unix':start_at});effect=True
  try:server.apps.start(base.APP)
  except Exception:pass
  for i in range(60):
   admit();app=base.obj(server.apps.get(base.APP));phase=restored(app,old,allowed,start_at);durable(state/f'start-observation-{i:02}.json',app)
   if phase in ('ACTIVE','RUNNING') and not app.get('pending_deployment'):break
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
    binding={'deployment_id':d['deployment_id'],'source_code_path':p['source_code_path'],'source_sha256':m['source_sha256'],'expires_at_unix':end,'caps':CAPS,'scope':'external_coordinator_only_not_server_global','process_epoch':None,'candidate_kind':'experimental_linux191','numeric_equivalence':'failed','final_release_authorized':False};durable(state/'demo-ledger/binding.json',binding);result.update(status='experimental_ui_evaluation_pending',binding=binding,cleanup_required_before_or_at_unix=end);handoff=True;break
   require(phase not in ('FAILED','CANCELLED'),'EXPERIMENT191_DEPLOY_FAILED');sleep(5)
  else:raise ValueError('EXPERIMENT191_DEPLOY_PENDING')
 except Exception as e:result.update(error_type=type(e).__name__,error_code=str(e) if str(e).startswith(('EXPERIMENT191_','FINAL168_')) else 'EXPERIMENT191_EXECUTION_FAILED')
 finally:
  if server:result['api_reserved']=server.api.counts;server.api.session.close()
  if effect and not handoff:result['cleanup']=cleanup(cfg,state,allowed,sleep=sleep)
  durable(state/'result.json',result)
 return result

def stop(root=ROOT):
 root=Path(root);review(root);state=root/STATE;require((state/'start-intent.json').exists(),'EXPERIMENT191_NO_OWN_EFFECT');allowed=read(state/'allowed-deployments.json') if (state/'allowed-deployments.json').exists() else read(state/'restoration-observed.json') if (state/'restoration-observed.json').exists() else {read(root/OLD)['deployment_id']:read(root/OLD)['source_code_path']};return cleanup(config(),state,allowed)
def supervised_execute():
 result=execute();print(json.dumps(result,indent=2),flush=True)
 if result.get('status')=='experimental_ui_evaluation_pending':
  end=result['cleanup_required_before_or_at_unix'];state=ROOT/STATE
  while time.time()<end:
   if (state/'cleanup/result.json').exists():return
   time.sleep(min(10,max(.01,end-time.time())))
  if not (state/'cleanup').exists():print(json.dumps(stop(),indent=2),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group();g.add_argument('--materialize',action='store_true');g.add_argument('--execute',action='store_true');g.add_argument('--stop',action='store_true');a=p.parse_args()
 if a.execute:supervised_execute()
 else:print(json.dumps(materialize() if a.materialize else stop() if a.stop else preflight(),indent=2))
