import importlib.util
from pathlib import Path
import pytest
from test_candidate_coordinator_192 import fixture
ROOT=Path(__file__).resolve().parents[2]
def module():
 s=importlib.util.spec_from_file_location('counts193test',ROOT/'runs/sk06-sk10-counts-193.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def test_requires_completed_ui_and_preserves_ledger(tmp_path):
 _,obs=fixture(tmp_path);m=module();c=m.CountsCoordinator(tmp_path,clock=lambda:100)
 with pytest.raises(ValueError,match='FOUR_TURNS_FIRST'):c.reserve_count('count-market',obs,tmp_path,tmp_path/'missing')
 assert not (c.path/'turn-count-market-intent.json').exists()
def test_refuses_unknown_actions(tmp_path):
 fixture(tmp_path);m=module();c=m.CountsCoordinator(tmp_path)
 with pytest.raises(ValueError,match='ACTION'):c.reserve_count('turn0',None,None,None)
def test_rejects_fixture_publisher_before_reservation(tmp_path):
 _,obs=fixture(tmp_path);m=module();c=m.CountsCoordinator(tmp_path,clock=lambda:100)
 for t in m.prior.TURNS:c.reserve_action(t,obs);c.receipt(t)
 result=tmp_path/'result.json';m.base.durable(result,{'status':'fixture','sql_reserved':33})
 with pytest.raises(ValueError,match='REAL081'):c.reserve_count('count-market',obs,tmp_path,result)
 assert not (c.path/'turn-count-market-intent.json').exists()
def test_fixture_selected_generation_same_ledger_no_resend_and_stale_rejected(tmp_path,monkeypatch):
 from types import SimpleNamespace
 import json
 _,obs=fixture(tmp_path);m=module();c=m.CountsCoordinator(tmp_path,clock=lambda:100)
 for t in m.prior.TURNS:c.reserve_action(t,obs);c.receipt(t)
 result=tmp_path/'result.json';m.base.durable(result,{'status':'published_readback_verified','sql_reserved':33,'generation_sha256':'fixture-pin'})
 # Explicit coordinator fixture; production RotationReader remains unchanged.
 monkeypatch.setattr(m,'RotationReader',lambda *a,**k:SimpleNamespace(select=lambda:SimpleNamespace(payload={'identity_profile':m.NAMED_IDENTITY_PROFILE},pin='fixture-pin',certificate=SimpleNamespace(sha256='fixture-cert'))))
 v=json.loads(obs.read_text());v.update(generation_sha256='fixture-pin',store_source='protected_volume_readback',store_observed_at_unix=99);obs.write_text(json.dumps(v))
 c.reserve_count('count-market',obs,tmp_path,result)
 scope=m.base.read(c.path/'turn-count-market-genie-scope.json');assert scope['sql_statement_cap'] is None and scope['sql_statements_actual'] is None
 with pytest.raises(ValueError,match='NO_RESEND'):c.reserve_count('count-market',obs,tmp_path,result)
 v['store_observed_at_unix']=1;obs.write_text(json.dumps(v))
 with pytest.raises(ValueError,match='CURRENT_STORE'):c.reserve_count('count-families',obs,tmp_path,result)
 assert (c.path/'turn-turn3-intent.json').is_file()
