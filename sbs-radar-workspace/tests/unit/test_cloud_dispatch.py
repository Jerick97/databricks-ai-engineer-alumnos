import json
from types import SimpleNamespace
import pytest
from sbs.operations.cloud_dispatch import WriterConfig,job_settings,CloudDispatcher,SqliteLedger

def config():return WriterConfig(7,'writer-sp','cluster','/Shared/sealed/refresh','a'*64,'b'*64,'c'*64)
class Jobs:
 def __init__(self):self.calls=[];self.settings=job_settings(config());self.state={'life_cycle_state':'QUEUED'}
 def get(self,job_id):return {'job_id':7,'run_as_user_name':'writer-sp','settings':self.settings}
 def get_permissions(self,job_id):return {'access_control_list':[]}
 def run_now(self,**kw):self.calls.append(kw);return SimpleNamespace(response=SimpleNamespace(run_id=99))
 def get_run(self,run_id,**kw):
  request=self.calls[-1]['idempotency_token'] if self.calls else str(run_id)
  task=json.loads(json.dumps(self.settings['tasks'][0]))
  task['resolved_values']={'notebook_task':{'base_parameters':{'request_id':request,'release_id':'a'*64,'job_id':'7','run_id':str(run_id),'snapshot_backend_id':'b'*64}}}
  return {'job_id':7,'run_id':run_id,'state':self.state,'trigger':'PERIODIC','tasks':[task],'job_parameters':[{'name':'release_id','value':'a'*64},{'name':'request_id','value':request}]}

def boundary():return {'job_id':7,'writer_principal':'writer-sp','exclusive_writer':True,'ddl_and_acl_controlled':True,'storage_authorized':True,'snapshot_backend_atomic':True,'policy_id':'c'*64,'snapshot_backend_id':'b'*64,'evidence_id':'verified-boundary','evidence_mode':'fixture'}
def dispatcher(tmp_path,jobs=None):
 j=jobs or Jobs();return CloudDispatcher(config(),j,SqliteLedger(tmp_path/'ledger.db'),boundary_probe=boundary,expected_acl={'access_control_list':[]},evidence_mode='fixture'),j

def test_settings_paused_queue_single_writer():
 s=job_settings(config());assert s['max_concurrent_runs']==1 and s['queue']=={'enabled':True}
 assert s['schedule']['pause_status']=='PAUSED' and s['schedule']['timezone_id']=='America/Lima'
 assert s['run_as']=={'service_principal_name':'writer-sp'}

def test_durable_dedup_exact_sdk_payload(tmp_path):
 d,j=dispatcher(tmp_path);a=d.request('event-123');b=d.request('event-123');assert a==b and len(j.calls)==1
 assert len(j.calls[0]['idempotency_token'])==64 and j.calls[0]['queue'].as_dict()=={'enabled':True}
 d2,_=dispatcher(tmp_path,j);assert d2.request('event-123')==a and len(j.calls)==1
 assert a['status']=='submitted' and a['run_id']==99

@pytest.mark.parametrize('mutate',[lambda s:s.update(max_concurrent_runs=2),lambda s:s.update(queue={'enabled':False}),lambda s:s.update(run_as={'service_principal_name':'other'}),lambda s:s['tasks'][0].update(existing_cluster_id='wrong')])
def test_job_mismatch_blocks_post(tmp_path,mutate):
 d,j=dispatcher(tmp_path);mutate(j.settings)
 with pytest.raises(ValueError):d.request('event')
 assert not j.calls

def test_boundary_required(tmp_path):
 d,j=dispatcher(tmp_path);d.boundary_probe=lambda:{}
 with pytest.raises(ValueError):d.request('event')
 assert not j.calls

def test_timeout_does_not_resubmit_or_report_success(tmp_path):
 d,j=dispatcher(tmp_path)
 def fail(**kw):j.calls.append(kw);raise TimeoutError('secret')
 j.run_now=fail;out=d.request('event');assert out['status']=='submission_unknown'
 assert d.request('event')['status']=='submission_unknown' and len(j.calls)==1
 assert 'secret' not in json.dumps(out)

def test_job_success_requires_verified_publication_result(tmp_path):
 d,j=dispatcher(tmp_path);d.request('event');j.state={'life_cycle_state':'TERMINATED','result_state':'SUCCESS'}
 assert d.refresh('event')['status']=='job_succeeded_publication_unverified'
 j.state={'life_cycle_state':'TERMINATED','result_state':'FAILED'}
 assert d.refresh('event')['status']=='job_failed'

def test_daily_registration_without_run_now(tmp_path):
 d,j=dispatcher(tmp_path);out=d.observe_daily(88);assert out['run_id']==88 and out['source']=='daily' and not j.calls

def test_wrong_run_scope_rejected(tmp_path):
 d,j=dispatcher(tmp_path);d.request('event');j.get_run=lambda run_id,**kw:{'job_id':8,'run_id':run_id,'state':{'life_cycle_state':'TERMINATED','result_state':'SUCCESS'}}
 with pytest.raises(ValueError):d.refresh('event')


def test_active_daily_config_explicit_and_job_parameters_verified(tmp_path):
 from dataclasses import replace
 c=replace(config(),schedule_enabled=True)
 assert job_settings(c)['schedule']['pause_status']=='UNPAUSED'
 d,j=dispatcher(tmp_path);d.request('event');original=j.get_run
 def wrong(run_id,**kw):
  r=original(run_id);r['job_parameters'][0]['value']='wrong';return r
 j.get_run=wrong
 with pytest.raises(ValueError,match='RUN_PARAMETERS'):d.refresh('event')

def test_acl_and_publication_identity(tmp_path):
 d,j=dispatcher(tmp_path);j.get_permissions=lambda job_id:{'access_control_list':[{'user_name':'extra'}]}
 with pytest.raises(ValueError,match='ACL'):d.request('event')
 assert not j.calls
 j.get_permissions=lambda job_id:{'access_control_list':[]};d.request('event');j.state={'life_cycle_state':'TERMINATED','result_state':'SUCCESS'}
 d.result_probe=lambda run_id,**kw:{'job_id':7,'run_id':run_id,'release_id':'a'*64,'evidence_mode':'fixture','verified':True,'status':'published','publication_id':'d'*64}
 assert d.refresh('event')['status']=='publication_verified'
 d.result_probe=lambda run_id,**kw:{'verified':True,'status':'published'}
 assert d.refresh('event')['status']=='job_succeeded_publication_unverified'

@pytest.mark.parametrize('change',[lambda r:r['tasks'][0].update(existing_cluster_id='wrong'),lambda r:r['tasks'][0]['notebook_task'].update(notebook_path='/wrong'),lambda r:r['tasks'].append(dict(r['tasks'][0])),lambda r:r['tasks'][0].update(sql_task={'query':{'query_id':'x'}}),lambda r:r['tasks'][0]['resolved_values']['notebook_task']['base_parameters'].update(extra='bad')])
def test_actual_run_snapshot_mismatch_never_verified(tmp_path,change):
 d,j=dispatcher(tmp_path);d.request('event');original=j.get_run
 def altered(run_id,**kw):
  r=original(run_id,**kw);change(r);return r
 j.get_run=altered
 out=d.refresh('event');assert out['status']=='execution_contract_not_verified' and out['execution_verified'] is False

@pytest.mark.parametrize('life,result',[('QUEUED',None),('TERMINATED','SUCCESS'),('SKIPPED','SKIPPED')])
def test_missing_actual_task_metadata_preserves_state(tmp_path,life,result):
 d,j=dispatcher(tmp_path);d.request('event');j.state={'life_cycle_state':life,'result_state':result};original=j.get_run
 def missing(run_id,**kw):
  r=original(run_id,**kw);r.pop('tasks');return r
 j.get_run=missing
 out=d.refresh('event');assert out['status']=='execution_contract_not_verified' and out['life_cycle_state']==life and out['result_state']==result
