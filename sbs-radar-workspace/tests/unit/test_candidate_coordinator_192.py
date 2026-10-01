from pathlib import Path
import importlib.util
import pytest
ROOT=Path(__file__).resolve().parents[2]
def module():
 s=importlib.util.spec_from_file_location('test192',ROOT/'runs/sk10-candidate-coordinator-192.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def fixture(tmp_path):
 m=module();write=m.prior.prior.durable
 binding={'deployment_id':'191-deploy','source_code_path':'/191','source_sha256':'sha191','expires_at_unix':200,'caps':{'generation_posts':4,'embedding_posts':2,'embedding_tokens':20000},'scope':'external_coordinator_only_not_server_global','process_epoch':None,'candidate_kind':'experimental_linux191','numeric_equivalence':'failed','final_release_authorized':False}
 write(tmp_path/m.LEDGER/'binding.json',binding);write(tmp_path/m.MATERIALIZED/'manifest.json',{'source_sha256':'sha191'});write(tmp_path/m.MATERIALIZED/'deployment-payload.json',{'source_code_path':'/191','source_sha256':'sha191','expires_at_unix':200})
 obs=tmp_path/'observed.json';write(obs,{'deployment_id':'191-deploy','source_sha256':'sha191','observed_at_unix':99})
 return m,obs

def test_uses191sameledger_unknown_epoch_and_no_reset(tmp_path):
 m,obs=fixture(tmp_path);ledger=m.CandidateCoordinator(tmp_path,clock=lambda:100);out=ledger.reserve_action('turn3',obs)
 assert out['numeric_equivalence']=='failed' and out['process_epoch'] is None and out['final_release_authorized'] is False
 ledger.receipt('turn3');record=m.prior.prior.read(tmp_path/m.LEDGER/'turn-turn3-receipt.json');assert record['unknown']['generation_posts']==1 and record['reservation_retained']
 with pytest.raises(ValueError,match='NO_RESEND'):m.CandidateCoordinator(tmp_path,clock=lambda:100).reserve_action('turn3',obs)
 assert not (tmp_path/'deployment/state/final-app-168').exists()

def test_reject_final168_binding_or_changed_numeric_claim(tmp_path):
 m,_=fixture(tmp_path);p=tmp_path/m.LEDGER/'binding.json';v=m.prior.prior.read(p);v['numeric_equivalence']='passed';p.write_text(__import__('json').dumps(v))
 with pytest.raises(ValueError,match='CANDIDATE_BINDING'):m.CandidateCoordinator(tmp_path)

def test_onlyfour_actions_unknown_quota_blocks(tmp_path):
 m,obs=fixture(tmp_path);ledger=m.CandidateCoordinator(tmp_path,clock=lambda:100)
 with pytest.raises(ValueError,match='ONLY_FOUR'):ledger.reserve_action('count-families',obs)
 ledger.block('turn0')
 with pytest.raises(ValueError,match='UNKNOWN_QUOTA'):ledger.reserve_action('turn0',obs)

def test_no_ledger_or_manifest_no_admission(tmp_path):
 m=module()
 with pytest.raises(FileNotFoundError):m.CandidateCoordinator(tmp_path)
 assert not (tmp_path/m.LEDGER).exists()
