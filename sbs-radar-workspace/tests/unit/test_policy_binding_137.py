import ast,unittest,tempfile,json,time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from sbs.operations import policy_binding_137 as p

class Regression137(unittest.TestCase):
 def test_journal_overlap_constructor_and_cli_before_mkdir(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)/'project';old=root/'deployment/state/provision106'
   for state in (old,old/'child',old.parent,root):
    with self.subTest(state=state):
     with self.assertRaisesRegex(ValueError,'JOURNAL_OVERLAP_FORBIDDEN'):
      p.PolicyBinder130(root,state,{})
     with patch('sys.argv',['binding137','--root',str(root),'--execute','--review-file',str(Path(tmp)/'missing'),'--journal',str(state)]):
      with self.assertRaisesRegex(ValueError,'JOURNAL_OVERLAP_FORBIDDEN'):p.main()
     self.assertFalse(state.exists())
 def test_resume_expiry_during_config_get_has_no_writes(self):
  tree=ast.parse((p.ROOT/'tests/unit/test_policy_binding_130.py').read_bytes())
  fn=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='test_policy_issued_only_after_fresh_checks_two_writes_resume_unchanged')
  prefix=[]
  for node in fn.body:
   if isinstance(node,ast.With):break
   prefix.append(node)
  ns={'OWNER':p.OWNER,'PRINCIPAL':p.PRINCIPAL};exec(compile(ast.fix_missing_locations(ast.Module(body=prefix,type_ignores=[])),'fixture130','exec'),ns)
  now=int(time.time()*1000);clock=[now]
  class Session(ns['Http']):
   fail_probe=True;cross_expiry=False;writes=0
   def request(self,method,url,**kwargs):
    if method=='GET' and '/driver-policy130-' in url:
     if self.fail_probe:self.fail_probe=False;raise RuntimeError('stop before intent')
     result=super().request(method,url,**kwargs)
     if self.cross_expiry:clock[0]=now+p.POLICY_TTL_MS+1
     return result
    if method!='GET':self.writes+=1
    return super().request(method,url,**kwargs)
  with tempfile.TemporaryDirectory() as tmp:
   state=Path(tmp);session=Session();cfg=SimpleNamespace(host='https://'+p.HOST,workspace_id=None,authenticate=lambda:{})
   review={'approved':True,'scope':'policy_binding130','issued_at_ms':now-1000,'expires_at_ms':now+600000,'limits':p.LIMITS,'policy_ttl_ms':p.POLICY_TTL_MS,'files':p.review_inputs(p.ROOT)}
   runner=p.PolicyBinder130(p.ROOT,state,review,config_factory=lambda:cfg,session=session,clock=lambda:clock[0])
   with self.assertRaisesRegex(ValueError,'BINDING_TRANSPORT_UNKNOWN'):runner.run()
   policy=(state/'policy130.json').read_bytes();clock[0]=now+p.POLICY_TTL_MS-1;session.cross_expiry=True
   review={**review,'issued_at_ms':clock[0]-1000,'expires_at_ms':clock[0]+600000}
   runner=p.PolicyBinder130(p.ROOT,state,review,config_factory=lambda:cfg,session=session,clock=lambda:clock[0])
   with self.assertRaisesRegex(ValueError,'NEW_POLICY_VERSION_REQUIRED'):runner.run()
   self.assertEqual(session.writes,0);self.assertEqual(policy,(state/'policy130.json').read_bytes());self.assertFalse((state/'result.json').exists())
