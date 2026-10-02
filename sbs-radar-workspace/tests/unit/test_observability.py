import json
from pathlib import Path

import pytest

from sbs.observability import record_event, summarize_costs, summarize_freshness


@pytest.fixture
def context(tmp_path):
    run = dict(run_id='run-1', task_id='task-1', skill_id='SK11', skill_version='0.1.1',
               spec_hash='a'*64, configuration_hash='b'*64, input_artifact_ids=[],
               outputs=[], checks=[], cost=None, mode='local', status='running', next_action='Continue')
    event = dict(event_schema_version='0.1.1', event_id='event-1', run_id='run-1',
                 task_id='task-1', event_name='capture_failed', stage='capture', status='failed',
                 timestamp='2026-09-23T12:00:00Z', error_code='CAPTURE_FAILED')
    registry = {'run-1': {'event_id': ['event-1', 'event-2'], 'task_id': ['task-1'], 'run_id': ['run-1']}}
    (tmp_path/'registry.json').write_text(json.dumps(registry))
    return run, event, tmp_path


def test_projection_and_deterministic_bytes(context):
    run, event, root = context
    event.update(debug='https://host/?token=secret', exception='secret exception', cost='unknown')
    assert record_event(run, event, root=root) == 'event-1'
    raw = (root/'events.jsonl').read_bytes()
    saved = json.loads(raw)
    assert saved['cost'] is None and saved['cost_state'] == 'no_reportado'
    assert b'secret' not in raw and b'http' not in raw
    assert raw == (json.dumps(saved, sort_keys=True, separators=(',', ':'), ensure_ascii=False)+'\n').encode()
    event['event_id'] = 'event-2'
    record_event(run, event, root=root)
    assert len((root/'events.jsonl').read_text().splitlines()) == 2


@pytest.mark.parametrize('field,value', [
    ('run_id', 'run-2'), ('event_id', '../secret'), ('event_id', 'unregistered'),
    ('trace_id', 'https://host'), ('event_id', 'sk-secret'), ('cost', float('nan')),
    ('cost', True), ('duration_ms', -1), ('attempt_number', 0), ('input_tokens', True),
    ('timestamp', '2026-01-01'), ('status', 'exception secret'), ('stage', 'sql'),
    ('configuration_hash', 'a'*64), ('freshness_status', 'current'), ('artifact_ids', ['unknown']),
    ('cost_state', 'estimated'), ('currency', 'EUR'), ('reranking_observed', 1),
])
def test_invalid_value_never_writes(context, field, value):
    run, event, root = context
    event[field] = value
    with pytest.raises(ValueError, match='^OBS_[A-Z_]+$'):
        record_event(run, event, root=root)
    assert sorted(p.name for p in root.iterdir()) == ['registry.json']


def test_invalid_run_safe_error(context):
    run, event, root = context
    run['secret'] = 'do not echo'
    with pytest.raises(ValueError, match='^OBS_INVALID_RUN$'):
        record_event(run, event, root=root)
    assert not (root/'events.jsonl').exists()


def test_symlink_destination_rejected(context, tmp_path):
    run, event, root = context
    outside = root/'outside'
    outside.write_text('untouched')
    (root/'events.jsonl').symlink_to(outside)
    with pytest.raises(ValueError):
        record_event(run, event, root=root)
    assert outside.read_text() == 'untouched'


def test_costs_coverage():
    assert summarize_costs([{'cost': .02, 'currency': 'USD'}, {'cost': .03, 'currency': 'USD'}, {'cost': None}]) == {
        'known_subtotal': .05, 'currency': 'USD', 'known_count': 2, 'sample_count': 3,
        'coverage': 2/3, 'exact_total': None}
    with pytest.raises(ValueError):
        summarize_costs([{'cost': 1, 'currency': 'EUR'}])


def test_freshness_attempt_is_not_success():
    monday = {'event_name': 'capture_succeeded', 'status': 'succeeded', 'timestamp': '2026-09-21T12:00:00Z', 'data_as_of': '2026-09-21T00:00:00Z'}
    wednesday = {'event_name': 'capture_failed', 'status': 'failed', 'timestamp': '2026-09-23T12:00:00Z'}
    result = summarize_freshness([wednesday, monday])
    assert result == {'last_attempt_at': wednesday['timestamp'], 'last_attempt_status': 'failed',
                      'last_success_at': monday['timestamp'], 'data_as_of': monday['data_as_of'], 'freshness_status': 'capture_failed'}


def test_failure_preserves_existing_file(context, monkeypatch):
    import sbs.observability as obs
    run, event, root = context
    record_event(run, event, root=root)
    before = (root/'events.jsonl').read_bytes()
    event['event_id'] = 'event-2'
    def fail(*args):
        raise OSError('secret internal exception')
    monkeypatch.setattr(obs.os, 'replace', fail)
    with pytest.raises(ValueError, match='^OBS_STORAGE_ERROR$'):
        record_event(run, event, root=root)
    assert (root/'events.jsonl').read_bytes() == before
    assert not list(root.glob('.event-*'))


@pytest.mark.parametrize('bad_id', ['sk-123456', 'secret-abcd', 'https://example.test', '../escape'])
def test_registered_suspicious_ids_rejected(context, bad_id):
    run, event, root = context
    registry = json.loads((root/'registry.json').read_text())
    registry['run-1']['event_id'].append(bad_id)
    (root/'registry.json').write_text(json.dumps(registry))
    event['event_id'] = bad_id
    with pytest.raises(ValueError, match='^OBS_UNAUTHORIZED_ID$'):
        record_event(run, event, root=root)
    assert not (root/'events.jsonl').exists()


def test_root_traversal_rejected(context):
    run, event, root = context
    with pytest.raises(ValueError, match='^OBS_INVALID_ROOT$'):
        record_event(run, event, root=root/'child'/'..')
    assert not (root/'events.jsonl').exists()


def test_cost_state_normalized(context):
    run, event, root = context
    event.update(cost=.02, currency='USD', cost_state='no_reportado')
    record_event(run, event, root=root)
    saved = json.loads((root/'events.jsonl').read_text())
    assert saved['cost'] == .02 and saved['cost_state'] == 'observado'


def test_empty_summaries_and_success_without_asof():
    assert summarize_costs([])['coverage'] is None
    assert summarize_costs([])['exact_total'] is None
    assert summarize_freshness([])['last_success_at'] is None
    result = summarize_freshness([{'event_name': 'capture_succeeded', 'status': 'succeeded', 'timestamp': '2026-09-21T12:00:00Z'}])
    assert result['data_as_of'] is None
    assert result['freshness_status'] == 'unknown'


@pytest.mark.parametrize('prior', [b'{broken}\n', b'\xff\n', b'[]\n'])
def test_corrupt_existing_stream_not_modified(context, prior):
    run, event, root = context
    (root/'events.jsonl').write_bytes(prior)
    with pytest.raises(ValueError, match='^OBS_STORAGE_ERROR$'):
        record_event(run, event, root=root)
    assert (root/'events.jsonl').read_bytes() == prior


def test_invalid_utf8_registry_has_stable_error(context):
    run, event, root = context
    (root/'registry.json').write_bytes(b'\xffsecret')
    with pytest.raises(ValueError, match='^OBS_INVALID_REGISTRY$') as caught:
        record_event(run, event, root=root)
    assert caught.value.__suppress_context__
    assert not (root/'events.jsonl').exists()


def test_huge_cost_has_stable_error(context):
    run, event, root = context
    event.update(cost=10**400, currency='USD')
    with pytest.raises(ValueError, match='^OBS_INVALID_EVENT$'):
        record_event(run, event, root=root)
    assert not (root/'events.jsonl').exists()


def test_cost_aggregate_overflow_rejected():
    with pytest.raises(ValueError, match='^OBS_INVALID_EVENT$'):
        summarize_costs([{'cost': 1e308, 'currency': 'USD'}]*2)


def test_terminal_capture_precedes_started_at_same_instant():
    started = {'event_name': 'capture_attempted', 'status': 'started', 'timestamp': '2026-09-21T12:00:00Z', 'attempt_number': 1}
    failed = dict(started, event_name='capture_failed', status='failed')
    one = summarize_freshness([failed, started])
    two = summarize_freshness([started, failed])
    assert one == two
    assert one['last_attempt_status'] == 'failed'


def test_conflicting_terminal_capture_rejected():
    success = {'event_name': 'capture_succeeded', 'status': 'succeeded', 'timestamp': '2026-09-21T12:00:00Z', 'attempt_number': 1}
    failed = dict(success, event_name='capture_failed', status='failed')
    for rows in ([success, failed], [failed, success]):
        with pytest.raises(ValueError, match='^OBS_AMBIGUOUS_CAPTURE$'):
            summarize_freshness(rows)
