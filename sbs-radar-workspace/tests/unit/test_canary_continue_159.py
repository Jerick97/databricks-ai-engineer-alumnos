from pathlib import Path
from types import SimpleNamespace
import importlib.util
import pytest
ROOT=Path(__file__).resolve().parents[2]
def module():
 s=importlib.util.spec_from_file_location('test159',ROOT/'deployment/canary_continue_159.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def test_actual_preflight_no_effects():
 p=module().preflight();assert p['uploads_max']==p['start_max']==0 and p['deploy_max']==1 and p['expires_at_unix']==1790709142

def test_continuation_wait_then_only_deploy(tmp_path,monkeypatch):
 m=module();p=m.preflight();monkeypatch.setattr(m,'preflight',lambda r:p);monkeypatch.setattr(m,'check_review',lambda r:None)
 (tmp_path/m.FREEZE).parent.mkdir(parents=True);(tmp_path/m.FREEZE).write_text('{}');(tmp_path/m.REVIEW).write_text('{}');calls=[]
 class Apps:
  def get(self,name):
   calls.append('get');return {'name':name,'service_principal_id':77041447522099,'service_principal_client_id':'a947eccf-5f94-4369-a3d4-8f83b4ea98a1','compute_status':{'state':'STARTING' if len(calls)==1 else 'ACTIVE'}}
  def deploy(self,name,body):calls.append('deploy');return SimpleNamespace(response={'deployment_id':'owned159'})
  def get_deployment(self,*args):return {'status':{'state':'SUCCEEDED'}}
 api=SimpleNamespace(maximum={'start':1},counts={},calls=0,session=SimpleNamespace(close=lambda:None));server=SimpleNamespace(apps=Apps(),api=api)
 kwargs=dict(root=tmp_path,config_factory=lambda **k:SimpleNamespace(host=m.base.HOST,authenticate=lambda:{'auth':'fixture'}),services_factory=lambda *a,**k:server,clock=lambda:1790709000,sleep=lambda n:None)
 out=m.execute(**kwargs);assert out['status']=='deployed_linux_evidence_pending' and calls==['get','get','deploy'] and api.maximum['start']==0
 with pytest.raises(FileExistsError):m.execute(**kwargs)
 assert calls.count('deploy')==1

def test_expired_before_auth_or_state(tmp_path,monkeypatch):
 m=module();p=m.preflight();monkeypatch.setattr(m,'preflight',lambda r:p);monkeypatch.setattr(m,'check_review',lambda r:None)
 with pytest.raises(ValueError,match='EXPIRED'):m.execute(root=tmp_path,clock=lambda:1790709142,config_factory=lambda **kw:(_ for _ in ()).throw(AssertionError()))
 assert not (tmp_path/m.STATE).exists()
