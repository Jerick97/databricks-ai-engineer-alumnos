from pathlib import Path
import importlib.util
import pytest
ROOT=Path(__file__).resolve().parents[2]
def module():
 s=importlib.util.spec_from_file_location('test170',ROOT/'runs/sk10-demo-coordinator-170.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def setup(tmp_path):
 m=module();m.prior.durable(tmp_path/'binding.json',{'deployment_id':'demo','source_sha256':'sha','expires_at_unix':200,'caps':{'generation_posts':4,'embedding_posts':2,'embedding_tokens':20000}});obs=tmp_path/'observed.json';m.prior.durable(obs,{'deployment_id':'demo','source_sha256':'sha','observed_at_unix':99});return m,m.Coordinator(tmp_path,clock=lambda:100),obs

def test_null_epoch_honest_and_receipt_keeps_unknown_reserved(tmp_path):
 m,ledger,obs=setup(tmp_path);out=ledger.reserve_action('turn3',obs);assert out['process_epoch'] is None
 ledger.receipt('turn3');receipt=m.prior.read(tmp_path/'turn-turn3-receipt.json');assert receipt['unknown']=={'generation_posts':1,'embedding_posts':1,'embedding_tokens':20000} and receipt['reservation_retained']
 with pytest.raises(ValueError,match='NO_RESEND'):ledger.reserve_action('turn3',obs)


def test_unknown_quota_blocks_next_action(tmp_path):
 m,ledger,obs=setup(tmp_path);m.prior.durable(tmp_path/'quota-unknown.json',{'reason':'uncoordinated_request'})
 with pytest.raises(ValueError,match='UNKNOWN_QUOTA'):ledger.reserve_action('turn0',obs)


def test_immutable_exact_action_route_budget():
 m=module();actions=m.prior.read(ROOT/m.ACTIONS)
 from sbs.conversation import route_intent
 for i in range(3):assert actions[f'turn{i}']['reserved']['generation_posts']==0 and route_intent(actions[f'turn{i}']['question'])['comparison']
 assert route_intent(actions['turn3']['question'])['implications'] and actions['turn3']['reserved']['generation_posts']==1
 for name in ('count-families','count-market'):assert route_intent(actions[name]['question'])['pure_count']
 assert not route_intent('¿Y solo para conducta de mercado?')['counts']


def test_stale_observation_rejected(tmp_path):
 m,ledger,obs=setup(tmp_path);ledger.clock=lambda:300
 with pytest.raises(ValueError,match="STALE_OR_EXPIRED"):ledger.reserve_action("turn0",obs)
