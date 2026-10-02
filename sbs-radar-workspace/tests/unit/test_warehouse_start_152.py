import unittest,tempfile,time,json
from pathlib import Path
from types import SimpleNamespace
from sbs.operations import warehouse_start_152 as p
class Warehouse152(unittest.TestCase):
 def exercise(self,unknown=False,stuck=False):
  class Http:
   adapters={}
   def __init__(self):self.starts=0;self.gets=0
   def request(self,m,url,**kw):
    if m=='POST':
     assert url.endswith(p.PATH+'/start');self.starts+=1
     if unknown:raise RuntimeError('unknown')
     v={}
    else:
     self.gets+=1
     v={'id':p.OWNER_ID,'userName':p.OWNER,'active':True} if url.endswith(p.ME) else {'id':p.WAREHOUSE,'state':'STOPPED' if stuck or not self.starts else 'RUNNING'}
    raw=json.dumps(v).encode();return SimpleNamespace(status_code=200,headers={},raw=SimpleNamespace(read=lambda *a,**k:raw),close=lambda:None)
  with tempfile.TemporaryDirectory() as d:
   state=Path(d).resolve();now=int(time.time()*1000);review={'approved':True,'scope':'warehouse152_one_start','issued_at_ms':now-1000,'expires_at_ms':now+600000,'limits':p.LIMITS,'files':p.inputs()};cfg=SimpleNamespace(host='https://'+p.HOST,authenticate=lambda:{})
   http=Http();run=lambda:p.WarehouseStart152(p.ROOT,state,review,config_factory=lambda:cfg,session=http,sleep=lambda _:None).run()
   result=run();self.assertEqual(http.starts,1);self.assertLessEqual(http.gets,7)
   if stuck:
    self.assertEqual(result['budget'],{'get':7,'start':1})
    with self.assertRaisesRegex(ValueError,'BUDGET_EXHAUSTED'):run()
   else:self.assertEqual(result['status'],'running_observed');run()
   self.assertEqual(http.starts,1)
 def test_start_and_resume(self):self.exercise()
 def test_unknown_not_resent_and_get_reconciles(self):self.exercise(unknown=True)
 def test_stuck_budget_cumulative(self):self.exercise(stuck=True)
