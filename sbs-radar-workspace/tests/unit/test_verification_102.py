from copy import deepcopy
from pathlib import Path
import json
import pytest
from sbs.comparison.literal_102 import literal_changes
from sbs.conversation.verification_102 import VerificationGenerator
from sbs.conversation.comparison_focus_094 import build_focus
ROOT=Path(__file__).resolve().parents[2]
def request077():return json.loads((ROOT/'deployment/state/generation-rag-077/generation-0-request.json').read_bytes())
def test_literal_operations_reconstruct_complete_text_and_offsets():
    focus=build_focus(json.loads(request077()['messages'][1]['content']))
    result=literal_changes(focus);left=result['before'];right=result['after']
    assert ''.join(op['before_text'] for op in result['operations'])==left['text']
    assert ''.join(op['after_text'] for op in result['operations'])==right['text']
    for op in result['operations']:
        assert left['text'][op['before_start']:op['before_end']]==op['before_text']
        assert right['text'][op['after_start']:op['after_end']]==op['after_text']
        assert op['before_source_start']==left['start']+op['before_start']
    assert result['semantic_materiality']=='not_evaluated'
@pytest.mark.parametrize('before,after',[('a b','a c'),('must act','must not act'),('one\n','one\ntwo\n'),('old\nnew','new'),('same','same'),('áé','áéñ')])
def test_generic_variants_not_case_gold(before,after):
    focus=build_focus(json.loads(request077()['messages'][1]['content']))
    for c in focus['citations']:
        c['text']=before if c['side']=='before' else after;c['end']=c['start']+len(c['text'])
    out=literal_changes(focus)
    assert ''.join(x['before_text'] for x in out['operations'])==before
    assert ''.join(x['after_text'] for x in out['operations'])==after
    assert out['text_equal']==(before==after)
def test_ambiguous_focal_alignment_is_rejected():
    focus=build_focus(json.loads(request077()['messages'][1]['content']));focus['citations'].append(deepcopy(focus['citations'][0]))
    with pytest.raises(ValueError):literal_changes(focus)
def candidate088():
    answer=json.loads((ROOT/'runs/sk05-sk07-json-wrapper-088-replay.json').read_bytes())['answer']
    return {k:answer[k] for k in ('material_claims','limitations')}
def make_generator(tmp_path,outputs):
    from sbs.conversation.databricks import DatabricksGenerator
    class Transport:
        calls=[];last_attempt={}
        def __call__(self,body):
            self.calls.append(deepcopy(body));self.last_attempt={'stage':'http_completed','http_status':200}
            value=outputs[len(self.calls)-1]
            return {'model':'gpt-oss-120b-080525','choices':[{'finish_reason':'stop','message':{'content':[{'type':'reasoning','summary':[{'type':'summary_text','text':'not evidence'}]},{'type':'text','text':json.dumps(value)}]}}]}
    transport=Transport()
    original=DatabricksGenerator(transport=transport,max_requests=4,max_tokens=5000,endpoint='databricks-gpt-oss-120b',expected_response_model='gpt-oss-120b-080525',max_input_chars=120000)
    return VerificationGenerator(original,tmp_path),transport

def test_two_pass_untrusted_draft_scoped_context_and_capture(tmp_path):
    bad=json.loads((ROOT/'deployment/state/generation-candidate-091/parsed-object.json').read_bytes())
    corrected=candidate088();generator,transport=make_generator(tmp_path,[bad,corrected]);request=request077();original=deepcopy(request)
    result=generator(request)
    assert result==corrected and request==original and generator.requests==2
    second=json.loads(transport.calls[1]['messages'][1]['content'])
    assert second['draft']['trust']=='untrusted_candidate_not_evidence'
    assert second['draft']['generated_claims']==bad
    assert 'tool_results' not in second and 'conversation_memory' not in second and 'evidence' not in second
    assert all(c['provision_id']=='art20.3' for c in second['comparison_focus']['citations'])
    assert all(len(c['text'])==c['end']-c['start'] for c in second['comparison_focus']['citations'])
    for phase in ('draft','verification'):
        assert (tmp_path/'turn-0'/phase/'intent.json').is_file()
        assert (tmp_path/'turn-0'/phase/'response.json').is_file()
    assert generator.budget=={'reserved':2,'network_known':2,'network_unknown':0}
    assert generator.last_attempt['quality_accepted'] is False

def test_four_turns_exact_eight_posts_no_reset(tmp_path):
    value=candidate088();generator,transport=make_generator(tmp_path,[value]*8)
    for _ in range(4):generator(request077())
    assert len(transport.calls)==8 and generator.requests==8
    with pytest.raises(ValueError,match='TURN_QUOTA'):generator(request077())
    assert len(transport.calls)==8

def test_verification_wrong_roles_rejected_no_fallback(tmp_path):
    wrong=json.loads((ROOT/'deployment/state/generation-candidate-091/parsed-object.json').read_bytes())
    generator,transport=make_generator(tmp_path,[candidate088(),wrong])
    with pytest.raises(ValueError,match='ROLES_REJECTED'):generator(request077())
    assert len(transport.calls)==2 and json.loads((tmp_path/'turn-0/verification.json').read_bytes())==wrong

def test_bad_draft_schema_stops_before_second_post(tmp_path):
    generator,transport=make_generator(tmp_path,[{'extra':'invalid'}])
    with pytest.raises(ValueError,match='DRAFT_SCHEMA_INVALID'):generator(request077())
    assert len(transport.calls)==1

@pytest.mark.parametrize('field',['comparison_focus','comparison_literal','draft','verification'])
def test_injected_verification_fields_denied_before_transport(tmp_path,field):
    request=request077();data=json.loads(request['messages'][1]['content']);data[field]={};request['messages'][1]['content']=json.dumps(data)
    generator,transport=make_generator(tmp_path,[])
    with pytest.raises(ValueError,match='CLIENT_FIELDS'):generator(request)
    assert not transport.calls

def test_same_model_schema_not_semantic_acceptance(tmp_path):
    value=candidate088();generator,transport=make_generator(tmp_path,[value,value])
    out=generator(request077())
    assert out==value and generator.last_attempt['quality_accepted'] is False
def test_real_localservice_uses_only_verified_pass(tmp_path):
    from sbs.runtime import LocalService
    from sbs.conversation.typed_content_091 import validate_candidate
    service=LocalService(mode='local');draft=candidate088();revised=deepcopy(draft);revised['limitations'].append('fixture verification pass')
    generator,transport=make_generator(tmp_path,[draft,revised]);service.generator=generator
    result=service.ask('offline102',json.loads(request077()['messages'][1]['content'])['question'],'cyber-504','art20.3')
    assert result['status']=='answered'
    assert service.last_result['answer']['material_claims']==revised['material_claims']
    assert 'fixture verification pass' in service.last_result['answer']['limitations']
    assert service.last_result['trace']['validation']['valid'] is True
    assert service.generator.requests==2 and service.embedding is None
    assert validate_candidate(revised,request077())['quality_accepted'] is False

def test_duplicate_phase_intent_stops_before_post(tmp_path):
    from sbs.conversation.generation_contract_086 import write_once
    write_once(tmp_path/'turn-0/draft','intent.json',{'fixture':'existing'})
    generator,transport=make_generator(tmp_path,[candidate088()])
    with pytest.raises(FileExistsError):generator(request077())
    assert transport.calls==[]

def test_verifier_foreign_ids_rejected_without_repair(tmp_path):
    value=candidate088();wrong=deepcopy(value);wrong['material_claims'][0]['citation_ids']=['outside-current-pack']
    generator,transport=make_generator(tmp_path,[value,wrong])
    with pytest.raises(ValueError,match='ROLES_REJECTED'):generator(request077())
    assert len(transport.calls)==2

def test_runner_preflight_without_auth_and_review_blocks(tmp_path,monkeypatch):
    import databricks.sdk,importlib.util
    def forbidden(*a,**k):raise AssertionError('auth forbidden')
    monkeypatch.setattr(databricks.sdk,'WorkspaceClient',forbidden)
    spec=importlib.util.spec_from_file_location('runner102test',ROOT/'runs/sk07-generation-rag-102.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    plan=module.preflight()
    assert plan['limits']['generation_posts']==8 and plan['limits']['draft_posts']==plan['limits']['verification_posts']==4
    monkeypatch.setattr(module,'preflight',lambda root:plan)
    with pytest.raises(FileNotFoundError):module.execute(tmp_path)
    assert not (tmp_path/module.STATE).exists()
def test_failed_phase_cannot_restart_instance(tmp_path):
    generator,transport=make_generator(tmp_path,[{'invalid':'draft'}])
    with pytest.raises(ValueError):generator(request077())
    with pytest.raises(ValueError,match='ALREADY_FAILED'):generator(request077())
    assert len(transport.calls)==1
