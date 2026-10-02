"""Local replay of observed 050 response; not a cloud execution or certificate."""
import json
from pathlib import Path
from copy import deepcopy
import pytest
from databricks.sdk.service.sql import StatementResponse
from sbs.genie.publication import PublicationReader

FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures/publication/empty-select-050.json'


def observed():
    return json.loads(FIXTURE.read_text())['response']


def execute(response):
    class Replay:
        def execute_statement(self, **kwargs):
            return response
    return PublicationReader(Replay(), warehouse_id='fixture', metadata_get=lambda _: {},
                             governance_probe=lambda _: {}, evidence_mode='fixture')._execute('SELECT fixture')


@pytest.mark.parametrize('sdk_model', [False, True])
def test_observed_empty_select_accepts_omitted_chunks(sdk_model):
    response = observed()
    columns, rows, proof = execute(StatementResponse.from_dict(response) if sdk_model else response)
    assert [c['name'] for c in columns] == ['id', 'family', 'synthetic', 'source_kind', 'corpus_hash',
        'config_hash', 'known_at', 'published_on', 'effective_on', 'review_status', 'human_approved',
        'lineage_json', 'payload_json']
    assert rows == []
    assert proof['row_count'] == 0
    assert proof['evidence_mode'] == 'fixture'


@pytest.mark.parametrize('field', ['total_row_count', 'total_chunk_count'])
@pytest.mark.parametrize('value', [None, True, False, -1, 0.0, '0', 1])
def test_omitted_chunks_requires_exact_integer_zero_counts(field, value):
    response = observed()
    response['manifest'][field] = value
    with pytest.raises(ValueError):
        execute(response)


@pytest.mark.parametrize('chunks', [None, {}, [{'chunk_index': 0, 'row_offset': 0, 'row_count': 0}]])
def test_explicit_invalid_chunks_are_not_normalized(chunks):
    response = observed()
    response['manifest']['chunks'] = chunks
    with pytest.raises(ValueError):
        execute(response)


@pytest.mark.parametrize('chunks_present', [False, True])
@pytest.mark.parametrize('result', [
    {'data_array': [['unexpected']]}, {'data_array': {}}, {'data_array': False},
    {'external_links': [{'external_link': 'https://invalid.example'}]},
    {'chunk_index': 0}, {'row_offset': 1}, {'row_count': 1},
    {'next_chunk_index': 1}, {'next_chunk_index': False},
    {'next_chunk_internal_link': '/api/2.0/sql/statements/x/result/chunks/1'}, [], 'bad', None,
])
def test_empty_manifest_rejects_contradictory_result(chunks_present, result):
    response = observed()
    if chunks_present:
        response['manifest']['chunks'] = []
    response['result'] = deepcopy(result)
    with pytest.raises(ValueError):
        execute(response)


@pytest.mark.parametrize('change', [
    {'truncated': True}, {'truncated': None}, {'format': 'ARROW_STREAM'},
    {'schema': {'columns': []}}, {'schema': {'columns': [{'name': 'id', 'position': 1, 'type_name': 'STRING'}]}},
])
def test_empty_result_preserves_format_truncation_schema_checks(change):
    response = observed()
    response['manifest'].update(change)
    with pytest.raises(ValueError):
        execute(response)


def test_explicit_empty_chunks_remains_valid():
    response = observed()
    response['manifest']['chunks'] = []
    assert execute(response)[1] == []
