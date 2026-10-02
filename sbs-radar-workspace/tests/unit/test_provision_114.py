import unittest,tempfile,json
from pathlib import Path
from types import SimpleNamespace
from sbs.operations.provision_106 import ScopedApi,RemoteError,HOST,PREFIX
from sbs.operations.provision_114 import Head404Api
class Head114(unittest.TestCase):
 def adapter(self,status,directory,journal):
  self.sent=[]
  def request(*args,**kwargs):
   self.sent.append(args)
   return SimpleNamespace(status_code=status,headers={},raw=SimpleNamespace(read=lambda *a,**kw:b''),close=lambda:None)
  session=SimpleNamespace(adapters={},request=request)
  original=ScopedApi(SimpleNamespace(host='https://'+HOST,authenticate=lambda:{},workspace_id=None),journal=journal,authorize=lambda:None,prefix=directory,session=session)
  return Head404Api(original,expected_directory=directory)
 def test_head404_empty_body_absent_once_same_budget(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d).resolve();directory=PREFIX+'/bootstrap106/'+'a'*64;adapter=self.adapter(404,directory,root)
   with self.assertRaises(RemoteError) as caught:adapter.do('HEAD','/api/2.0/fs/directories'+directory)
   self.assertEqual(caught.exception.code,'RESOURCE_DOES_NOT_EXIST');self.assertEqual(caught.exception.status,404)
   self.assertEqual(len(self.sent),1);self.assertEqual(json.loads((root/'budget.json').read_bytes()),{'http':1,'sql':0,'mutations':0})
 def test_head403_is_not_absence(self):
  with tempfile.TemporaryDirectory() as d:
   directory=PREFIX+'/bootstrap106/'+'a'*64;adapter=self.adapter(403,directory,Path(d).resolve())
   with self.assertRaises(RemoteError) as caught:adapter.do('HEAD','/api/2.0/fs/directories'+directory)
   self.assertEqual(caught.exception.status,403);self.assertEqual(caught.exception.code,'UNCLASSIFIED')
 def test_other_method_and_path_not_normalized(self):
  original=SimpleNamespace(do=lambda *a,**k:(_ for _ in ()).throw(RemoteError(404,'UNCLASSIFIED')))
  adapter=Head404Api(original,expected_directory='/Volumes/fixed')
  for method,path in [('GET','/api/2.0/fs/directories/Volumes/fixed'),('HEAD','/api/2.0/fs/directories/Volumes/other')]:
   with self.assertRaises(RemoteError) as caught:adapter.do(method,path)
   self.assertEqual(caught.exception.code,'UNCLASSIFIED')
if __name__=='__main__':unittest.main()

class Resume114(unittest.TestCase):
 def test_concrete_resume_keeps_prior_effects_and_policy(self):
  import time
  from test_provision_106_sdk import MemoryHttp,ROOT
  from sbs.operations.provision_106 import Provisioner,review_inputs,LIMITS
  from sbs.operations.provision_114 import Provisioner114,patch_inputs
  class EmptyHeadHttp(MemoryHttp):
   def request(self,method,url,**kwargs):
    response=super().request(method,url,**kwargs)
    if method=='HEAD' and response.status_code==404:
     response.raw=SimpleNamespace(read=lambda *a,**kw:b'');response.headers={}
    return response
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp).resolve();now=int(time.time()*1000)
   review={'approved':True,'scope':'provision106','issued_at_ms':now-1000,'expires_at_ms':now+300000,'writer_mode':'execute','limits':LIMITS,'files':review_inputs(ROOT)}
   patch={**review,'scope':'provision114_head404','files':patch_inputs(ROOT)}
   session=EmptyHeadHttp();cfg=SimpleNamespace(host='https://'+HOST,workspace_id=None,authenticate=lambda:{})
   with self.assertRaises(RemoteError):Provisioner(ROOT,root,review,writer_mode='execute',config_factory=lambda:cfg,session=session).run()
   prior={str(p.relative_to(root)):p.read_bytes() for stage in ('table','seed','control_acl') for p in (root/stage).glob('*.json')}
   prior['policy.json']=(root/'policy.json').read_bytes()
   before=json.loads((root/'budget.json').read_bytes());self.assertEqual(before['mutations'],3)
   result=Provisioner114(ROOT,root,review,patch,writer_mode='execute',config_factory=lambda:cfg,session=session).run()
   self.assertEqual(result['status'],'provisioned_paused_not_run')
   self.assertEqual({p:(root/p).read_bytes() for p in prior},prior)
   from sbs.operations.provision_105 import control_steps
   for sql in [s['payload']['statement'] for s in control_steps()]:self.assertEqual(sum(bool(b) and b.get('statement')==sql for _,_,b in session.calls),1)
   after=json.loads((root/'budget.json').read_bytes());self.assertGreater(after['http'],before['http']);self.assertEqual(after['mutations'],11)
   print('fixture_only_resume114_budget',before,after)
