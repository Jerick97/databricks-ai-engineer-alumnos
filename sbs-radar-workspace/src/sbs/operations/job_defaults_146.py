"""Strict projection of five observed Jobs task defaults; preserve raw evidence.

Portable overlay, no changes to the sealed105 writer. Runtime fields remain raw
and existing CloudDispatcher execution-contract checks remain authoritative.
"""
import copy,json,hashlib
from pathlib import Path
from types import SimpleNamespace
DEFAULTS={'disabled':False,'email_notifications':{},'min_retry_interval_millis':0,'retry_on_timeout':False,'run_if':'ALL_SUCCESS'}
TOP_DEFAULTS={'format':'MULTI_TASK','email_notifications':{},'webhook_notifications':{}}
RUNTIME={'attempt_number','cleanup_duration','cluster_instance','end_time','execution_duration','queue_duration','resolved_values','run_duration','run_id','run_page_url','setup_duration','start_time','state','status'}
def require(v,code):
 if not v:raise ValueError(code)
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False)
def pin(v):return hashlib.sha256(canonical(v).encode()).hexdigest()
def equal(a,b):return canonical(a)==canonical(b)
def task_projection(task,expected,*,runtime=False):
 require(isinstance(task,dict) and isinstance(expected,dict),'TASK_OBJECT_REQUIRED')
 out=copy.deepcopy(task)
 for k,v in expected.items():require(k in out and equal(out[k],v),'REQUIRED_TASK_FIELD_CHANGED')
 for k in set(out)-set(expected):
  if k in DEFAULTS:
   require(equal(out[k],DEFAULTS[k]),'TASK_DEFAULT_VALUE_CHANGED');del out[k]
  else:require(runtime and k in RUNTIME,'UNSUPPORTED_TASK_FIELD')
 return out

def normalize_job(raw,expected):
 require(isinstance(raw,dict) and isinstance(raw.get('settings'),dict),'JOB_OBJECT_REQUIRED')
 out=copy.deepcopy(raw);settings=out['settings']
 require(isinstance(settings.get('tasks'),list) and len(settings['tasks'])==len(expected['tasks'])==1,'SINGLE_TASK_REQUIRED')
 settings['tasks']=[task_projection(settings['tasks'][0],expected['tasks'][0])]
 for k,v in expected.items():require(k in settings and equal(settings[k],v),'REQUIRED_SETTING_CHANGED')
 for k in set(settings)-set(expected):require(k in TOP_DEFAULTS and equal(settings[k],TOP_DEFAULTS[k]),'UNSUPPORTED_SETTING')
 return out

def normalize_run(raw,expected):
 require(isinstance(raw,dict) and isinstance(raw.get('tasks'),list) and len(raw['tasks'])==1,'SINGLE_RUN_TASK_REQUIRED')
 out=copy.deepcopy(raw);out['tasks']=[task_projection(raw['tasks'][0],expected['tasks'][0],runtime=True)];return out

class DefaultsApi146:
 def __init__(self,base,expected,job_id,evidence):
  require(callable(evidence),'RAW_EVIDENCE_SINK_REQUIRED');self.base=base;self._cfg=base._cfg;self.expected=copy.deepcopy(expected);self.job_id=job_id;self.evidence=evidence
 def do(self,method,path=None,**kwargs):
  raw=self.base.do(method,path,**kwargs)
  if method=='GET' and path in ('/api/2.2/jobs/get','/api/2.2/jobs/runs/get'):
   require(raw.get('job_id')==self.job_id,'OVERLAY_JOB_SCOPE')
   record={'version':'job-defaults146','path':path,'raw':copy.deepcopy(raw),'raw_sha256':pin(raw)}
   # Raw survives validation failure as well as successful projection.
   try:out=normalize_job(raw,self.expected) if path.endswith('/jobs/get') else normalize_run(raw,self.expected)
   except Exception:
    self.evidence({**record,'status':'rejected_projection'});raise
   self.evidence({**record,'status':'projected','projection_sha256':pin(out),'removed_defaults':list(DEFAULTS)})
   return out
  return raw

def bind_services146(services,writer,evidence):
 from databricks.sdk.service.jobs import JobsAPI
 from sbs.operations.cloud_dispatch import job_settings
 out=SimpleNamespace(**vars(services));out.jobs=JobsAPI(DefaultsApi146(services.jobs._api,job_settings(writer),writer.job_id,evidence));return out

def execute_from_config146(config,project_root,*,job_id,run_id,release_id,profile=None):
 """Explicit105 execution helper; only Jobs response adapter differs."""
 from databricks.sdk.core import Config
 from sbs.operations import load_sealed_plan
 from sbs.operations.cloud_driver import sdk_services,bind_driver
 from dataclasses import replace
 require(type(job_id) is int and job_id==config.writer.job_id and type(run_id) is int and run_id>0 and release_id==config.writer.release_id,'JOB_CONTEXT_MISMATCH')
 root=Path(project_root).resolve();plan=load_sealed_plan(root)
 pairs_config=json.loads((root/'config/genie-pilot-002.json').read_bytes());pairs={v['pair']['pair_id']:v['pair'] for v in pairs_config['contexts']};plan=replace(plan,pairs=tuple(pairs.values()))
 cfg=Config(profile=profile) if profile else Config();base=sdk_services(cfg)
 services=bind_services146(base,config.writer,lambda record:print(json.dumps({'overlay146_metadata':record},sort_keys=True)))
 try:return bind_driver(config,services,evidence_mode='real').execute(root,plan,run_id=run_id)
 finally:base.api.session.close()
