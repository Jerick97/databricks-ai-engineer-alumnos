import unittest
from sbs.operations.provision_118 import private_settings,validate_home_acl,PRIVATE_HOME
from sbs.operations.provision_106 import OWNER
class Private118(unittest.TestCase):
 def test_private_settings_same_paused_writer_contract(self):
  s=private_settings(notebook_path=PRIVATE_HOME+'/sbs-radar-writer118-'+'a'*16,release_id='b'*64,snapshot_backend_id='c'*64,boundary_policy_id='d'*64)
  self.assertEqual(s['schedule']['pause_status'],'PAUSED');self.assertEqual(s['tasks'][0]['notebook_task']['notebook_path'],PRIVATE_HOME+'/sbs-radar-writer118-'+'a'*16)
  self.assertNotIn('job_id',s)
 def test_home_acl_rejects_shared_writers(self):
  with self.assertRaises(ValueError):validate_home_acl({'object_id':'/directories/2571826969054457','object_type':'directory','access_control_list':[{'group_name':'users','all_permissions':[{'permission_level':'CAN_MANAGE'}]}]})
if __name__=='__main__':unittest.main()

class PrivateResume118(unittest.TestCase):
 def test_real_serializers_resume_two_failures_without_shared_acl_changes(self):
  import tempfile,time,json
  from pathlib import Path
  from types import SimpleNamespace
  from test_provision_106_sdk import MemoryHttp,ROOT
  from sbs.operations.provision_106 import Provisioner,review_inputs,LIMITS,HOST,RemoteError,PRINCIPAL
  from sbs.operations.provision_114 import Provisioner114,patch_inputs as inputs114
  from sbs.operations.provision_118 import PrivateProvisioner118,patch_inputs as inputs118,HOME_ID
  home=json.loads((ROOT/'runs/sk08-private-home-118b.json').read_bytes())
  class PrivateHttp(MemoryHttp):
   private_granted=False
   def request(self,method,url,**kwargs):
    path=url.split(HOST,1)[1];params=kwargs.get('params') or {};body=None
    if method=='GET' and path.endswith('/workspace/get-status') and params.get('path')==PRIVATE_HOME:body=home['metadata']
    elif method=='GET' and path.endswith('/permissions/directories/'+str(HOME_ID)):body=home['acl']
    elif method=='GET' and path.endswith('/workspace/get-status') and params.get('path','').startswith(PRIVATE_HOME+'/sbs-radar-writer118-') and params['path'] in self.notebooks:body={'path':params['path'],'object_id':89,'object_type':'NOTEBOOK'}
    elif path.endswith('/permissions/notebooks/88'):body={'access_control_list':[{'group_name':'users','all_permissions':[{'permission_level':'CAN_MANAGE','inherited':True}]}]}
    elif path.endswith('/permissions/notebooks/89'):
     if method=='PATCH':self.private_granted=True
     body={'access_control_list':[{'user_name':OWNER,'all_permissions':[{'permission_level':'CAN_MANAGE','inherited':False}]},{'group_name':'admins','all_permissions':[{'permission_level':'CAN_MANAGE','inherited':True}]}]+([{'service_principal_name':PRINCIPAL,'all_permissions':[{'permission_level':'CAN_READ','inherited':False}]}] if self.private_granted else [])}
    if body is not None:
     self.calls.append((method,path,kwargs.get('json')));raw=json.dumps(body).encode();return SimpleNamespace(status_code=200,headers={},raw=SimpleNamespace(read=lambda *a,**k:raw),close=lambda:None)
    response=super().request(method,url,**kwargs)
    if method=='HEAD' and response.status_code==404:response.raw=SimpleNamespace(read=lambda *a,**kw:b'');response.headers={}
    return response
  with tempfile.TemporaryDirectory() as tmp:
   state=Path(tmp).resolve();now=int(time.time()*1000)
   review={'approved':True,'scope':'provision106','issued_at_ms':now-1000,'expires_at_ms':now+600000,'writer_mode':'execute','limits':LIMITS,'files':review_inputs(ROOT)}
   review114={**review,'scope':'provision114_head404','files':inputs114(ROOT)};review118={**review,'scope':'private_writer118','files':inputs118(ROOT)}
   http=PrivateHttp();cfg=SimpleNamespace(host='https://'+HOST,workspace_id=None,authenticate=lambda:{})
   with self.assertRaises(RemoteError):Provisioner(ROOT,state,review,writer_mode='execute',config_factory=lambda:cfg,session=http).run()
   with self.assertRaisesRegex(ValueError,'UNTRUSTED_NOTEBOOK_WRITER'):Provisioner114(ROOT,state,review,review114,writer_mode='execute',config_factory=lambda:cfg,session=http).run()
   previous={str(p.relative_to(state)):p.read_bytes() for stage in ('table','seed','control_acl','bundle','notebook_bootstrap') for p in (state/stage).glob('*.json')};previous['policy.json']=(state/'policy.json').read_bytes()
   before=json.loads((state/'budget.json').read_bytes());self.assertEqual(before,{'http':45,'mutations':7,'sql':6})
   result=PrivateProvisioner118(ROOT,state,review,review118,writer_mode='execute',config_factory=lambda:cfg,session=http).run()
   self.assertEqual(result['status'],'provisioned_paused_not_run');self.assertTrue(result['notebook']['path'].startswith(PRIVATE_HOME+'/'))
   self.assertEqual({p:(state/p).read_bytes() for p in previous},previous)
   self.assertFalse(any(method=='PATCH' and path.endswith('/permissions/notebooks/88') for method,path,_ in http.calls))
   self.assertEqual(http.job['tasks'][0]['notebook_task']['notebook_path'],result['notebook']['path']);self.assertEqual(http.job['schedule']['pause_status'],'PAUSED')
   after=json.loads((state/'budget.json').read_bytes());self.assertEqual(after['mutations'],12);self.assertLessEqual(after['http'],120);self.assertLessEqual(after['sql'],12)
   import hashlib
   frozen=json.loads((ROOT/'runs/sk12-writer-code-manifest-105.json').read_bytes())
   for source in ('src/sbs/operations/cloud_dispatch.py','src/sbs/operations/cloud_driver.py'):
    self.assertEqual(hashlib.sha256((ROOT/source).read_bytes()).hexdigest(),frozen['files'][source])
   print('fixture_private118_budget',before,after)
