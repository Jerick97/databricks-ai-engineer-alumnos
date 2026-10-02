import unittest,tempfile,time,json,copy
from pathlib import Path
from types import SimpleNamespace
from sbs.operations import job_reconcile_146 as p
class Reconcile146(unittest.TestCase):
 def test_actual_job_readback_no_post_and_raw_saved(self):
  job=json.loads((p.ROOT/'runs/sk11-job-settings-146.json').read_bytes());jid=job['job_id']
  class Http:
   adapters={}
   def request(self,m,url,**kw):
    assert m=='GET';path=url.split(p.HOST)[1]
    if path.endswith('/Me'):v={'id':p.OWNER_ID,'userName':p.OWNER,'active':True}
    elif '/ServicePrincipals/' in path:v={'id':'72803555975940','applicationId':p.PRINCIPAL,'active':True}
    elif path==p.RULE_PATH:v={'name':p.RULE_NAME,'etag':'fresh','grant_rules':[{'role':'roles/servicePrincipal.user','principals':['users/'+p.OWNER]}]}
    elif path.endswith('/jobs/list'):v={'jobs':[{'job_id':jid}]}
    elif path.endswith('/jobs/get'):v=job
    elif '/permissions/jobs/' in path:v={'object_id':'/jobs/'+str(jid),'access_control_list':[{'user_name':p.OWNER,'all_permissions':[{'permission_level':'IS_OWNER'}]}]}
    else:raise AssertionError(path)
    raw=json.dumps(v).encode();return SimpleNamespace(status_code=200,headers={},raw=SimpleNamespace(read=lambda *a,**k:raw),close=lambda:None)
  with tempfile.TemporaryDirectory() as d:
   state=Path(d).resolve();now=int(time.time()*1000);review={'approved':True,'scope':'job_reconcile146_read_only','issued_at_ms':now-1000,'expires_at_ms':now+600000,'limits':p.LIMITS,'files':p.review_inputs()}
   cfg=SimpleNamespace(host='https://'+p.HOST,workspace_id=None,authenticate=lambda:{})
   result=p.JobRecovery143(p.ROOT,state,review,config_factory=lambda:cfg,session=Http()).run()
   self.assertEqual(result['job_id'],jid);self.assertEqual(result['budget']['create_post'],0);self.assertFalse((state/'create-intent.json').exists())
   evidence=[json.loads(x.read_bytes()) for x in state.glob('metadata146-*')];self.assertEqual(evidence[0]['raw'],job)
   self.assertFalse((state/'reconciliation.json').exists())
