from pathlib import Path
from types import SimpleNamespace
import importlib.util
import pytest
ROOT=Path(__file__).resolve().parents[2]
def module():
 s=importlib.util.spec_from_file_location('test185',ROOT/'deployment/canary_continue_185.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def test_current_exact_restore_preflight():
 p=module().preflight();assert p['upload_max']==p['start_max']==0 and p['deploy_max']==1 and '01f1bc423d1a1c5c81d7de749ad20cce' in p['old_ids']

def test_foreign_deployment_rejected():
 m=module();p=m.preflight();a={'name':m.base.APP,'service_principal_id':77041447522099,'service_principal_client_id':'a947eccf-5f94-4369-a3d4-8f83b4ea98a1','compute_status':{'state':'ACTIVE'},'pending_deployment':{'source_code_path':p['old_source'],'deployment_id':'unseen'}}
 with pytest.raises(ValueError,match='OTHER_DEPLOYMENT'):m.known(a,p)

@pytest.mark.parametrize('passed',[True,False])
def test_only_deploy_capture_before_cleanup_or_handoff(tmp_path,monkeypatch,passed):
 m=module();p=m.preflight();monkeypatch.setattr(m,'preflight',lambda r:p);monkeypatch.setattr(m,'check_review',lambda r:None)
 for name in (m.FREEZE,m.REVIEW):m.durable(tmp_path/name,{})
 m.durable(tmp_path/m.prior.STATE/'source-binding.json',{'fixture':True});events=[];posts=[];pending=[True]
 class Apps:
  def get(self,name):
   value={'name':name,'service_principal_id':77041447522099,'service_principal_client_id':'a947eccf-5f94-4369-a3d4-8f83b4ea98a1','compute_status':{'state':'ACTIVE'},'last_deployment_id':p['old_ids'][1]}
   if pending[0]:value['pending_deployment']={'source_code_path':p['old_source'],'deployment_id':p['old_ids'][1]};pending[0]=False
   return value
  def deploy(self,name,body):posts.append('deploy');return SimpleNamespace(response={'deployment_id':'new185','source_code_path':p['source_code_path']})
  def get_deployment(self,*a):return {'status':{'state':'SUCCEEDED'}}
 api=SimpleNamespace(maximum={'start':1},counts={},calls=0,session=SimpleNamespace(close=lambda:None));server=SimpleNamespace(apps=Apps(),api=api)
 def capture(*a,**kw):events.append('capture');return {'status':'captured_linux_report153_pass' if passed else 'captured_linux_report153_failed','report_sha256':'fixture'}
 def cleanup(*a,**kw):events.append('cleanup');return {'status':'fixture_stopped'}
 kwargs=dict(root=tmp_path,config_factory=lambda **k:SimpleNamespace(host=m.base.HOST,authenticate=lambda:{'auth':'fixture'}),services_factory=lambda *a,**k:server,clock=lambda:p['expires_at_unix']-100,sleep=lambda n:None,capture_fn=capture,cleanup_fn=cleanup)
 result=m.execute(**kwargs);assert posts==['deploy'] and api.maximum['start']==0
 assert events==(['capture'] if passed else ['capture','cleanup'])
 assert (tmp_path/m.STATE/'active-handoff.json').exists()==passed
 with pytest.raises(FileExistsError):m.execute(**kwargs)
