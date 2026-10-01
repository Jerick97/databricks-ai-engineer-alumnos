"""One separately admitted metadata create after original118 unknown outcome.

No automatic resend, original journal mutation, role grant, Job run, SQL, start,
unpause or expired config upload. Capture HTTP receipt before SDK interpretation.
"""
from pathlib import Path
from types import SimpleNamespace
import json,time,re
from .cloud_dispatch import require,canonical,digest,obj
from .provision_106 import HOST,OWNER,OWNER_ID,PRINCIPAL,safe_json,sha
from .provision_118 import private_settings
from .provision_105 import _write_new
from . import atomic,exclusive_lock
ROOT=Path(__file__).resolve().parents[3]
LIMITS={'http':24,'create_post':1}
RULE_PATH='/api/2.0/preview/accounts/access-control/rule-sets'
RULE_NAME='accounts/d07dc225-12fb-4805-91a2-735f02373714/servicePrincipals/'+PRINCIPAL+'/ruleSets/default'

def original(root=ROOT):
 root=Path(root);files=list((root/'deployment/state/provision106/job').glob('*.intent.json'))
 require(len(files)==1,'ONE_ORIGINAL_INTENT_REQUIRED')
 path=files[0];record=safe_json(path);require(record.get('step_sha256')==digest(record.get('step')) and record['step'].get('step_id')=='create_job','ORIGINAL_INTENT_INVALID')
 payload=record['step']['payload'];require(payload.get('name')=='sbs-radar-single-writer' and payload.get('run_as')=={'service_principal_name':PRINCIPAL} and payload.get('schedule',{}).get('pause_status')=='PAUSED','ORIGINAL_SCOPE_INVALID')
 return path,record,payload

def create_kwargs(payload):
 from databricks.sdk.service.jobs import JobSettings,JobAccessControlRequest
 settings={k:v for k,v in payload.items() if k!='access_control_list'}
 parsed=JobSettings.from_dict(settings);kwargs={k:getattr(parsed,k) for k in settings}
 kwargs['access_control_list']=[JobAccessControlRequest.from_dict(v) for v in payload['access_control_list']]
 return kwargs

def serialize_create(root=ROOT):
 from databricks.sdk.service.jobs import JobsAPI
 payload=original(root)[2];captured={}
 class Capture:
  _cfg=SimpleNamespace(workspace_id=None)
  def do(self,method,path,**kwargs):captured.update(method=method,path=path,body=kwargs['body']);return {}
 JobsAPI(Capture()).create(**create_kwargs(payload))
 require(captured=={'method':'POST','path':'/api/2.2/jobs/create','body':payload},'SDK_SERIALIZATION_DRIFT')
 return payload,captured

def policy_settings_unchanged(root=ROOT):
 payload=original(root)[2];task=payload['tasks'][0]['notebook_task'];params=task['base_parameters']
 values=dict(notebook_path=task['notebook_path'],release_id=next(x['default'] for x in payload['parameters'] if x['name']=='release_id'),snapshot_backend_id=params['snapshot_backend_id'])
 a=private_settings(**values,boundary_policy_id='a'*64);b=private_settings(**values,boundary_policy_id='b'*64)
 require(a==b=={k:v for k,v in payload.items() if k!='access_control_list'},'POLICY_SETTINGS_DEPENDENCY_CHANGED')
 return {'settings_identical':True,'settings_sha256':digest(a),'scope':'distinct synthetic policy hashes prove builder independence; not a new policy or authorization','old_policy_preserved':True}

def review_inputs(root=ROOT):
 root=Path(root);path=original(root)[0]
 names=['src/sbs/operations/job_recovery_126.py','src/sbs/operations/provision_106.py','src/sbs/operations/provision_118.py','src/sbs/operations/provision_105.py','src/sbs/operations/provision_114.py','src/sbs/operations/cloud_dispatch.py','src/sbs/operations/__init__.py','runs/sk11-job-recovery-126-imports.json',str(path.relative_to(root)),'runs/sk11-job-reconcile-124.json','runs/sk11-job-recovery-126-offline-diagnostic.json','runs/sk12-writer-assignment-017-rules-observation.json']
 closure=safe_json(root/'runs/sk11-job-recovery-126-imports.json')['modules']
 require(isinstance(closure,dict) and all(p.startswith('src/sbs/') and p.endswith('.py') and '..' not in Path(p).parts for p in closure),'IMPORT_CLOSURE_INVALID')
 return {p:sha((root/p).read_bytes()) for p in sorted(set(names)|set(closure))}

def bounded_text(value,limit):
 text=value if isinstance(value,str) else ''
 text=re.sub(r'(?i)bearer\s+\S+','Bearer [REDACTED]',text)
 text=re.sub(r'(?i)(access_token|refresh_token|client_secret|password)\s*[:=]\s*\S+',r'\1=[REDACTED]',text)
 return ''.join(c if ord(c)>=32 else ' ' for c in text)[:limit]

class RecoveryApi:
 def __init__(self,cfg,*,state,authorize,payload,session=None):
  from urllib.parse import urlsplit
  import requests
  u=urlsplit(cfg.host);require(u.scheme=='https' and u.hostname==HOST and u.port is None and u.path in ('','/') and not any((u.username,u.password,u.query,u.fragment)),'WORKSPACE_HOST_INVALID')
  self._cfg=cfg;self.state=Path(state);self.authorize=authorize;self.payload=payload;self.post_receipt=None
  self.session=session or requests.Session();require(all(a.max_retries.total==0 for a in self.session.adapters.values()),'RETRIES_FORBIDDEN')
 def do(self,method,path=None,*,query=None,body=None,headers=None,**extra):
  require(not extra,'API_EXTRA_FIELDS_FORBIDDEN')
  reads={'/api/2.0/preview/scim/v2/Me','/api/2.0/preview/scim/v2/ServicePrincipals/72803555975940','/api/2.2/jobs/list','/api/2.2/jobs/get',RULE_PATH}
  is_post=method=='POST' and path=='/api/2.2/jobs/create'
  require(is_post or method=='GET' and (path in reads or re.fullmatch('/api/2.0/permissions/jobs/[0-9]+',path or '')),'API_SCOPE_INVALID')
  if is_post:require(body==self.payload and (self.state/'create-intent.json').is_file(),'CREATE_PAYLOAD_OR_INTENT_INVALID')
  self.authorize();bp=self.state/'budget.json';budget=safe_json(bp) if bp.exists() else {'http':0,'create_post':0}
  require(set(budget)==set(LIMITS) and all(type(budget[k]) is int and 0<=budget[k]<=LIMITS[k] for k in LIMITS),'BUDGET_INVALID')
  budget['http']+=1;budget['create_post']+=int(is_post);require(all(budget[k]<=LIMITS[k] for k in LIMITS),'RECOVERY_BUDGET_EXCEEDED');atomic(bp,budget)
  n=budget['http'];prefix=self.state/('http-%03d'%n)
  try:auth=self._cfg.authenticate();self.authorize()
  except Exception:
   _write_new(Path(str(prefix)+'-local-failure.json'),{'phase':'authenticate_or_admission','request_method_not_invoked':True,'method':method,'path':path})
   raise ValueError('RECOVERY_AUTH_OR_ADMISSION_FAILED') from None
  try:r=self.session.request(method,'https://'+HOST+path,params=query,json=body,headers={**(headers or {}),**auth},timeout=(10,60),allow_redirects=False,stream=True)
  except Exception:
   _write_new(Path(str(prefix)+'-transport-failure.json'),{'phase':'session_request','method':method,'path':path,'outcome':'unknown'})
   raise ValueError('RECOVERY_TRANSPORT_UNKNOWN') from None
  receipt=Path(str(prefix)+'-response.json')
  # Persist status/request IDs before body/JSON/SDK interpretation.
  observed={'method':method,'path':path,'http_status':r.status_code,'request_ids':{k:bounded_text(r.headers.get(k),256) for k in ('x-databricks-request-id','x-request-id') if r.headers.get(k)},'sdk_interpretation_not_yet_performed':True}
  try:
   _write_new(receipt,observed)
   if is_post:self.post_receipt=str(receipt.name)
   content=r.raw.read(1048577,decode_content=True);require(len(content)<=1048576,'RESPONSE_TOO_LARGE')
   _write_new(Path(str(prefix)+'-body-evidence.json'),{'bytes':len(content),'sha256':sha(content),'raw_body_not_persisted':True})
   try:data=json.loads(content) if content else {}
   except Exception:raise ValueError('RECOVERY_JSON_INVALID') from None
   require(isinstance(data,dict),'RECOVERY_JSON_OBJECT_REQUIRED')
   if not 200<=r.status_code<300:
    _write_new(Path(str(prefix)+'-error.json'),{'http_status':r.status_code,'error_code':bounded_text(data.get('error_code'),100),'message':bounded_text(data.get('message'),1000),'request_ids':observed['request_ids']})
    raise ValueError('RECOVERY_HTTP_REJECTED')
   return data
  finally:r.close()

class JobRecovery126:
 def __init__(self,root,state,review,*,profile=None,config_factory=None,session=None):
  from databricks.sdk.service.jobs import JobsAPI
  import importlib.metadata
  require(importlib.metadata.version('databricks-sdk')=='0.102.0','SDK_VERSION_MISMATCH')
  self.root=Path(root).resolve();self.state=Path(state).resolve();self.review=review
  require(review.get('files')==review_inputs(self.root),'REVIEW_INPUTS_REQUIRED')
  self.old_path,self.old,self.payload=original(self.root);serialize_create(self.root);self.authorize()
  if config_factory:cfg=config_factory()
  else:
   from databricks.sdk.core import Config
   cfg=Config(profile=profile) if profile else Config()
  self.api=RecoveryApi(cfg,state=self.state,authorize=self.authorize,payload=self.payload,session=session);self.jobs=JobsAPI(self.api)
 def authorize(self):
  r=self.review;now=int(time.time()*1000)
  require(r.get('approved') is True and r.get('scope')=='job_recovery126_one_new_create' and r.get('limits')==LIMITS,'RECOVERY_REVIEW_REQUIRED')
  require(type(r.get('issued_at_ms')) is int and type(r.get('expires_at_ms')) is int and r['issued_at_ms']<=now<r['expires_at_ms'] and 0<r['expires_at_ms']-r['issued_at_ms']<=1800000,'RECOVERY_WINDOW_INVALID')
  for p,pin in r['files'].items():require(sha((self.root/p).read_bytes())==pin,'RECOVERY_INPUT_DRIFT')
 def identity_and_rules(self):
  user=self.api.do('GET','/api/2.0/preview/scim/v2/Me');require(user.get('id')==OWNER_ID and user.get('userName')==OWNER and user.get('active') is True,'OPERATOR_IDENTITY_INVALID')
  sp=self.api.do('GET','/api/2.0/preview/scim/v2/ServicePrincipals/72803555975940');require(sp.get('id')=='72803555975940' and sp.get('applicationId')==PRINCIPAL and sp.get('active') is True,'WRITER_IDENTITY_INVALID')
  rules=self.api.do('GET',RULE_PATH,query={'name':RULE_NAME,'etag':''});require(rules.get('name')==RULE_NAME and isinstance(rules.get('grant_rules'),list),'RULESET_IDENTITY_INVALID')
  user_role=any(r.get('role')=='roles/servicePrincipal.user' and 'users/'+OWNER in r.get('principals',[]) for r in rules['grant_rules'])
  # Direct rules do not enumerate all inherited roles; no causal inference.
  record={'ruleset':rules,'direct_user_role_observed':user_role,'inherited_run_as_permission':'not_established_here','enforcement':'Jobs create API remains authoritative; this does not grant any role'}
  atomic(self.state/'current-ruleset.json',record);return record
 def reconcile(self):
  listing=self.api.do('GET','/api/2.2/jobs/list',query={'name':'sbs-radar-single-writer','limit':25,'expand_tasks':True})
  require(not listing.get('has_more') and not listing.get('next_page_token'),'INCOMPLETE_JOB_LIST')
  candidates=listing.get('jobs',[]);require(isinstance(candidates,list),'JOBS_LIST_INVALID')
  ids=[v.get('job_id') for v in candidates];require(all(type(i) is int and i>0 for i in ids),'CANDIDATE_JOB_ID_INVALID')
  if len(ids)>1:return {'status':'duplicates_observed_no_run','candidate_ids':ids,'listing':listing}
  if not ids:return {'status':'no_job_observed','listing':listing}
  job=obj(self.jobs.get(ids[0]));require(job.get('job_id')==ids[0] and job.get('run_as_user_name')==PRINCIPAL and not job.get('next_page_token'),'JOB_IDENTITY_MISMATCH')
  expected={k:v for k,v in self.payload.items() if k!='access_control_list'};actual=job.get('settings',{})
  require(all(actual.get(k)==v for k,v in expected.items()) and not any(actual.get(k) for k in ('continuous','trigger','git_source','job_clusters')),'RECOVERED_JOB_SETTINGS_MISMATCH')
  acl=obj(self.jobs.get_permissions(str(ids[0])));require(acl.get('object_id')=='/jobs/'+str(ids[0]) and isinstance(acl.get('access_control_list'),list),'RECOVERED_ACL_INVALID')
  return {'status':'job_observed_paused','job_id':ids[0],'job':job,'acl':acl,'settings_sha256':digest(expected)}
 def run(self):
  self.identity_and_rules()
  before=self.reconcile()
  ip=self.state/'create-intent.json';outcome='not_attempted'
  if before['status']=='no_job_observed' and not ip.exists():
   _write_new(ip,{'original_intent_sha256':sha(self.old_path.read_bytes()),'original_step_sha256':self.old['step_sha256'],'payload_sha256':digest(self.payload),'payload':self.payload,'status':'separately_admitted_single_create_intent','original_attempt_outcome':'unknown'})
   try:
    response=obj(self.jobs.create(**create_kwargs(self.payload)));atomic(self.state/'create-response-candidate.json',{'candidate':response,'binding_requires_GET':True});outcome='response_received_binding_pending'
   except Exception as exc:
    code=str(exc);outcome=code if re.fullmatch('[A-Z0-9_]{1,100}',code) else 'RECOVERY_OUTCOME_UNKNOWN'
  elif ip.exists():outcome='prior_recovery_intent_readback_only'
  after=before if before['status']!='no_job_observed' else self.reconcile()
  receipts=[p.name for p in self.state.glob('http-*-response.json') if safe_json(p).get('method')=='POST']
  require(len(receipts)<=1,'MULTIPLE_RECOVERY_POST_RECEIPTS')
  result={'status':after['status'],'original_attempt_outcome':'unknown_preserved','original_intent_sha256':sha(self.old_path.read_bytes()),'recovery_attempt':outcome,'recovery_intent_sha256':sha(ip.read_bytes()) if ip.exists() else None,'post_http_receipt':self.api.post_receipt or (receipts[0] if receipts else None),'observation':after,'budget':safe_json(self.state/'budget.json'),'original_budget_not_modified':True,'accounting':'original106 budget remains unchanged; separate126 max1 create POST; eventual original12+recovery1=13 remote mutation attempts','config_upload':False,'policy130_required':True,'job_run':False,'cloud_acceptance':False,'cost':None}
  atomic(self.state/'reconciliation.json',result);return result

def preflight(root=ROOT):
 serialize_create(root)
 return {'status':'offline_recovery_ready','limits':LIMITS,'original_attempt':'unknown','old_intent_sha256':sha(original(root)[0].read_bytes()),'policy130':policy_settings_unchanged(root),'ruleset_read_path':RULE_PATH,'ruleset_name':RULE_NAME,'cloud_executed':False,'review_inputs':review_inputs(root),'cost':None}

def main():
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--execute',action='store_true');p.add_argument('--review-file',type=Path);p.add_argument('--journal',type=Path);p.add_argument('--profile');a=p.parse_args()
 if not a.execute:print(json.dumps(preflight(a.root)));return
 require(a.review_file is not None and a.journal is not None,'REVIEW_AND_SEPARATE_JOURNAL_REQUIRED')
 require(a.journal.resolve()!= (a.root/'deployment/state/provision106').resolve(),'ORIGINAL_JOURNAL_FORBIDDEN')
 a.journal.mkdir(parents=True,exist_ok=True)
 with exclusive_lock(a.journal):
  runner=JobRecovery126(a.root,a.journal,safe_json(a.review_file),profile=a.profile)
  try:print(json.dumps(runner.run()))
  finally:runner.api.session.close()
if __name__=='__main__':main()
