"""Request-contract tests only; replayed fixtures do not prove model semantics."""
import importlib.util
import json
from pathlib import Path
from sbs.conversation.hybrid_125 import HybridGenerator as Baseline
ROOT=Path(__file__).resolve().parents[2]

def module(path,name):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
candidate=module('deployment/overlay212/src/sbs/conversation/hybrid_125.py','sbs.conversation.hybrid_212_test')
fixtures=module('tests/unit/test_hybrid_125.py','hybrid125_fixtures212')
rawfixtures=module('tests/unit/test_qwen_trial_110.py','qwen110_fixtures212')

def run(kind,path,request,response):
    old,raw,capture=rawfixtures.make(path,response)
    generator=kind(old.delegate,path,ROOT)
    output=generator(request)
    return output,raw.calls,capture

def test_added_policy_reaches_actual_model_request_without_other_changes(tmp_path):
    request=fixtures.source(3);original=json.dumps(request,sort_keys=True)
    response=fixtures.proposal_response()
    old,calls_old,_=run(Baseline,tmp_path/'baseline',request,response)
    new,calls_new,_=run(candidate.HybridGenerator,tmp_path/'candidate',request,response)
    assert json.dumps(request,sort_keys=True)==original
    assert old==new  # generated response is neither replaced nor repaired by this patch
    assert len(calls_old)==len(calls_new)==1
    previous=calls_old[0]['messages'][0]['content'];current=calls_new[0]['messages'][0]['content']
    assert 'como concurrente con el mandato principal' not in previous
    assert 'como concurrente con el mandato principal' in current
    assert 'Mantén las condiciones y excepciones que la fuente sí establece expresamente.' in current
    assert 'No clasifiques automáticamente toda aparición de «sin que» como prohibición' in current
    calls_new[0]['messages'][0]['content']=previous
    assert calls_new==calls_old  # model, temperature, question, evidence, ids, limits unchanged

def test_extractive_route_still_has_zero_posts_and_identical_source_text(tmp_path):
    request=fixtures.source(0)
    old,calls_old,_=run(Baseline,tmp_path/'baseline',request,fixtures.proposal_response())
    new,calls_new,_=run(candidate.HybridGenerator,tmp_path/'candidate',request,fixtures.proposal_response())
    assert old==new and calls_old==calls_new==[]

def test_material_failure_is_preserved_as_evaluation_case():
    actual=json.loads((ROOT/'runs/ui210/turn3-rendered.json').read_bytes())
    answer=[x['text'] for x in actual if x['role']=='assistant'][-1]
    assert 'condicionada a que no resulten exigibles trámites adicionales' in answer
    assert 'sin que resulten exigibles al usuario trámites o exigencias adicionales' in answer
    # No edited gold or automatic semantic PASS: this exact response must be rejected by independent review.
