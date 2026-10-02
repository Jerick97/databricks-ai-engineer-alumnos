import unittest
from sbs.operations.job_recovery_143 import serialize_create,policy_settings_unchanged
class Recovery126(unittest.TestCase):
 def test_original_sdk_serialization_is_exact(self):
  payload,wire=serialize_create()
  self.assertEqual(payload,wire['body']);self.assertEqual(wire['path'],'/api/2.2/jobs/create')
 def test_fresh_policy_does_not_change_jobs_payload(self):
  self.assertTrue(policy_settings_unchanged()['settings_identical'])
if __name__=='__main__':unittest.main()

class Concrete126(unittest.TestCase):
 def exercise(self,mode):
  from pathlib import Path
  from types import SimpleNamespace
  import tempfile,time,json
  from sbs.operations.job_recovery_143 import ROOT,JobRecovery143,review_inputs,LIMITS,HOST,OWNER,OWNER_ID,PRINCIPAL,RULE_NAME,original
  payload=original(ROOT)[2]
  class Http:
   adapters={}
   def __init__(self):self.created=False;self.calls=[]
   def request(self,method,url,**kwargs):
    path=url.split(HOST,1)[1];self.calls.append((method,path));status=200;body={};raw=None
    if path.endswith('/Me'):body={'id':OWNER_ID,'userName':OWNER,'active':True}
    elif '/ServicePrincipals/' in path:body={'id':'72803555975940','applicationId':PRINCIPAL,'active':True}
    elif path.endswith('/rule-sets'):body={'name':RULE_NAME,'grant_rules':[{'role':('roles/servicePrincipal.manager' if mode=='missing_role' else 'roles/servicePrincipal.user'),'principals':['users/'+OWNER]}]}
    elif path.endswith('/jobs/list'):body={'jobs':[{'job_id':901},{'job_id':902}]} if mode=='duplicates' else ({'jobs':[{'job_id':901}]} if self.created else {})
    elif path.endswith('/jobs/create'):
     if mode=='reject':status=403;body={'error_code':'PERMISSION_DENIED','message':'fixture missing permission; no production causal claim'}
     else:self.created=True;raw=b'not-json'
    elif path.endswith('/jobs/get'):body={'job_id':901,'run_as_user_name':PRINCIPAL,'settings':{k:v for k,v in payload.items() if k!='access_control_list'}}
    elif '/permissions/jobs/' in path:body={'object_id':'/jobs/901','access_control_list':[{'user_name':OWNER,'all_permissions':[{'permission_level':'IS_OWNER'}]},{'service_principal_name':PRINCIPAL,'all_permissions':[{'permission_level':'CAN_MANAGE_RUN'}]}]}
    else:raise AssertionError(path)
    raw=raw if raw is not None else json.dumps(body).encode()
    return SimpleNamespace(status_code=status,headers={'x-databricks-request-id':'fixture-request-126'},raw=SimpleNamespace(read=lambda *a,**k:raw),close=lambda:None)
  with tempfile.TemporaryDirectory() as tmp:
   state=Path(tmp).resolve();now=int(time.time()*1000)
   review={'approved':True,'scope':'job_recovery143_after_user_role','issued_at_ms':now-1000,'expires_at_ms':now+600000,'limits':LIMITS,'files':review_inputs(ROOT)}
   http=Http();cfg=SimpleNamespace(host='https://'+HOST,workspace_id=None,authenticate=lambda:{})
   before={p:p.read_bytes() for folder in ('provision106','job-recovery126') for p in (ROOT/'deployment/state'/folder).rglob('*.json')}
   if mode=='missing_role':
    with self.assertRaisesRegex(ValueError,'FRESH_OWNER_USER_ROLE_REQUIRED'):JobRecovery143(ROOT,state,review,config_factory=lambda:cfg,session=http).run()
    self.assertFalse(any(m=='POST' for m,_ in http.calls));return
   result=JobRecovery143(ROOT,state,review,config_factory=lambda:cfg,session=http).run()
   resumed=JobRecovery143(ROOT,state,review,config_factory=lambda:cfg,session=http).run()
   self.assertEqual({p:p.read_bytes() for p in before},before)
   expected_posts=0 if mode=='duplicates' else 1
   self.assertEqual(sum(m=='POST' for m,_ in http.calls),expected_posts)
   self.assertTrue(all(m in ('GET','POST') for m,_ in http.calls))
   if mode=='reject':
    errors=[json.loads(p.read_bytes()) for p in state.glob('*-error.json')]
    self.assertEqual(errors[0]['http_status'],403);self.assertEqual(errors[0]['error_code'],'PERMISSION_DENIED');self.assertEqual(errors[0]['request_ids']['x-databricks-request-id'],'fixture-request-126')
    self.assertEqual(resumed['recovery_attempt'],'prior_recovery_intent_readback_only')
   elif mode=='duplicates':
    self.assertEqual(result['status'],'duplicates_observed_no_run');self.assertEqual(result['observation']['candidate_ids'],[901,902]);self.assertFalse((state/'create-intent.json').exists())
   else:
    self.assertEqual(result['status'],'job_observed_paused');self.assertEqual(result['recovery_attempt'],'RECOVERY_JSON_INVALID');self.assertEqual(result['original_attempt_outcome'],'unknown_preserved')
    receipts=[json.loads(p.read_bytes()) for p in state.glob('*-response.json')]
    post=next(r for r in receipts if r['method']=='POST');self.assertEqual(post['http_status'],200);self.assertTrue(post['sdk_interpretation_not_yet_performed'])
 def test_rejected_post_captured_and_never_resent(self):self.exercise('reject')
 def test_invalid_response_json_reconciles_real_get_binding(self):self.exercise('invalid_json')
 def test_duplicates_no_post_no_run(self):self.exercise('duplicates')

 def test_missing_fresh_role_no_post(self):self.exercise('missing_role')
