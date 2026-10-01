from pathlib import Path
import importlib.util
import pytest
ROOT=Path(__file__).resolve().parents[2]
def module():
 s=importlib.util.spec_from_file_location('test186',ROOT/'deployment/final_handoff_186.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def test_samefinalstate_only185predecessor_activehandoff():
 m=module();p=m.preflight();assert p['start_max']==0 and p['final_state']=='deployment/state/final-app-168' and m.runner.mission.STATE==m.previous.STATE

def test_stopped_rejected_before_any_start():
 m=module();old={'source_code_path':'/own','deployment_id':'185'}
 app={'name':m.runner.base.APP,'service_principal_id':77041447522099,'service_principal_client_id':'a947eccf-5f94-4369-a3d4-8f83b4ea98a1','compute_status':{'state':'STOPPED'},'last_deployment_id':'185'}
 with pytest.raises(ValueError,match='NO_START'):m.active_only(app,old)
 app['compute_status']['state']='ACTIVE';assert m.active_only(app,old)=='ACTIVE'

def test_services_startcap_forcedzero_withoutchanging168(monkeypatch,tmp_path):
 from types import SimpleNamespace
 m=module();monkeypatch.setattr(m,'check_review',lambda r:None);service=SimpleNamespace(api=SimpleNamespace(maximum={'start':1}))
 def execute(**kwargs):return kwargs['services_factory']().api.maximum
 monkeypatch.setattr(m.runner,'execute',execute)
 assert m.execute(root=tmp_path,services_factory=lambda:service)['start']==0
