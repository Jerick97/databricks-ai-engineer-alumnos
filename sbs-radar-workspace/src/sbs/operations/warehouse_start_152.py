"""One start of observed existing warehouse;7GET total including identity."""
from pathlib import Path
import json,time,re
from .provision_106 import HOST,OWNER,OWNER_ID,WAREHOUSE,safe_json,sha
from .cloud_dispatch import require
from .provision_105 import _write_new
from .job_recovery_126 import ROOT,bounded_text
from . import atomic,exclusive_lock
LIMITS={'get':7,'start':1}
PATH='/api/2.0/sql/warehouses/'+WAREHOUSE
ME='/api/2.0/preview/scim/v2/Me'
def inputs(root=ROOT):
 names=set(safe_json(Path(root)/'runs/sk11-job-recovery-126-imports.json')['modules'])|{'src/sbs/operations/warehouse_start_152.py','runs/sk00-autonomy-053.json','runs/sk11-warehouse-start-112.json','runs/sk11-warehouse-restart-122.json'}
 return {p:sha((Path(root)/p).read_bytes()) for p in sorted(names)}
class WarehouseStart152:
 def __init__(self,root,state,review,*,profile=None,config_factory=None,session=None,sleep=time.sleep):
  self.root=Path(root).resolve();self.state=Path(state).resolve();self.review=review;self.sleep=sleep
  require(review.get('files')==inputs(self.root),'WAREHOUSE_REVIEW_INPUTS');self.authorize()
  if config_factory:cfg=config_factory()
  else:
   from databricks.sdk.core import Config
   cfg=Config(profile=profile) if profile else Config()
  require(cfg.host.rstrip('/')=='https://'+HOST,'WAREHOUSE_HOST');self.cfg=cfg
  import requests
  self.session=session or requests.Session();require(all(a.max_retries.total==0 for a in self.session.adapters.values()),'WAREHOUSE_RETRIES_FORBIDDEN')
 def authorize(self):
  r=self.review;now=int(time.time()*1000)
  require(r.get('approved') is True and r.get('scope')=='warehouse152_one_start' and r.get('limits')==LIMITS,'WAREHOUSE_REVIEW_REQUIRED')
  require(type(r.get('issued_at_ms')) is int and type(r.get('expires_at_ms')) is int and r['issued_at_ms']<=now<r['expires_at_ms'] and 0<r['expires_at_ms']-r['issued_at_ms']<=1800000,'WAREHOUSE_WINDOW_EXPIRED')
  for p,pin in r['files'].items():require(sha((self.root/p).read_bytes())==pin,'WAREHOUSE_INPUT_DRIFT')
 def call(self,method,path):
  require((method=='GET' and path in (ME,PATH)) or (method=='POST' and path==PATH+'/start' and (self.state/'start-intent.json').exists()),'WAREHOUSE_SCOPE')
  self.authorize();p=self.state/'budget.json';b=safe_json(p) if p.exists() else {'get':0,'start':0};require(set(b)==set(LIMITS) and all(type(b[k]) is int and 0<=b[k]<=LIMITS[k] for k in LIMITS),'WAREHOUSE_BUDGET_INVALID')
  b['get' if method=='GET' else 'start']+=1;require(all(b[k]<=LIMITS[k] for k in LIMITS),'WAREHOUSE_BUDGET_EXHAUSTED');atomic(p,b)
  n=sum(b.values());auth=self.cfg.authenticate();self.authorize()
  try:r=self.session.request(method,'https://'+HOST+path,headers=auth,timeout=(10,60),allow_redirects=False,stream=True)
  except Exception:raise ValueError('WAREHOUSE_TRANSPORT_UNKNOWN') from None
  try:
   _write_new(self.state/('http-%02d-status.json'%n),{'method':method,'path':path,'status':r.status_code,'request_ids':{k:bounded_text(r.headers.get(k),256) for k in ('x-request-id','x-databricks-request-id') if r.headers.get(k)}})
   raw=r.raw.read(1048577,decode_content=True);require(len(raw)<=1048576,'WAREHOUSE_RESPONSE_CAP')
   try:body=json.loads(raw) if raw else {}
   except Exception:raise ValueError('WAREHOUSE_RESPONSE_INVALID') from None
   require(isinstance(body,dict),'WAREHOUSE_RESPONSE_INVALID')
   if not 200<=r.status_code<300:
    _write_new(self.state/('http-%02d-error.json'%n),{'status':r.status_code,'error_code':bounded_text(body.get('error_code'),100),'message':bounded_text(body.get('message'),1000)})
    raise ValueError('WAREHOUSE_HTTP_REJECTED')
   self.authorize();return body
  finally:r.close()
 def observe(self):
  value=self.call('GET',PATH);require(value.get('id')==WAREHOUSE and value.get('state') in ('STOPPED','STOPPING','STARTING','RUNNING','DELETING','DELETED'),'WAREHOUSE_IDENTITY_OR_STATE')
  n=safe_json(self.state/'budget.json')['get'];_write_new(self.state/('warehouse-%02d.json'%n),value);return value
 def run(self):
  me=self.call('GET',ME);require(me.get('id')==OWNER_ID and me.get('userName')==OWNER and me.get('active') is True,'WAREHOUSE_OWNER_IDENTITY')
  current=self.observe();ip=self.state/'start-intent.json';outcome='not_attempted'
  if current['state']=='STOPPED' and not ip.exists():
   _write_new(ip,{'warehouse_id':WAREHOUSE,'observed_state':'STOPPED','operation':'start_once','authorization':'053','size_change':False})
   try:self.call('POST',PATH+'/start');outcome='response_received'
   except Exception as exc:outcome=str(exc) if re.fullmatch('[A-Z0-9_]+',str(exc)) else 'UNKNOWN'
  elif ip.exists():outcome='prior_intent_no_resend'
  while current['state'] in ('STOPPED','STOPPING','STARTING') and safe_json(self.state/'budget.json')['get']<LIMITS['get']:
   if current['state']=='STOPPED' and outcome in ('not_attempted','prior_intent_no_resend'):break
   self.sleep(3);current=self.observe()
  result={'status':'running_observed' if current['state']=='RUNNING' else 'not_running_observed','warehouse':current,'start_outcome':outcome,'budget':safe_json(self.state/'budget.json'),'job_run':False,'size_change':False,'cost':None}
  atomic(self.state/'result.json',result);return result

def main():
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');p.add_argument('--review-file',type=Path);p.add_argument('--profile');a=p.parse_args()
 if not a.execute:print(json.dumps({'status':'preflight_only','limits':LIMITS,'files':inputs(),'cloud_executed':False}));return
 require(a.review_file is not None,'REVIEW_REQUIRED');state=ROOT/'deployment/state/warehouse-start152';state.mkdir(parents=True,exist_ok=True)
 with exclusive_lock(state):
  runner=WarehouseStart152(ROOT,state,safe_json(a.review_file),profile=a.profile)
  try:print(json.dumps(runner.run()))
  finally:runner.session.close()
if __name__=='__main__':main()
