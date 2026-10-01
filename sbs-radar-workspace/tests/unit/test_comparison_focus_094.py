from copy import deepcopy
from pathlib import Path
import json
import pytest
from sbs.conversation.comparison_focus_094 import build_focus,ComparisonGenerator,TrialTypedTransport
from sbs.guardrails.comparison_roles_094 import validate_roles
ROOT=Path(__file__).resolve().parents[2]
def data077():return json.loads(json.loads((ROOT/'deployment/state/generation-rag-077/generation-0-request.json').read_bytes())['messages'][1]['content'])
def test_actual091_rejected_without_rewrite():
    candidate=json.loads((ROOT/'deployment/state/generation-candidate-091/parsed-object.json').read_bytes());original=deepcopy(candidate)
    result=validate_roles(candidate,build_focus(data077()))
    assert result['valid'] is False
    assert {e['code'] for e in result['errors']}=={'CLAIM_CITATION_ROLE_MISMATCH'}
    assert candidate==original

def test_actual088_roles_valid_not_semantic_quality():
    answer=json.loads((ROOT/'runs/sk05-sk07-json-wrapper-088-replay.json').read_bytes())['answer']
    generated={k:answer[k] for k in ('material_claims','limitations')}
    result=validate_roles(generated,build_focus(data077()))
    assert result['valid'] is True and result['semantic_entailment']=='not_evaluated'

def test_focus_only_focal_full_text_exact_sides():
    data=data077();focus=build_focus(data)
    assert len(focus['citations'])==2
    for citation in focus['citations']:
        original=next(c for c in data['evidence']['citations'] if c['citation_id']==citation['citation_id'])
        assert citation['text']==original['text']
        assert {k:citation[k] for k in ('document_id','version_id')}==data['context']['pair'][citation['side']]
        assert citation['provision_id']==data['context']['selected_provision_id']

@pytest.mark.parametrize('family',['cybersecurity','market_conduct'])
def test_generic_families_and_roles(family):
    data=data077();data['context']['family']=family;data['context']['pair']['family']=family;data['evidence']['pair']=deepcopy(data['context']['pair'])
    focus=build_focus(data);before=next(c['citation_id'] for c in focus['citations'] if c['side']=='before');after=next(c['citation_id'] for c in focus['citations'] if c['side']=='after')
    def generated(label,ids):return {'material_claims':[{'text':label+': fixture','citation_ids':ids}],'limitations':[]}
    for label,ids,ok in [('Antes',[before],True),('Después',[after],True),('Cambio',[before,after],True),('Antes',[before,after],False),('Cambio',[before],False),('Implicancia propuesta',['foreign'],False)]:
        assert validate_roles(generated(label,ids),focus)['valid'] is ok

@pytest.mark.parametrize('mutate',[
 lambda d:d['evidence']['pair']['before'].update(version_id='foreign'),
 lambda d:d['evidence']['citations'].append(deepcopy(d['evidence']['citations'][-1])),
 lambda d:d['evidence']['citations'][-1].update(version_id='foreign'),
])
def test_scope_conflicts(mutate):
    data=data077();mutate(data)
    with pytest.raises(ValueError):build_focus(data)

def test_only_server_authorized_reference():
    data=data077();reference=deepcopy(data['evidence']['citations'][-1]);reference.update(citation_id='ref',provision_id='reference-article');data['evidence']['citations'].append(reference)
    assert 'ref' not in [c['citation_id'] for c in build_focus(data)['citations']]
    assert 'ref' in [c['citation_id'] for c in build_focus(data,authorized_references=('reference-article',))['citations']]

def test_adapter_rejects_before_returning_to_conversation(tmp_path):
    candidate=json.loads((ROOT/'deployment/state/generation-candidate-091/parsed-object.json').read_bytes())
    class Delegate:
        last_attempt={};requests=0
        def __call__(self,request):self.requests+=1;self.request=deepcopy(request);return deepcopy(candidate)
    delegate=Delegate();adapter=ComparisonGenerator(delegate,tmp_path)
    request=json.loads((ROOT/'deployment/state/generation-rag-077/generation-0-request.json').read_bytes());original=deepcopy(request)
    with pytest.raises(ValueError,match='COMPARISON_ROLES_REJECTED'):adapter(request)
    assert request==original and delegate.requests==1
    assert 'comparison_focus' in json.loads(delegate.request['messages'][1]['content'])
    assert adapter.last_attempt['comparison_roles']['valid'] is False
@pytest.mark.parametrize('pair,provision',[('cyber-504','art20.3'),('market-3274','art27'),('market-3274','art29.1.4')])
def test_actual_localservice_pack_both_families(pair,provision):
    from sbs.runtime import LocalService
    service=LocalService(mode='local');entry=service.entry(pair,provision)
    question=next(q for q in service.query_cache if ('20.3' if provision=='art20.3' else '27' if provision=='art27' else '29.1') in q)
    # Actual cached vectors and full verified focus expansion; no reranker or
    # embedding initialization. This is scope coverage, not retrieval quality.
    result=service.rag(question,entry['context'])
    data={'context':entry['context'],'evidence':result['evidence']}
    focus=build_focus(data)
    assert focus['comparison_available']
    assert all(c['provision_id']==provision for c in focus['citations'])
    for c in focus['citations']:
        assert c['text']==service.originals[(c['document_id'],c['version_id'])][c['start']:c['end']]
    assert service.generator is None and service.embedding is None

def test_reference_cannot_replace_change_counterpart():
    data=data077();ref=deepcopy(data['evidence']['citations'][-1]);ref.update(citation_id='ref-after',provision_id='reference')
    data['evidence']['citations'].append(ref)
    focus=build_focus(data,authorized_references=('reference',))
    before=next(c['citation_id'] for c in focus['citations'] if c['side']=='before')
    value={'material_claims':[{'text':'Cambio: fixture','citation_ids':[before,'ref-after']}],'limitations':[]}
    checked=validate_roles(value,focus)
    assert not checked['valid'] and checked['errors'][0]['code']=='COMPARISON_FOCAL_CITATIONS_REQUIRED'

def test_four_captures_and_network_counters(tmp_path):
    class Delegate:
        last_attempt={}
        def __call__(self,body):
            self.last_attempt={'stage':'http_completed','http_status':200}
            return {'model':'model','choices':[{'finish_reason':'stop','message':{'content':[{'type':'text','text':'{}'}]}}]}
    transport=TrialTypedTransport(Delegate(),tmp_path,'model')
    for i in range(4):transport({'messages':[]})
    assert transport.network_post_attempts==4 and len(list(tmp_path.glob('generation-*/response.json')))==4
    with pytest.raises(ValueError):transport({'messages':[]})
    assert transport.network_post_attempts==4

def test_auth_failure_is_not_network_post(tmp_path):
    class Delegate:
        last_attempt={}
        def __call__(self,body):self.last_attempt={'stage':'authenticate'};raise RuntimeError('fixture')
    transport=TrialTypedTransport(Delegate(),tmp_path,'model')
    with pytest.raises(RuntimeError):transport({})
    assert transport.calls==1 and transport.network_post_attempts==0

def test_preflight_no_credentials(monkeypatch):
    import databricks.sdk,importlib.util
    def forbidden(*a,**k):raise AssertionError('credentials forbidden')
    monkeypatch.setattr(databricks.sdk,'WorkspaceClient',forbidden)
    spec=importlib.util.spec_from_file_location('runner094test',ROOT/'runs/sk07-generation-rag-094.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    assert len(module.preflight()['turns'])==4
def test_actual_localservice_rejects_inversion_without_answer(tmp_path):
    from sbs.runtime import LocalService
    service=LocalService(mode='local')
    candidate=json.loads((ROOT/'deployment/state/generation-candidate-091/parsed-object.json').read_bytes())
    class Delegate:
        last_attempt={};requests=0
        def __call__(self,request):self.requests+=1;return deepcopy(candidate)
    service.generator=ComparisonGenerator(Delegate(),tmp_path)
    question=data077()['question']
    result=service.ask('offline094',question,'cyber-504','art20.3')
    assert result['status']=='generation_error'
    assert service.generator.requests==1
    assert service.generator.last_attempt['stage']=='comparison_roles_rejected'
    assert result['answer']==''

def test_failed_capture_does_not_recount_previous_network(tmp_path):
    from sbs.conversation.generation_contract_086 import write_once
    class Delegate:
        last_attempt={'stage':'http_completed','http_status':200}
        def __call__(self,body):raise AssertionError('must not call')
    write_once(tmp_path/'generation-0','request.json',{})
    transport=TrialTypedTransport(Delegate(),tmp_path,'model')
    with pytest.raises(FileExistsError):transport({})
    assert transport.network_post_attempts==0
@pytest.mark.parametrize('timeout_location',['authenticate','post'])
def test_real_transport_timeout_is_ambiguous_not_known_post(tmp_path,monkeypatch,timeout_location):
    import requests
    from types import SimpleNamespace
    from sbs.conversation.databricks import SingleShotTransport
    calls=[]
    class Session:
        trust_env=True
        def post(self,*a,**kw):calls.append(1);raise requests.Timeout('fixture')
        def close(self):pass
    def authenticate():
        if timeout_location=='authenticate':raise requests.Timeout('fixture')
        return {}
    monkeypatch.setattr(requests,'Session',Session)
    base=SingleShotTransport(SimpleNamespace(config=SimpleNamespace(host='https://fixture.invalid',authenticate=authenticate)),endpoint='fixture')
    transport=TrialTypedTransport(base,tmp_path,'model')
    with pytest.raises(RuntimeError):transport({})
    assert len(calls)==(0 if timeout_location=='authenticate' else 1)
    assert transport.network_post_attempts==0
    assert transport.network_post_attempts_unknown==1
