import unittest,json,copy
from pathlib import Path
from sbs.operations.job_defaults_146 import normalize_job,normalize_run,DefaultsApi146
from sbs.operations.job_recovery_143 import original,ROOT
class Defaults146(unittest.TestCase):
 def setUp(self):
  self.raw=json.loads((ROOT/'runs/sk11-job-settings-146.json').read_bytes());self.expected={k:v for k,v in original()[2].items() if k!='access_control_list'}
 def test_actual_raw_preserved_exact_projection(self):
  raw=copy.deepcopy(self.raw);out=normalize_job(raw,self.expected)
  self.assertEqual(raw,self.raw);self.assertTrue(all(out['settings'][k]==v for k,v in self.expected.items()))
 def test_defaults_values_and_unknown_and_other_task_fail(self):
  for key,value in [('disabled',0),('email_notifications',{'on_failure':['x']}),('min_retry_interval_millis',False),('retry_on_timeout',True),('run_if','ALL_DONE'),('unknown',False),('spark_python_task',{})]:
   bad=copy.deepcopy(self.raw);bad['settings']['tasks'][0][key]=value
   with self.subTest(key=key):
    with self.assertRaises(ValueError):normalize_job(bad,self.expected)
 def test_expected_fields_never_normalized(self):
  bad=copy.deepcopy(self.raw);bad['settings']['tasks'][0]['max_retries']=1
  with self.assertRaises(ValueError):normalize_job(bad,self.expected)
 def test_adapter_preserves_raw_evidence_before_projection(self):
  from types import SimpleNamespace
  records=[];base=SimpleNamespace(_cfg=SimpleNamespace(workspace_id=None),do=lambda *a,**k:copy.deepcopy(self.raw))
  api=DefaultsApi146(base,self.expected,self.raw['job_id'],records.append)
  from databricks.sdk.service.jobs import JobsAPI
  job=JobsAPI(api).get(self.raw['job_id']);self.assertTrue(all(job.settings.as_dict()[k]==v for k,v in self.expected.items()))
  self.assertEqual(records[0]['raw'],self.raw);self.assertTrue(records[0]['projection_sha256'])
 def test_runtime_preserved_but_unknown_task_fields_fail(self):
  task=copy.deepcopy(self.raw['settings']['tasks'][0]);task.update(run_id=3,state={'life_cycle_state':'RUNNING'})
  run={'job_id':self.raw['job_id'],'run_id':3,'tasks':[task]};normalized=normalize_run(run,self.expected)
  self.assertEqual(normalized['tasks'][0]['run_id'],3);self.assertEqual(normalized['tasks'][0]['state'],task['state'])
  task['unknown']=False
  with self.assertRaises(ValueError):normalize_run(run,self.expected)
 def test_portable_overlay_embedded_and_compiles_both_modes(self):
  from sbs.operations.notebook_overlay_146 import notebook_source146
  import hashlib
  source=(ROOT/'src/sbs/operations/job_defaults_146.py').read_bytes();namespace={'__name__':'isolated_overlay146'};exec(compile(source,'overlay146','exec'),namespace)
  self.assertEqual(namespace['normalize_job'](self.raw,self.expected),normalize_job(self.raw,self.expected))
  for mode in ('preflight','execute'):
   notebook=notebook_source146(archive_path='/Volumes/x/code.tar.gz',archive_sha='a'*64,manifest_path='deployment/writer-code-manifest-105.json',release_id='b'*64,config_path='/Volumes/x/config.json',config_sha='c'*64,mode=mode)
   compile(notebook,'notebook146-'+mode,'exec');self.assertIn(hashlib.sha256(source).hexdigest(),notebook);self.assertIn('execute_from_config146',notebook)
 def test_frozen_dispatcher_verify_and_execution_contract_through_adapter(self):
  from sbs.operations.cloud_dispatch import CloudDispatcher,WriterConfig
  from sbs.operations.job_defaults_146 import bind_services146
  from databricks.sdk.service.jobs import JobsAPI
  from types import SimpleNamespace
  from sbs.operations.provision_106 import PRINCIPAL
  payload=self.expected;task=payload['tasks'][0]
  writer=WriterConfig(job_id=self.raw['job_id'],writer_principal=PRINCIPAL,cluster_id=None,notebook_path=task['notebook_task']['notebook_path'],release_id=payload['parameters'][1]['default'],snapshot_backend_id=task['notebook_task']['base_parameters']['snapshot_backend_id'],boundary_policy_id='c'*64,schedule_enabled=False,compute_mode='serverless',environment_version='4',environment_dependencies=tuple(payload['environments'][0]['spec']['dependencies']))
  acl={'object_id':'/jobs/'+str(writer.job_id),'access_control_list':[{'user_name':'owner','all_permissions':[{'permission_level':'IS_OWNER'}]}]}
  class Api:
   _cfg=SimpleNamespace(workspace_id=None)
   def do(inner,m,path,**kw):return copy.deepcopy(self.raw if path.endswith('/jobs/get') else acl)
  records=[];services=bind_services146(SimpleNamespace(jobs=JobsAPI(Api())),writer,records.append)
  boundary={'job_id':writer.job_id,'writer_principal':PRINCIPAL,'evidence_mode':'fixture','policy_id':writer.boundary_policy_id,'snapshot_backend_id':writer.snapshot_backend_id,'evidence_id':'fixture146',**{k:True for k in ('exclusive_writer','ddl_and_acl_controlled','storage_authorized','snapshot_backend_atomic')}}
  dispatcher=CloudDispatcher(writer,services.jobs,None,boundary_probe=lambda:boundary,expected_acl=acl,evidence_mode='fixture')
  self.assertEqual(len(dispatcher.verify()),64);self.assertEqual(records[0]['raw'],self.raw)
  record={'job_id':writer.job_id,'run_id':9,'source':'on_demand','idempotency_token':'d'*64,'release_id':writer.release_id}
  run_task=copy.deepcopy(self.raw['settings']['tasks'][0]);run_task['resolved_values']={'notebook_task':{'base_parameters':{'request_id':'d'*64,'release_id':writer.release_id,'job_id':str(writer.job_id),'run_id':'9','snapshot_backend_id':writer.snapshot_backend_id}}}
  self.assertIsNone(dispatcher._execution_contract(normalize_run({'tasks':[run_task]},self.expected),record))
