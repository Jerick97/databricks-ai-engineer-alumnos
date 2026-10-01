"""Synthetic local contract fixtures; no normative or authorization evidence."""
import copy
import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]


def validate(kind, payload):
    path = ROOT / 'src/sbs/contracts.py'
    assert path.exists(), 'SK01 validator not implemented'
    spec = importlib.util.spec_from_file_location('contracts_under_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate_contract(kind, payload)


PAIR = {'pair_id': 'p1', 'family': 'cybersecurity', 'before': {'document_id': 'd1', 'version_id': 'v2'}, 'after': {'document_id': 'd1', 'version_id': 'v3'}}
CITE = {'citation_id': 'c1', 'document_id': 'd1', 'version_id': 'v2', 'provision_id': 'art1', 'page': 1, 'start': 0, 'end': 5, 'text': 'Texto', 'source_kind': 'normative'}
PACK = {'evidence_id': 'e1', 'evidence_version': '1', 'pair': PAIR, 'citations': [CITE, {**CITE, 'citation_id': 'c2', 'version_id': 'v3'}], 'coverage': 'complete', 'limitations': [], 'synthetic': True}
SOURCE = {'document_id': 'd1', 'version_id': 'v2', 'family': 'cybersecurity', 'url': 'https://example.org/doc.pdf', 'sha256': 'a'*64, 'captured_at': '2026-09-27T12:00:00Z', 'published_on': None, 'effective_on': None, 'date_unknown_reasons': {'published_on': 'No determinado', 'effective_on': 'No determinado'}, 'source_kind': 'normative', 'synthetic': True}
ANSWER = {'answer_id': 'a1', 'context_id': 'q1', 'evidence': PACK, 'processing_status': 'ready', 'review_status': 'unreviewed', 'text': 'Cambio propuesto', 'material_claims': [{'text': 'Cambió', 'citation_ids': ['c1','c2']}], 'limitations': []}
REVIEW = {'review_id': 'r1', 'subject_id': 'a1', 'review_status': 'approved', 'actor_id': 'actor1', 'actor_role': 'reviewer', 'reviewed_at': '2026-09-27T12:00:00Z', 'evidence_id': 'e1', 'evidence_version': '1'}


@pytest.mark.parametrize('kind,payload', [
    ('SourceDocument', SOURCE), ('VersionPair', PAIR), ('EvidencePack', PACK), ('Answer', ANSWER), ('ReviewDecision', REVIEW),
    ('Provision', {**CITE, 'synthetic': True}),
    ('ChangeSet', {'change_set_id': 'ch1', 'pair': PAIR, 'evidence': PACK, 'processing_status': 'ready', 'review_status': 'proposed', 'change_ids': ['change1']}),
    ('QueryContext', {'context_id': 'q1', 'family': 'cybersecurity', 'pair': PAIR, 'target_date': None, 'selected_provision_id': None}),
    ('RunRecord', {'run_id': 'run1', 'task_id': 't1', 'skill_id': 'SK01', 'skill_version': '0.1.0', 'spec_hash': 'a'*64, 'input_artifact_ids': [], 'configuration_hash': 'b'*64, 'mode': 'local', 'outputs': [], 'checks': [], 'cost': None, 'status': 'passed', 'next_action': 'Independent review'}),
    ('ModelBundle', {'bundle_id': 'b1', 'revision': '1', 'embedding_model': 'test', 'embedding_revision': 'r1', 'tokenizer': 'test', 'dimension': 3, 'reranker_model': 'test', 'reranker_revision': 'r1', 'generation_model': 'test', 'generation_revision': 'r1', 'chunking_version': '1', 'parameters': {}}),
    ('ValidationResult', {'valid': True, 'errors': []}),
])
def test_supported_contracts_accept_minimal_records(kind, payload):
    assert validate(kind, payload) == {'valid': True, 'errors': []}


@pytest.mark.parametrize('field,value', [('url','not a uri'), ('captured_at','2026-02-30'), ('published_on','2026-02-30'), ('unexpected',True)])
def test_source_rejects_bad_formats_and_unknown_fields(field, value):
    assert not validate('SourceDocument', {**SOURCE, field: value})['valid']


def test_unknown_dates_require_reason_and_are_not_inferred_or_mutated():
    source = copy.deepcopy(SOURCE)
    assert validate('SourceDocument', source)['valid']
    assert source == SOURCE
    source['date_unknown_reasons'] = {}
    assert not validate('SourceDocument', source)['valid']


@pytest.mark.parametrize('field', ['actor_id','actor_role','reviewed_at','evidence_id','evidence_version'])
def test_approved_requires_recorded_actor_date_and_exact_evidence(field):
    review = {k:v for k,v in REVIEW.items() if k != field}
    assert not validate('ReviewDecision', review)['valid']


def test_declared_reader_cannot_form_approved_record_but_role_is_not_authentication():
    assert not validate('ReviewDecision', {**REVIEW, 'actor_role':'reader'})['valid']
    assert validate('ReviewDecision', REVIEW)['valid']  # structural only; no authorization claim


@pytest.mark.parametrize('status', ['ready','partial'])
def test_chat_does_not_require_review(status):
    answer = {**ANSWER, 'processing_status': status, 'limitations': ['Coverage pending'] if status == 'partial' else []}
    assert validate('Answer', answer)['valid']
    assert not validate('Answer', {**answer, 'processing_status':'approved'})['valid']


@pytest.mark.parametrize('mutation', ['wrong_version','wrong_document','offsets','missing_counterpart','duplicate_id','fictitious_legal_source'])
def test_evidence_rejects_broken_local_links(mutation):
    pack = copy.deepcopy(PACK)
    if mutation == 'wrong_version': pack['citations'][0]['version_id'] = 'v1'
    if mutation == 'wrong_document': pack['citations'][0]['document_id'] = 'other'
    if mutation == 'offsets': pack['citations'][0]['end'] = 0
    if mutation == 'missing_counterpart': pack['citations'].pop()
    if mutation == 'duplicate_id': pack['citations'][1]['citation_id'] = 'c1'
    if mutation == 'fictitious_legal_source': pack['citations'][0]['source_kind'] = 'fictitious_process'
    result = validate('EvidencePack', pack)
    assert not result['valid']
    assert all('path' in error and 'phase' in error for error in result['errors'])


def test_partial_evidence_explains_missing_counterpart():
    pack = {**PACK, 'citations': [CITE], 'coverage': 'partial', 'limitations':['Missing counterpart']}
    assert validate('EvidencePack', pack)['valid']
    assert not validate('EvidencePack', {**pack, 'limitations': []})['valid']


def test_pair_cannot_compare_same_identity():
    assert not validate('VersionPair', {**PAIR, 'after': PAIR['before']})['valid']


def test_answer_rejects_unresolved_claim_citation_and_stale_approval():
    assert not validate('Answer', {**ANSWER, 'material_claims': [{'text':'Claim','citation_ids':['missing']}]})['valid']
    approved = {**ANSWER, 'review_status':'approved', 'review': REVIEW}
    assert validate('Answer', approved)['valid']
    stale = copy.deepcopy(approved)
    stale['evidence']['evidence_version'] = '2'
    assert not validate('Answer', stale)['valid']
    assert not validate('Answer', {**ANSWER, 'review_status':'approved'})['valid']


def test_unknown_kind_and_non_object_fail_closed():
    assert not validate('../../outside', {})['valid']
    assert not validate('Answer', None)['valid']


@pytest.mark.parametrize('kind,payload,field', [
    ('ReviewDecision', REVIEW, 'actor_id'),
    ('VersionPair', PAIR, 'pair_id'),
    ('SourceDocument', SOURCE, 'document_id'),
])
def test_identity_cannot_be_only_whitespace(kind, payload, field):
    assert not validate(kind, {**payload, field: ' \t\n'})['valid']


def test_embedded_identity_cannot_be_only_whitespace():
    pack = copy.deepcopy(PACK)
    pack['citations'][0]['provision_id'] = ' \t\n'
    assert not validate('EvidencePack', pack)['valid']


def test_minimal_proposed_review_is_consistent_standalone_and_embedded():
    review = {'review_id':'r2', 'subject_id':'a1', 'review_status':'proposed'}
    assert validate('ReviewDecision', review)['valid']
    assert validate('Answer', {**ANSWER, 'review_status':'proposed', 'review':review})['valid']


@pytest.mark.parametrize('partial_link', [ {'evidence_id':'e1'}, {'evidence_version':'1'} ])
def test_optional_review_evidence_link_requires_both_fields(partial_link):
    review = {'review_id':'r2', 'subject_id':'a1', 'review_status':'proposed', **partial_link}
    assert not validate('ReviewDecision', review)['valid']


def test_proposed_review_checks_evidence_when_link_present():
    review = {**REVIEW, 'review_status':'proposed', 'evidence_version':'old'}
    assert not validate('Answer', {**ANSWER, 'review_status':'proposed', 'review':review})['valid']


@pytest.mark.parametrize('payload', [
    {'valid':True, 'errors':[{'path':'','phase':'structural','message':'Bad value'}]},
    {'valid':False, 'errors':[]},
])
def test_validation_result_cannot_contradict_errors(payload):
    assert not validate('ValidationResult', payload)['valid']


@pytest.mark.parametrize('kind,field,payload', [
    ('SourceDocument','sha256',SOURCE),
    ('RunRecord','spec_hash',{'run_id':'r','task_id':'t','skill_id':'SK01','skill_version':'0.1.0','spec_hash':'a'*64,'input_artifact_ids':[],'configuration_hash':'b'*64,'mode':'local','outputs':[],'checks':[],'cost':None,'status':'passed','next_action':'review'}),
    ('RunRecord','configuration_hash',{'run_id':'r','task_id':'t','skill_id':'SK01','skill_version':'0.1.0','spec_hash':'a'*64,'input_artifact_ids':[],'configuration_hash':'b'*64,'mode':'local','outputs':[],'checks':[],'cost':None,'status':'passed','next_action':'review'}),
])
def test_hash_must_be_exactly_64_hex_characters(kind, field, payload):
    assert not validate(kind, {**payload, field:'a'*64+'\n'})['valid']
