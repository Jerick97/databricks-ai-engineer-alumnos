"""Additive private-home continuation of106/114; no Shared ACL changes.

Run orchestration copied from frozen106 with explicit private path/stage changes.
Shared bootstrap remains inert. Same original journal, policy and120/12/12 quotas.
"""
from pathlib import Path
from types import SimpleNamespace
import json,re,time
from . import provision_106 as base
from .provision_106 import (HOST,OWNER,OWNER_ID,PRINCIPAL,WAREHOUSE,VOLUME,PREFIX,LIMITS,RemoteError,DriverConfig,notebook_source,sha,safe_json)
from .provision_105 import TABLE,control_steps,DEPENDENCIES
from .provision_114 import Head404Api
from .cloud_dispatch import require,obj,digest,canonical,job_settings
from . import atomic,exclusive_lock
PRIVATE_HOME='/Users/'+OWNER
HOME_ID=2571826969054457

def private_settings(*,notebook_path,release_id,snapshot_backend_id,boundary_policy_id):
 require(isinstance(notebook_path,str) and re.fullmatch(re.escape(PRIVATE_HOME)+r'/sbs-radar-writer118-[0-9a-f]{16}',notebook_path),'PRIVATE_NOTEBOOK_NAMESPACE_INVALID')
 require(all(isinstance(v,str) and re.fullmatch('[0-9a-f]{64}',v) for v in (release_id,snapshot_backend_id,boundary_policy_id)),'OBSERVED_BINDINGS_REQUIRED')
 return job_settings(SimpleNamespace(writer_principal=PRINCIPAL,notebook_path=notebook_path,release_id=release_id,snapshot_backend_id=snapshot_backend_id,boundary_policy_id=boundary_policy_id,schedule_enabled=False,compute_mode='serverless',cluster_id=None,environment_version='4',environment_dependencies=DEPENDENCIES))

def validate_home_acl(acl):
 require(acl.get('object_id')=='/directories/'+str(HOME_ID) and acl.get('object_type')=='directory' and isinstance(acl.get('access_control_list'),list),'HOME_ACL_IDENTITY_INVALID')
 owner=False
 for entry in acl['access_control_list']:
  permissions=entry.get('all_permissions');require(isinstance(permissions,list) and permissions,'HOME_PERMISSIONS_INVALID')
  require(entry.get('user_name')==OWNER or entry.get('group_name')=='admins','UNTRUSTED_HOME_PRINCIPAL')
  require(all(p.get('permission_level') in ('CAN_READ','CAN_RUN','CAN_EDIT','CAN_MANAGE') for p in permissions),'HOME_PERMISSION_INVALID')
  if entry.get('user_name')==OWNER:owner=any(p.get('permission_level')=='CAN_MANAGE' and p.get('inherited') is False for p in permissions)
 require(owner,'HOME_OWNER_CONTROL_REQUIRED')
 return {'object_id':HOME_ID,'acl_sha256':digest(acl)}

class PrivateApi118(base.ScopedApi):
 """Only two additional paths: private import and GET existing home ACL."""
 def __init__(self,*args,private_notebook,**kwargs):
  super().__init__(*args,**kwargs);self.private_notebook=private_notebook
 def do(self,method,path=None,*,query=None,body=None,headers=None,data=None,raw=False,response_headers=None,**extra):
  private_import=method=='POST' and path=='/api/2.0/workspace/import'
  home_acl=method=='GET' and path=='/api/2.0/permissions/directories/'+str(HOME_ID)
  require(not(method=='POST' and path=='/api/2.0/workspace/mkdirs'),'NO_NEW_WORKSPACE_DIRECTORY')
  if method=='POST' and path=='/api/2.2/jobs/create':
   tasks=body.get('tasks',[]) if isinstance(body,dict) else []
   require(len(tasks)==1 and tasks[0].get('notebook_task',{}).get('notebook_path')==self.private_notebook,'JOB_PRIVATE_NOTEBOOK_REQUIRED')
  if not(private_import or home_acl):return super().do(method,path,query=query,body=body,headers=headers,data=data,raw=raw,response_headers=response_headers,**extra)
  require(not extra and query in (None,{}) and data is None and not raw and response_headers is None,'PRIVATE_REQUEST_INVALID')
  if private_import:
   require(isinstance(body,dict) and set(body)=={'path','content','format','language','overwrite'} and body['path']==self.private_notebook and body['format']=='SOURCE' and body['language']=='PYTHON' and type(body['overwrite']) is bool and isinstance(body['content'],str),'PRIVATE_IMPORT_SCOPE_INVALID')
   require(self.permit==(method,path,digest(body),None),'WRITE_NOT_APPROVED');self.permit=None
  else:require(body is None,'HOME_GET_BODY_FORBIDDEN')
  self.authorize();self.reserve(sql=False,mutation=private_import)
  auth=self._cfg.authenticate();self.authorize()
  try:r=self.session.request(method,self._cfg.host.rstrip('/')+path,params={},json=body,data=None,headers={**(headers or {}),**auth},timeout=(10,60),allow_redirects=False,stream=True)
  except Exception:raise ValueError('TRANSPORT_OUTCOME_UNKNOWN') from None
  try:
   content=r.raw.read(33554433,decode_content=True);require(len(content)<=33554432,'RESPONSE_LIMIT')
   if not 200<=r.status_code<300:raise RemoteError(r.status_code,'UNCLASSIFIED')
   return json.loads(content) if content else {}
  finally:r.close()

def patch_inputs(root):
 names=['src/sbs/operations/provision_118.py','src/sbs/operations/provision_114.py','runs/sk08-private-home-118b.json','runs/sk08-notebook-acl-118.json','runs/sk11-provision-106-freeze.json']
 return {p:sha((Path(root)/p).read_bytes()) for p in names}

class PrivateProvisioner118(base.Provisioner):
 def __init__(self,root,journal,review,patch_review,**kwargs):
  self.patch_review=patch_review;self.patch_root=Path(root).resolve()
  require(patch_review.get('files')==patch_inputs(root),'PRIVATE_REVIEW_INPUTS_REQUIRED')
  state=Path(journal).resolve()
  require((state/'budget.json').is_file() and (state/'policy.json').is_file() and all(len(list((state/stage).glob('*.observed.json')))==1 for stage in ('table','seed','control_acl','bundle','notebook_bootstrap')),'EXISTING_106_BOUND_STATE_REQUIRED')
  super().__init__(root,journal,review,**kwargs)
  self.notebook=PRIVATE_HOME+'/sbs-radar-writer118-'+self.pin[:16]
  original=self.api
  self.api=PrivateApi118(original._cfg,journal=self.journal,authorize=self.authorize,prefix=self.prefix,session=original.session,private_notebook=self.notebook)
  for service in (self.jobs,self.workspace,self.tables,self.grants,self.sql,self.files,self.me,self.warehouses,self.volumes):service._api=self.api
  self.files._api=Head404Api(self.api,expected_directory=self.prefix)
 def authorize(self):
  r=self.patch_review;now=int(time.time()*1000)
  require(r.get('approved') is True and r.get('scope')=='private_writer118' and r.get('writer_mode')==self.mode and r.get('limits')==LIMITS,'PRIVATE_REVIEW_REQUIRED')
  require(type(r.get('issued_at_ms')) is int and type(r.get('expires_at_ms')) is int and r['issued_at_ms']<=now<r['expires_at_ms'] and 0<r['expires_at_ms']-r['issued_at_ms']<=1800000,'PRIVATE_WINDOW_REQUIRED')
  for name,pin in r['files'].items():require(sha((self.patch_root/name).read_bytes())==pin,'PRIVATE_INPUT_DRIFT')
  super().authorize()
 def home(self):
  status=obj(self.workspace.get_status(PRIVATE_HOME));require(status.get('path')==PRIVATE_HOME and status.get('object_type')=='DIRECTORY' and status.get('object_id')==HOME_ID,'PRIVATE_HOME_IDENTITY_INVALID')
  acl=self.api.do('GET','/api/2.0/permissions/directories/'+str(HOME_ID));return validate_home_acl(acl)
 def run(self):
  from databricks.sdk.service.jobs import JobSettings,JobAccessControlRequest,JobPermissionLevel
  from databricks.sdk.service.catalog import PermissionsChange,Privilege
  from databricks.sdk.service.workspace import WorkspaceObjectAccessControlRequest,WorkspaceObjectPermissionLevel
  self.authorize()
  user=obj(self.me.me());require(user.get('userName')==OWNER and user.get('id')==OWNER_ID and user.get('active') is True,'OPERATOR_IDENTITY_INVALID');self.owner=user['userName']
  self.home()
  sp=self.api.do('GET','/api/2.0/preview/scim/v2/ServicePrincipals/72803555975940');require(sp.get('id')=='72803555975940' and sp.get('applicationId')==PRINCIPAL and sp.get('active') is True,'WRITER_PRINCIPAL_INVALID')
  require(obj(self.warehouses.get(WAREHOUSE)).get('state')=='RUNNING','WAREHOUSE_NOT_RUNNING')
  volume=obj(self.volumes.read(VOLUME));require(volume.get('full_name')==VOLUME,'VOLUME_IDENTITY_INVALID')
  policy={'trusted_administrators':[self.owner],'maintenance':'Only the reviewed provision106 operator mutates dedicated control DDL/seed under exclusive maintenance. Workspace administrators remain trusted.','exclusive_writer':'Only the named paused Job runs as the existing writer principal; privileged administrators remain trusted.','singleton_control':'No parallel DDL/INSERT/DELETE into dedicated control table during provisioning or operation.','storage_authorized':'Existing UC Volume is SBS-owned; effective writer privileges must be observed before first run.','issued_at_ms':self.review['issued_at_ms'],'expires_at_ms':self.review['expires_at_ms']}
  policy_path=self.journal/'policy.json'
  if policy_path.exists():policy=safe_json(policy_path)
  else:atomic(policy_path,policy)
  require(policy['trusted_administrators']==[self.owner],'POLICY_OPERATOR_DRIFT')
  # No existing resource is adopted without a prior local durable intent.
  if not list((self.journal/'table').glob('*.intent.json')):require(self.table() is None,'EXISTING_TABLE_REQUIRES_RECONCILIATION')
  table_step=control_steps()[0]
  self.table_id=self.one('table','create_control',table_step['payload'],self.table,lambda _:self.statement(table_step['payload']['statement'],mutation=True))['table_id']
  def seed_effect(_):
   self.rows(want_empty=True);return self.statement(control_steps()[1]['payload']['statement'],mutation=True)
  self.one('seed','seed_control',control_steps()[1]['payload'],self.rows,seed_effect)
  # Add exactly two privileges to the new dedicated table; no data-table ACLs.
  grant_payload={'changes':[{'principal':PRINCIPAL,'add':['SELECT','MODIFY']}]}
  def grant_observe():
   require(self.table() is not None,'CONTROL_TABLE_REQUIRED');g=obj(self.grants.get('table',TABLE,principal=PRINCIPAL));require(not g.get('next_page_token'),'GRANT_PAGINATION_UNSUPPORTED')
   matches=[p for p in g.get('privilege_assignments',[]) if p.get('principal')==PRINCIPAL]
   if not matches:return None
   require(len(matches)==1,'GRANT_IDENTITY_AMBIGUOUS');priv=set(matches[0].get('privileges',[]));require(priv<={'SELECT','MODIFY'},'EXCESS_WRITER_CONTROL_GRANT')
   return {'principal':PRINCIPAL,'privileges':sorted(priv),'sha256':digest(g)} if priv=={'SELECT','MODIFY'} else None
  self.one('control_acl','set_job_acl',grant_payload,grant_observe,lambda _:self.api.with_permit('PATCH','/api/2.1/unity-catalog/permissions/table/'+TABLE,grant_payload,lambda:self.grants.update('table',TABLE,changes=[PermissionsChange(principal=PRINCIPAL,add=[Privilege.SELECT,Privilege.MODIFY])])))
  def directory_observe():
   try:self.files.get_directory_metadata(self.prefix)
   except RemoteError as e:
    if e.status==404 and e.code in ('RESOURCE_DOES_NOT_EXIST','NOT_FOUND'):return None
    raise
   return {'directory':self.prefix}
  self.one('volume_directory','upload_bundle',{'path':self.prefix},directory_observe,lambda _:self.api.with_permit('PUT','/api/2.0/fs/directories'+self.prefix,None,lambda:self.files.create_directory(self.prefix)))
  archive_path=self.prefix+'/code.tar.gz';self.upload('bundle',archive_path,self.bundle.read_bytes())
  self.bootstrap='# Databricks notebook source\nprint("SBS118 provisioning preflight: final server configuration pending; no cloud writer execution")\n'
  if not list((self.journal/'notebook_bootstrap118').glob('*.intent.json')):require(self.notebook_readback(self.bootstrap) is None,'EXISTING_NOTEBOOK_FORBIDDEN')
  if any(self.journal.glob('notebook_bound118_*')):
   receipts=list((self.journal/'notebook_bootstrap118').glob('*.observed.json'));require(len(receipts)==1,'BOOTSTRAP_RECEIPT_REQUIRED')
   nb=safe_json(receipts[0])['observation'];current=obj(self.workspace.get_status(self.notebook))
   require(current.get('object_id')==nb['object_id'] and current.get('path')==self.notebook and current.get('object_type')=='NOTEBOOK','NOTEBOOK_ID_DRIFT');self.api.notebook_ids.add(nb['object_id'])
  else:nb=self.import_notebook('notebook_bootstrap118',self.bootstrap)
  acl_payload={'access_control_list':[{'service_principal_name':PRINCIPAL,'permission_level':'CAN_READ'}]}
  def notebook_acl():
   permissions=obj(self.workspace.get_permissions('notebooks',str(nb['object_id'])))
   entries=permissions.get('access_control_list',[]);require(isinstance(entries,list),'NOTEBOOK_ACL_INVALID')
   for entry in entries:
    levels={p.get('permission_level') for p in entry.get('all_permissions',[])}
    if levels&{'CAN_EDIT','CAN_MANAGE'}:require(entry.get('user_name')==self.owner or entry.get('group_name')=='admins','UNTRUSTED_NOTEBOOK_WRITER')
   for entry in entries:
    if entry.get('service_principal_name')==PRINCIPAL:
     levels={p.get('permission_level') for p in entry.get('all_permissions',[])};require(levels<={'CAN_READ','CAN_RUN'},'WRITER_NOTEBOOK_WRITE_FORBIDDEN')
     if levels:return {'object_id':nb['object_id'],'acl_sha256':digest(permissions)}
   return None
  self.one('notebook_acl118','set_job_acl',acl_payload,notebook_acl,lambda _:self.api.with_permit('PATCH','/api/2.0/permissions/notebooks/'+str(nb['object_id']),acl_payload,lambda:self.workspace.update_permissions('notebooks',str(nb['object_id']),access_control_list=[WorkspaceObjectAccessControlRequest(service_principal_name=PRINCIPAL,permission_level=WorkspaceObjectPermissionLevel.CAN_READ)])))
  backend={'control_table':TABLE,'control_table_id':self.table_id,'warehouse_id':WAREHOUSE,'volume_prefix':PREFIX}
  settings=private_settings(notebook_path=self.notebook,release_id=self.package['release_id'],snapshot_backend_id=digest(backend),boundary_policy_id=digest(policy))
  if not list((self.journal/'job').glob('*.intent.json')):require(self.job_observation(settings) is None,'EXISTING_JOB_REQUIRES_RECONCILIATION')
  access=[{'user_name':self.owner,'permission_level':'IS_OWNER'},{'service_principal_name':PRINCIPAL,'permission_level':'CAN_MANAGE_RUN'}];create_payload={**settings,'access_control_list':access}
  def create_job(_):
   require(self.job_observation(settings) is None,'JOB_APPEARED_BEFORE_CREATE')
   parsed=JobSettings.from_dict(settings);kwargs={k:getattr(parsed,k) for k in settings}
   kwargs['access_control_list']=[JobAccessControlRequest.from_dict(v) for v in access]
   return self.api.with_permit('POST','/api/2.2/jobs/create',create_payload,lambda:self.jobs.create(**kwargs))
  job=self.one('job','create_job',create_payload,lambda:self.job_observation(settings),create_job);job_id=job['job_id']
  acl=obj(self.jobs.get_permissions(str(job_id)));require(acl.get('object_id')=='/jobs/'+str(job_id) and isinstance(acl.get('access_control_list'),list),'JOB_ACL_INVALID')
  writer_permission=False;owner_permission=False
  for entry in acl['access_control_list']:
   principal=entry.get('service_principal_name');user_name=entry.get('user_name');group=entry.get('group_name');levels={p.get('permission_level') for p in entry.get('all_permissions',[])}
   if principal==PRINCIPAL:require(levels<={'CAN_VIEW','CAN_MANAGE_RUN'},'WRITER_ACL_EXCESS');writer_permission='CAN_MANAGE_RUN' in levels
   elif user_name==self.owner:owner_permission='IS_OWNER' in levels
   elif levels&{'CAN_MANAGE_RUN','CAN_MANAGE','IS_OWNER'}:require(group=='admins','UNTRUSTED_JOB_ACL')
  require(writer_permission and owner_permission,'JOB_ACL_BINDING_REQUIRED')
  config={'writer':{'job_id':job_id,'writer_principal':PRINCIPAL,'cluster_id':None,'notebook_path':self.notebook,'release_id':self.package['release_id'],'snapshot_backend_id':digest(backend),'boundary_policy_id':digest(policy),'schedule_enabled':False,'compute_mode':'serverless','environment_version':'4','environment_dependencies':list(__import__('sbs.operations.provision_105',fromlist=['DEPENDENCIES']).DEPENDENCIES)},**backend,'expected_acl':acl,'policy':policy,'release_manifest':self.package['release_manifest'],'capture_mode':'sealed','capture_state_root':None}
  # backend's keys map exactly to DriverConfig; its snapshot hash includes same identity.
  DriverConfig.from_dict(config);config_raw=(canonical(config)+'\n').encode();config_pin=sha(config_raw);config_path=self.prefix+'/driver-'+config_pin+'.json'
  self.upload('config',config_path,config_raw)
  final=notebook_source(archive_path=archive_path,archive_sha=self.pin,manifest_path=self.package['release_manifest'],release_id=self.package['release_id'],config_path=config_path,config_sha=config_pin,mode=self.mode)
  previous_source=None
  if self.mode=='execute':
   require(policy['issued_at_ms']<=int(time.time()*1000)<policy['expires_at_ms'],'WRITER_POLICY_RENEWAL_REQUIRED')
   if (self.journal/'notebook_bound118_preflight').exists():
    previous_source=notebook_source(archive_path=archive_path,archive_sha=self.pin,manifest_path=self.package['release_manifest'],release_id=self.package['release_id'],config_path=config_path,config_sha=config_pin,mode='preflight')
  bound=self.import_notebook('notebook_bound118_'+self.mode,final,overwrite=True,previous_source=previous_source)
  self.home()
  require(self.job_observation(settings)['job_id']==job_id,'FINAL_JOB_DRIFT');require(obj(self.jobs.get_permissions(str(job_id)))==acl,'FINAL_ACL_DRIFT');self.rows()
  result={'status':'provisioned_paused_not_run','continuation':'private_home118','inert_shared_bootstrap':'retained_unused_by_Job','job_id':job_id,'control_table_id':self.table_id,'notebook':bound,'config_path':config_path,'config_sha256':config_pin,'archive_sha256':self.pin,'writer_mode':self.mode,'schedule':'PAUSED 08:00 America/Lima','cloud_acceptance':False,'cost':None,'remaining':['effective USE CATALOG/SCHEMA, warehouse CAN_USE and Volume READ/WRITE for writer','first real writer run via CloudDispatcher, output readback and recovery','sealed bootstrap does not establish live daily capture; remote capture needs separately bound config/recovery','writer administrative policy renewal before expiry','Genie certificate separate TTL5min renewal','independent E2E acceptance before enabling schedule']}
  atomic(self.journal/'result.json',result);atomic(self.journal/'driver-config.json',config);return result

def preflight(root):
 result=base.preflight(root);observation=safe_json(Path(root)/'runs/sk08-private-home-118b.json')
 require(observation.get('path')==PRIVATE_HOME and observation.get('metadata',{}).get('object_id')==HOME_ID,'HOME_DIAGNOSIS_REQUIRED');validate_home_acl(observation['acl'])
 return {**result,'continuation':'private_home118','private_home':PRIVATE_HOME,'private_home_id':HOME_ID,'patch_inputs':patch_inputs(root),'new_workspace_directories':0,'shared_acl_changes':0}

def main():
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path.cwd());p.add_argument('--execute',action='store_true');p.add_argument('--review-file',type=Path);p.add_argument('--patch-review-file',type=Path);p.add_argument('--journal',type=Path);p.add_argument('--profile');p.add_argument('--writer-mode',choices=['preflight','execute'],default='preflight');a=p.parse_args()
 if not a.execute:print(json.dumps(preflight(a.root)));return
 require(all(v is not None for v in (a.review_file,a.patch_review_file,a.journal)),'REVIEW_PATCH_AND_EXISTING_JOURNAL_REQUIRED');preflight(a.root)
 with exclusive_lock(a.journal):
  executor=PrivateProvisioner118(a.root,a.journal,safe_json(a.review_file),safe_json(a.patch_review_file),profile=a.profile,writer_mode=a.writer_mode)
  try:print(json.dumps(executor.run()))
  finally:executor.api.session.close()
if __name__=='__main__':main()
