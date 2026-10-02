import unittest
from sbs.operations.policy_binding_146 import trusted_job_acl,trusted_notebook_acl
from sbs.operations.provision_106 import OWNER,PRINCIPAL
class Policy130(unittest.TestCase):
 def test_job_acl_rejects_untrusted_runner(self):
  acl={'object_id':'/jobs/9','access_control_list':[{'user_name':'other','all_permissions':[{'permission_level':'CAN_MANAGE_RUN'}]}]}
  with self.assertRaises(ValueError):trusted_job_acl(acl,9)
 def test_notebook_acl_rejects_writer_edit(self):
  acl={'object_id':'/notebooks/8','access_control_list':[{'service_principal_name':PRINCIPAL,'all_permissions':[{'permission_level':'CAN_EDIT'}]}]}
  with self.assertRaises(ValueError):trusted_notebook_acl(acl,8)
if __name__=='__main__':unittest.main()

class ConcretePolicy130(unittest.TestCase):
 def test_policy_issued_only_after_fresh_checks_two_writes_resume_unchanged(self):
  from pathlib import Path
  from types import SimpleNamespace
  import tempfile,json,time,base64
  from sbs.operations.policy_binding_146 import PolicyBinder130,ROOT,review_inputs,LIMITS,POLICY_TTL_MS,prior_observation,HOST,WAREHOUSE,TABLE,VOLUME,PREFIX
  from sbs.operations.job_recovery_126 import original
  _,nb=prior_observation(ROOT,'notebook_bootstrap118');_,table=prior_observation(ROOT,'table')
  source_intent=next((ROOT/'deployment/state/provision106/notebook_bootstrap118').glob('*.intent.json'))
  source=base64.b64decode(json.loads(source_intent.read_bytes())['step']['payload']['content'])
  package=json.loads((ROOT/'runs/sk12-writer-portable-105.json').read_bytes())
  archive_path=PREFIX+'/bootstrap106/'+package['archive_sha256']+'/code.tar.gz'
  payload=original(ROOT)[2]
  class Http:
   adapters={}
   def __init__(self):self.calls=[];self.files={archive_path:(ROOT/package['archive']).read_bytes()};self.source=source
   def request(self,method,url,**kwargs):
    path=url.split(HOST,1)[1];params=kwargs.get('params') or {};body=kwargs.get('json');self.calls.append((method,path));status=200;value={};raw=None
    if path.endswith('/Me'):value={'id':'76826984571984','userName':OWNER,'active':True}
    elif '/ServicePrincipals/' in path:value={'id':'72803555975940','applicationId':PRINCIPAL,'active':True}
    elif path.endswith('/jobs/list'):value={'jobs':[{'job_id':901}]}
    elif path.endswith('/jobs/get'):value={'job_id':901,'run_as_user_name':PRINCIPAL,'settings':json.loads((ROOT/'runs/sk11-job-settings-146.json').read_bytes())['settings']}
    elif '/permissions/jobs/' in path:value={'object_id':'/jobs/901','access_control_list':[{'user_name':OWNER,'all_permissions':[{'permission_level':'IS_OWNER'}]},{'service_principal_name':PRINCIPAL,'all_permissions':[{'permission_level':'CAN_MANAGE_RUN'}]}]}
    elif '/tables/' in path:value={'full_name':TABLE,'table_id':table['table_id'],'table_type':'MANAGED','data_source_format':'DELTA','owner':OWNER,'properties':{'delta.isolationLevel':'Serializable'},'columns':[{'name':n,'type_name':t,'nullable':False} for n,t in [('control_id','STRING'),('revision','LONG'),('state_json','STRING')]]}
    elif '/volumes/' in path:value={'full_name':VOLUME}
    elif '/warehouses/' in path:value={'id':WAREHOUSE,'state':'STOPPED'}
    elif path.endswith('/workspace/get-status'):value={'path':nb['path'],'object_id':nb['object_id'],'object_type':'NOTEBOOK'}
    elif '/permissions/notebooks/' in path:value={'object_id':'/notebooks/'+str(nb['object_id']),'access_control_list':[{'user_name':OWNER,'all_permissions':[{'permission_level':'CAN_MANAGE'}]},{'service_principal_name':PRINCIPAL,'all_permissions':[{'permission_level':'CAN_READ'}]}]}
    elif path.endswith('/workspace/export'):value={'content':base64.b64encode(self.source).decode()}
    elif path.endswith('/workspace/import'):self.source=base64.b64decode(body['content'])
    elif '/fs/files/' in path:
     file_path=path[len('/api/2.0/fs/files'):]
     if method=='PUT':self.files[file_path]=kwargs['data'].read()
     elif file_path not in self.files:status=404;value={'error_code':'RESOURCE_DOES_NOT_EXIST'}
     else:raw=self.files[file_path]
    else:raise AssertionError((method,path))
    raw=raw if raw is not None else json.dumps(value).encode()
    return SimpleNamespace(status_code=status,headers={'content-length':str(len(raw)),'x-databricks-request-id':'fixture130'},raw=SimpleNamespace(read=lambda *a,**k:raw),close=lambda:None)
  with tempfile.TemporaryDirectory() as tmp:
   state=Path(tmp).resolve();now=int(time.time()*1000)
   review={'approved':True,'scope':'policy_binding146','issued_at_ms':now-1000,'expires_at_ms':now+600000,'limits':LIMITS,'policy_ttl_ms':POLICY_TTL_MS,'files':review_inputs(ROOT)}
   old={p:p.read_bytes() for p in (ROOT/'deployment/state/provision106').rglob('*.json')}
   session=Http();cfg=SimpleNamespace(host='https://'+HOST,workspace_id=None,authenticate=lambda:{})
   runner=PolicyBinder130(ROOT,state,review,config_factory=lambda:cfg,session=session,clock=lambda:now)
   self.assertFalse((state/'policy146.json').exists())
   result=runner.run()
   self.assertEqual(result['policy_issued_at_ms'],now);self.assertEqual(result['policy_expires_at_ms'],now+POLICY_TTL_MS)
   self.assertTrue(result['job_settings_unchanged']);self.assertEqual(result['budget']['writes'],2);self.assertFalse(result['job_run'])
   self.assertEqual({p:p.read_bytes() for p in old},old)
   policy=(state/'policy146.json').read_bytes()
   second=PolicyBinder130(ROOT,state,review,config_factory=lambda:cfg,session=session,clock=lambda:now+1000).run()
   self.assertEqual((state/'policy146.json').read_bytes(),policy);self.assertEqual(second['budget']['writes'],2)
   self.assertEqual(sum(m!='GET' for m,_ in session.calls),2)
   self.assertFalse(any('/jobs/create' in p or '/run-now' in p or '/sql/statements' in p or '/start' in p for _,p in session.calls))
   print('fixture130_budget',result['budget'],second['budget'])
 def test_auth_failure_emits_no_policy(self):
  from pathlib import Path
  from types import SimpleNamespace
  import tempfile,time
  from sbs.operations.policy_binding_146 import PolicyBinder130,ROOT,review_inputs,LIMITS,POLICY_TTL_MS,HOST
  with tempfile.TemporaryDirectory() as tmp:
   state=Path(tmp).resolve();now=int(time.time()*1000)
   review={'approved':True,'scope':'policy_binding146','issued_at_ms':now-1000,'expires_at_ms':now+600000,'limits':LIMITS,'policy_ttl_ms':POLICY_TTL_MS,'files':review_inputs(ROOT)}
   def fail():raise ValueError('AUTH_FIXTURE_FAILURE')
   session=SimpleNamespace(adapters={},request=lambda *a,**k:self.fail('network request'))
   cfg=SimpleNamespace(host='https://'+HOST,workspace_id=None,authenticate=fail)
   runner=PolicyBinder130(ROOT,state,review,config_factory=lambda:cfg,session=session)
   with self.assertRaisesRegex(ValueError,'AUTH_FIXTURE_FAILURE'):runner.run()
   self.assertFalse((state/'policy146.json').exists())
