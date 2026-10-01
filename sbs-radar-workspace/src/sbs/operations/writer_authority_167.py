"""Portable167 typed writer authority, never a fabricated ACL/Jobs response."""
import ast,base64,copy,hashlib,json,time,re
from dataclasses import dataclass,asdict
from pathlib import Path
from types import SimpleNamespace
OWNER='sociosdosmilveintiseis@gmail.com'
OWNER_ID='76826984571984'
NOTEBOOK_ID=3178573112927427
MAX_TTL=300000
DATA_NAMES={'DELIVERY167','ATTESTATION167'}
MISSING_ATTESTED={'max_retries','timeout_seconds','disable_auto_optimization'}
TASK_DEFAULTS={'disabled':False,'email_notifications':{},'min_retry_interval_millis':0,'retry_on_timeout':False,'run_if':'ALL_SUCCESS'}
RUNTIME={'attempt_number','cleanup_duration','cluster_instance','end_time','execution_duration','queue_duration','resolved_values','run_duration','run_id','run_page_url','setup_duration','start_time','state','status','effective_performance_target'}
def require(value,code):
 if not value:raise ValueError(code)
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)
def digest(v):return hashlib.sha256(canonical(v).encode()).hexdigest()
def sha(v):return hashlib.sha256(v).hexdigest()
def same(a,b):return canonical(a)==canonical(b)
def obj(v):return v.as_dict() if hasattr(v,'as_dict') else v

def parse_source(raw):
 require(isinstance(raw,bytes) and len(raw)<=262144,'AUTHORITY_SOURCE_CAP')
 raw=raw.replace(b'\r\n',b'\n');text=raw.decode();tree=ast.parse(text);found={};ranges={}
 for node in ast.walk(tree):
  if isinstance(node,ast.Name) and node.id in DATA_NAMES and isinstance(node.ctx,(ast.Store,ast.Del)):
   matches=[n for n in tree.body if isinstance(n,ast.Assign) and len(n.targets)==1 and n.targets[0] is node]
   require(len(matches)==1 and node.id not in found,'AUTHORITY_DATA_ASSIGNMENT_INVALID');assignment=matches[0]
   try:found[node.id]=ast.literal_eval(assignment.value)
   except Exception:raise ValueError('AUTHORITY_NON_LITERAL') from None
   ranges[assignment.lineno]=(assignment.end_lineno,node.id)
 require(set(found)==DATA_NAMES,'AUTHORITY_BLOCKS_REQUIRED')
 lines=text.splitlines(keepends=True);out=[];i=1
 while i<=len(lines):
  if i in ranges:end,name=ranges[i];out.append(name+' = None\n');i=end+1
  else:out.append(lines[i-1]);i+=1
 return found,sha(''.join(out).encode())

def strict_settings(raw,expected):
 require(isinstance(raw,dict) and isinstance(raw.get('settings'),dict),'WRITER_JOB_OBJECT')
 settings=copy.deepcopy(raw['settings']);tasks=settings.get('tasks');require(isinstance(tasks,list) and len(tasks)==1,'WRITER_SINGLE_TASK')
 task=tasks[0];exp=expected['tasks'][0]
 for k,v in exp.items():require(k in task and same(task[k],v),'WRITER_TASK_SETTING_CHANGED')
 for k in set(task)-set(exp):require(k in TASK_DEFAULTS and same(task[k],TASK_DEFAULTS[k]),'WRITER_UNKNOWN_TASK_SETTING');del task[k]
 for k,v in expected.items():require(k in settings and same(settings[k],v),'WRITER_JOB_SETTING_CHANGED')
 for k in set(settings)-set(expected):require(k in {'format','email_notifications','webhook_notifications'} and same(settings[k],{'format':'MULTI_TASK','email_notifications':{},'webhook_notifications':{}}[k]),'WRITER_UNKNOWN_JOB_SETTING')
 return digest(expected)

def trusted_acls(job_acl,notebook_acl,job_id,principal):
 require(job_acl.get('object_id')=='/jobs/'+str(job_id) and notebook_acl.get('object_id')=='/notebooks/'+str(NOTEBOOK_ID),'AUTHORITY_ACL_IDENTITY')
 owner=False;writer=False
 for entry in job_acl.get('access_control_list',[]):
  levels={p.get('permission_level') for p in entry.get('all_permissions',[])}
  if entry.get('user_name')==OWNER:owner='IS_OWNER' in levels
  elif entry.get('service_principal_name')==principal:require(levels<={'CAN_VIEW','CAN_MANAGE_RUN'},'AUTHORITY_WRITER_MANAGE_FORBIDDEN');writer='CAN_MANAGE_RUN' in levels
  elif levels&{'CAN_MANAGE','CAN_MANAGE_RUN','IS_OWNER'}:require(entry.get('group_name')=='admins','AUTHORITY_UNTRUSTED_JOB_RUNNER')
 require(owner and writer,'AUTHORITY_JOB_OWNER_WRITER')
 nb_owner=False;nb_reader=False
 for entry in notebook_acl.get('access_control_list',[]):
  levels={p.get('permission_level') for p in entry.get('all_permissions',[])}
  if entry.get('user_name')==OWNER:nb_owner='CAN_MANAGE' in levels
  if levels&{'CAN_MANAGE','CAN_EDIT'}:require(entry.get('user_name')==OWNER or entry.get('group_name')=='admins','AUTHORITY_UNTRUSTED_NOTEBOOK_WRITER')
  if entry.get('service_principal_name')==principal:require(levels<={'CAN_READ','CAN_RUN'},'AUTHORITY_WRITER_NOTEBOOK_WRITE');nb_reader=bool(levels)
 require(nb_owner and nb_reader,'AUTHORITY_NOTEBOOK_OWNER_READER')

@dataclass(frozen=True)
class WriterAuthorityEvidence:
 kind:str
 run_id:int
 attestation_sha256:str
 acl_provenance:str
 observed_runtime_fields:tuple
 attested_only_fields:tuple
 widget_provenance:str
 historical_api_fields_missing:tuple
 expires_at_ms:int

class AttestedWriterVerifier167:
 def __init__(self,config,delivery,widgets,*,clock=None):
  self.config=config;self.delivery=copy.deepcopy(delivery);self.widgets=copy.deepcopy(widgets);self.clock=clock or (lambda:int(time.time()*1000));self.attestation=None;self.evidence=None;self.authority_reads=0
 def policy_live(self):
  p=self.config.policy;now=self.clock();require(type(now) is int and p['issued_at_ms']<=now<p['expires_at_ms'],'AUTHORITY_POLICY_EXPIRED')
 def require_live(self):
  self.policy_live();a=self.attestation;require(isinstance(a,dict) and a['issued_at_ms']<=self.clock()<a['expires_at_ms'],'AUTHORITY_ATTESTATION_EXPIRED_OR_ABSENT')
 def accept_source(self,raw):
  self.policy_live();parts,core=parse_source(raw);require(same(parts['DELIVERY167'],self.delivery) and core==self.delivery['template_sha256'],'AUTHORITY_CORE_OR_DELIVERY_CHANGED')
  a=parts['ATTESTATION167']
  if a is None:return False
  fields={'version','state','issuer','issued_at_ms','expires_at_ms','job_id','run_id','request_token','request_id','writer_principal','release_id','snapshot_backend_id','policy_id','notebook_id','notebook_path','delivery_sha256','pre','post'}
  require(isinstance(a,dict) and set(a)==fields and a['version']=='writer-authority167' and a['state']=='AUTHORIZED','AUTHORITY_SCHEMA')
  c=self.config;w=c.writer;now=self.clock()
  require(a['issuer']=={'id':OWNER_ID,'userName':OWNER} and type(a['issued_at_ms']) is int and type(a['expires_at_ms']) is int and a['issued_at_ms']<=now<a['expires_at_ms'] and 0<a['expires_at_ms']-a['issued_at_ms']<=MAX_TTL and a['expires_at_ms']<=c.policy['expires_at_ms'],'AUTHORITY_TIME_OR_ISSUER')
  require(type(a['job_id']) is int and a['job_id']==w.job_id and type(a['run_id']) is int and a['run_id']>0,'AUTHORITY_RUN_IDS')
  values={'job_id':str(w.job_id),'run_id':str(a['run_id']),'request_id':a['request_token'],'release_id':w.release_id,'snapshot_backend_id':w.snapshot_backend_id}
  require(self.widgets==values,'AUTHORITY_RUNTIME_WIDGET_MISMATCH')
  require(a['request_id']==self.delivery['request_id'] and a['request_token']==self.delivery['request_token'] and a['request_token']==digest({'job_id':w.job_id,'request_id':a['request_id']}),'AUTHORITY_REQUEST_SCOPE')
  require(a['writer_principal']==w.writer_principal and a['release_id']==w.release_id and a['snapshot_backend_id']==w.snapshot_backend_id and a['policy_id']==w.boundary_policy_id and a['notebook_id']==NOTEBOOK_ID and a['notebook_path']==w.notebook_path and a['delivery_sha256']==digest(self.delivery),'AUTHORITY_BOUND_CONFIG')
  from sbs.operations.cloud_dispatch import job_settings
  for phase in ('pre','post'):
   p=a[phase];require(set(p)=={'observed_at_ms','settings_sha256','job_acl','notebook_acl','notebook_id','notebook_path','operator'},'AUTHORITY_OBSERVATION_FIELDS')
   require(type(p['observed_at_ms']) is int and a['issued_at_ms']-MAX_TTL<=p['observed_at_ms']<=a['issued_at_ms'] and p['operator']==a['issuer'],'AUTHORITY_OBSERVATION_TIME')
   require(p['notebook_id']==NOTEBOOK_ID and p['notebook_path']==w.notebook_path and p['settings_sha256']==digest(job_settings(w)) and same(p['job_acl'],c.expected_acl),'AUTHORITY_OBSERVATION_CHANGED')
   trusted_acls(p['job_acl'],p['notebook_acl'],w.job_id,w.writer_principal)
  require(a['pre']['observed_at_ms']<=a['post']['observed_at_ms'] and same(a['pre']['job_acl'],a['post']['job_acl']) and same(a['pre']['notebook_acl'],a['post']['notebook_acl']),'AUTHORITY_ACL_DRIFT')
  require(self.attestation is None or same(self.attestation,a),'AUTHORITY_ATTESTATION_CHANGED')
  self.attestation=copy.deepcopy(a);self.require_live();return True
 def observe_protected(self,api):
  require(self.authority_reads<32,'AUTHORITY_READ_CAP');self.authority_reads+=1
  status=api.do('GET','/api/2.0/workspace/get-status',query={'path':self.config.writer.notebook_path});require(status.get('object_id')==NOTEBOOK_ID and status.get('path')==self.config.writer.notebook_path,'AUTHORITY_NOTEBOOK_ID_CHANGED')
  for _ in range(30):
   self.policy_live();require(self.authority_reads<31,'AUTHORITY_READ_CAP');self.authority_reads+=1
   value=api.do('GET','/api/2.0/workspace/export',query={'path':self.config.writer.notebook_path,'format':'SOURCE'})
   if self.accept_source(base64.b64decode(value.get('content',''),validate=True)):break
   time.sleep(2)
  else:raise ValueError('AUTHORITY_PENDING_TIMEOUT')
  require(self.attestation is not None,'AUTHORITY_PENDING_TIMEOUT');self.authority_reads+=1
  status=api.do('GET','/api/2.0/workspace/get-status',query={'path':self.config.writer.notebook_path});require(status.get('object_id')==NOTEBOOK_ID,'AUTHORITY_NOTEBOOK_ID_CHANGED');self.require_live()
 def verify_runtime(self,job,run,me):
  self.require_live();c=self.config;w=c.writer;a=self.attestation
  from sbs.operations.cloud_dispatch import job_settings
  expected=job_settings(w);strict_settings(job,expected)
  require(type(job.get('job_id')) is int and job.get('job_id')==w.job_id and job.get('run_as_user_name')==w.writer_principal and not job.get('next_page_token'),'AUTHORITY_CURRENT_JOB_ID')
  require(me.get('active') is True and me.get('userName')==w.writer_principal and me.get('id')=='72803555975940','AUTHORITY_ACTUAL_SUBJECT')
  require(type(run.get('job_id')) is int and type(run.get('run_id')) is int and run.get('job_id')==w.job_id and run.get('run_id')==a['run_id'] and not run.get('next_page_token') and run.get('state',{}).get('life_cycle_state')=='RUNNING' and run.get('trigger')=='ONE_TIME','AUTHORITY_ACTUAL_RUN')
  require(not any(run.get(k) for k in ('overriding_parameters','git_source','job_clusters')),'AUTHORITY_RUN_EXTRA_CONFIG')
  tasks=run.get('tasks');require(isinstance(tasks,list) and len(tasks)==1,'AUTHORITY_RUN_TASKS');t=tasks[0];exp=expected['tasks'][0]
  required=set(exp)-MISSING_ATTESTED
  for k in required:require(k in t and same(t[k],exp[k]),'AUTHORITY_RUNTIME_TASK_CHANGED')
  for k in MISSING_ATTESTED:
   if k in t:require(same(t[k],exp[k]),'AUTHORITY_RUNTIME_ATTESTED_CONTRADICTION')
  for k in set(t)-set(exp):
   require(k in TASK_DEFAULTS or k in RUNTIME,'AUTHORITY_RUNTIME_UNKNOWN_FIELD')
   if k in TASK_DEFAULTS:require(same(t[k],TASK_DEFAULTS[k]),'AUTHORITY_RUNTIME_DEFAULT_CHANGED')
  require(t.get('attempt_number')==0 and type(t.get('attempt_number')) is int and type(t.get('run_id')) is int and t['run_id']>0,'AUTHORITY_RUNTIME_ATTEMPT')
  if t.get('cluster_instance'):raise ValueError('AUTHORITY_SERVERLESS_CLUSTER_UNEXPECTED')
  if 'effective_performance_target' in t:require(t['effective_performance_target']=='PERFORMANCE_OPTIMIZED','AUTHORITY_RUNTIME_PERFORMANCE_CHANGED')
  if 'resolved_values' in t:require(t['resolved_values']=={'notebook_task':{'base_parameters':self.widgets}},'AUTHORITY_API_RESOLVED_VALUES_CONTRADICTION')
  missing=tuple(sorted(set(exp)-set(t)))
  self.evidence=WriterAuthorityEvidence('operator_attested_writer167',a['run_id'],digest(a),'owner_live_pre_and_postdispatch; protected_notebook_delivery; NOT writer_live_ACL',tuple(sorted(t)),missing,'actual_dbutils_widgets_compared_with_attestation_and_get_run',missing+(() if 'resolved_values' in t else ('resolved_values',)),a['expires_at_ms'])
  return self.evidence

class WriterSession167:
 """Gate after SDK authenticate and immediately before every workspace send."""
 def __init__(self,session,authority):
  self.session=session;self.authority=authority;self.adapters=session.adapters;self.counts={'http':0,'sql':0,'files_put':0}
  require(all(a.max_retries.total==0 for a in self.adapters.values()),'WRITER167_RETRIES_FORBIDDEN')
 def request(self,method,url,**kwargs):
  a=self.authority;c=a.config;host='https://dbc-0410b264-20c7.cloud.databricks.com';require(url.startswith(host+'/api/') and not any(x in url for x in ('?','#','..')),'WRITER167_HOST_PATH')
  path=url[len(host):];body=kwargs.get('json');params=kwargs.get('params') or {};prefix='/api/2.0/fs/files'+c.volume_prefix
  allowed_get={'/api/2.0/preview/scim/v2/Me','/api/2.2/jobs/get','/api/2.2/jobs/runs/get','/api/2.1/unity-catalog/tables/'+c.control_table,'/api/2.0/sql/warehouses/'+c.warehouse_id,'/api/2.0/workspace/export','/api/2.0/workspace/get-status'}
  sql=method=='POST' and path=='/api/2.0/sql/statements';upload=method=='PUT' and (path.startswith(prefix+'/') or path.startswith('/api/2.0/fs/directories'+c.volume_prefix+'/'))
  read=method=='GET' and (path in allowed_get or path.startswith(prefix+'/') or re.fullmatch('/api/2.0/sql/statements/[a-zA-Z0-9-]+',path))
  require(read or sql or upload,'WRITER167_OPERATION_FORBIDDEN')
  if path.startswith('/api/2.0/workspace/'):require(params.get('path')==c.writer.notebook_path,'WRITER167_NOTEBOOK_SCOPE')
  if path=='/api/2.2/jobs/get':require(params.get('job_id')==c.writer.job_id,'WRITER167_JOB_SCOPE')
  if path=='/api/2.2/jobs/runs/get':require(params.get('run_id')==int(a.widgets['run_id']),'WRITER167_RUN_SCOPE')
  if sql:
   table='.'.join('`'+v+'`' for v in c.control_table.split('.'));allowed={'SELECT control_id, revision, state_json FROM '+table,'UPDATE '+table+' SET revision = revision + 1, state_json = :state WHERE control_id = :control AND revision = :revision'}
   require(isinstance(body,dict) and body.get('warehouse_id')==c.warehouse_id and body.get('statement') in allowed,'WRITER167_SQL_SCOPE')
  if method=='GET':a.policy_live()
  else:a.require_live()
  self.counts['http']+=1;self.counts['sql']+=int(sql);self.counts['files_put']+=int(upload)
  require(self.counts['http']<=4000 and self.counts['sql']<=100 and self.counts['files_put']<=512,'WRITER167_QUOTA')
  response=self.session.request(method,url,**kwargs)
  try:
   if method=='GET':a.policy_live()
   else:a.require_live()
  except Exception:response.close();raise
  return response
 def close(self):self.session.close()

def execute_from_config167(config,project_root,*,delivery,widgets):
 """Use sealed105 pipeline/CAS; explicit subclass replaces writer authority only."""
 from databricks.sdk.core import Config
 from sbs.operations.cloud_driver import CloudDriver,sdk_services
 from sbs.operations.cloud_writer import prepare_and_publish
 from sbs.operations import load_sealed_plan
 from dataclasses import replace
 import requests
 authority=AttestedWriterVerifier167(config,delivery,widgets)
 cfg=Config();require(cfg.host.rstrip('/')=='https://dbc-0410b264-20c7.cloud.databricks.com','WRITER167_HOST')
 session=WriterSession167(requests.Session(),authority);services=sdk_services(cfg,session=session)
 class AttestedCloudDriver167(CloudDriver):
  def writer_guard(self,job_id,run_id):
   require(job_id==config.writer.job_id and run_id==int(widgets['run_id']),'WRITER167_CONTEXT')
   authority.require_live()
   job=self.services.api.do('GET','/api/2.2/jobs/get',query={'job_id':job_id})
   run=self.services.api.do('GET','/api/2.2/jobs/runs/get',query={'run_id':run_id,'include_resolved_values':True})
   me=obj(self.services.current_user.me());evidence=authority.verify_runtime(job,run,me)
   self.identity();_,state=self.control.read();token=delivery['request_token'];record=state['requests'].get(token)
   require(isinstance(record,dict) and record.get('job_id')==job_id and record.get('run_id')==run_id and record.get('idempotency_token')==token and record.get('release_id')==config.writer.release_id and record.get('status')=='submitted' and record.get('evidence_mode')=='real','WRITER167_LEDGER_BINDING')
   self.observations['writer_authority167']=asdict(evidence);return True
  def execute(self,root,plan,*,run_id):
   self.writer_guard(config.writer.job_id,run_id)
   result=prepare_and_publish(root,plan,run_id=run_id,artifact_store=self.artifacts,writer=self.writer,capture_mode=config.capture_mode,capture_state_root=config.capture_state_root)
   return {**result,'evidence_mode':'real','observations':self.observations,'cloud_acceptance':False,'writer_transport':session.counts}
 try:
  authority.observe_protected(services.api)
  print(json.dumps({'writer_authority167_attestation':authority.attestation},sort_keys=True))
  root=Path(project_root).resolve();plan=load_sealed_plan(root);pairs=json.loads((root/'config/genie-pilot-002.json').read_bytes());unique={}
  for item in pairs['contexts']:
   pair=item['pair'];key=pair['pair_id'];require(key not in unique or unique[key]==pair,'WRITER167_PAIR_CONFLICT');unique[key]=pair
  plan=replace(plan,pairs=tuple(unique.values()))
  return AttestedCloudDriver167(config,services,evidence_mode='real').execute(root,plan,run_id=int(widgets['run_id']))
 finally:session.close()
