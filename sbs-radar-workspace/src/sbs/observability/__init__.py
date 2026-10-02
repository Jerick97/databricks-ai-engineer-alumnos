"""SK11 event schema 0.1.1, local instrumentation only.

record_event(run, event, *, root=None) -> event_id validates RunRecord and
projects the closed event schema before touching storage. Required event fields:
event_schema_version, event_id, run_id, task_id, event_name, stage, status,
timestamp. Unknown keys are discarded; invalid allowed values raise a stable
OBS_* ValueError without payloads. IDs must be safe opaque strings AND members
of a trusted root/registry.json: {run_id: {field_name: [authorized_values]}}.
Every ID, hash, and version (except schema version) requires field-specific
membership. Configure this registry outside untrusted input; it is a local test
boundary, not authentication or an integrated SK08 authorization service.

root defaults to project runs/observability, must already exist, and must have
no symlink or '..' components. Paths never derive from event IDs. events.jsonl
is rewritten atomically under a local POSIX lock to append complete lines;
this does not claim cloud durability or protection against hostile local users.
No timestamps or IDs are generated. Retention/export/ACL are not implemented.
Unknown cost (missing, null or 'unknown') becomes null/no_reportado. Known cost
requires USD and becomes observado. current/stale are rejected until a verified
threshold policy is integrated. Metadata reconstructs conditions, never promises
exact model reproduction. Summaries accept already verified local observations.
"""
import fcntl
import json
import math
import os
import re
import tempfile
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path

from sbs.contracts import validate_contract

VERSION = '0.1.1'
_ENUMS = {
    'event_name': 'run_started stage_finished capture_attempted capture_succeeded capture_failed run_finished review_recorded',
    'stage': 'capture extract align diff retrieve_lexical retrieve_vector fuse rerank retrieve_counterpart query_genie generate validate review',
    'status': 'started succeeded partial failed blocked',
    'last_attempt_status': 'started succeeded partial failed blocked',
    'freshness_status': 'unknown capture_failed',
    'error_code': 'NONE SOURCE_UNAVAILABLE CAPTURE_FAILED EXTRACTION_FAILED EVIDENCE_INCOMPLETE ACCESS_DENIED CONFIGURATION_MISSING PROVIDER_TIMEOUT PROVIDER_ERROR VALIDATION_FAILED UNKNOWN_ERROR',
    'currency': 'USD', 'cost_state': 'observado no_reportado',
    'comparison_direction': 'before_to_after', 'fusion_mode': 'none rrf native unknown',
    'review_state': 'sin_revisar propuesta revisado_con_observaciones aprobado rechazado',
}
_IDS = set('event_id trace_id span_id parent_span_id run_id task_id family_id document_id case_id conversation_id before_version_id after_version_id skill_id skill_version code_revision_id prompt_template_id prompt_template_version model_bundle_id retrieval_bundle_id index_version_id review_id actor_ref_id'.split())
_ARRAYS = set('artifact_ids candidate_ids selected_passage_ids citation_ids'.split())
_HASHES = {'spec_hash', 'configuration_hash'}
_TIMES = set('timestamp started_at ended_at last_attempt_at last_success_at data_as_of'.split())
_DATES = {'target_date', 'knowledge_date'}
_INTS = set('input_tokens output_tokens candidate_count selected_count attempt_number'.split())
_NUMS = {'duration_ms', 'cost'}
_ALLOWED = set(_ENUMS) | _IDS | _ARRAYS | _HASHES | _TIMES | _DATES | _INTS | _NUMS | {'reranking_observed', 'event_schema_version'}
_REQUIRED = {'event_schema_version', 'event_id', 'run_id', 'task_id', 'event_name', 'stage', 'status', 'timestamp'}


def _fail(code='INVALID_EVENT'):
    raise ValueError('OBS_' + code) from None


def _number(value):
    try:
        return type(value) in (int, float) and value >= 0 and math.isfinite(value)
    except (OverflowError, ValueError):
        return False


def _time(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})', value):
        _fail()
    try:
        if value[-1] != 'Z' and (int(value[-5:-3]) > 23 or int(value[-2:]) > 59):
            _fail()
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        _fail()


def _safe_id(value):
    return isinstance(value, str) and bool(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,95}', value)) and not any(x in value.lower() for x in ('..', 'secret', 'token', 'password', 'bearer')) and not value.lower().startswith('sk-')


def _project(run, event, registry):
    if not isinstance(event, dict) or not _REQUIRED.issubset(event):
        _fail()
    out = {k: v for k, v in event.items() if k in _ALLOWED}
    if any(out[k] is None for k in _REQUIRED) or out['event_schema_version'] != VERSION:
        _fail()
    scope = registry.get(run['run_id'], {})
    if not isinstance(scope, dict):
        _fail('INVALID_REGISTRY')
    for key, value in out.items():
        if value is None:
            continue
        if key in _IDS | _HASHES | _ARRAYS:
            values = value if key in _ARRAYS else [value]
            if not isinstance(values, list):
                _fail()
            allowed = scope.get(key, [])
            if not isinstance(allowed, list):
                _fail('INVALID_REGISTRY')
            for item in values:
                if not _safe_id(item) or item not in allowed:
                    _fail('UNAUTHORIZED_ID')
                if key in _HASHES and not re.fullmatch('[a-f0-9]{64}', item):
                    _fail()
        elif key in _ENUMS and (not isinstance(value, str) or value not in _ENUMS[key].split()):
            _fail()
        elif key in _TIMES:
            _time(value)
        elif key in _DATES:
            try:
                if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
                    _fail()
                date.fromisoformat(value)
            except ValueError:
                _fail()
        elif key in _INTS and (type(value) is not int or value < (1 if key == 'attempt_number' else 0)):
            _fail()
        elif key in _NUMS and not (key == 'cost' and value == 'unknown') and not _number(value):
            _fail()
        elif key == 'reranking_observed' and type(value) is not bool:
            _fail()
    for key in ('run_id', 'task_id', 'skill_id', 'skill_version', 'spec_hash', 'configuration_hash'):
        if key in out and out[key] != run[key]:
            _fail('CORRELATION_ERROR')
    cost = out.get('cost')
    if cost is None or cost == 'unknown':
        out.update(cost=None, cost_state='no_reportado')
    else:
        if out.get('currency') != 'USD':
            _fail()
        out['cost_state'] = 'observado'
    if out.get('started_at') and out.get('ended_at') and _time(out['ended_at']) < _time(out['started_at']):
        _fail()
    expected = {'capture_succeeded': 'succeeded', 'capture_failed': 'failed'}
    if out['event_name'] in expected and out['status'] != expected[out['event_name']]:
        _fail()
    return out


def record_event(run, event, *, root=None):
    """Append one validated event, return its caller-provided registered event_id."""
    try:
        valid = validate_contract('RunRecord', run)['valid']
    except (ValueError, TypeError):
        valid = False
    if not valid or not _number(run['cost']) and run['cost'] is not None:
        _fail('INVALID_RUN')
    root = Path(root) if root is not None else Path(__file__).resolve().parents[3] / 'runs' / 'observability'
    if '..' in root.parts or any(p.is_symlink() for p in [root, *root.parents]):
        _fail('INVALID_ROOT')
    try:
        registry_path = root/'registry.json'
        if registry_path.is_symlink():
            _fail('INVALID_ROOT')
        registry = json.loads(registry_path.read_text())
        if not isinstance(registry, dict):
            _fail('INVALID_REGISTRY')
    except (OSError, UnicodeError, json.JSONDecodeError):
        _fail('INVALID_REGISTRY')
    out = _project(run, event, registry)
    line = (json.dumps(out, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)+'\n').encode('utf-8')
    target, lock = root/'events.jsonl', root/'.events.lock'
    if target.is_symlink() or lock.is_symlink():
        _fail('INVALID_ROOT')
    temporary = None
    try:
        with open(lock, 'a') as guard:
            fcntl.flock(guard, fcntl.LOCK_EX)
            prior = target.read_bytes() if target.exists() else b''
            if prior and not prior.endswith(b'\n'):
                _fail('STORAGE_ERROR')
            try:
                for existing in prior.decode('utf-8').splitlines():
                    parsed = json.loads(existing, parse_constant=lambda _: _fail('STORAGE_ERROR'))
                    if not isinstance(parsed, dict):
                        _fail('STORAGE_ERROR')
            except (UnicodeError, json.JSONDecodeError):
                _fail('STORAGE_ERROR')
            with tempfile.NamedTemporaryFile(dir=root, prefix='.event-', delete=False) as stream:
                temporary = stream.name
                stream.write(prior + line)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
            temporary = None
    except OSError:
        _fail('STORAGE_ERROR')
    finally:
        if temporary:
            try:
                os.unlink(temporary)
            except OSError:
                pass
    return out['event_id']


def summarize_costs(events):
    """Return observed USD subtotal and denominator; unknown costs are not zero."""
    rows = list(events)
    known = []
    for row in rows:
        value = row.get('cost')
        if value is None or value == 'unknown':
            continue
        if not _number(value) or row.get('currency') != 'USD':
            _fail()
        known.append(Decimal(str(value)))
    subtotal = float(sum(known, Decimal(0)))
    if not math.isfinite(subtotal):
        _fail()
    return dict(known_subtotal=subtotal, currency='USD', known_count=len(known),
                sample_count=len(rows), coverage=len(known)/len(rows) if rows else None,
                exact_total=subtotal if rows and len(known) == len(rows) else None)


def summarize_freshness(events):
    """Separate latest capture attempt/success; no implicit current/stale policy.

    Timestamp and optional attempt_number identify ties. Terminal observations
    supersede started observations; conflicting terminal states or success as-of
    values raise OBS_AMBIGUOUS_CAPTURE, independently of input order.
    """
    rows = [r for r in events if r.get('event_name') in ('capture_attempted', 'capture_succeeded', 'capture_failed')]
    for row in rows:
        _time(row.get('timestamp'))
        if row.get('status') not in _ENUMS['status'].split():
            _fail()
        if row['event_name'] in ('capture_succeeded', 'capture_failed') and row['status'] != ('succeeded' if row['event_name'] == 'capture_succeeded' else 'failed'):
            _fail()
        if row.get('data_as_of') is not None:
            _time(row['data_as_of'])
        attempt = row.get('attempt_number')
        if attempt is not None and (type(attempt) is not int or attempt < 1):
            _fail()
    grouped = {}
    for row in rows:
        key = (_time(row['timestamp']), row.get('attempt_number') or 0)
        grouped.setdefault(key, []).append(row)
    rows = []
    for key in sorted(grouped):
        group = grouped[key]
        terminals = [r for r in group if r['status'] != 'started']
        choices = terminals or group
        if len({r['status'] for r in choices}) > 1:
            _fail('AMBIGUOUS_CAPTURE')
        successful = [r for r in choices if r['event_name'] == 'capture_succeeded']
        if successful:
            if len({r.get('data_as_of') for r in successful}) > 1:
                _fail('AMBIGUOUS_CAPTURE')
            choices = successful
        rows.append(min(choices, key=lambda r: (r['timestamp'], r['event_name'])))
    latest = rows[-1] if rows else {}
    successes = [r for r in rows if r['event_name'] == 'capture_succeeded' and r['status'] == 'succeeded']
    success = successes[-1] if successes else {}
    return dict(last_attempt_at=latest.get('timestamp'), last_attempt_status=latest.get('status'),
                last_success_at=success.get('timestamp'), data_as_of=success.get('data_as_of'),
                freshness_status='capture_failed' if latest.get('status') == 'failed' else 'unknown')
