from copy import deepcopy
import json
from pathlib import Path
import pytest
from sbs.conversation.typed_content_091 import normalize_response,TypedCaptureTransport,validate_candidate
from sbs.conversation.databricks import DatabricksGenerator
MODEL='gpt-oss-120b-080525'
ROOT=Path(__file__).resolve().parents[2]
def envelope(content,finish='stop',model=MODEL):
    return {'model':model,'choices':[{'finish_reason':finish,'message':{'content':content}}]}
def text(value):return {'type':'text','text':value}
def reasoning():return {'type':'reasoning','summary':[{'type':'summary_text','text':'UNTRUSTED_REASONING'}]}
def test_order_and_preservation():
    raw=envelope([reasoning(),text('{"x":'),reasoning(),text('1}')]);saved=deepcopy(raw)
    normalized,meta=normalize_response(raw,MODEL)
    assert raw==saved
    assert normalized['choices'][0]['message']['content']=='{"x":1}'
    assert meta['text_block_indices']==[1,3] and meta['reasoning_blocks_excluded']==2
    assert 'UNTRUSTED_REASONING' not in json.dumps(meta)
@pytest.mark.parametrize('content',[
    ' {} ',[],[reasoning()],[text('')],[text('{}'), 'arbitrary'],
    [{'type':'image','text':'{}'}],[{'type':'text','text':3}],
    [{'type':'text','text':'{}','extra':True}],
    [{'type':'reasoning','summary':'{}'},text('{}')],
    [{'type':'reasoning','summary':[text('{}')]},text('{}')],
    [text('{}'),text(' extra')],[text('{"a":1,"a":2}')],
    [text('```json\n{}\n```\nprose')],
])
def test_reject_content(content):
    with pytest.raises(ValueError):normalize_response(envelope(content),MODEL)
@pytest.mark.parametrize('finish,model',[('length',MODEL),('tool_calls',MODEL),(None,MODEL),('stop','other')])
def test_reject_envelope(finish,model):
    with pytest.raises(ValueError):normalize_response(envelope([text('{}')],finish,model),MODEL)
def test_capture_before_rejection_and_single_call(tmp_path):
    raw=envelope([text('{}')],finish='length')
    class Delegate:
        last_attempt={'http_status':200}
        calls=0
        def __call__(self,body):self.calls+=1;return raw
    delegate=Delegate();transport=TypedCaptureTransport(delegate,tmp_path,expected_response_model=MODEL)
    with pytest.raises(ValueError):transport({'messages':[]})
    assert json.loads((tmp_path/'response.json').read_text())==raw
    with pytest.raises(ValueError):transport({'messages':[]})
    assert delegate.calls==1
    assert json.loads((tmp_path/'normalization.json').read_text())['status']=='rejected'
def test_generator_compatibility(tmp_path):
    raw=envelope([reasoning(),text('```json\n{"material_claims":[],"limitations":[]}\n```')])
    transport=TypedCaptureTransport(lambda body:raw,tmp_path,expected_response_model=MODEL)
    generator=DatabricksGenerator(transport=transport,max_requests=1,max_tokens=5000,expected_response_model=MODEL)
    assert generator({'messages':[{'role':'user','content':'fixture'}]})=={'material_claims':[],'limitations':[]}
    assert generator.last_attempt['stage']=='completed'
    with pytest.raises(ValueError):generator({'messages':[]})
def test_real_validators_reject_schema_and_citation():
    body=json.loads((ROOT/'deployment/state/generation-rag-077/generation-0-request.json').read_text())
    assert validate_candidate({'wrong':'schema'},body)['status']=='generated_contract_rejected'
    source=json.loads((ROOT/'runs/sk05-sk07-json-wrapper-088-replay.json').read_text())['answer']
    generated={k:deepcopy(source[k]) for k in ('material_claims','limitations')}
    result=validate_candidate(generated,body)
    assert result['status']=='technical_answer_candidate' and result['quality_accepted'] is False
    generated['material_claims'][0]['citation_ids']=['invented']
    assert validate_candidate(generated,body)['status']=='answer_contract_rejected'
def test_observed090_is_truncated_not_accepted():
    smoke=json.loads((ROOT/'runs/sk05-generation-candidates-090-databricks-gpt-oss-120b.json').read_text())
    with pytest.raises(ValueError,match='TYPED_FINISH_NOT_STOP'):
        normalize_response(envelope(smoke['outputs'][0],smoke['finish_reasons'][0],smoke['model']),MODEL)
def runner():
    import importlib.util
    spec=importlib.util.spec_from_file_location('candidate091test',ROOT/'runs/sk05-sk07-generation-candidate-091.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def test_preflight_without_credentials(monkeypatch):
    import databricks.sdk
    def forbidden(*a,**k):raise AssertionError('credentials forbidden')
    monkeypatch.setattr(databricks.sdk,'WorkspaceClient',forbidden)
    plan,selection,body=runner().preflight()
    assert plan['budget']['generation_posts']==1 and body['max_tokens']==5000
    assert selection['quality_accepted'] is False

def test_durable_one_post_and_full_replay(tmp_path,monkeypatch):
    import databricks.sdk
    from types import SimpleNamespace
    module=runner();plan,selection,body=module.preflight()
    for path in [module.PLAN,plan['request']]:
        dest=tmp_path/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((ROOT/path).read_bytes())
    monkeypatch.setattr(module,'preflight',lambda root:(plan,selection,body))
    monkeypatch.setattr(module,'check_review',lambda root:None)
    monkeypatch.setattr(module,'sha',lambda path:'a'*64)
    monkeypatch.setattr(databricks.sdk,'WorkspaceClient',lambda **kwargs:SimpleNamespace(config=SimpleNamespace(host=plan['workspace_host'])))
    # Explicit synthetic adaptation of archived086 for plumbing only; never an
    # actual GPT-OSS observation or claim of semantic quality.
    original=json.loads((ROOT/'deployment/state/generation-contract-086/response.json').read_text())
    raw=envelope([reasoning(),text(original['choices'][0]['message']['content'])])
    calls=[]
    class Delegate:
        last_attempt={'http_status':200}
        def __call__(self,request):calls.append(request);return raw
    monkeypatch.setattr(module,'SingleShotTransport',lambda *a,**k:Delegate())
    result=module.execute(tmp_path)
    assert result['status']=='technical_answer_candidate' and result['quality_accepted'] is False
    assert calls==[body] and 'answer' not in result
    assert (tmp_path/module.STATE/'replay.json').is_file()
    with pytest.raises(FileExistsError):module.execute(tmp_path)
    assert len(calls)==1

def test_review_required_before_admission(tmp_path,monkeypatch):
    module=runner();real=module.preflight()
    monkeypatch.setattr(module,'preflight',lambda root:real)
    with pytest.raises(FileNotFoundError):module.execute(tmp_path)
    assert not (tmp_path/module.STATE).exists()
