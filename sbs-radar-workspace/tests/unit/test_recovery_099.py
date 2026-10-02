import importlib.util,json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('r099',ROOT/'runs/sk07-recovery-099.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
def fixture(root):
    state=root/r.OLD;state.mkdir(parents=True)
    for name in ('admission.json','result.json'):(state/name).write_bytes((ROOT/r.OLD/name).read_bytes())
    return state
def test_current_zero_effect_preserved(tmp_path):
    state=fixture(tmp_path);before={p.name:p.read_bytes() for p in state.iterdir()}
    r.check_zero_effect(tmp_path)
    assert before=={p.name:p.read_bytes() for p in state.iterdir()}
@pytest.mark.parametrize('key',['generation_requests','generation_network_post_attempts','generation_network_post_attempts_unknown','embedding_post_attempts','embedding_tokens_reserved'])
def test_any_attempt_or_ambiguity_rejected(tmp_path,key):
    state=fixture(tmp_path);p=state/'result.json';v=json.loads(p.read_bytes());v[key]=1;p.write_text(json.dumps(v))
    with pytest.raises(ValueError):r.check_zero_effect(tmp_path)
def test_intent_and_readmission_rejected(tmp_path):
    state=fixture(tmp_path);p=state/'turn-0-intent.json';p.write_text('{}')
    with pytest.raises(ValueError):r.check_zero_effect(tmp_path)
    p.unlink();(tmp_path/r.NEW).mkdir()
    with pytest.raises(ValueError):r.check_zero_effect(tmp_path)
