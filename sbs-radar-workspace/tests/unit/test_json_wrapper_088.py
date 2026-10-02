"""Strict whole-response compatibility; synthetic adversarial fixtures."""
import json
import pytest
from sbs.conversation.json_wrapper_088 import unwrap_json_object,StrictCaptureTransport
from sbs.conversation.databricks import DatabricksGenerator

@pytest.mark.parametrize('text,mode',[('{"x":1}','raw_json'),('```json\n{"x":1}\n```','json_fence'),(' \n```json\r\n{"x":1}\r\n``` \n','json_fence')])
def test_only_raw_or_one_complete_json_fence(text,mode):
    body,metadata=unwrap_json_object(text)
    assert json.loads(body)=={'x':1} and metadata['wrapper']==mode

@pytest.mark.parametrize('text',['prefix {"x":1}','```json\n{}\n``` suffix','prefix ```json\n{}\n```','```\n{}\n```','```JSON\n{}\n```','```json\n{}\n```\n```json\n{}\n```','{"x":1,}','{"x":1,"x":2}','{"x":NaN}','{"x":1e999}','[]','null','{}{}','```json\n[]\n```'])
def test_no_extraction_repair_ambiguity_or_nonobject(text):
    with pytest.raises(ValueError):unwrap_json_object(text)

def test_captures_original_fence_and_only_changes_message_content(tmp_path):
    raw='```json\n{"x":1}\n```'
    response={'model':'model','choices':[{'finish_reason':'stop','message':{'content':raw}}],'usage':{'total_tokens':3}}
    calls=[]
    def invoke(body):calls.append(body);return response
    transport=StrictCaptureTransport(invoke,tmp_path,max_requests=1)
    generator=DatabricksGenerator(transport=transport,max_requests=1,max_tokens=50,endpoint='ep',expected_response_model='model')
    assert generator({'messages':[{'role':'user','content':'fixture'}]})=={'x':1}
    assert json.loads((tmp_path/'generation-0/response.json').read_bytes())==response
    assert response['choices'][0]['message']['content']==raw
    assert len(calls)==1 and generator.last_attempt['content_wrapper']['wrapper']=='json_fence'


@pytest.mark.parametrize('kind',['identity','length'])
def test_wrapper_keeps_model_and_truncation_checks(tmp_path,kind):
    response={'model':'wrong' if kind=='identity' else 'model','choices':[{'finish_reason':'length' if kind=='length' else 'stop','message':{'content':'```json\n{}\n```'}}]}
    transport=StrictCaptureTransport(lambda _:response,tmp_path,max_requests=1,expected_response_model='model')
    generator=DatabricksGenerator(transport=transport,max_requests=1,max_tokens=50,endpoint='ep',expected_response_model='model')
    with pytest.raises(ValueError,match='model_mismatch' if kind=='identity' else 'truncated'):generator({'messages':[{'role':'user','content':'fixture'}]})
    assert transport.calls==1 and (tmp_path/'generation-0/response.json').is_file()


def test_exact_archived086_replay_validators_without_credentials(monkeypatch):
    import importlib.util
    from pathlib import Path
    import databricks.sdk
    def forbidden(*a,**kw):raise AssertionError('credential initialization forbidden')
    monkeypatch.setattr(databricks.sdk,'WorkspaceClient',forbidden)
    root=Path(__file__).resolve().parents[2]
    spec=importlib.util.spec_from_file_location('replay088_test',root/'runs/sk05-sk07-json-wrapper-088-replay.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    result=module.replay()
    assert result['status']=='technical_answer_candidate' and result['answer_validation']['valid'] is True
    assert all(result['adversarial_probes'].values())
    assert result['quality_accepted'] is False and result['new_inferences']==0
