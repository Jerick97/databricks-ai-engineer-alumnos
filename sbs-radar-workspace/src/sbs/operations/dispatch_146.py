"""Bounded one-run dispatcher; existing SharedLedger owns idempotency.

No scheduling, writes to Files, grants or auto retry. Separate local budget counts
workspace sends; normal OAuth refresh traffic is not counted or persisted.
"""
from pathlib import Path
from types import SimpleNamespace
import json,time,re
from .cloud_driver import SingleAttemptApi,CloudDriver,load_config
from .cloud_dispatch import require,digest,obj
from .provision_106 import HOST,OWNER,OWNER_ID,safe_json,sha
from .provision_105 import _write_new
from .policy_binding_137 import separate_journal
from . import atomic,exclusive_lock
ROOT=Path(__file__).resolve().parents[3]
LIMITS={'http':128,'sql':24,'run_now':1}
def review_inputs(root=ROOT):
 root=Path(root);paths=safe_json(root/'runs/sk11-dispatch-146-imports.json')['modules'];return {p:sha((root/p).read_bytes()) for p in sorted(set(paths)|{'src/sbs/operations/job_defaults_146.py','src/sbs/operations/dispatch_146.py','runs/sk11-dispatch-146-imports.json'})}
class BoundedSession142:
 def __init__(self,session,state,config,request_id,authorize):
  self.session=session;self.state=Path(state);self.config=config;self.authorize=authorize
  self.host='https://'+HOST;self.adapters=session.adapters
  require(all(a.max_retries.total==0 for a in self.adapters.values()),'RETRIES_FORBIDDEN')
  require(isinstance(request_id,str) and re.fullmatch('[A-Za-z0-9_-]{1,128}',request_id),'REQUEST_ID_INVALID')
  key=digest({'job_id':config.writer.job_id,'request_id':request_id})
  self.expected={'job_id':config.writer.job_id,'idempotency_token':key,'job_parameters':{'request_id':key,'release_id':config.writer.release_id},'queue':{'enabled':True}}
 def request(self,method,url,**kwargs):
  self.authorize();require(isinstance(url,str) and url.startswith(self.host+'/api/') and not any(v in url for v in ('?','#','..')),'DISPATCH_HOST_PATH_INVALID')
  path=url[len(self.host):];run=method=='POST' and path=='/api/2.2/jobs/run-now';sql=method=='POST' and path=='/api/2.0/sql/statements';body=kwargs.get('json')
  require(method=='GET' or run or sql,'DISPATCH_OPERATION_FORBIDDEN')
  if run:require(body==self.expected,'DISPATCH_RUN_SCOPE')
  if sql:
   table='.'.join('`'+p+'`' for p in self.config.control_table.split('.'))
   allowed={'SELECT control_id, revision, state_json FROM '+table,'UPDATE '+table+' SET revision = revision + 1, state_json = :state WHERE control_id = :control AND revision = :revision'}
   require(isinstance(body,dict) and body.get('warehouse_id')==self.config.warehouse_id and body.get('statement') in allowed,'DISPATCH_SQL_SCOPE')
  p=self.state/'budget.json';b=safe_json(p) if p.exists() else dict.fromkeys(LIMITS,0)
  require(set(b)==set(LIMITS) and all(type(b[k]) is int and 0<=b[k]<=LIMITS[k] for k in LIMITS),'DISPATCH_BUDGET_INVALID')
  b['http']+=1;b['sql']+=int(sql);b['run_now']+=int(run)
  require(all(b[k]<=LIMITS[k] for k in LIMITS),'DISPATCH_BUDGET_EXHAUSTED');atomic(p,b)
  prefix=self.state/('http-%03d'%b['http']);_write_new(Path(str(prefix)+'-intent.json'),{'method':method,'path':path,'body_sha256':digest(body) if body is not None else None})
  self.authorize()
  try:response=self.session.request(method,url,**kwargs)
  except Exception:
   _write_new(Path(str(prefix)+'-unknown.json'),{'request_outcome':'unknown','method':method,'path':path});raise ValueError('DISPATCH_TRANSPORT_UNKNOWN') from None
  _write_new(Path(str(prefix)+'-response.json'),{'status':response.status_code,'method':method,'path':path})
  return response
 def close(self):self.session.close()
class RunApi142:
 def __init__(self,base):self.base=base;self._cfg=base._cfg
 def do(self,method,path=None,*,body=None,headers=None,**kwargs):
  if method!='POST' or path!='/api/2.2/jobs/run-now':return self.base.do(method,path,body=body,headers=headers,**kwargs)
  require(not kwargs,'DISPATCH_RUN_EXTRA_FIELDS')
  response=self.base.session.request(method,self._cfg.host.rstrip('/')+path,json=body,headers={**(headers or {}),**self._cfg.authenticate()},timeout=(10,60),allow_redirects=False,stream=True)
  try:
   require(200<=response.status_code<300,'DISPATCH_RUN_HTTP_REJECTED');raw=response.raw.read(65537,decode_content=True);require(len(raw)<=65536,'DISPATCH_RUN_RESPONSE_TOO_LARGE')
   value=json.loads(raw);require(isinstance(value,dict) and type(value.get('run_id')) is int and value['run_id']>0,'DISPATCH_RUN_ID_REQUIRED');return value
  finally:response.close()

def execute(config_path,config_sha,state,review,*,profile,request_id='sbs-writer-first-146',root=ROOT):
 root=Path(root).resolve();state=Path(state).resolve();separate_journal(root,state)
 require(state==root/'deployment/state/dispatch146','DISPATCH_JOURNAL_FIXED')
 config=load_config(config_path,config_sha)
 require(review.get('files')==review_inputs(root),'DISPATCH_REVIEW_INPUTS_REQUIRED')
 def authorize():
  now=int(time.time()*1000)
  require(review.get('approved') is True and review.get('scope')=='dispatch146_one_run' and review.get('limits')==LIMITS and review.get('config_sha256')==config_sha,'DISPATCH_REVIEW_REQUIRED')
  require(type(review.get('issued_at_ms')) is int and type(review.get('expires_at_ms')) is int and review['issued_at_ms']<=now<review['expires_at_ms'] and review['expires_at_ms']-review['issued_at_ms']<=1800000,'DISPATCH_REVIEW_EXPIRED')
  require(config.policy['issued_at_ms']<=now<config.policy['expires_at_ms'],'DISPATCH_POLICY_EXPIRED')
  for p,h in review['files'].items():require(sha((root/p).read_bytes())==h,'DISPATCH_INPUT_DRIFT')
 authorize()
 from databricks.sdk.core import Config
 from databricks.sdk.service import jobs,catalog,sql,compute,iam,files
 import requests
 cfg=Config(profile=profile);require(cfg.host.rstrip('/')=='https://'+HOST,'DISPATCH_HOST_INVALID');auth=cfg.authenticate();del auth
 state.mkdir(parents=True,exist_ok=True)
 with exclusive_lock(state):
  session=BoundedSession142(requests.Session(),state,config,request_id,authorize);api=SingleAttemptApi(cfg,session=session,max_calls=128)
  services=SimpleNamespace(api=api,jobs=jobs.JobsAPI(RunApi142(api)),tables=catalog.TablesAPI(api),statement_execution=sql.StatementExecutionAPI(api),warehouses=sql.WarehousesAPI(api),clusters=compute.ClustersAPI(api),current_user=iam.CurrentUserAPI(api),files=files.FilesAPI(api))
  try:
   me=obj(services.current_user.me());require(me.get('id')==OWNER_ID and me.get('userName')==OWNER and me.get('active') is True,'DISPATCH_OPERATOR_INVALID')
   from .job_defaults_146 import bind_services146,pin as metadata_pin
   services=bind_services146(services,config.writer,lambda record:atomic(state/('metadata146-'+metadata_pin(record)+'.json'),record))
   driver=CloudDriver(config,services,evidence_mode='real');record=driver.dispatcher.request(request_id)
   result={'request':record,'budget':safe_json(state/'budget.json'),'job_run_success':'not_observed','e2e':False,'cost':None};atomic(state/'result.json',result);return result
  finally:session.close()
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--config-sha256',required=True);p.add_argument('--review',type=Path,required=True);p.add_argument('--profile',required=True);a=p.parse_args()
 print(json.dumps(execute(a.config,a.config_sha256,ROOT/'deployment/state/dispatch146',safe_json(a.review),profile=a.profile)))
