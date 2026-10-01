"""Bounded evidence and separate single stop for owned145/151 canary."""
from pathlib import Path
import argparse,base64,importlib.util,json,time
from datetime import datetime
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('observe148recovery151',ROOT/'deployment/canary_recovery_154.py');prior=importlib.util.module_from_spec(s);s.loader.exec_module(prior)
history=prior.history
base=prior.base;read=base.read;durable=base.durable;require=base.require;sha=prior.sha
FREEZE='runs/sk12-canary-observe-stop-148-freeze.json';REVIEW='runs/sk09-canary-observe-stop-148-review.json'
ORIGIN='https://sbs-radar-pilot-7474657121564806.aws.databricksapps.com'
APP_PATH='/api/2.0/apps/'+base.APP

def preflight(root=ROOT):
 root=Path(root);prior.preflight(root)
 return dict(status='prepared_review_required',app_gets_max=3,stop_posts_max=1,stop_readback_gets_max=10,provider_calls=0,scope='technical canary only; stop separate from evidence')
def check_review(root):
 review=read(root/REVIEW);require(review.get('status')=='PASS_CANARY_OBSERVE_STOP_148' and review.get('freeze_sha256')==sha(root/FREEZE),'CANARY148_REVIEW_REQUIRED')
 for p,h in read(root/FREEZE)['files_sha256'].items():require(sha(root/p)==h,'CANARY148_INPUT_DRIFT')
 prior.check_review(root)
def binding(root):
 old=root/history.prior.STATE;state=root/prior.STATE
 source=read(old/'source-binding.json');admission=read(state/'admission.json')
 require(admission['freeze_sha256']==sha(root/prior.FREEZE) and admission['expires_at_unix']==source['expires_at_unix'],'CANARY148_ADMISSION_CHANGED')
 require(read(state/'start-intent.json')=={'app':base.APP},'CANARY148_START_NOT_OWNED')
 before=read(state/'app-prestart.json');history.identity(before)
 require(before.get('compute_status',{}).get('state')=='STOPPED' and not before.get('active_deployment') and not before.get('pending_deployment'),'CANARY148_PRIOR_COMPUTE_NOT_STOPPED')
 receipt=read(state/'deploy-receipt.json') if (state/'deploy-receipt.json').exists() else {}
 if (state/'deploy-intent.json').exists():require(read(state/'deploy-intent.json')=={'source_code_path':source['source_code_path'],'mode':'SNAPSHOT'},'CANARY148_DEPLOY_INTENT_CHANGED')
 return {'deployment_id':receipt.get('deployment_id'),'source_code_path':source['source_code_path'],'source_sha256':source['source_sha256']}
def owned(app,expected,*,allow_unbound=False):
 history.identity(app)
 for key in ('active_deployment','pending_deployment'):
  item=app.get(key)
  if item:require(item.get('source_code_path')==expected['source_code_path'] and (not expected['deployment_id'] or item.get('deployment_id')==expected['deployment_id']),'CANARY148_DEPLOYMENT_NOT_OWNED')
 require(allow_unbound or bool(app.get('active_deployment')),'CANARY148_ACTIVE_DEPLOYMENT_NOT_OWNED')
 url=app.get('url');parts=urlsplit(url or '')
 require(url==ORIGIN and parts.scheme=='https' and parts.hostname==urlsplit(ORIGIN).hostname and not parts.username and not parts.password and not parts.query and not parts.fragment and parts.port is None,'CANARY148_APP_URL_CHANGED')
 return app.get('compute_status',{}).get('state')
def latest_owned(payload,expected):
 require(not payload.get('next_page_token'),'CANARY148_DEPLOYMENT_HISTORY_INCOMPLETE')
 items=payload.get('app_deployments');require(isinstance(items,list),'CANARY148_DEPLOYMENT_HISTORY_SHAPE')
 if not items:require(expected['deployment_id'] is None,'CANARY148_OWN_DEPLOYMENT_MISSING');return
 require(all(isinstance(x,dict) and isinstance(x.get('create_time'),str) for x in items),'CANARY148_DEPLOYMENT_TIMESTAMP')
 times=[datetime.fromisoformat(x['create_time'].replace('Z','+00:00')) for x in items];require(all(t.tzinfo is not None for t in times),'CANARY148_TIMESTAMP_TIMEZONE');latest=max(times);matches=[x for x,t in zip(items,times) if t==latest]
 require(len(matches)==1 and matches[0].get('source_code_path')==expected['source_code_path'] and (not expected['deployment_id'] or matches[0].get('deployment_id')==expected['deployment_id']),'CANARY148_LATEST_DEPLOYMENT_NOT_OWNED')

class Transport:
 def __init__(self,cfg,state,session,clock=time.time):
  self.cfg=cfg;self.state=state;self.session=session;self.clock=clock;self.end=clock()+600;self.counts={'workspace_get':0,'app_get':0,'stop':0};self.seq=0
  require(cfg.host.rstrip('/')==base.HOST,'CANARY148_HOST_CHANGED');require(all(a.max_retries.total==0 for a in session.adapters.values()),'CANARY148_RETRIES_FORBIDDEN');session.trust_env=False
 def request(self,kind,path):
  require(self.clock()<self.end,'CANARY148_ACTION_TIMEOUT')
  if kind=='app_get':require(path in ('/health','/evidence'),'CANARY148_PATH_FORBIDDEN');url=ORIGIN+path;method='GET';cap=3
  elif kind=='workspace_get':require(path in (APP_PATH,APP_PATH+'/deployments'),'CANARY148_PATH_FORBIDDEN');url=base.HOST+path;method='GET';cap=13
  else:require(kind=='stop' and path==APP_PATH+'/stop','CANARY148_PATH_FORBIDDEN');url=base.HOST+path;method='POST';cap=1
  require(self.counts[kind]<cap,'CANARY148_REQUEST_CAP');self.counts[kind]+=1;self.seq+=1
  durable(self.state/f'http-intent-{self.seq:02}.json',{'kind':kind,'method':method,'url':url})
  headers=self.cfg.authenticate();require(self.clock()<self.end,'CANARY148_ACTION_TIMEOUT')
  response=self.session.request(method,url,params={'page_size':20} if path==APP_PATH+'/deployments' else None,headers=headers,timeout=(15,30),allow_redirects=False,stream=True)
  try:
   content=response.raw.read(1048577,decode_content=True)
   durable(self.state/f'http-response-{self.seq:02}.json',{'kind':kind,'url':url,'status':response.status_code,'body_base64':base64.b64encode(content[:1048576]).decode(),'truncated':len(content)>1048576})
   require(len(content)<=1048576,'CANARY148_RESPONSE_CAP');require(200<=response.status_code<300,'CANARY148_HTTP_FAILED_NO_RETRY')
   return json.loads(content) if content else {}
  finally:response.close()

def execute(action,root=ROOT,*,config_factory=None,session_factory=None,sleep=time.sleep):
 root=Path(root);require(action in ('evidence','stop'),'CANARY148_ACTION');preflight(root);check_review(root);expected=binding(root)
 if config_factory is None:
  from databricks.sdk.core import Config
  config_factory=Config
 if session_factory is None:
  import requests
  session_factory=requests.Session
 cfg=config_factory(profile='databricks-ai-engineer-aws');require(cfg.host.rstrip('/')==base.HOST,'CANARY148_HOST_CHANGED');headers=cfg.authenticate();require(bool(headers),'CANARY148_AUTH');del headers
 state=root/'deployment/state'/('linux-canary-148-'+action);state.mkdir(parents=True,exist_ok=False)
 durable(state/'admission.json',{'action':action,'freeze_sha256':sha(root/FREEZE),'review_sha256':sha(root/REVIEW),'binding':expected,'app_get_max':3,'stop_max':1 if action=='stop' else 0,'stop_readback_max':10,'renew_deployment_window':False})
 transport=Transport(cfg,state,session_factory());result={'status':'incomplete','action':action,'quality_accepted':False,'provider_calls':0}
 try:
  observed=transport.request('workspace_get',APP_PATH);phase=owned(observed,expected,allow_unbound=action=='stop')
  if action=='evidence':
   require(phase in ('ACTIVE','RUNNING'),'CANARY148_COMPUTE_NOT_ACTIVE')
   for path in ('/health','/evidence'):
    value=transport.request('app_get',path);durable(state/(path[1:]+'-parsed.json'),value)
   result['status']='evidence_captured_not_validated'
  else:
   if phase=='STOPPED':result['status']='already_stopped_observed'
   else:
    require(phase in ('ACTIVE','RUNNING'),'CANARY148_COMPUTE_NOT_STOPPABLE')
    # Latest identity observation immediately before one stop; no other deployment.
    observed=transport.request('workspace_get',APP_PATH);require(owned(observed,expected,allow_unbound=True) in ('ACTIVE','RUNNING'),'CANARY148_COMPUTE_CHANGED')
    latest_owned(transport.request('workspace_get',APP_PATH+'/deployments'),expected)
    durable(state/'stop-intent.json',{'app':base.APP,**expected})
    try:transport.request('stop',APP_PATH+'/stop')
    except Exception as e:durable(state/'stop-ambiguous.json',{'error_type':type(e).__name__,'retry':False})
    for i in range(10):
     observed=transport.request('workspace_get',APP_PATH);history.identity(observed)
     pending=observed.get('pending_deployment');require(not pending or pending.get('source_code_path')==expected['source_code_path'],'CANARY148_PENDING_DEPLOYMENT')
     active=observed.get('active_deployment')
     require(not active or ((not expected['deployment_id'] or active.get('deployment_id')==expected['deployment_id']) and active.get('source_code_path')==expected['source_code_path']),'CANARY148_DEPLOYMENT_CHANGED')
     if observed.get('compute_status',{}).get('state')=='STOPPED':result['status']='stopped_observed';break
     sleep(2)
    else:result['status']='stop_unconfirmed_no_retry'
 except Exception as error:result.update(error_type=type(error).__name__,error_code=str(error) if str(error).startswith('CANARY148_') else 'CANARY148_BOUNDED_FAILURE')
 finally:
  result['reserved_http_attempts']=transport.counts;transport.session.close();durable(state/'result.json',result)
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--execute',choices=('evidence','stop'));a=p.parse_args();print(json.dumps(execute(a.execute) if a.execute else preflight(),indent=2))
