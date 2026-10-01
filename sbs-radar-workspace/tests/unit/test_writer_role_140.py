import unittest,tempfile,time,json,copy
from pathlib import Path
from types import SimpleNamespace
from sbs.operations import writer_role_140 as p
class Role140(unittest.TestCase):
 def test_preserve_fresh_grants_and_etag_sdk_put_resume(self):
  original={'name':p.RULE_NAME,'etag':'fresh','grant_rules':[{'role':'roles/servicePrincipal.manager','principals':['users/'+p.OWNER,'groups/other']},{'role':p.ROLE,'principals':['users/other']}]}
  class Http:
   adapters={}
   def __init__(self):self.rules=copy.deepcopy(original);self.puts=0
   def request(self,m,url,**kw):
    path=url.split(p.HOST)[1]
    if path.endswith('/Me'):v={'id':p.OWNER_ID,'userName':p.OWNER,'active':True}
    elif '/ServicePrincipals/' in path:v={'id':'72803555975940','applicationId':p.PRINCIPAL,'active':True}
    elif path==p.RULE_PATH and m=='GET':v=self.rules
    elif path==p.RULE_PATH and m=='PUT':
     assert kw['json']==p.proposal(original);self.puts+=1;self.rules={'name':p.RULE_NAME,**kw['json']['rule_set'],'etag':'new'};v=self.rules
    else:raise AssertionError((m,path))
    raw=json.dumps(v).encode();return SimpleNamespace(status_code=200,headers={},raw=SimpleNamespace(read=lambda *a,**k:raw),close=lambda:None)
  with tempfile.TemporaryDirectory() as tmp:
   now=int(time.time()*1000);review={'approved':True,'scope':'writer_role140_user_only','issued_at_ms':now-1000,'expires_at_ms':now+600000,'files':p.review_inputs(),'limits':p.LIMITS}
   cfg=SimpleNamespace(host='https://'+p.HOST,workspace_id=None,authenticate=lambda:{})
   http=Http();state=Path(tmp)
   run=lambda:p.WriterRole140(p.ROOT,state,review,config_factory=lambda:cfg,session=http).run()
   result=run();self.assertEqual(result['budget'],{'http':5,'rule_put':1});self.assertEqual(http.puts,1)
   self.assertEqual(p.pairs(result['ruleset']),p.pairs(original)|{(p.ROLE,'users/'+p.OWNER)})
   run();self.assertEqual(http.puts,1)
 def test_existing_user_no_change(self):
  r={'name':p.RULE_NAME,'etag':'e','grant_rules':[{'role':p.ROLE,'principals':['users/'+p.OWNER]}]}
  self.assertEqual(p.proposal(r)['rule_set']['grant_rules'],r['grant_rules'])
 def test_unknown_fields_fail_closed(self):
  with self.assertRaisesRegex(ValueError,'RULESET_INVALID'):p.proposal({'name':p.RULE_NAME,'etag':'e','grant_rules':[],'unknown':1})
 def test_transport_rejects_other_mutations_and_ruleset(self):
  with tempfile.TemporaryDirectory() as tmp:
   api=p.RoleApi(SimpleNamespace(host='https://'+p.HOST),state=tmp,authorize=lambda:None,payload=None,session=SimpleNamespace(adapters={}))
   for method,path in [('POST','/api/2.2/jobs/create'),('PATCH',p.RULE_PATH),('PUT','/other')]:
    with self.assertRaisesRegex(ValueError,'API_SCOPE_INVALID'):api.do(method,path)
   with self.assertRaisesRegex(ValueError,'RULE_QUERY_INVALID'):api.do('GET',p.RULE_PATH,query={'name':'other','etag':''})
