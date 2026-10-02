"""Bounded additive metadata grants for existing SBS writer; default offline.

Reuses069 raw UC observation/unknown-before semantics and105 durable no-resend
steps. Four PATCH maximum, never set_permissions/PUT, ownership, SQL or Jobs.
"""
from pathlib import Path
from urllib.parse import urlsplit
import json,time
from sbs.operations import atomic,exclusive_lock
from sbs.operations.cloud_dispatch import require,canonical,digest
from sbs.operations.provision_105 import step_once,_write_new
from sbs.operations.provision_106 import HOST,OWNER,OWNER_ID,PRINCIPAL,WAREHOUSE,sha,safe_json
PID='72803555975940';CATALOG='neptuno_manuel_arguelles';SCHEMA=CATALOG+'.sbs_radar'
TARGETS=(('catalog',CATALOG,('USE_CATALOG',)),('schema',SCHEMA,('USE_SCHEMA',)),('volume',SCHEMA+'.release_artifacts',('READ_VOLUME','WRITE_VOLUME')),('warehouse',WAREHOUSE,('CAN_USE',)))
LIMITS={'http':64,'patch':4}

def uc_rows(data,*,unknown=False):
 require(isinstance(data,dict) and not data.get('next_page_token'),'UC_PAGINATION_OR_SHAPE_INVALID')
 if unknown and data=={}:return []
 rows=data.get('privilege_assignments');require(isinstance(rows,list),'UC_ASSIGNMENTS_REQUIRED')
 require(all(isinstance(a,dict) and isinstance(a.get('principal'),str) and isinstance(a.get('privileges'),list) for a in rows),'UC_ROW_INVALID')
 return rows

def privileges(data,subjects,*,unknown=False):
 result=set()
 for row in uc_rows(data,unknown=unknown):
  if row['principal'] in subjects:
   for privilege in row['privileges']:
    value=privilege.get('privilege') if isinstance(privilege,dict) else privilege
    require(isinstance(value,str),'UC_PRIVILEGE_INVALID');result.add(value)
 return result

def acl_rows(data):
 require(isinstance(data,dict) and data.get('object_id')=='/sql/warehouses/'+WAREHOUSE and data.get('object_type')=='warehouses' and isinstance(data.get('access_control_list'),list) and not data.get('next_page_token'),'WAREHOUSE_ACL_INVALID')
 return data['access_control_list']

def levels(data,groups):
 result=set()
 for row in acl_rows(data):
  require(isinstance(row,dict) and isinstance(row.get('all_permissions'),list),'WAREHOUSE_ROW_INVALID')
  if row.get('service_principal_name')==PRINCIPAL or row.get('group_name') in groups:
   result.update(p.get('permission_level') for p in row['all_permissions'])
 require(result<={'CAN_USE'},'EXCESS_WRITER_WAREHOUSE_PRIVILEGE');return result

def preserved(before,after,*,warehouse):
 def other(data,unknown):
  rows=acl_rows(data) if warehouse else uc_rows(data,unknown=unknown)
  return sorted(canonical(r) for r in rows if (r.get('service_principal_name')!=PRINCIPAL if warehouse else r['principal'] not in {PRINCIPAL,PID}))
 old=other(before,True);new=other(after,False)
 if before=={}:
  require(not old,'UNKNOWN_BASELINE_INVALID');return 'visible_rows_only_unknown_before'
 require(old==new,'UNRELATED_PERMISSION_CHANGED');return 'all_observed_other_rows_preserved'

def delta(target,before,groups):
 kind,name,required=target;needed=set(required)
 if kind=='warehouse':
  return None if needed<=levels(before['direct'],groups) else {'access_control_list':[{'service_principal_name':PRINCIPAL,'permission_level':'CAN_USE'}]}
 direct=privileges(before['direct'],{PRINCIPAL,PID},unknown=True)
 effective=privileges(before['effective'],{PRINCIPAL,PID}|groups,unknown=True)
 require((direct|effective)<=needed|{'BROWSE'},'EXCESS_WRITER_UC_PRIVILEGE')
 missing=sorted(needed-direct-effective)
 return {'changes':[{'principal':PRINCIPAL,'add':missing}]} if missing else None

def paths(target):
 kind,name,_=target
 if kind=='warehouse':return ('/api/2.0/permissions/warehouses/'+name,None)
 return ('/api/2.1/unity-catalog/permissions/'+kind+'/'+name,'/api/2.1/unity-catalog/effective-permissions/'+kind+'/'+name)

def review_inputs(root):
 names=['src/sbs/guardrails/writer_grants_117.py','src/sbs/operations/provision_105.py','src/sbs/operations/provision_106.py','src/sbs/operations/__init__.py','runs/sk08-sk11-writer-access-116.json','runs/sk08-app-grants-069.py']
 return {name:sha((Path(root)/name).read_bytes()) for name in names}

class WriterGrants:
 def __init__(self,root,journal,review,*,profile=None,config_factory=None,session=None):
  self.root=Path(root).resolve();self.state=Path(journal).resolve();self.review=review
  require(review.get('files')==review_inputs(self.root),'REVIEW_INPUTS_REQUIRED');self.authorize()
  if config_factory:self.cfg=config_factory()
  else:
   from databricks.sdk.core import Config
   self.cfg=Config(profile=profile) if profile else Config()
  u=urlsplit(self.cfg.host);require(u.scheme=='https' and u.hostname==HOST and u.port is None and u.path in ('','/') and not any((u.username,u.password,u.query,u.fragment)),'WORKSPACE_HOST_INVALID')
  import requests
  self.session=session or requests.Session();require(all(a.max_retries.total==0 for a in self.session.adapters.values()),'RETRIES_FORBIDDEN')
 def authorize(self):
  r=self.review;now=int(time.time()*1000)
  require(r.get('approved') is True and r.get('scope')=='writer_grants117' and r.get('limits')==LIMITS,'REVIEW_REQUIRED')
  require(type(r.get('issued_at_ms')) is int and type(r.get('expires_at_ms')) is int and r['issued_at_ms']<=now<r['expires_at_ms'] and 0<r['expires_at_ms']-r['issued_at_ms']<=1800000,'REVIEW_WINDOW_INVALID')
  for name,pin in r['files'].items():require(sha((self.root/name).read_bytes())==pin,'REVIEW_INPUT_DRIFT')
 def call(self,method,path,*,body=None,params=None):
  read_paths={'/api/2.0/preview/scim/v2/Me','/api/2.0/preview/scim/v2/ServicePrincipals/'+PID}|{p for t in TARGETS for p in paths(t) if p}
  require(method in ('GET','PATCH') and path in read_paths,'REQUEST_OUTSIDE_SCOPE')
  if method=='PATCH':
   matches=[t for t in TARGETS if paths(t)[0]==path];require(len(matches)==1,'PATCH_PATH_INVALID');target=matches[0]
   if target[0]=='warehouse':require(body=={'access_control_list':[{'service_principal_name':PRINCIPAL,'permission_level':'CAN_USE'}]},'PATCH_BODY_INVALID')
   else:
    changes=body.get('changes') if isinstance(body,dict) else None
    require(set(body)=={'changes'} and isinstance(changes,list) and len(changes)==1 and set(changes[0])=={'principal','add'} and changes[0]['principal']==PRINCIPAL and isinstance(changes[0]['add'],list) and bool(changes[0]['add']) and set(changes[0]['add'])<=set(target[2]) and len(set(changes[0]['add']))==len(changes[0]['add']),'PATCH_BODY_INVALID')
  self.authorize();bp=self.state/'budget.json';b=safe_json(bp) if bp.exists() else {'http':0,'patch':0};b['http']+=1;b['patch']+=int(method=='PATCH');require(all(type(b[k]) is int and 0<=b[k]<=LIMITS[k] for k in LIMITS),'CUMULATIVE_BUDGET_EXCEEDED');atomic(bp,b)
  headers=self.cfg.authenticate();self.authorize()
  try:r=self.session.request(method,'https://'+HOST+path,headers=headers,params=params,json=body,timeout=(10,60),allow_redirects=False,stream=True)
  except Exception:raise ValueError('HTTP_OUTCOME_UNKNOWN') from None
  try:
   raw=r.raw.read(1048577,decode_content=True);require(len(raw)<=1048576,'RESPONSE_TOO_LARGE');require(200<=r.status_code<300,'HTTP_NOT_CONFIRMED');data=json.loads(raw);require(isinstance(data,dict),'JSON_OBJECT_REQUIRED');return data
  finally:r.close()
 def identity(self):
  user=self.call('GET','/api/2.0/preview/scim/v2/Me');require(user.get('id')==OWNER_ID and user.get('userName')==OWNER and user.get('active') is True,'OPERATOR_IDENTITY_INVALID')
  sp=self.call('GET','/api/2.0/preview/scim/v2/ServicePrincipals/'+PID);require(sp.get('id')==PID and sp.get('applicationId')==PRINCIPAL and sp.get('active') is True,'WRITER_IDENTITY_INVALID')
  groups=sp.get('groups',[]);require(isinstance(groups,list) and all(isinstance(g,dict) for g in groups),'GROUPS_INVALID');names={g['display'] for g in groups if isinstance(g.get('display'),str)};require('admins' not in names,'WRITER_ADMIN_GROUP')
  return {'principal_id':PID,'application_id':PRINCIPAL,'observed_groups':sorted(names),'implicit_or_unlisted_group_membership':'not_established'}
 def observe(self,target):
  direct,effective=paths(target)
  if target[0]=='warehouse':return {'direct':self.call('GET',direct),'effective':None}
  return {'direct':self.call('GET',direct,params={'max_results':150}),'effective':self.call('GET',effective,params={'max_results':150})}
 def run(self):
  identity=self.identity();ip=self.state/'identity.json'
  if ip.exists():require(safe_json(ip)==identity,'GROUP_OR_IDENTITY_DRIFT')
  else:_write_new(ip,identity)
  groups=set(identity['observed_groups']);out=[]
  for target in TARGETS:
   kind,name,required=target;folder=self.state/kind;folder.mkdir(exist_ok=True);bp=folder/'before.json'
   if bp.exists():before=safe_json(bp)
   else:
    before=self.observe(target);delta(target,before,groups);_write_new(bp,before)
   change=delta(target,before,groups)
   if change is None:
    current=self.observe(target);require(delta(target,current,groups) is None,'EXISTING_PERMISSION_LOST')
    preservation=preserved(before['direct'],current['direct'],warehouse=kind=='warehouse')
    out.append({'kind':kind,'status':'available_without_patch','availability':'direct_or_explicitly_observed_group','preservation':preservation});continue
   path=paths(target)[0]
   def readback():
    current=self.observe(target)
    if kind=='warehouse':
     direct_levels=levels(current['direct'],set());complete=set(required)<=direct_levels
    else:
     direct_priv=privileges(current['direct'],{PRINCIPAL},unknown=True)
     effective_priv=privileges(current['effective'],{PRINCIPAL,PID}|groups,unknown=True)
     require((direct_priv|effective_priv)<=set(required)|{'BROWSE'},'EXCESS_WRITER_UC_PRIVILEGE');complete=set(required)<=direct_priv
    if complete:
     preservation=preserved(before['direct'],current['direct'],warehouse=kind=='warehouse')
     if kind!='warehouse':uc_rows(current['direct'],unknown=False)
     return {'resource':name,'direct_required_permissions_observed':True,'preservation':preservation,'direct':current['direct'],'effective':current['effective'],'effective_is_empty_unknown':current['effective']=={}}
    # A mutation uses the exact observed baseline; drift requires independent review.
    require(canonical(current)==canonical(before),'PRE_PATCH_PERMISSION_DRIFT');return None
   step={'step_id':'set_job_acl','operation':'writer_grants117_'+kind,'payload':{'path':path,'body':change},'precondition':'fresh pinned identity; no pagination/excess; original visible entries preserved'}
   result=step_once(folder,step,authorize=self.authorize,observe=readback,effect=lambda payload:self.call('PATCH',payload['path'],body=payload['body']))
   require(result['status']=='confirmed_by_readback','GRANT_RECONCILIATION_REQUIRED');out.append({'kind':kind,'status':'direct_grants_verified','readback':result['observation']})
  require(self.identity()==identity,'FINAL_IDENTITY_DRIFT')
  result={'status':'writer_grants_metadata_verified','principal':PRINCIPAL,'resources':out,'budget':safe_json(self.state/'budget.json'),'volume_scope':'entire existing release_artifacts UC Volume, not just bootstrap prefix','control_table':'unchanged; SELECT/MODIFY already106','app_reader_acl':'unchanged','runtime_identity_verified':False,'job_run':False,'sql':0,'cloud_acceptance':False,'cost':None};atomic(self.state/'result.json',result);return result

def preflight(root):
 prior=safe_json(Path(root)/'runs/sk08-sk11-writer-access-116.json');require(prior.get('principal')==PRINCIPAL and prior.get('http_calls')==4,'BASELINE116_INVALID')
 return {'status':'offline_preflight_passed','targets':TARGETS,'limits':LIMITS,'files':review_inputs(root),'volume_scope':'whole release_artifacts Volume','cloud_executed':False,'cost':None}

def main():
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path.cwd());p.add_argument('--execute',action='store_true');p.add_argument('--review-file',type=Path);p.add_argument('--journal',type=Path);p.add_argument('--profile');a=p.parse_args()
 if not a.execute:print(json.dumps(preflight(a.root)));return
 require(a.review_file is not None and a.journal is not None,'REVIEW_AND_JOURNAL_REQUIRED');preflight(a.root);review=safe_json(a.review_file);a.journal.mkdir(parents=True,exist_ok=True)
 with exclusive_lock(a.journal):
  executor=WriterGrants(a.root,a.journal,review,profile=a.profile)
  try:print(json.dumps(executor.run()))
  finally:executor.session.close()
if __name__=='__main__':main()
