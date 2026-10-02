"""One diagnostic import + run of same Job; explicit raw readbacks, no data writes."""
from pathlib import Path
import base64,json,time
from .provision_106 import HOST,OWNER,OWNER_ID,safe_json,sha,normalize_source
from .job_recovery_126 import ROOT,bounded_text,original
from .cloud_dispatch import require,digest
from .job_defaults_146 import normalize_job
from .policy_binding_137 import trusted_job_acl,trusted_notebook_acl
from .provision_105 import _write_new
from . import atomic,exclusive_lock
JOB=989326861421503
NOTEBOOK='/Users/sociosdosmilveintiseis@gmail.com/sbs-radar-writer118-5af111bd1d790c6c'
NBID=3178573112927427
LIMITS={'get':16,'import':1,'run':1}
SOURCE='deployment/writer_diagnostic_158_notebook.py'
def inputs(root=ROOT):
 names=set(safe_json(Path(root)/'runs/sk11-dispatch-146-imports.json')['modules'])|{'src/sbs/operations/writer_diagnostic_158.py',SOURCE,'deployment/state/policy-binding146/driver-config146.json','deployment/state/writer-monitor156/output-472124888759957.json'}
 names.update(str(p.relative_to(root)) for p in (Path(root)/'deployment/state/policy-binding146/notebook146').glob('*.intent.json'))
 return {p:sha((Path(root)/p).read_bytes()) for p in sorted(names)}
class Diagnostic158:
 def __init__(self,root,state,review,*,profile=None,config_factory=None,session=None):
  self.root=Path(root).resolve();self.state=Path(state).resolve();self.review=review
  require(review.get('files')==inputs(self.root),'DIAGNOSTIC_INPUTS');self.authorize()
  from databricks.sdk.core import Config
  import requests
  self.cfg=config_factory() if config_factory else Config(profile=profile) if profile else Config();require(self.cfg.host.rstrip('/')=='https://'+HOST,'DIAGNOSTIC_HOST')
  self.session=session or requests.Session();require(all(a.max_retries.total==0 for a in self.session.adapters.values()),'DIAGNOSTIC_RETRIES')
  self.source=(self.root/SOURCE).read_bytes();self.source_pin=sha(normalize_source(self.source))
  prior=list((self.root/'deployment/state/policy-binding146/notebook146').glob('*.intent.json'));require(len(prior)==1,'BOUND_NOTEBOOK_REQUIRED')
  self.restore=safe_json(prior[0])['step']['payload'];self.old_pin=sha(normalize_source(base64.b64decode(self.restore['content'])))
  self.expected={k:v for k,v in original(self.root)[2].items() if k!='access_control_list'};token=digest({'job_id':JOB,'diagnostic':'158'})
  self.run_body={'job_id':JOB,'idempotency_token':token,'job_parameters':{'request_id':token,'release_id':next(x['default'] for x in self.expected['parameters'] if x['name']=='release_id')},'queue':{'enabled':True}}
 def authorize(self):
  r=self.review;now=int(time.time()*1000)
  require(r.get('approved') is True and r.get('scope')=='writer_diagnostic158_one_import_one_run' and r.get('limits')==LIMITS,'DIAGNOSTIC_REVIEW')
  require(type(r.get('issued_at_ms')) is int and type(r.get('expires_at_ms')) is int and r['issued_at_ms']<=now<r['expires_at_ms'] and 0<r['expires_at_ms']-r['issued_at_ms']<=1800000,'DIAGNOSTIC_WINDOW')
  for p,h in r['files'].items():require(sha((self.root/p).read_bytes())==h,'DIAGNOSTIC_DRIFT')
 def call(self,method,path,*,query=None,body=None):
  gets={'/api/2.0/preview/scim/v2/Me':None,'/api/2.2/jobs/get':{'job_id':JOB},'/api/2.0/permissions/jobs/'+str(JOB):None,'/api/2.0/workspace/get-status':{'path':NOTEBOOK},'/api/2.0/permissions/notebooks/'+str(NBID):None,'/api/2.0/workspace/export':{'path':NOTEBOOK,'format':'SOURCE'}}
  kind='get' if method=='GET' and path in gets and query==gets[path] and body is None else None
  if method=='POST' and path=='/api/2.0/workspace/import':
   expected={'path':NOTEBOOK,'format':'SOURCE','language':'PYTHON','overwrite':True,'content':base64.b64encode(self.source).decode()};require(body==expected and (self.state/'import-intent.json').exists(),'DIAGNOSTIC_IMPORT_SCOPE');kind='import'
  if method=='POST' and path=='/api/2.2/jobs/run-now':require(body==self.run_body and (self.state/'run-intent.json').exists(),'DIAGNOSTIC_RUN_SCOPE');kind='run'
  require(kind is not None,'DIAGNOSTIC_API_SCOPE');self.authorize();p=self.state/'budget.json';b=safe_json(p) if p.exists() else dict.fromkeys(LIMITS,0)
  require(set(b)==set(LIMITS) and all(type(b[k]) is int and 0<=b[k]<=LIMITS[k] for k in LIMITS),'DIAGNOSTIC_BUDGET_INVALID');b[kind]+=1;require(all(b[k]<=LIMITS[k] for k in LIMITS),'DIAGNOSTIC_BUDGET');atomic(p,b)
  auth=self.cfg.authenticate();self.authorize();n=sum(b.values())
  try:r=self.session.request(method,'https://'+HOST+path,params=query,json=body,headers=auth,timeout=(10,60),allow_redirects=False,stream=True)
  except Exception:raise ValueError('DIAGNOSTIC_TRANSPORT_UNKNOWN') from None
  try:
   _write_new(self.state/('http-%02d-status.json'%n),{'path':path,'method':method,'status':r.status_code,'request_id':bounded_text(r.headers.get('x-request-id'),256)})
   raw=r.raw.read(2097153,decode_content=True);require(len(raw)<=2097152,'DIAGNOSTIC_RESPONSE_CAP');value=json.loads(raw) if raw else {};require(isinstance(value,dict),'DIAGNOSTIC_RESPONSE_INVALID');_write_new(self.state/('http-%02d-response.json'%n),value);require(200<=r.status_code<300,'DIAGNOSTIC_HTTP_REJECTED');return value
  finally:r.close()
 def export(self):return normalize_source(base64.b64decode(self.call('GET','/api/2.0/workspace/export',query={'path':NOTEBOOK,'format':'SOURCE'})['content']))
 def run(self):
  me=self.call('GET','/api/2.0/preview/scim/v2/Me');require(me.get('id')==OWNER_ID and me.get('userName')==OWNER and me.get('active') is True,'DIAGNOSTIC_OWNER')
  job=self.call('GET','/api/2.2/jobs/get',query={'job_id':JOB});require(job.get('job_id')==JOB and job.get('run_as_user_name')==self.expected['run_as']['service_principal_name'],'DIAGNOSTIC_JOB_IDENTITY');normalize_job(job,self.expected)
  trusted_job_acl(self.call('GET','/api/2.0/permissions/jobs/'+str(JOB)),JOB)
  nb=self.call('GET','/api/2.0/workspace/get-status',query={'path':NOTEBOOK});require(nb.get('object_id')==NBID and nb.get('path')==NOTEBOOK,'DIAGNOSTIC_NOTEBOOK_IDENTITY')
  trusted_notebook_acl(self.call('GET','/api/2.0/permissions/notebooks/'+str(NBID)),NBID)
  observed=self.export();pin=sha(observed);require(pin in (self.old_pin,self.source_pin),'DIAGNOSTIC_NOTEBOOK_DRIFT')
  restore_path=self.state/'restore146-payload.json'
  if not restore_path.exists():_write_new(restore_path,self.restore)
  ip=self.state/'import-intent.json'
  if pin!=self.source_pin:
   require(not ip.exists(),'DIAGNOSTIC_IMPORT_UNKNOWN_NO_RESEND');payload={'path':NOTEBOOK,'format':'SOURCE','language':'PYTHON','overwrite':True,'content':base64.b64encode(self.source).decode()};_write_new(ip,payload)
   self.call('POST','/api/2.0/workspace/import',body=payload);require(sha(self.export())==self.source_pin,'DIAGNOSTIC_IMPORT_READBACK')
  rp=self.state/'run-intent.json';result={'status':'diagnostic_prior_intent_no_resend','job_id':JOB,'run_id_candidate':None}
  if not rp.exists():
   _write_new(rp,self.run_body);response=self.call('POST','/api/2.2/jobs/run-now',body=self.run_body);rid=response.get('run_id');require(type(rid) is int and rid>0,'DIAGNOSTIC_RUN_RESPONSE');result={'status':'diagnostic_submitted_requires_GET','job_id':JOB,'run_id_candidate':rid}
  result.update(budget=safe_json(self.state/'budget.json'),notebook_restore_required=True,pipeline_executed=False,cloud_acceptance=False,cost=None);atomic(self.state/'result.json',result);return result

def main():
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');p.add_argument('--review-file',type=Path);p.add_argument('--profile');a=p.parse_args()
 if not a.execute:print(json.dumps({'status':'diagnostic_only_preflight','limits':LIMITS,'files':inputs(),'cloud_executed':False}));return
 require(a.review_file is not None,'REVIEW_REQUIRED');state=ROOT/'deployment/state/writer-diagnostic158';state.mkdir(parents=True,exist_ok=True)
 with exclusive_lock(state):
  runner=Diagnostic158(ROOT,state,safe_json(a.review_file),profile=a.profile)
  try:print(json.dumps(runner.run()))
  finally:runner.session.close()
if __name__=='__main__':main()
