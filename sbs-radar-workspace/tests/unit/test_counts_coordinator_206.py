import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
ROOT = Path(__file__).resolve().parents[2]


def module():
    path = ROOT / 'runs/sk06-sk10-counts-206.py'
    assert path.exists(), '206 adapter missing'
    spec = importlib.util.spec_from_file_location('counts206test', path)
    m = importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m


def fixture(root, monkeypatch):
    m = module();write = m.experiment.durable
    binding = {'deployment_id':'fixture-deploy','source_code_path':'/fixture199',
        'source_sha256':'fixture-sha','expires_at_unix':200,'caps':m.experiment.CAPS,
        'scope':'external_coordinator_only_not_server_global','process_epoch':None,
        'candidate_kind':'experimental_linux199','numeric_equivalence':'failed',
        'final_release_authorized':False}
    state=root/m.experiment.STATE;ledger=state/'demo-ledger';write(ledger/'binding.json',binding)
    write(ledger/'migration.json',{'target_binding_sha256':m.experiment.sha(ledger/'binding.json')})
    receipt={'deployment_id':'fixture-deploy','source_code_path':'/fixture199'}
    write(state/'deploy-receipt.json',receipt)
    continuation=root/m.continuation.STATE
    write(continuation/'deploy-receipt.json',receipt)
    write(root/m.continuation.REVIEW,{'fixture':True})
    write(state/'continuation207.json',{'state':m.continuation.STATE,
       'deploy_receipt_sha256':m.experiment.sha(continuation/'deploy-receipt.json'),
       'review_sha256':m.experiment.sha(root/m.continuation.REVIEW)})
    write(continuation/'result.json',{'status':'experimental_ui_evaluation_pending',
       'binding':binding,'cleanup_required_before_or_at_unix':200})
    monkeypatch.setattr(m.experiment,'review',lambda root:None)
    monkeypatch.setattr(m.continuation,'review',lambda root:None)
    monkeypatch.setattr(m.experiment,'ready',lambda root:(None,{'source_sha256':'fixture-sha'},
       {'source_code_path':'/fixture199','expires_at_unix':200}))
    observation=root/'observation.json';write(observation,{'deployment_id':'fixture-deploy',
        'source_sha256':'fixture-sha','observed_at_unix':99,'generation_sha256':'fixture-pin',
        'store_source':'protected_volume_readback','store_observed_at_unix':99})
    return m,ledger,observation


def completed(m, ledger):
    actions=m.experiment.read(ROOT/m.experiment.ACTIONS)
    for turn in m.experiment.TURNS:
        m.experiment.durable(ledger/f'turn-{turn}-intent.json',{
            'turn_id':turn,'reserved':actions[turn]['reserved']})
        m.experiment.durable(ledger/f'turn-{turn}-receipt.json',{'fixture':True})


def test_constructor_never_resets_or_reserves_and_missing_four_turns_blocks(tmp_path,monkeypatch):
    m,ledger,obs=fixture(tmp_path,monkeypatch)
    before={p.name:p.read_bytes() for p in ledger.iterdir()}
    c=m.CountsCoordinator(tmp_path,clock=lambda:100)
    with pytest.raises(ValueError,match='FOUR_TURNS_FIRST'):
        c.reserve_count('count-market',obs,tmp_path,tmp_path/'missing-result')
    assert {p.name:p.read_bytes() for p in ledger.iterdir()}==before
    assert not (tmp_path/'deployment/state/experimental-app191').exists()


@pytest.mark.parametrize('mutation',['source','handoff','receipt','cleanup'])
def test_rejects_changed_binding_or_nonpending_handoff(tmp_path,monkeypatch,mutation):
    m,ledger,obs=fixture(tmp_path,monkeypatch)
    def write(path,value):
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value))
    if mutation=='source':
        binding=m.experiment.read(ledger/'binding.json');binding['source_sha256']='foreign';write(ledger/'binding.json',binding)
    elif mutation=='handoff':
        result=m.experiment.read(tmp_path/m.continuation.STATE/'result.json');result['status']='incomplete';write(tmp_path/m.continuation.STATE/'result.json',result)
    elif mutation=='receipt':
        write(tmp_path/m.continuation.STATE/'deploy-receipt.json',{'deployment_id':'foreign'})
    else:write(tmp_path/m.continuation.STATE/'cleanup/result.json',{'status':'stopped'})
    with pytest.raises(ValueError):m.CountsCoordinator(tmp_path,clock=lambda:100)
    assert not list(ledger.glob('turn-count-*-intent.json'))


def test_fresh_generation_required_before_any_reservation(tmp_path,monkeypatch):
    m,ledger,obs=fixture(tmp_path,monkeypatch);completed(m,ledger)
    result=tmp_path/'published.json';m.experiment.durable(result,{'status':'published_readback_verified','sql_reserved':33,'generation_sha256':'fixture-pin'})
    def stale(*_args,**_kwargs):
        return SimpleNamespace(select=lambda:(_ for _ in ()).throw(ValueError('PUBLICATION_EXPIRED')))
    monkeypatch.setattr(m.counts,'RotationReader',stale)
    with pytest.raises(ValueError,match='PUBLICATION_EXPIRED'):
        m.CountsCoordinator(tmp_path,clock=lambda:100).reserve_count('count-market',obs,tmp_path,result)
    assert not (ledger/'turn-count-market-intent.json').exists()


def test_counts_use_existing_ledger_no_resend_no_refund_and_stale_store_blocks(tmp_path,monkeypatch):
    m,ledger,obs=fixture(tmp_path,monkeypatch);completed(m,ledger)
    result=tmp_path/'published.json';m.experiment.durable(result,{'status':'published_readback_verified','sql_reserved':33,'generation_sha256':'fixture-pin'})
    monkeypatch.setattr(m.counts,'RotationReader',lambda *a,**k:SimpleNamespace(select=lambda:SimpleNamespace(
        payload={'identity_profile':m.counts.NAMED_IDENTITY_PROFILE},pin='fixture-pin',certificate=SimpleNamespace(sha256='fixture-cert'))))
    c=m.CountsCoordinator(tmp_path,clock=lambda:100);c.reserve_count('count-market',obs,tmp_path,result)
    c.receipt_count('count-market')
    receipt=m.experiment.read(ledger/'turn-count-market-receipt.json')
    assert receipt['reservation_retained'] is True
    with pytest.raises(ValueError,match='NO_RESEND'):
        m.CountsCoordinator(tmp_path,clock=lambda:100).reserve_count('count-market',obs,tmp_path,result)
    o=m.experiment.read(obs);o['store_observed_at_unix']=1;obs.write_text(json.dumps(o))
    with pytest.raises(ValueError,match='CURRENT_STORE'):
        c.reserve_count('count-families',obs,tmp_path,result)
    assert len(list(ledger.glob('turn-*-intent.json')))==5
    scope=m.experiment.read(ledger/'turn-count-market-genie-scope.json')
    assert scope['sql_statement_cap'] is None and scope['sql_statements_actual'] is None


def test_actual_app_metadata_age_and_ui_failure_block_before_reservation(tmp_path,monkeypatch):
    m,ledger,obs=fixture(tmp_path,monkeypatch);completed(m,ledger)
    result=tmp_path/'published.json';m.experiment.durable(result,{'status':'published_readback_verified','sql_reserved':33,'generation_sha256':'fixture-pin'})
    monkeypatch.setattr(m.counts,'RotationReader',lambda *a,**k:SimpleNamespace(select=lambda:SimpleNamespace(
        payload={'identity_profile':m.counts.NAMED_IDENTITY_PROFILE},pin='fixture-pin',certificate=SimpleNamespace(sha256='fixture-cert'))))
    c=m.CountsCoordinator(tmp_path,clock=lambda:150)
    o=m.experiment.read(obs);o.update(observed_at_unix=1,store_observed_at_unix=149);obs.write_text(json.dumps(o))
    with pytest.raises(ValueError,match='STALE_OR_EXPIRED'):
        c.reserve_count('count-families',obs,tmp_path,result)
    assert not list(ledger.glob('turn-count-*-intent.json'))
    m.experiment.durable(ledger/'ui-failed.json',{'fixture':True})
    with pytest.raises(ValueError,match='UI_BLOCKED'):
        c.reserve_count('count-families',obs,tmp_path,result)
