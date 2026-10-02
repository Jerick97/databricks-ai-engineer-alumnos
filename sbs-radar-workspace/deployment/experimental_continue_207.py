"""Resume207: reconcile partial204 uploads; preserve199 package/deadline and every attempt."""
from pathlib import Path
from types import SimpleNamespace
import argparse,importlib.util,io,json,time
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('continue207fix204',ROOT/'deployment/experimental_continue_204.py');fix=importlib.util.module_from_spec(s);s.loader.exec_module(fix)
prior=fix.prior;base=prior.base;require=prior.require;read=prior.read;durable=prior.durable;sha=prior.sha;CAPS=prior.CAPS;known=prior.known;config=prior.config;operator_identity=prior.operator_identity;control=prior.control;cleanup=prior.cleanup
STATE='deployment/state/experimental-continue207';FREEZE='runs/sk12-experimental-207-freeze.json';REVIEW='runs/sk09-experimental-207-review.json';PREVIOUS=fix.STATE
LIMITS={'http':1487,'upload':226,'mkdir':0,'start':1,'deploy':1};PRIOR_COUNTS={'http':1017,'upload':243,'mkdir':84,'start':2,'deploy':2}
END=fix.END;SOURCE=fix.SOURCE

def preflight(root=ROOT):
 root=Path(root);package,m,p,allowed,old=fix.preflight(root);fix.review(root);state=root/PREVIOUS;result=read(state/'result.json')
 require(result['api_reserved']=={'http':112,'upload':9,'mkdir':42,'start':0,'deploy':0} and result['aggregate_191_194_199_204']==PRIOR_COUNTS and result['error_type']=='DatabricksError' and result['cleanup']['status']=='stopped_observed','EXPERIMENT207_PRIOR_ATTEMPTS')
 require(read(state/'cleanup/result.json')['status']=='stopped_observed' and not (state/'start-intent.json').exists() and not (state/'deploy-intent.json').exists(),'EXPERIMENT207_PRIOR_EFFECTS')
 verified={};attempted={}
 for n,h in m['files_sha256'].items():
  key=base.sha(n.encode());expected={'path':p['source_code_path']+'/'+n,'sha256':h}
  for tag,bag in [('uploaded-',verified),('upload-',attempted)]:
   path=state/(tag+key+'.json')
   if path.exists():require(read(path)==expected,'EXPERIMENT207_RECEIPT_DRIFT');bag[n]=h
 require(len(verified)==8 and len(attempted)==9 and set(verified)<set(attempted),'EXPERIMENT207_PARTIAL_SCOPE')
 require(set(verified)==set(sorted(m['files_sha256'])[:8]) and set(attempted)==set(sorted(m['files_sha256'])[:9]),'EXPERIMENT207_ORDER')
 directories={read(x)['path'] for x in state.glob('mkdir-*.json')};expected_dirs={p['source_code_path'],*[p['source_code_path']+'/'+str(Path(n).parent) for n in m['files_sha256'] if str(Path(n).parent)!='.']}
 require(len(directories)==42 and directories==expected_dirs,'EXPERIMENT207_DIRECTORIES')
 stopped=read(root/'deployment/state/auth-observation207/app.json');require(known(stopped,allowed)=='STOPPED' and stopped.get('default_source_code_path')==old['source_code_path'],'EXPERIMENT207_STOPPED_OBSERVATION')
 return package,m,p,allowed,old,verified,set(attempted)-set(verified),directories

def review(root):
 value=read(root/REVIEW);require(value.get('status')=='PASS_EXPERIMENTAL_CONTINUE_207' and value.get('freeze_sha256')==sha(root/FREEZE) and value.get('one_additional_failed_import_attempt_retained') is True,'EXPERIMENT207_REVIEW')
 for n,h in read(root/FREEZE)['files_sha256'].items():require(sha(root/n)==h,'EXPERIMENT207_INPUT_DRIFT')

def services(cfg,prefix,admit,*,state):
 from databricks.sdk.mixins.workspace import WorkspaceExt
 from databricks.sdk.service.apps import AppsAPI
 original=prior.prior.transport.services(cfg,prefix,admit,uploads=226,mkdirs=0,state=state)
 api=prior.prior.LedgerAPI(original.api,state,LIMITS);return SimpleNamespace(workspace=WorkspaceExt(api),apps=AppsAPI(api),api=api)

def resume_upload(server,state,package,files,prefix,verified,ambiguous,directories,admit):
 from databricks.sdk.service.workspace import ImportFormat,ExportFormat
 def status(path):
  try:return base.obj(server.workspace.get_status(path))
  except Exception as e:
   if getattr(e,'error_code',None)=='RESOURCE_DOES_NOT_EXIST':return None
   raise
 def verify(path,h):
  with server.workspace.download(path,format=ExportFormat.AUTO) as stream:got=base.sha(stream.read(8388609))
  require(got==h,'EXPERIMENT207_REMOTE_DRIFT')
 for path in sorted(directories):
  admit();require((status(path) or {}).get('object_type')=='DIRECTORY','EXPERIMENT207_DIRECTORY_DRIFT')
 for n,h in sorted(files.items()):
  admit();path=prefix+'/'+n;key=base.sha(n.encode())
  if n in verified:
   verify(path,h);durable(state/('adopted-'+key+'.json'),{'path':path,'sha256':h,'prior204_verified':True});continue
  observed=status(path)
  if n in ambiguous:
   durable(state/'failed-import-reconciled.json',{'path':path,'observed':observed,'prior_attempt_retained':True,'new_import_allowed_only_if_missing':observed is None})
   if observed is not None:
    require(observed.get('object_type')=='FILE','EXPERIMENT207_AMBIGUOUS_TYPE');verify(path,h);durable(state/('adopted-'+key+'.json'),{'path':path,'sha256':h,'prior204_ambiguous_now_verified':True});continue
  else:require(observed is None,'EXPERIMENT207_UNEXPECTED_EXISTING_FILE')
  raw=(package/'source'/n).read_bytes();require(base.sha(raw)==h and len(raw)<=8388608,'EXPERIMENT207_LOCAL_DRIFT');durable(state/('upload-'+key+'.json'),{'path':path,'sha256':h})
  try:
   with io.BytesIO(raw) as stream:server.workspace.upload(path,stream,format=ImportFormat.RAW,overwrite=False)
  except Exception as exc:durable(state/('upload-error-'+key+'.json'),{'stage':'workspace_import','error_type':type(exc).__name__,'message_recorded':False,'automatic_retry':False,'next_step':'single_export_reconciliation'})
  verify(path,h);durable(state/('uploaded-'+key+'.json'),{'path':path,'sha256':h})
 durable(state/'source-verified.json',{'files':len(files),'source_code_path':prefix,'prior_verified_rechecked':len(verified),'prior_import_attempts_retained':9,'mkdir_attempts':0})

def execute(root=ROOT,*,config_factory=config,services_factory=services,clock=time.time,sleep=time.sleep,identity_fn=operator_identity,cfg=None):
 root=Path(root);package,m,p,allowed,old,verified,ambiguous,directories=preflight(root);review(root);end=p['expires_at_unix']
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
  app=base.obj(server.apps.get(base.APP));require(known(app,allowed)=='STOPPED' and app.get('default_source_code_path')==old['source_code_path'],'EXPERIMENT204_INITIAL_CHANGED');durable(state/'app-before.json',app)
  resume_upload(server,state,package,m['files_sha256'],p['source_code_path'],verified,ambiguous,directories,admit)
  admit();app=base.obj(server.apps.get(base.APP));require(known(app,allowed)=='STOPPED','EXPERIMENT207_PRESTART_CHANGED')
  start_at=clock();durable(state/'start-intent.json',{'app':base.APP,'at_unix':start_at});effect=True
  try:server.apps.start(base.APP)
  except Exception:pass
  for i in range(60):
   admit();app=base.obj(server.apps.get(base.APP));phase=prior.prior.restored(app,old,allowed,start_at);durable(state/f'active-observation-{i:02}.json',app)
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
    binding={'deployment_id':d['deployment_id'],'source_code_path':p['source_code_path'],'source_sha256':m['source_sha256'],'expires_at_unix':end,'caps':CAPS,'scope':'external_coordinator_only_not_server_global','process_epoch':None,'candidate_kind':'experimental_linux199','numeric_equivalence':'failed','final_release_authorized':False};durable(root/prior.STATE/'deploy-receipt.json',d);prior.migrate_ledger(root,root/prior.STATE,binding);durable(root/prior.STATE/'continuation207.json',{'state':STATE,'deploy_receipt_sha256':sha(state/'deploy-receipt.json'),'review_sha256':sha(root/REVIEW)});result.update(status='experimental_ui_evaluation_pending',binding=binding,cleanup_required_before_or_at_unix=end);handoff=True;break
   require(phase not in ('FAILED','CANCELLED'),'EXPERIMENT191_DEPLOY_FAILED');sleep(5)
  else:raise ValueError('EXPERIMENT191_DEPLOY_PENDING')
 except Exception as e:result.update(error_type=type(e).__name__,error_code=str(e) if str(e).startswith(('EXPERIMENT191_','EXPERIMENT194_','EXPERIMENT199_','EXPERIMENT204_','EXPERIMENT207_','FINAL168_')) else 'EXPERIMENT191_EXECUTION_FAILED')
 finally:
  if server:
   result['api_reserved']=server.api.counts;result['aggregate_191_194_199_204_207']={k:PRIOR_COUNTS[k]+server.api.counts[k] for k in LIMITS};server.api.session.close()
  if effect and not handoff:result['cleanup']=cleanup(cfg,state,allowed,sleep=sleep)
  durable(state/'result.json',result)
 return result

def stop(root=ROOT,*,cfg=None):
 root=Path(root);review(root);state=root/STATE;require((state/'start-intent.json').exists(),'EXPERIMENT204_NOT_ADOPTED')
 allowed=read(state/'allowed-deployments.json') if (state/'allowed-deployments.json').exists() else read(state/'restoration-observed.json') if (state/'restoration-observed.json').exists() else fix.adopted(read(root/fix.OBSERVATION),root)[0]
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
  _,m,p,_,_,verified,ambiguous,_=preflight();print(json.dumps({'status':'prepared207_same_window','source_sha256':m['source_sha256'],'expires_at_unix':p['expires_at_unix'],'prior_verified':len(verified),'ambiguous_files':list(ambiguous),'additional_limits':LIMITS,'prior_aggregate':PRIOR_COUNTS},indent=2))
