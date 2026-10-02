from pathlib import Path
from copy import deepcopy
import json
import pytest
from sbs.conversation.focal_packet_115 import focal_packet,restore_packet,transform_request,FocalGenerator
ROOT=Path(__file__).resolve().parents[2]
def source(i=1):
    body=json.loads((ROOT/f'deployment/state/generation-rag-110/generation-{i}/request.json').read_bytes())
    data=json.loads(body['messages'][1]['content']);data.pop('comparison_focus');data.pop('comparison_literal');return data

def test_retains_exact_quotes_metadata_and_reversible_source():
    data=source();original=deepcopy(data);packet,manifest=focal_packet(data)
    assert data==original and restore_packet(packet,manifest)==original
    assert len(packet['evidence']['citations'])==2
    for c in packet['evidence']['citations']:
        assert c==next(x for x in data['evidence']['citations'] if x['citation_id']==c['citation_id'])
        assert c['text'].encode()==next(x['text'].encode() for x in data['evidence']['citations'] if x['citation_id']==c['citation_id'])
    for k in ('question','context','conversation_memory','implications','limitations','scope','fictitious_process_context'):assert packet[k]==data[k]
    assert not {'tool_results','compaction','comparison_focus','comparison_literal'} & packet.keys()
    assert len(json.dumps(packet,ensure_ascii=False))<15000

def test_dynamic_required_citations_both_sides_exact():
    packet,manifest=focal_packet(source(0));ids=packet['required_citations']
    assert len(ids['Antes']['required_ids'])==len(ids['Después']['required_ids'])==1
    assert ids['Cambio']['required_ids']==ids['Antes']['required_ids']+ids['Después']['required_ids']
    assert set(ids['Cambio']['required_ids'])=={c['citation_id'] for c in packet['evidence']['citations']}

def test_tampered_packet_or_manifest_rejected():
    packet,manifest=focal_packet(source());packet['evidence']['citations'][0]['text']+='changed'
    with pytest.raises(ValueError):restore_packet(packet,manifest)
    packet,manifest=focal_packet(source());manifest['removed_fields']['tool_results']={}
    with pytest.raises(ValueError):restore_packet(packet,manifest)

@pytest.mark.parametrize('kind',['extra','client_policy','genie','missing_side'])
def test_unsupported_scope_not_silently_reduced(kind):
    data=source()
    if kind=='extra':data['unknown_material_context']='must preserve'
    elif kind=='client_policy':data['required_citations']={}
    elif kind=='genie':data['tool_results']['genie']={'rows':[[1]]}
    else:data['evidence']['citations']=[c for c in data['evidence']['citations'] if c['version_id']!=data['context']['pair']['before']['version_id']]
    with pytest.raises(ValueError):focal_packet(data)
def make(tmp_path,response=None):
    import importlib.util
    spec=importlib.util.spec_from_file_location('fixture110_for115',ROOT/'tests/unit/test_qwen_trial_110.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    old,raw,capture=m.make(tmp_path,response)
    return FocalGenerator(old.delegate,tmp_path,ROOT),raw,capture,m.request()

def test_policy_variant_conflicts_removed_not_appended():
    request=json.loads((ROOT/'deployment/state/generation-rag-077/generation-0-request.json').read_bytes())
    adapted,manifest,focus=transform_request(request,ROOT)
    assert 'La compaction del servidor' not in adapted['messages'][0]['content']
    assert 'required_citations' in adapted['messages'][0]['content']
    assert 'cada claim Cambio cita obligatoriamente ambos IDs' in adapted['messages'][0]['content']
    assert 'La compaction del servidor' in request['messages'][0]['content']
    request['messages'][0]['content']+=' changed'
    with pytest.raises(ValueError,match='UPSTREAM_POLICY'):transform_request(request,ROOT)

def test_compact_operations_reconstruct_full_focal_texts():
    packet,manifest=focal_packet(source())
    ops=packet['comparison_operations'];by_id={c['citation_id']:c['text'] for c in packet['evidence']['citations']}
    before=by_id[ops['before_citation_id']];after=by_id[ops['after_citation_id']]
    assert ''.join(before[a:b] for _,a,b,c,d in ops['opcodes'])==before
    assert ''.join(after[c:d] for _,a,b,c,d in ops['opcodes'])==after

def test_one_pass_full_server_pack_unchanged(tmp_path):
    from sbs.runtime import LocalService
    service=LocalService(mode='local');generator,raw,capture,request=make(tmp_path);service.generator=generator
    question=json.loads(request['messages'][1]['content'])['question']
    result=service.ask('offline115',question,'cyber-504','art20.3')
    assert result['status']=='answered' and len(raw.calls)==1
    provided=json.loads(raw.calls[0]['messages'][1]['content'])
    assert len(provided['evidence']['citations'])==2
    assert len(service.last_result['answer']['evidence']['citations'])>2
    assert service.last_result['trace']['validation']['valid'] is True
    assert service.last_result['trace']['generator']['source_evidence_sha256']
    assert (tmp_path/'generation-0-source.json').is_file()
    assert (tmp_path/'generation-0-packet-map.json').is_file()
    assert raw.calls[0]['max_tokens']==8000

def test_actual110_failed_output_still_rejected_unmodified(tmp_path):
    response=json.loads((ROOT/'deployment/state/generation-rag-110/generation-1/response.json').read_bytes())
    generator,raw,capture,request=make(tmp_path,response)
    request['messages'][1]['content']=json.dumps(source())
    with pytest.raises(ValueError,match='ROLES_REJECTED'):generator(request)
    assert len(raw.calls)==1
    assert json.loads((tmp_path/'generation-0/response.json').read_bytes())==response

def test_four_turn_budget_one_post_each(tmp_path):
    generator,raw,capture,request=make(tmp_path)
    for _ in range(4):generator(request)
    assert len(raw.calls)==4
    with pytest.raises(ValueError):generator(request)
    assert len(raw.calls)==4

def test_retention_proof_tamper_rejected():
    packet,manifest=focal_packet(source());manifest['retained_citations'][0]['text_sha256']='f'*64
    with pytest.raises(ValueError,match='RETENTION_PROOF'):restore_packet(packet,manifest)

def test_runner_preflight_no_sdk_and_single_review_gate(tmp_path,monkeypatch):
    import databricks.sdk,importlib.util
    def forbidden(*a,**k):raise AssertionError('noSDK')
    monkeypatch.setattr(databricks.sdk,'WorkspaceClient',forbidden)
    spec=importlib.util.spec_from_file_location('runner115test',ROOT/'runs/sk07-generation-rag-115.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    plan=m.preflight();assert plan['limits']['generation_posts']==4
    monkeypatch.setattr(m,'preflight',lambda root:plan)
    with pytest.raises(FileNotFoundError):m.execute(tmp_path)
    assert not (tmp_path/m.STATE).exists()
