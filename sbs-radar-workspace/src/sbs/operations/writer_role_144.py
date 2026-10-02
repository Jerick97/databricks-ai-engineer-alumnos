"""144: one etag-conditional ruleset replacement preserving all existing grants."""
from pathlib import Path
import json,time,re,copy
from .job_recovery_126 import ROOT,HOST,OWNER,OWNER_ID,PRINCIPAL,RULE_PATH,RULE_NAME,bounded_text,safe_json,sha,require,atomic,_write_new,exclusive_lock,obj
LIMITS={'http':12,'rule_put':1}
ROLE='roles/servicePrincipal.user'

def separate(root,state):
 state=Path(state).resolve()
 for name in ('provision106','job-recovery126','writer-role140'):
  old=(Path(root)/'deployment/state'/name).resolve()
  require(state!=old and old not in state.parents and state not in old.parents,'HISTORICAL_JOURNAL_OVERLAP')

def review_inputs(root=ROOT):
 root=Path(root)
 closure=safe_json(root/'runs/sk11-job-recovery-126-imports.json')['modules']
 names=set(closure)|{'src/sbs/operations/writer_role_144.py','src/sbs/operations/job_recovery_126.py','runs/sk08-sk11-role-144-invocation.json','deployment/state/writer-role140/http-004-error.json','deployment/state/job-recovery126/http-005-error.json','deployment/state/job-recovery126/current-ruleset.json','deployment/writer-assignment-proposal-017.json'}
 return {p:sha((root/p).read_bytes()) for p in sorted(names)}

def checked(r):
 require(isinstance(r,dict) and set(r)<= {'name','etag','grant_rules'} and r.get('name')==RULE_NAME and isinstance(r.get('etag'),str) and bool(r['etag']) and isinstance(r.get('grant_rules'),list),'RULESET_INVALID')
 for g in r['grant_rules']:
  require(isinstance(g,dict) and set(g)=={'role','principals'} and isinstance(g['role'],str) and isinstance(g['principals'],list) and all(isinstance(v,str) for v in g['principals']),'GRANT_INVALID')
 return r

def has_role(r):return any(g['role']==ROLE and 'users/'+OWNER in g['principals'] for g in checked(r)['grant_rules'])
def proposal(r):
 r=checked(r);grants=copy.deepcopy(r['grant_rules'])
 if not has_role(r):grants.append({'role':ROLE,'principals':['users/'+OWNER]})
 return {'name':RULE_NAME,'rule_set':{'name':RULE_NAME,'etag':r['etag'],'grant_rules':grants}}
def pairs(r):return {(g['role'],p) for g in checked(r)['grant_rules'] for p in g['principals']}

class RoleApi:
 def __init__(self,cfg,*,state,authorize,payload,session=None):
  from urllib.parse import urlsplit
  import requests
  u=urlsplit(cfg.host);require(u.scheme=='https' and u.hostname==HOST and u.port is None and u.path in ('','/') and not any((u.username,u.password,u.query,u.fragment)),'WORKSPACE_HOST_INVALID')
  self._cfg=cfg;self.state=Path(state);self.authorize=authorize;self.payload=payload;self.post_receipt=None
  self.session=session or requests.Session();require(all(a.max_retries.total==0 for a in self.session.adapters.values()),'RETRIES_FORBIDDEN')
 def do(self,method,path=None,*,query=None,body=None,headers=None,**extra):
  require(not extra,'API_EXTRA_FIELDS_FORBIDDEN')
  reads={'/api/2.0/preview/scim/v2/Me','/api/2.0/preview/scim/v2/ServicePrincipals/72803555975940',RULE_PATH}
  is_post=method=='PUT' and path==RULE_PATH
  require(is_post or method=='GET' and path in reads,'API_SCOPE_INVALID')
  if is_post:require(body==self.payload and (self.state/'rule-intent.json').is_file(),'CREATE_PAYLOAD_OR_INTENT_INVALID')
  if method=='GET' and path==RULE_PATH:require(query=={'name':RULE_NAME,'etag':''},'RULE_QUERY_INVALID')
  self.authorize();bp=self.state/'budget.json';budget=safe_json(bp) if bp.exists() else {'http':0,'rule_put':0}
  require(set(budget)==set(LIMITS) and all(type(budget[k]) is int and 0<=budget[k]<=LIMITS[k] for k in LIMITS),'BUDGET_INVALID')
  budget['http']+=1;budget['rule_put']+=int(is_post);require(all(budget[k]<=LIMITS[k] for k in LIMITS),'RECOVERY_BUDGET_EXCEEDED');atomic(bp,budget)
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

class WriterRole144:
 def __init__(self,root,state,review,*,profile=None,config_factory=None,session=None):
  separate(root,state)
  import importlib.metadata
  from databricks.sdk.service.iam import AccountAccessControlProxyAPI
  require(importlib.metadata.version('databricks-sdk')=='0.102.0','SDK_VERSION_MISMATCH')
  self.root=Path(root).resolve();self.state=Path(state).resolve();self.review=review
  require(review.get('files')==review_inputs(root),'REVIEW_INPUTS_REQUIRED');self.authorize()
  if config_factory:cfg=config_factory()
  else:
   from databricks.sdk.core import Config
   cfg=Config(profile=profile) if profile else Config()
  self.api=RoleApi(cfg,state=self.state,authorize=self.authorize,payload=None,session=session);self.rules=AccountAccessControlProxyAPI(self.api)
 def authorize(self):
  r=self.review;now=int(time.time()*1000)
  require(r.get('approved') is True and r.get('scope')=='writer_role144_user_only' and r.get('limits')==LIMITS,'ROLE_REVIEW_REQUIRED')
  require(type(r.get('issued_at_ms')) is int and type(r.get('expires_at_ms')) is int and r['issued_at_ms']<=now<r['expires_at_ms'] and 0<r['expires_at_ms']-r['issued_at_ms']<=1800000,'ROLE_REVIEW_EXPIRED')
  for p,pin in r['files'].items():require(sha((self.root/p).read_bytes())==pin,'ROLE_INPUT_DRIFT')
 def get(self):return checked(self.api.do('GET',RULE_PATH,query={'name':RULE_NAME,'etag':''}))
 def run(self):
  from databricks.sdk.service.iam import RuleSetUpdateRequest
  me=self.api.do('GET','/api/2.0/preview/scim/v2/Me');require(me.get('id')==OWNER_ID and me.get('userName')==OWNER and me.get('active') is True,'OPERATOR_IDENTITY_INVALID')
  sp=self.api.do('GET','/api/2.0/preview/scim/v2/ServicePrincipals/72803555975940');require(sp.get('id')=='72803555975940' and sp.get('applicationId')==PRINCIPAL and sp.get('active') is True,'WRITER_IDENTITY_INVALID')
  before=self.get();ip=self.state/'rule-intent.json'
  if ip.exists():
   intent=safe_json(ip);require(intent['payload']==proposal(intent['before']),'INTENT_DRIFT');expected=intent['payload']['rule_set']['grant_rules']
  elif has_role(before):expected=before['grant_rules']
  else:
   payload=proposal(before);expected=payload['rule_set']['grant_rules'];_write_new(ip,{'before':before,'payload':payload,'status':'single_put_intent'})
   self.api.payload=payload
   try:self.rules.update_rule_set(RULE_NAME,RuleSetUpdateRequest.from_dict(payload['rule_set']))
   except Exception as exc:
    code=str(exc);atomic(self.state/'put-outcome.json',{'status':code if re.fullmatch('[A-Z0-9_]{1,100}',code) else 'UNKNOWN','no_resend':True})
  after=self.get()
  require(has_role(after),'ROLE_RECONCILE_REQUIRED_NO_RESEND')
  expect={'name':RULE_NAME,'etag':after['etag'],'grant_rules':expected}
  require(pairs(after)==pairs(expect),'RULESET_GRANTS_DRIFT')
  result={'status':'owner_writer_user_role_observed','ruleset':after,'before':before,'budget':safe_json(self.state/'budget.json'),'job_created':False,'job_run':False,'cloud_acceptance':False,'cost':None}
  atomic(self.state/'result.json',result);return result

def main():
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--execute',action='store_true');p.add_argument('--review-file',type=Path);p.add_argument('--journal',type=Path);p.add_argument('--profile');a=p.parse_args()
 if not a.execute:print(json.dumps({'status':'offline_role144_ready','limits':LIMITS,'review_inputs':review_inputs(a.root),'cloud_executed':False}));return
 require(a.review_file is not None and a.journal is not None,'REVIEW_AND_JOURNAL_REQUIRED');separate(a.root,a.journal);a.journal.mkdir(parents=True,exist_ok=True)
 with exclusive_lock(a.journal):
  runner=WriterRole144(a.root,a.journal,safe_json(a.review_file),profile=a.profile)
  try:print(json.dumps(runner.run()))
  finally:runner.api.session.close()
if __name__=='__main__':main()
