from pathlib import Path
from copy import deepcopy
import importlib.util,json
import pytest
from sbs.conversation.hybrid_125 import HybridGenerator,extractive_claims,TemperatureZeroTransport
from sbs.conversation.comparison_focus_094 import build_focus
from sbs.comparison.literal_102 import literal_changes
ROOT=Path(__file__).resolve().parents[2]
def source(i=0):
    r=json.loads((ROOT/f'deployment/state/generation-rag-115/generation-{i}-source.json').read_bytes());return r

def make(tmp_path,response=None):
    spec=importlib.util.spec_from_file_location('fixture125',ROOT/'tests/unit/test_qwen_trial_110.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    old,raw,capture=m.make(tmp_path,response);return HybridGenerator(old.delegate,tmp_path,ROOT),raw,capture

def test_exact_quotes_and_lossless_operations():
    data=json.loads(source()['messages'][1]['content']);focus=build_focus(data);out,literal=extractive_claims(focus)
    assert out['material_claims'][0]['text']=='Antes: '+literal['before']['text']
    assert out['material_claims'][1]['text']=='Después: '+literal['after']['text']
    assert ''.join(o['before_text'] for o in literal['operations'])==literal['before']['text']
    assert ''.join(o['after_text'] for o in literal['operations'])==literal['after']['text']
    assert 'Fragmentos literales' in out['material_claims'][2]['text']
    assert out['material_claims'][2]['citation_ids']==[literal['before']['citation_id'],literal['after']['citation_id']]

def test_extractive_no_post_and_truthful_diagnostics(tmp_path):
    g,raw,capture=make(tmp_path);out=g(source())
    assert out['material_claims'][0]['text'].startswith('Antes: ')
    assert not raw.calls and g.requests==0 and capture.network_post_attempts==0
    assert g.last_attempt['source']=='source_extractive' and g.last_attempt['model_inferences_this_turn']==0
    assert g.last_attempt['response_model'] is None

def test_unicode_equal_and_empty():
    focus=build_focus(json.loads(source()['messages'][1]['content']))
    for c in focus['citations']:c['text']='á\nΩ  👩🏽';c['end']=c['start']+len(c['text'])
    out,literal=extractive_claims(focus)
    assert literal['text_equal'] and 'Igualdad literal verificada exclusivamente' in out['material_claims'][2]['text']
    for c in focus['citations']:c['text']='';c['end']=c['start']
    with pytest.raises(ValueError,match='EMPTY'):extractive_claims(focus)

def proposal_response(label='Implicancia propuesta'):
    data=json.loads(source(3)['messages'][1]['content']);f=build_focus(data);cid=f['citations'][0]['citation_id']
    value={'material_claims':[{'text':label+': propuesta de prueba para un proceso ficticio.','citation_ids':[cid]}],'limitations':['Fixture, no calidad normativa.']}
    return {'model':'qwen35-122b-a10b','choices':[{'finish_reason':'stop','message':{'content':[{'type':'text','text':json.dumps(value)}]}}]}

def test_three_extractions_one_proposal_one_post(tmp_path):
    g,raw,capture=make(tmp_path,proposal_response())
    for i in range(3):g(source(i))
    out=g(source(3))
    assert len(raw.calls)==g.requests==capture.network_post_attempts==1
    assert raw.calls[0]['temperature']==0 and raw.calls[0]['max_tokens']==8000
    assert 'Sólo Implicancia propuesta:' in raw.calls[0]['messages'][0]['content']
    assert [c['text'].split(':',1)[0] for c in out['material_claims']]==['Antes','Después','Cambio','Implicancia propuesta']
    assert json.loads((tmp_path/'generation-0/request.json').read_bytes())['temperature']==0
    assert g.last_attempt['source']=='source_extractive_plus_model_proposal'
    with pytest.raises(ValueError):g(source(3))
    assert len(raw.calls)==1

@pytest.mark.parametrize('label',['Antes','Después','Cambio'])
def test_out_of_intent_rejected_never_dropped(tmp_path,label):
    g,raw,capture=make(tmp_path,proposal_response(label))
    with pytest.raises(ValueError):g(source(3))
    assert len(raw.calls)==1
    assert (tmp_path/'hybrid-0-model-parsed.json').is_file()
    with pytest.raises(ValueError):g(source())

@pytest.mark.parametrize('kind',['implications_string','genie','missing_comparison'])
def test_unsupported_server_scope(tmp_path,kind):
    req=source();d=json.loads(req['messages'][1]['content'])
    if kind=='implications_string':d['implications']='false'
    elif kind=='genie':d['tool_results']['genie']={}
    else:d['tool_results'].pop('comparison')
    req['messages'][1]['content']=json.dumps(d);g,raw,capture=make(tmp_path)
    with pytest.raises(ValueError):g(req)
    assert not raw.calls

def test_actual_localservice_quote_guards_and_no_inference(tmp_path):
    from sbs.runtime import LocalService
    g,raw,capture=make(tmp_path);service=LocalService(mode='local');service.generator=g
    d=json.loads(source()['messages'][1]['content'])
    result=service.ask('offline125',d['question'],'cyber-504','art20.3')
    assert result['status']=='answered' and service.last_result['trace']['validation']['valid']
    assert service.last_result['trace']['generator']['source']=='source_extractive'
    assert not raw.calls

@pytest.mark.parametrize('question',['Resume el artículo seleccionado','Hola, explícame este documento','¿Cuántas diferencias hay en el artículo?'])
def test_noncomparison_or_mixed_question_rejected(tmp_path,question):
    req=source();d=json.loads(req['messages'][1]['content']);d['question']=question;req['messages'][1]['content']=json.dumps(d)
    g,raw,capture=make(tmp_path)
    with pytest.raises(ValueError,match='SCOPE'):g(req)
    assert not raw.calls

def test_temperature_error_consumes_one_attempt_no_retry(tmp_path):
    g,raw,capture=make(tmp_path)
    def fail(body):
        assert body['temperature']==0
        raise RuntimeError('endpoint rejected parameter')
    class Fail:
        last_attempt={'stage':'http_error','http_status':400}
        calls=0
        def __call__(self,body):self.calls+=1;return fail(body)
    failed=Fail();capture.delegate=failed
    with pytest.raises(RuntimeError):g(source(3))
    assert failed.calls==g.requests==1
    assert g.last_attempt['model_inferences_this_turn'] is None
    with pytest.raises(ValueError):g(source(3))
    assert failed.calls==1

def test_preflight_no_auth_and_review_required(tmp_path,monkeypatch):
    import databricks.sdk
    def forbidden(*a,**k):raise AssertionError('SDK forbidden')
    monkeypatch.setattr(databricks.sdk,'WorkspaceClient',forbidden)
    spec=importlib.util.spec_from_file_location('runner125',ROOT/'runs/sk07-generation-rag-125.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    plan=m.preflight();assert plan['expected_generation_posts']==1 and plan['limits']['generation_posts']==4
    monkeypatch.setattr(m,'preflight',lambda root:plan)
    with pytest.raises(FileNotFoundError):m.execute(tmp_path)
    assert not (tmp_path/m.STATE).exists()

def test_literal_changes_never_claim_equality_for_different_text():
    focus=build_focus(json.loads(source()['messages'][1]['content']))
    for c in focus['citations']:
        c['text']='á b' if c['side']=='before' else 'á c 👩🏽';c['end']=c['start']+len(c['text'])
    out,literal=extractive_claims(focus)
    assert not literal['text_equal'] and 'Igualdad literal verificada' not in out['material_claims'][2]['text']
    for op in literal['operations']:
        for side in ('before','after'):
            c=literal[side]
            assert c['text'][op[side+'_source_start']-c['start']:op[side+'_source_end']-c['start']]==op[side+'_text']

def test_real_initializer_no_auth_and_temperature_boundary(tmp_path):
    from types import SimpleNamespace
    from sbs.runtime import LocalService
    from sbs.conversation.hybrid_125 import initialize_hybrid_models
    from sbs.conversation.qwen_trial_110 import load_candidate
    def forbidden():raise AssertionError('auth forbidden')
    client=SimpleNamespace(config=SimpleNamespace(host='https://dbc-0410b264-20c7.cloud.databricks.com',authenticate=forbidden))
    service=LocalService(mode='local');capture=initialize_hybrid_models(service,ROOT,tmp_path,load_candidate(ROOT),client_factory=lambda:client)
    assert isinstance(service.generator,HybridGenerator) and capture.calls==0
    assert isinstance(service.generator.delegate.transport,TemperatureZeroTransport)
    assert service.generator.requests==0 and service.embedding.calls_attempted==0

def test_auth_failure_precedes_admission(tmp_path,monkeypatch):
    import databricks.sdk.core
    spec=importlib.util.spec_from_file_location('runner125auth',ROOT/'runs/sk07-generation-rag-125.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    plan=m.preflight();monkeypatch.setattr(m,'preflight',lambda root:plan);monkeypatch.setattr(m,'check_review',lambda root:None)
    def rejected(**kwargs):raise RuntimeError('normal credential cache failure')
    monkeypatch.setattr(databricks.sdk.core,'Config',rejected)
    with pytest.raises(RuntimeError):m.execute(tmp_path)
    assert not (tmp_path/m.STATE).exists()

def test_public_literal_change_readability_no_technical_offsets():
    focus=build_focus(json.loads(source()['messages'][1]['content']));out,literal=extractive_claims(focus)
    text=out['material_claims'][2]['text']
    assert 'Unicode' not in text and 'Rangos' not in text and 'source_start' not in text
    assert any(word in text for word in ('Texto añadido','Texto eliminado','Texto reemplazado'))
    assert all('before_source_start' in op for op in literal['operations'])
    assert any(op['operation']=='equal' for op in literal['operations'])
