from copy import deepcopy
from pathlib import Path
import json
import pytest
from sbs.conversation.qwen_trial_110 import QwenLiteralGenerator,load_candidate
from sbs.conversation.databricks import DatabricksGenerator
from sbs.conversation.comparison_focus_094 import TrialTypedTransport
ROOT=Path(__file__).resolve().parents[2]
def request():return json.loads((ROOT/'deployment/state/generation-rag-077/generation-0-request.json').read_bytes())
def value():
    answer=json.loads((ROOT/'runs/sk05-sk07-json-wrapper-088-replay.json').read_bytes())['answer'];return {k:answer[k] for k in ('material_claims','limitations')}
def make(tmp_path,response=None):
    class Raw:
        calls=[];last_attempt={}
        def __call__(self,body):
            self.calls.append(deepcopy(body));self.last_attempt={'stage':'http_completed','http_status':200}
            return response or {'model':'qwen35-122b-a10b','choices':[{'finish_reason':'stop','message':{'content':[{'type':'text','text':json.dumps(value())}]}}]}
    raw=Raw();capture=TrialTypedTransport(raw,tmp_path,'qwen35-122b-a10b')
    base=DatabricksGenerator(transport=capture,max_requests=4,max_tokens=8000,endpoint='databricks-qwen35-122b-a10b',expected_response_model='qwen35-122b-a10b',max_input_chars=120000)
    return QwenLiteralGenerator(base,tmp_path),raw,capture

def test_one_call_per_turn_and_four_limit(tmp_path):
    generator,raw,capture=make(tmp_path)
    for _ in range(4):assert generator(request())==value()
    assert len(raw.calls)==4 and generator.requests==4
    assert all(body['max_tokens']==8000 and body['stream'] is False for body in raw.calls)
    assert all('comparison_literal' in json.loads(body['messages'][1]['content']) for body in raw.calls)
    with pytest.raises(ValueError):generator(request())
    assert len(raw.calls)==4

def test_actual109_truncation_captured_then_rejected(tmp_path):
    smoke=json.loads((ROOT/'runs/sk05-generation-candidates-109-databricks-qwen35-122b-a10b.json').read_bytes())
    response={'model':smoke['model'],'choices':[{'finish_reason':smoke['finish_reasons'][0],'message':{'content':smoke['outputs'][0]}}]}
    generator,raw,capture=make(tmp_path,response)
    with pytest.raises(ValueError):generator(request())
    assert len(raw.calls)==1
    assert json.loads((tmp_path/'generation-0/response.json').read_bytes())==response
    with pytest.raises(ValueError):generator(request())
    assert len(raw.calls)==1

@pytest.mark.parametrize('kind',['reasoning_only','unknown_type','wrong_model'])
def test_unobserved_success_not_assumed(tmp_path,kind):
    content=[{'type':'reasoning','summary':[{'type':'summary_text','text':'{}'}]}] if kind=='reasoning_only' else [{'type':'alien','text':'{}'}] if kind=='unknown_type' else [{'type':'text','text':json.dumps(value())}]
    generator,raw,capture=make(tmp_path,{'model':'wrong' if kind=='wrong_model' else 'qwen35-122b-a10b','choices':[{'finish_reason':'stop','message':{'content':content}}]})
    with pytest.raises(ValueError):generator(request())
    assert len(raw.calls)==1
def test_real_initializer_loads_pinned_local_models_without_auth(tmp_path):
    from types import SimpleNamespace
    from sbs.runtime import LocalService
    from sbs.conversation.qwen_trial_110 import initialize_trial_models
    def forbidden():raise AssertionError('authentication forbidden')
    client=SimpleNamespace(config=SimpleNamespace(host='https://dbc-0410b264-20c7.cloud.databricks.com',authenticate=forbidden))
    service=LocalService(mode='local')
    transport=initialize_trial_models(service,ROOT,tmp_path,load_candidate(ROOT),client_factory=lambda:client)
    assert service.generator.max_tokens==8000 and service.generator.requests==0
    assert service.generator.endpoint=='databricks-qwen35-122b-a10b'
    assert service.generator.expected_response_model=='qwen35-122b-a10b'
    assert service.embedding.max_calls==2 and service.embedding.calls_attempted==0
    assert service.reranker is not None and transport.calls==0
    assert service.provenance['generation_selection']['quality_accepted'] is False

def test_guard_rejects_inverted_citations_after_single_call(tmp_path):
    wrong=json.loads((ROOT/'deployment/state/generation-candidate-091/parsed-object.json').read_bytes())
    response={'model':'qwen35-122b-a10b','choices':[{'finish_reason':'stop','message':{'content':[{'type':'text','text':json.dumps(wrong)}]}}]}
    generator,raw,capture=make(tmp_path,response)
    with pytest.raises(ValueError,match='ROLES_REJECTED'):generator(request())
    assert len(raw.calls)==1
    assert json.loads((tmp_path/'generation-0-parsed.json').read_bytes())==wrong

def test_selection_strict_budget_and_observation_pins(tmp_path):
    import shutil
    cfg=json.loads((ROOT/'config/generation-selection-110.json').read_bytes())
    for name in ('config/generation-selection-110.json',cfg['observation_path']):
        path=tmp_path/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,path)
    assert load_candidate(tmp_path)['max_output_tokens']==8000
    cfg['max_output_tokens']=16000;(tmp_path/'config/generation-selection-110.json').write_text(json.dumps(cfg))
    with pytest.raises(ValueError,match='LIMIT'):load_candidate(tmp_path)
    cfg['max_output_tokens']=8000;(tmp_path/'config/generation-selection-110.json').write_text(json.dumps(cfg))
    (tmp_path/cfg['observation_path']).write_text('{}')
    with pytest.raises(ValueError,match='DRIFT'):load_candidate(tmp_path)

def test_preflight_no_auth_and_no_admission_without_review(tmp_path,monkeypatch):
    import databricks.sdk,importlib.util
    def forbidden(*a,**k):raise AssertionError('SDK forbidden')
    monkeypatch.setattr(databricks.sdk,'WorkspaceClient',forbidden)
    spec=importlib.util.spec_from_file_location('runner110test',ROOT/'runs/sk07-generation-rag-110.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    plan=m.preflight();assert plan['limits']['generation_output_tokens_each']==8000
    monkeypatch.setattr(m,'preflight',lambda root:plan)
    with pytest.raises(FileNotFoundError):m.execute(tmp_path)
    assert not (tmp_path/m.STATE).exists()

def test_localservice_final_guardrails_unchanged(tmp_path):
    from sbs.runtime import LocalService
    service=LocalService(mode='local');generator,raw,capture=make(tmp_path);service.generator=generator
    result=service.ask('offline110',json.loads(request()['messages'][1]['content'])['question'],'cyber-504','art20.3')
    assert result['status']=='answered' and len(raw.calls)==1
    assert service.last_result['trace']['validation']['valid'] is True
    assert service.generator.last_attempt['quality_accepted'] is False
