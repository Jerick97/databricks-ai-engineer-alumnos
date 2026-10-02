import unittest,tempfile,time,json
from pathlib import Path
from types import SimpleNamespace
from sbs.operations import writer_monitor_156 as p
class Monitor156(unittest.TestCase):
 def test_real_receipt_scope_fixture_output_once_resume_no_acceptance(self):
  bind=p.binding()
  class Http:
   adapters={}
   def __init__(self):self.outputs=0
   def request(self,m,url,**kw):
    assert m=='GET'
    if url.endswith(p.ME):v={'id':p.OWNER_ID,'userName':p.OWNER,'active':True}
    elif url.endswith(p.RUN):
     assert kw['params']['run_id']==bind['run_id'];v={'job_id':bind['job_id'],'run_id':bind['run_id'],'state':{'life_cycle_state':'TERMINATED','result_state':'SUCCESS'},'tasks':[{'task_key':'refresh','run_id':777}]}
    else:
     assert url.endswith(p.OUTPUT) and kw['params']['run_id']==777;self.outputs+=1;v={'notebook_output':{'result':json.dumps({'status':'published','evidence_mode':'real','cloud_acceptance':False}),'truncated':False}}
    raw=json.dumps(v).encode();return SimpleNamespace(status_code=200,headers={},raw=SimpleNamespace(read=lambda *a,**k:raw),close=lambda:None)
  with tempfile.TemporaryDirectory() as d:
   now=int(time.time()*1000);review={'approved':True,'scope':'writer_monitor156_read_only','issued_at_ms':now-1000,'expires_at_ms':now+600000,'limits':p.LIMITS,'files':p.inputs()};cfg=SimpleNamespace(host='https://'+p.HOST,authenticate=lambda:{})
   state=Path(d).resolve();session=Http();run=lambda:p.Monitor156(p.ROOT,state,review,config_factory=lambda:cfg,session=session,sleep=lambda _:None).run()
   result=run();self.assertFalse(result['success_accepted']);self.assertFalse(result['output_check']['output_validated']);self.assertTrue(result['output_check']['output_contract_matches']);run();self.assertEqual(session.outputs,1)
   runner=p.Monitor156(p.ROOT,state,review,config_factory=lambda:cfg,session=session,sleep=lambda _:None)
   with self.assertRaisesRegex(ValueError,'MONITOR_SCOPE'):runner.call(p.RUN,{'run_id':1,'include_resolved_values':True})
   (state/'budget.json').write_text('{"get":20}')
   with self.assertRaisesRegex(ValueError,'MONITOR_BUDGET_EXHAUSTED'):runner.run()
 def test_success_without_output_never_validated(self):
  self.assertFalse(p.output_validation({})['output_validated'])
  self.assertFalse(p.output_validation({'notebook_output':{'result':'{}','truncated':True}})['output_validated'])
