"""Read-only monitor: dispatched receipt only; 20GET including identity/output."""
from pathlib import Path
import json,time
from .provision_106 import HOST,OWNER,OWNER_ID,safe_json,sha
from .job_recovery_126 import ROOT,bounded_text
from .cloud_dispatch import require
from .provision_105 import _write_new
from . import atomic,exclusive_lock
RECEIPT='deployment/state/writer-diagnostic158/result.json'
LIMITS={'get':20,'outputs_per_task':1}
ME='/api/2.0/preview/scim/v2/Me'
RUN='/api/2.2/jobs/runs/get'
OUTPUT='/api/2.2/jobs/runs/get-output'
TERMINAL={'TERMINATED','SKIPPED','INTERNAL_ERROR'}
def binding(root=ROOT):
 r=safe_json(Path(root)/RECEIPT)
 require(r.get('status')=='diagnostic_submitted_requires_GET' and type(r.get('run_id_candidate')) is int and r['run_id_candidate']>0,'DIAGNOSTIC_CANDIDATE_REQUIRED')
 job=safe_json(Path(root)/'runs/sk11-job-settings-146.json')['job_id'];require(r.get('job_id')==job,'RECEIPT_JOB_MISMATCH')
 return {'job_id':job,'run_id':r['run_id_candidate'],'receipt_sha256':sha((Path(root)/RECEIPT).read_bytes()),'binding_requires_GET':True}
def inputs(root=ROOT):
 names=set(safe_json(Path(root)/'runs/sk11-job-recovery-126-imports.json')['modules'])|{'src/sbs/operations/diagnostic_monitor_162.py','runs/sk11-job-settings-146.json',RECEIPT}
 return {p:sha((Path(root)/p).read_bytes()) for p in sorted(names)}
def output_validation(raw):
 value=raw.get('notebook_output',{});text=value.get('result')
 if value.get('truncated') or raw.get('logs_truncated'):return {'status':'truncated_not_validated','output_validated':False}
 if not isinstance(text,str) or len(text.encode())>1500000:return {'status':'diagnostic_result_absent_or_oversize','output_validated':False}
 try:report=json.loads(text)
 except Exception:return {'status':'not_json_not_validated','output_validated':False}
 if not isinstance(report,dict) or report.get('version')!='diagnostic158':return {'status':'diagnostic_contract_invalid','output_validated':False}
 rows=report.get('observations');require(isinstance(rows,list) and len(rows)<=5 and report.get('mutations')==0 and report.get('sql')==0 and report.get('model_calls')==0 and report.get('pipeline_executed') is False,'DIAGNOSTIC_OUTPUT_SCOPE_INVALID')
 expected=[('Me','/api/2.0/preview/scim/v2/Me'),('job','/api/2.2/jobs/get'),('job_acl','/api/2.0/permissions/jobs/989326861421503'),('table','/api/2.1/unity-catalog/tables/neptuno_manuel_arguelles.sbs_radar.refresh_control'),('warehouse','/api/2.0/sql/warehouses/828756322bedff37')]
 require([(x.get('stage'),x.get('path')) for x in rows]==expected[:len(rows)],'DIAGNOSTIC_OUTPUT_TARGETS_INVALID')
 return {'status':'diagnostic_report_observed','diagnostic_report':report,'summary':[{'stage':x['stage'],'http_status':x.get('http_status'),'error_code':x.get('body',{}).get('error_code') if isinstance(x.get('body'),dict) else None,'local_error_type':x.get('local_error_type')} for x in rows],'all_five_responses_observed':len(rows)==5 and all(type(x.get('http_status')) is int for x in rows),'output_validated':False,'pipeline_acceptance':False,'root_cause_review_required':True}
class Monitor156:
 def __init__(self,root,state,review,*,profile=None,config_factory=None,session=None,sleep=time.sleep):
  self.root=Path(root).resolve();self.state=Path(state).resolve();self.review=review;self.sleep=sleep;self.binding=binding(root);self.allowed_output=None
  require(review.get('files')==inputs(root),'MONITOR_INPUT_PINS');self.authorize()
  if config_factory:cfg=config_factory()
  else:
   from databricks.sdk.core import Config
   cfg=Config(profile=profile) if profile else Config()
  require(cfg.host.rstrip('/')=='https://'+HOST,'MONITOR_HOST_INVALID');self.cfg=cfg
  import requests
  self.session=session or requests.Session();require(all(a.max_retries.total==0 for a in self.session.adapters.values()),'MONITOR_RETRIES_FORBIDDEN')
 def authorize(self):
  r=self.review;now=int(time.time()*1000)
  require(r.get('approved') is True and r.get('scope')=='diagnostic_monitor162_read_only' and r.get('limits')==LIMITS,'MONITOR_REVIEW_REQUIRED')
  require(type(r.get('issued_at_ms')) is int and type(r.get('expires_at_ms')) is int and r['issued_at_ms']<=now<r['expires_at_ms'] and 0<r['expires_at_ms']-r['issued_at_ms']<=1800000,'MONITOR_WINDOW_EXPIRED')
  for p,h in r['files'].items():require(sha((self.root/p).read_bytes())==h,'MONITOR_INPUT_DRIFT')
 def call(self,path,query=None):
  require((path==ME and query is None) or (path==RUN and query=={'run_id':self.binding['run_id'],'include_resolved_values':True}) or (path==OUTPUT and self.allowed_output is not None and query=={'run_id':self.allowed_output}),'MONITOR_SCOPE')
  self.authorize();p=self.state/'budget.json';b=safe_json(p) if p.exists() else {'get':0};require(set(b)=={'get'} and type(b['get']) is int and 0<=b['get']<20,'MONITOR_BUDGET_EXHAUSTED');b['get']+=1;atomic(p,b)
  auth=self.cfg.authenticate();self.authorize();r=self.session.request('GET','https://'+HOST+path,params={k:str(v).lower() if type(v) is bool else v for k,v in (query or {}).items()},headers=auth,timeout=(10,60),allow_redirects=False,stream=True)
  try:
   _write_new(self.state/('http-%02d-status.json'%b['get']),{'path':path,'status':r.status_code,'request_id':bounded_text(r.headers.get('x-request-id'),256)})
   raw=r.raw.read(2097153,decode_content=True);require(len(raw)<=2097152,'MONITOR_RESPONSE_CAP');value=json.loads(raw);require(isinstance(value,dict),'MONITOR_RESPONSE_INVALID')
   _write_new(self.state/('http-%02d-raw.json'%b['get']),value);require(200<=r.status_code<300,'MONITOR_HTTP_REJECTED');return value
  finally:r.close()
 def run(self):
  me=self.call(ME);require(me.get('id')==OWNER_ID and me.get('userName')==OWNER and me.get('active') is True,'MONITOR_OWNER_IDENTITY')
  run=None;output=None
  while safe_json(self.state/'budget.json')['get']<19:
   run=self.call(RUN,{'run_id':self.binding['run_id'],'include_resolved_values':True})
   require(run.get('job_id')==self.binding['job_id'] and run.get('run_id')==self.binding['run_id'] and not run.get('next_page_token'),'MONITOR_RUN_IDENTITY')
   self.binding['binding_requires_GET']=False
   state=run.get('state',{})
   if state.get('life_cycle_state') in TERMINAL:
    tasks=run.get('tasks');require(isinstance(tasks,list) and len(tasks)==1 and tasks[0].get('task_key')=='refresh','MONITOR_TASK_SCOPE')
    tid=tasks[0].get('run_id');require(type(tid) is int and tid>0,'MONITOR_TASK_RUN_ID');self.allowed_output=tid
    ip=self.state/('output-%d-intent.json'%tid);op=self.state/('output-%d.json'%tid)
    if op.exists():output=safe_json(op)
    elif not ip.exists():
     _write_new(ip,{'task_run_id':tid,'parent_run_id':self.binding['run_id'],'operation':'get_output_once'})
     output=self.call(OUTPUT,{'run_id':tid});_write_new(op,output)
    break
   self.sleep(3)
  check=output_validation(output) if output is not None else {'status':'output_not_observed','output_validated':False}
  if check.get('diagnostic_report'):
   report=check['diagnostic_report'];require(report.get('job_id')==self.binding['job_id'] and report.get('run_id')==self.binding['run_id'],'DIAGNOSTIC_RESULT_IDENTITY')
  result={'status':'diagnostic_observed_not_pipeline_accepted','binding':self.binding,'run_state':run.get('state') if run else None,'raw_run':run,'output_check':check,'budget':safe_json(self.state/'budget.json'),'success_accepted':False,'cloud_e2e':False,'cost':None}
  atomic(self.state/'result.json',result);return result

def main():
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');p.add_argument('--review-file',type=Path);p.add_argument('--profile');a=p.parse_args()
 if not a.execute:
  ready=(ROOT/RECEIPT).exists();print(json.dumps({'status':'ready_for_review' if ready else 'waiting_for_dispatch_receipt','limits':LIMITS,'files':inputs() if ready else None,'cloud_executed':False}));return
 require(a.review_file is not None,'MONITOR_REVIEW_REQUIRED');state=ROOT/'deployment/state/diagnostic-monitor162';state.mkdir(parents=True,exist_ok=True)
 with exclusive_lock(state):
  runner=Monitor156(ROOT,state,safe_json(a.review_file),profile=a.profile)
  try:print(json.dumps(runner.run()))
  finally:runner.session.close()
if __name__=='__main__':main()
