import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('sbs.app133.runtime218_test',ROOT/'deployment/overlay218/src/sbs/app133/runtime.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

def test_safe_vocab_only_no_exception_or_raw_payload(caplog):
    component=SimpleNamespace(last_attempt={'stage':'proposal_generation','generation':{'stage':'generated_json'},'response':'SECRET_DOCUMENT'})
    transport=SimpleNamespace(last_attempt={'stage':'typed_content','typed_content':{'code':'TYPED_FINISH_NOT_STOP'},'headers':{'Authorization':'SECRET_TOKEN'}})
    out=m.log_generation_failure(ValueError('SECRET_EXCEPTION'),component,transport)
    assert out['error_code']=='TYPED_FINISH_NOT_STOP'
    assert out['stage']=='proposal_generation'
    assert 'SECRET' not in caplog.text
    assert 'SBS_GENERATION_FAILURE' in caplog.text

def test_unrecognized_provider_values_are_not_logged(caplog):
    component=SimpleNamespace(last_attempt={'stage':'SECRET_STAGE','generation':{'stage':'SECRET_NESTED'}})
    transport=SimpleNamespace(last_attempt={'stage':'SECRET_TRANSPORT','error_code':'SECRET_CODE'})
    out=m.log_generation_failure(RuntimeError('SECRET_EXCEPTION'),component,transport)
    assert all(out[k]=='unknown' for k in ('stage','generation_stage','transport_stage','error_code'))
    assert 'SECRET' not in caplog.text

def test_budget_change_is_exact_constant_only():
    old=(ROOT/'deployment/state/incremental-package210/delta/src/sbs/app133/lifecycle210.py').read_text()
    new=(ROOT/'deployment/overlay218/src/sbs/app133/lifecycle210.py').read_text()
    assert new==old.replace("CAPS = {'generation_posts': 8, 'embedding_posts': 8, 'embedding_tokens': 80000}","CAPS = {'generation_posts': 6, 'embedding_posts': 5, 'embedding_tokens': 50000}",1)

def test_malformed_stage_types_are_redacted(caplog):
    component=SimpleNamespace(last_attempt={'stage':['SECRET_STAGE'],'generation':{'stage':{'SECRET_NESTED':1}}})
    transport=SimpleNamespace(last_attempt={'stage':['SECRET_TRANSPORT'],'typed_content':{'code':{'SECRET_CODE':1}}})
    out=m.log_generation_failure(ValueError('SECRET_EXCEPTION'),component,transport)
    assert all(out[k]=='unknown' for k in ('stage','generation_stage','transport_stage','error_code'))
    assert 'SECRET' not in caplog.text

def test_diagnostic_failure_cannot_mask_generator_exception(tmp_path,monkeypatch):
    class BrokenGenerator:
        last_attempt={'stage':'proposal_generation'}
        def __init__(self,*args):pass
        def __call__(self,request):raise ValueError('ORIGINAL_GENERATOR_ERROR')
    monkeypatch.setattr(m,'HybridGenerator',BrokenGenerator)
    def broken_logger(*args):raise OSError('LOG_WRITE_FAILED')
    monkeypatch.setattr(m,'log_generation_failure',broken_logger)
    budget=m.ProcessBudget(deadline=2000,max_posts=8,clock=lambda:1000)
    raw=SimpleNamespace(last_attempt={})
    route=m.RouteGenerator(raw,tmp_path,ROOT,budget)
    request=json.loads((ROOT/'deployment/state/generation-rag-115/generation-3-source.json').read_bytes())
    import pytest
    with pytest.raises(ValueError,match='ORIGINAL_GENERATOR_ERROR'):
        route(request)
