import unittest
from sbs.guardrails.writer_grants_117 import uc_rows,privileges,preserved,delta,TARGETS,PRINCIPAL
class Grants117(unittest.TestCase):
 def test_unknown_before_does_not_allow_unknown_after(self):
  self.assertEqual(uc_rows({},unknown=True),[])
  with self.assertRaises(ValueError):uc_rows({},unknown=False)
 def test_pagination_blocks(self):
  with self.assertRaises(ValueError):uc_rows({'privilege_assignments':[],'next_page_token':'more'},unknown=True)
 def test_delta_adds_only_missing_writer_privileges(self):
  target=TARGETS[2]
  before={'direct':{'privilege_assignments':[{'principal':PRINCIPAL,'privileges':['READ_VOLUME']}]},'effective':{}}
  body=delta(target,before,set())
  self.assertEqual(body,{'changes':[{'principal':PRINCIPAL,'add':['WRITE_VOLUME']}]})
 def test_preservation_rejects_other_entry_loss(self):
  before={'privilege_assignments':[{'principal':'other','privileges':['READ_VOLUME']}]}
  with self.assertRaises(ValueError):preserved(before,{'privilege_assignments':[]},warehouse=False)
if __name__=='__main__':unittest.main()

class ConcreteWriter117(unittest.TestCase):
 def test_four_minimal_patches_preserve_others_and_resume_without_resend(self):
  from pathlib import Path
  from types import SimpleNamespace
  import tempfile,json,time
  from sbs.guardrails.writer_grants_117 import WriterGrants,review_inputs,LIMITS,HOST,OWNER,OWNER_ID,PID,paths
  root=Path(__file__).resolve().parents[2]
  class Http:
   adapters={}
   def __init__(self):self.calls=[];self.granted={}
   def request(self,method,url,**kw):
    path=url.split(HOST,1)[1];body=kw.get('json');self.calls.append((method,path,body))
    if path.endswith('/Me'):response={'id':OWNER_ID,'userName':OWNER,'active':True}
    elif '/ServicePrincipals/' in path:response={'id':PID,'applicationId':PRINCIPAL,'active':True,'groups':[]}
    else:
     target=next(t for t in TARGETS if path in paths(t));kind,name,required=target
     if method=='PATCH':self.granted[kind]=True
     if kind=='warehouse':response={'object_id':'/sql/warehouses/'+name,'object_type':'warehouses','access_control_list':[{'user_name':'untouched-owner','all_permissions':[{'permission_level':'IS_OWNER','inherited':False}]}]+([{'service_principal_name':PRINCIPAL,'all_permissions':[{'permission_level':'CAN_USE','inherited':False}]}] if self.granted.get(kind) else [])}
     elif kind=='catalog' and not self.granted.get(kind):response={}
     else:response={'privilege_assignments':[{'principal':'untouched-app','privileges':[required[0]]}]+([{'principal':PRINCIPAL,'privileges':list(required)}] if self.granted.get(kind) else [])}
    raw=json.dumps(response).encode();return SimpleNamespace(status_code=200,raw=SimpleNamespace(read=lambda *a,**k:raw),close=lambda:None)
   def close(self):pass
  with tempfile.TemporaryDirectory() as tmp:
   journal=Path(tmp).resolve();now=int(time.time()*1000);review={'approved':True,'scope':'writer_grants117','issued_at_ms':now-1000,'expires_at_ms':now+600000,'limits':LIMITS,'files':review_inputs(root)}
   http=Http();cfg=SimpleNamespace(host='https://'+HOST,authenticate=lambda:{})
   result=WriterGrants(root,journal,review,config_factory=lambda:cfg,session=http).run()
   self.assertEqual(result['status'],'writer_grants_metadata_verified');self.assertEqual(sum(m=='PATCH' for m,_,_ in http.calls),4)
   first=json.loads((journal/'budget.json').read_bytes())
   again=WriterGrants(root,journal,review,config_factory=lambda:cfg,session=http).run()
   self.assertEqual(again['status'],'writer_grants_metadata_verified');self.assertEqual(sum(m=='PATCH' for m,_,_ in http.calls),4)
   self.assertTrue(all(m in ('GET','PATCH') for m,_,_ in http.calls))
   print('fixture_writer117_cumulative',first,json.loads((journal/'budget.json').read_bytes()))
 def test_ambiguous_patch_is_only_reconciled(self):
  from pathlib import Path
  import tempfile
  from sbs.operations.provision_105 import step_once
  with tempfile.TemporaryDirectory() as tmp:
   step={'step_id':'set_job_acl','operation':'writer_grants117_catalog','payload':{'changes':[{'principal':PRINCIPAL,'add':['USE_CATALOG']}]},'precondition':'reviewed'};calls=[]
   def fail(_):calls.append(1);raise TimeoutError()
   for _ in range(2):self.assertEqual(step_once(Path(tmp).resolve(),step,authorize=lambda:None,observe=lambda:None,effect=fail)['status'],'outcome_unknown')
   self.assertEqual(calls,[1])
