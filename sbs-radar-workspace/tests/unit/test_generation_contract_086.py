"""Offline diagnostic cases, not reconstructed responses from077."""
import json
from types import SimpleNamespace
import pytest
from sbs.conversation.generation_contract_086 import CapturingTransport, DiagnosticGenerator, classify_content, reserve_continuation

def response(content):return {'model':'model','choices':[{'finish_reason':'stop','message':{'content':content}}],'usage':{'completion_tokens':5}}

@pytest.mark.parametrize('content,code',[('```json\n{}\n```','generated_json_syntax'),('[]','generated_json_non_object'),('prefix {}','generated_json_syntax'),('{bad','generated_json_syntax')])
def test_exact_response_captured_before_parse_and_failure_is_specific(tmp_path,content,code):
    calls=[]
    def transport(body):calls.append(body);return response(content)
    archive=CapturingTransport(transport,tmp_path)
    g=DiagnosticGenerator(transport=archive,max_requests=1,max_tokens=100,endpoint='ep',expected_response_model='model')
    with pytest.raises(ValueError):g({'messages':[{'role':'user','content':'fixture'}]})
    saved=json.loads((tmp_path/'response.json').read_bytes())
    assert saved==response(content) and g.last_attempt['diagnostic']['code']==code
    assert len(calls)==1
    with pytest.raises(ValueError):g({'messages':[{'role':'user','content':'fixture'}]})
    assert len(calls)==1

def test_valid_object_passes_unchanged_and_diagnostics_do_not_leak_content(tmp_path):
    raw='{"material_claims":[],"limitations":["PRIVATE_SENTINEL"]}'
    t=CapturingTransport(lambda _:response(raw),tmp_path)
    g=DiagnosticGenerator(transport=t,max_requests=1,max_tokens=100,endpoint='ep',expected_response_model='model')
    assert g({'messages':[{'role':'user','content':'fixture'}]})==json.loads(raw)
    assert 'PRIVATE_SENTINEL' not in json.dumps(g.last_attempt)
    assert classify_content(raw)['code']=='generated_json_object'

def test_one_post_reservation_preserves_prior_quota(tmp_path):
    state=tmp_path/'086'
    reserve_continuation(state,prior_reserved=1,total_limit=4,parent_sha256='a'*64)
    admission=json.loads((state/'admission.json').read_bytes())
    assert admission['aggregate_reserved']==2 and admission['remaining_after_reservation']==2
    with pytest.raises(FileExistsError):reserve_continuation(state,prior_reserved=1,total_limit=4,parent_sha256='a'*64)
    with pytest.raises(ValueError):reserve_continuation(tmp_path/'extra',prior_reserved=4,total_limit=4,parent_sha256='a'*64)


@pytest.mark.parametrize('kind',['identity','truncated'])
def test_existing_identity_and_truncation_rejection_stay_intact(tmp_path,kind):
    envelope=response('{}')
    if kind=='identity':envelope['model']='wrong'
    else:envelope['choices'][0]['finish_reason']='length'
    t=CapturingTransport(lambda _:envelope,tmp_path)
    g=DiagnosticGenerator(transport=t,max_requests=1,max_tokens=100,endpoint='ep',expected_response_model='model')
    with pytest.raises(ValueError):g({'messages':[{'role':'user','content':'fixture'}]})
    assert (tmp_path/'response.json').is_file() and g.requests==1
    assert g.last_attempt['stage']==('model_identity' if kind=='identity' else 'truncated')


def test_persistence_failure_is_unconfirmed_and_never_retried(tmp_path):
    (tmp_path/'response.json').write_text('prior artifact')
    calls=[]
    def invoke(body):calls.append(body);return response('{}')
    t=CapturingTransport(invoke,tmp_path)
    g=DiagnosticGenerator(transport=t,max_requests=1,max_tokens=100,endpoint='ep',expected_response_model='model')
    with pytest.raises(RuntimeError,match='ARCHIVE_UNCONFIRMED'):g({'messages':[{'role':'user','content':'fixture'}]})
    assert g.last_attempt['response_archive']=='unconfirmed' and len(calls)==1
    assert (tmp_path/'response.json').read_text()=='prior artifact'


def test_diagnostic_does_not_confuse_json_object_with_schema_or_citations(tmp_path):
    from jsonschema import Draft202012Validator
    from pathlib import Path
    invalid={'unexpected':'not GeneratedClaims'}
    t=CapturingTransport(lambda _:response(json.dumps(invalid)),tmp_path)
    g=DiagnosticGenerator(transport=t,max_requests=1,max_tokens=100,endpoint='ep',expected_response_model='model')
    candidate=g({'messages':[{'role':'user','content':'fixture'}]})
    schema=json.loads((Path(__file__).resolve().parents[2]/'src/sbs/conversation/GeneratedClaims.json').read_bytes())
    assert candidate==invalid and not Draft202012Validator(schema).is_valid(candidate)
    assert g.last_attempt['diagnostic']['code']=='generated_json_object'
