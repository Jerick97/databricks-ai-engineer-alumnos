import unittest,json,copy,base64,tempfile,time
from pathlib import Path
from types import SimpleNamespace
from sbs.operations import writer_authority_167 as a
from sbs.operations import writer_delivery_167 as d
from sbs.operations.provision_106 import DriverConfig
from sbs.operations.cloud_dispatch import job_settings
ROOT=Path(__file__).resolve().parents[2]
def fixture():
 now=1000000;c=json.loads((ROOT/'deployment/state/policy-binding146/driver-config146.json').read_bytes());c['policy']={**c['policy'],'issued_at_ms':now-1000,'expires_at_ms':now+1000000};c['writer']['boundary_policy_id']=a.digest(c['policy']);config=DriverConfig.from_dict(c)
 delivery=d.build_delivery(archive_path='/Volumes/test/code.tar.gz',archive_sha='a'*64,manifest_path=c['release_manifest'],release_id=c['writer']['release_id'],config_path='/Volumes/test/config.json',config_sha=a.sha(a.canonical(c).encode()),job_id=config.writer.job_id,request_id='test167')
 rid=418932841079948;widgets={'job_id':str(config.writer.job_id),'run_id':str(rid),'request_id':delivery['request_token'],'release_id':config.writer.release_id,'snapshot_backend_id':config.writer.snapshot_backend_id}
 nba=json.loads((ROOT/'deployment/state/writer-diagnostic158/http-05-response.json').read_bytes());issuer={'id':a.OWNER_ID,'userName':a.OWNER}
 observation={'observed_at_ms':now-1,'settings_sha256':a.digest(job_settings(config.writer)),'job_acl':c['expected_acl'],'notebook_acl':nba,'notebook_id':a.NOTEBOOK_ID,'notebook_path':config.writer.notebook_path,'operator':issuer}
 record={'version':'writer-authority167','state':'AUTHORIZED','issuer':issuer,'issued_at_ms':now,'expires_at_ms':now+a.MAX_TTL,'job_id':config.writer.job_id,'run_id':rid,'request_token':delivery['request_token'],'request_id':delivery['request_id'],'writer_principal':config.writer.writer_principal,'release_id':config.writer.release_id,'snapshot_backend_id':config.writer.snapshot_backend_id,'policy_id':config.writer.boundary_policy_id,'notebook_id':a.NOTEBOOK_ID,'notebook_path':config.writer.notebook_path,'delivery_sha256':a.digest(delivery),'pre':observation,'post':copy.deepcopy(observation)}
 return now,config,delivery,widgets,record
class Authority167(unittest.TestCase):
 def test_non_circular_graph_and_actual_runtime_provenance(self):
  now,c,delivery,widgets,record=fixture();pending=d.render(delivery);bound=d.render(delivery,record)
  self.assertEqual(a.parse_source(pending.encode())[1],a.parse_source(bound.encode())[1]);self.assertEqual(a.parse_source(bound.encode())[1],delivery['template_sha256'])
  verifier=a.AttestedWriterVerifier167(c,delivery,widgets,clock=lambda:now);self.assertFalse(verifier.accept_source(pending.encode()));self.assertTrue(verifier.accept_source(bound.encode()))
  raw=json.loads((ROOT/'deployment/state/diagnostic-monitor162/result.json').read_bytes())['output_check']['diagnostic_report']['observations'];job=next(v['body'] for v in raw if v['stage']=='job');me=next(v['body'] for v in raw if v['stage']=='Me')
  run=json.loads((ROOT/'deployment/state/writer-monitor156/result.json').read_bytes())['raw_run'];original=copy.deepcopy(run);run['state']['life_cycle_state']='RUNNING' # fixture lifecycle, actual captured fields unchanged
  evidence=verifier.verify_runtime(job,run,me)
  self.assertEqual(set(evidence.attested_only_fields),a.MISSING_ATTESTED);self.assertIn('resolved_values',evidence.historical_api_fields_missing);self.assertIn('NOT writer_live_ACL',evidence.acl_provenance);self.assertNotIn('resolved_values',run['tasks'][0])
  self.assertEqual(original['tasks'],run['tasks'])
 def test_tamper_ast_core_delivery_run_and_time_rejected(self):
  now,c,delivery,widgets,record=fixture();valid=d.render(delivery,record)
  for changed in [valid.replace('archive.read_bytes()','archive.read_bytes()+b"x"'),valid+'\nATTESTATION167 = None\n',valid.replace('ATTESTATION167 = '+repr(record),'ATTESTATION167 = dict()'),valid.replace("'config_sha256': '"+delivery['config_sha256'],"'config_sha256': '"+'0'*64)]:
   with self.subTest(changed=changed[-30:]):
    with self.assertRaises(ValueError):a.AttestedWriterVerifier167(c,delivery,widgets,clock=lambda:now).accept_source(changed.encode())
  for key,value in [('run_id',record['run_id']+1),('job_id',True),('request_token','x'),('expires_at_ms',now),('expires_at_ms',now+a.MAX_TTL+1),('issued_at_ms',now+1),('notebook_id',4)]:
   bad={**record,key:value}
   with self.subTest(key=key):
    with self.assertRaises(ValueError):a.AttestedWriterVerifier167(c,delivery,widgets,clock=lambda:now).accept_source(d.render(delivery,bad).encode())
 def test_expiry_before_mutation_and_after_response(self):
  now,c,delivery,widgets,record=fixture();clock=[now];v=a.AttestedWriterVerifier167(c,delivery,widgets,clock=lambda:clock[0]);v.accept_source(d.render(delivery,record).encode())
  class Http:
   adapters={}
   calls=0
   def request(self,*args,**kwargs):self.calls+=1;clock[0]=record['expires_at_ms'];return SimpleNamespace(close=lambda:None)
  h=Http();s=a.WriterSession167(h,v);url='https://dbc-0410b264-20c7.cloud.databricks.com/api/2.0/fs/files'+c.volume_prefix+'/runs/1/a.json'
  with self.assertRaisesRegex(ValueError,'EXPIRED'):s.request('PUT',url,data=b'x')
  with self.assertRaisesRegex(ValueError,'EXPIRED'):s.request('PUT',url,data=b'x')
  self.assertEqual(h.calls,1)
 def test_acl_fabrication_not_used_and_manage_forbidden(self):
  now,c,delivery,widgets,record=fixture();bad=copy.deepcopy(record)
  for phase in ('pre','post'):
   for item in bad[phase]['notebook_acl']['access_control_list']:
    if item.get('service_principal_name'):item['all_permissions']=[{'permission_level':'CAN_EDIT'}]
  with self.assertRaises(ValueError):a.AttestedWriterVerifier167(c,delivery,widgets,clock=lambda:now).accept_source(d.render(delivery,bad).encode())
  v=a.AttestedWriterVerifier167(c,delivery,widgets,clock=lambda:now);s=a.WriterSession167(SimpleNamespace(adapters={}),v)
  with self.assertRaisesRegex(ValueError,'OPERATION_FORBIDDEN'):s.request('GET','https://dbc-0410b264-20c7.cloud.databricks.com/api/2.0/permissions/jobs/'+str(c.writer.job_id))
 def test_runtime_missing_not_synthesized_and_contradictions_rejected(self):
  now,c,delivery,widgets,record=fixture();v=a.AttestedWriterVerifier167(c,delivery,widgets,clock=lambda:now);v.accept_source(d.render(delivery,record).encode())
  rows=json.loads((ROOT/'deployment/state/diagnostic-monitor162/result.json').read_bytes())['output_check']['diagnostic_report']['observations'];job=next(x['body'] for x in rows if x['stage']=='job');me=next(x['body'] for x in rows if x['stage']=='Me')
  base=json.loads((ROOT/'deployment/state/writer-monitor156/result.json').read_bytes())['raw_run'];base['state']['life_cycle_state']='RUNNING'
  for key,value in [('max_retries',1),('timeout_seconds',601),('disable_auto_optimization',False),('attempt_number',1),('effective_performance_target','STANDARD'),('spark_python_task',{}),('unknown',None),('resolved_values',{'notebook_task':{'base_parameters':{}}})]:
   run=copy.deepcopy(base);run['tasks'][0][key]=value
   with self.subTest(key=key):
    with self.assertRaises(ValueError):v.verify_runtime(job,run,me)
 def test_pending_wait_is_bounded_and_no_mutations(self):
  from unittest.mock import patch
  now,c,delivery,widgets,record=fixture();v=a.AttestedWriterVerifier167(c,delivery,widgets,clock=lambda:now);pending=base64.b64encode(d.render(delivery).encode()).decode()
  class Api:
   calls=0
   def do(self,method,path,**kwargs):
    assert method=='GET';self.calls+=1
    return {'object_id':a.NOTEBOOK_ID,'path':c.writer.notebook_path} if path.endswith('/get-status') else {'content':pending}
  api=Api()
  with patch.object(a.time,'sleep',lambda _:None):
   with self.assertRaisesRegex(ValueError,'PENDING_TIMEOUT'):v.observe_protected(api)
  self.assertEqual(api.calls,31);self.assertIsNone(v.attestation)
