import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from sbs.operations.dispatch_146 import BoundedSession142,RunApi142
class Dispatch142(unittest.TestCase):
 def fixture(self,path):
  class Session:
   adapters={}
   calls=[]
   def request(self,*a,**k):
    self.calls.append((a,k));return SimpleNamespace(status_code=200,headers={},raw=SimpleNamespace(read=lambda *a,**k:b'{"run_id":7}'),close=lambda:None)
  config=SimpleNamespace(writer=SimpleNamespace(job_id=5,release_id='a'*64),control_table='catalog.sbs_radar.refresh_control',warehouse_id='wh')
  return BoundedSession142(Session(),path,config,'req',lambda:None)
 def test_run_scope_and_durable_no_second_attempt(self):
  with tempfile.TemporaryDirectory() as d:
   state=Path(d).resolve();s=self.fixture(state)
   bad=dict(s.expected);bad['job_id']=6
   with self.assertRaises(ValueError):s.request('POST',s.host+'/api/2.2/jobs/run-now',json=bad)
   self.assertFalse((state/'budget.json').exists())
   s.request('POST',s.host+'/api/2.2/jobs/run-now',json=s.expected)
   with self.assertRaises(ValueError):self.fixture(state).request('POST',s.host+'/api/2.2/jobs/run-now',json=s.expected)
   self.assertEqual(json.loads((state/'budget.json').read_text())['run_now'],1)
 def test_forbidden_mutations_and_wrong_host(self):
  with tempfile.TemporaryDirectory() as d:
   s=self.fixture(Path(d).resolve())
   for method,url in [('PUT',s.host+'/api/2.0/fs/files/Volumes/x'),('POST',s.host+'/api/2.2/jobs/create'),('GET','https://wrong.example/api/2.2/jobs/get')]:
    with self.assertRaises(ValueError):s.request(method,url,json={})
   with self.assertRaises(ValueError):s.request('POST',s.host+'/api/2.0/sql/statements',json={'warehouse_id':'wh','statement':'DROP TABLE catalog.sbs_radar.refresh_control'})
 def test_expired_before_reservation_and_send(self):
  with tempfile.TemporaryDirectory() as d:
   s=self.fixture(Path(d).resolve());s.authorize=lambda:(_ for _ in ()).throw(ValueError('expired'))
   with self.assertRaisesRegex(ValueError,'expired'):s.request('GET',s.host+'/api/2.2/jobs/get')
   self.assertFalse((Path(d)/'budget.json').exists())
 def test_generated_jobs_api_uses_exact_one_run_body(self):
  from databricks.sdk.service.jobs import JobsAPI,QueueSettings
  with tempfile.TemporaryDirectory() as d:
   s=self.fixture(Path(d).resolve());cfg=SimpleNamespace(host=s.host,authenticate=lambda:{},workspace_id=None)
   api=RunApi142(SimpleNamespace(_cfg=cfg,session=s))
   result=JobsAPI(api).run_now(job_id=5,idempotency_token=s.expected['idempotency_token'],job_parameters=s.expected['job_parameters'],queue=QueueSettings(enabled=True))
   self.assertEqual(result.response.run_id,7)
   self.assertEqual(s.session.calls[-1][1]['json'],s.expected)
