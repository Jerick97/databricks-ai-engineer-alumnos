"""SK03 deterministic, local textual comparison; not a legal interpretation.

compare accepts two pinned foundation extraction dictionaries. Structural bundles
use layer='structural_provisions'; raw_pages are accepted only as partial evidence.
The closed ChangeSet contract is returned at result['change_set']; change details,
bundle provenance and ambiguity candidates are a separate accompanying artifact.
Explicit alignments use provision IDs and mean caller-supplied correspondence,
not an expert approval. No semantic segmentation or similarity score is invented.
"""
from collections import defaultdict
from copy import deepcopy
from datetime import date, datetime
import hashlib
import json
import re

from sbs.contracts import validate_contract

VERSION = '0.1.0'


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode()).hexdigest()


def _validate(kind, value):
    result = validate_contract(kind, value)
    if not result['valid']:
        raise ValueError(f'{kind}_INVALID: {result["errors"]}')


def _bundle(bundle, reference):
    if not isinstance(bundle, dict):
        raise ValueError('PINNED_BUNDLE_REQUIRED')
    for field in ('sha256', 'config_hash', 'rawtext_sha256'):
        if not isinstance(bundle.get(field), str) or not re.fullmatch('[0-9a-f]{64}', bundle[field]):
            raise ValueError('BUNDLE_HASH_REQUIRED: ' + field)
    if not isinstance(bundle.get('extractor'), str) or not bundle['extractor'].strip():
        raise ValueError('EXTRACTOR_REQUIRED')
    raw = bundle.get('rawtext')
    if not isinstance(raw, str) or hashlib.sha256(raw.encode()).hexdigest() != bundle['rawtext_sha256']:
        raise ValueError('RAW_BUNDLE_INTEGRITY_FAILED')
    provisions, citation_ids = {}, set()
    if not isinstance(bundle.get('provisions'), list):
        raise ValueError('PROVISIONS_REQUIRED')
    for p in bundle['provisions']:
        _validate('Provision', p)
        if any(p[k] != reference[k] for k in ('document_id', 'version_id')):
            raise ValueError('PROVISION_OUTSIDE_PAIR')
        if p['source_kind'] != 'normative':
            raise ValueError('NORMATIVE_EVIDENCE_REQUIRED')
        if p['end'] > len(raw) or raw[p['start']:p['end']] != p['text']:
            raise ValueError('CITATION_BUNDLE_MISMATCH')
        if p['provision_id'] in provisions or p['citation_id'] in citation_ids:
            raise ValueError('DUPLICATE_PROVISION_OR_CITATION')
        provisions[p['provision_id']] = deepcopy(p)
        citation_ids.add(p['citation_id'])
    quality = bundle.get('quality', {})
    limitations = quality.get('limitations', [])
    if not isinstance(limitations, list) or any(not isinstance(x, str) or not x.strip() for x in limitations):
        raise ValueError('INVALID_BUNDLE_LIMITATIONS')
    limitations = list(limitations)
    if quality.get('status') != 'complete':
        limitations.append('extraction_coverage_unverified')
    if bundle.get('layer') != 'structural_provisions':
        limitations.append('semantic_segmentation_pending')
    if not provisions:
        limitations.append('no_verified_provisions')
    provenance = {k: bundle[k] for k in ('sha256', 'extractor', 'config_hash', 'rawtext_sha256')}
    provenance.update(reference)
    provenance['bundle_id'] = _hash(bundle)
    return provisions, limitations, provenance


def compare(version_pair, before, after, alignments=None, *, coverage='partial'):
    """Return a deterministic comparison artifact, never mutate input bundles.

    coverage='complete' is a caller assertion and cannot override source quality,
    missing annex limitations, raw-page segmentation, or ambiguous alignment.
    No_changes is global only for complete, resolved structural evidence.
    """
    _validate('VersionPair', version_pair)
    if coverage not in ('complete', 'partial'):
        raise ValueError('INVALID_COVERAGE')
    left, llimits, lp = _bundle(before, version_pair['before'])
    right, rlimits, rp = _bundle(after, version_pair['after'])
    if {p['citation_id'] for p in left.values()} & {p['citation_id'] for p in right.values()}:
        raise ValueError('CROSS_BUNDLE_CITATION_COLLISION')
    limitations = set(llimits + rlimits)
    if coverage != 'complete':
        limitations.add('caller_coverage_partial')
    resolved, changes, candidates = [], [], []
    used_left, used_right = set(), set()

    def align(a, b, method):
        a, b = sorted(a), sorted(b)
        resolved.append({'before': a, 'after': b, 'method': method})
        used_left.update(a)
        used_right.update(b)
        if len(a) > 1:
            kind = 'merged'
        elif len(b) > 1:
            kind = 'split'
        elif left[a[0]]['text'] != right[b[0]]['text']:
            kind = 'literal_modification'
        elif a != b:
            kind = 'renumbered_or_moved'
        else:
            return
        add_change(kind, a, b)

    def add_change(kind, a, b):
        item = {'kind': kind, 'before': sorted(a), 'after': sorted(b),
                'citation_ids': sorted([left[p]['citation_id'] for p in a] +
                                       [right[p]['citation_id'] for p in b]),
                'materiality': 'not_assessed'}
        item['change_id'] = _hash([version_pair, lp, rp, item])
        changes.append(item)

    if alignments is not None and not isinstance(alignments, list):
        raise ValueError('INVALID_ALIGNMENTS')
    for entry in alignments or []:
        if not isinstance(entry, dict) or set(entry) != {'before', 'after'}:
            raise ValueError('INVALID_ALIGNMENT')
        a, b = entry['before'], entry['after']
        if (not isinstance(a, list) or not isinstance(b, list) or not a or not b
                or any(not isinstance(p, str) for p in a + b)
                or (len(a) > 1 and len(b) > 1)
                or len(set(a)) != len(a) or len(set(b)) != len(b)
                or not set(a) <= left.keys() or not set(b) <= right.keys()
                or set(a) & used_left or set(b) & used_right):
            raise ValueError('INVALID_OR_OVERLAPPING_ALIGNMENT')
        align(a, b, 'explicit')

    # Exact means literal equality, without whitespace or punctuation rewriting.
    by_left, by_right = defaultdict(list), defaultdict(list)
    for p, item in left.items():
        if p not in used_left: by_left[item['text']].append(p)
    for p, item in right.items():
        if p not in used_right: by_right[item['text']].append(p)
    for text in sorted(by_left.keys() & by_right.keys()):
        a, b = by_left[text], by_right[text]
        if len(a) == len(b) == 1:
            align(a, b, 'unique_exact_text')
        else:
            candidates.append({'before': sorted(a), 'after': sorted(b), 'reason': 'duplicate_exact_text'})
            used_left.update(a)
            used_right.update(b)
    a, b = sorted(left.keys() - used_left), sorted(right.keys() - used_right)
    if a and b:
        candidates.append({'before': a, 'after': b, 'reason': 'explicit_alignment_required'})
    elif a or b:
        if limitations or candidates:
            candidates.append({'before': a, 'after': b, 'reason': 'absence_unverified'})
        else:
            for p in a: add_change('deleted', [p], [])
            for p in b: add_change('added', [], [p])
    if candidates:
        limitations.add('alignment_uncertain')
    if not left or not right:
        limitations.add('both_version_evidence_required')
    citations = sorted(({k: v for k, v in p.items() if k != 'synthetic'}
                        for p in [*left.values(), *right.values()]), key=lambda p: p['citation_id'])
    changes.sort(key=lambda c: c['change_id'])
    resolved.sort(key=lambda x: (x['before'], x['after']))
    candidates.sort(key=lambda x: (x['before'], x['after']))
    provenance = {'component': 'SK03', 'version': VERSION, 'before': lp, 'after': rp}
    fingerprint = _hash([version_pair, provenance, changes, resolved, candidates, sorted(limitations)])
    evidence = {'evidence_id': 'evidence-' + fingerprint, 'evidence_version': VERSION,
                'pair': deepcopy(version_pair), 'citations': citations,
                'coverage': 'partial' if limitations else 'complete',
                'limitations': sorted(limitations),
                'synthetic': any(p['synthetic'] for p in [*left.values(), *right.values()])}
    change_set = {'change_set_id': 'changeset-' + fingerprint, 'pair': deepcopy(version_pair),
                  'evidence': evidence, 'processing_status': 'partial' if limitations else 'ready',
                  'review_status': 'unreviewed', 'change_ids': [c['change_id'] for c in changes]}
    _validate('ChangeSet', change_set)
    return {'change_set': change_set, 'changes': changes, 'alignments': resolved,
            'candidates': candidates, 'provenance': provenance,
            'no_changes': not changes and not limitations}


def record_temporal(history, *, version, known_at, published_on, effective_on, source_id):
    """Append sourced knowledge without overwriting earlier, possibly corrected facts.

    None publication/effect dates remain unknown; knowledge time is never copied
    into those fields. The same source_id supplies these stated date assertions.
    Caller persists returned history; this function provides no durable storage.
    """
    if not isinstance(source_id, str) or not source_id.strip():
        raise ValueError('TEMPORAL_SOURCE_REQUIRED')
    if (not isinstance(version, dict) or set(version) != {'document_id', 'version_id'}
            or any(not isinstance(v, str) or not v.strip() for v in version.values())):
        raise ValueError('VERSION_IDENTITY_REQUIRED')
    if not isinstance(known_at, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})', known_at):
        raise ValueError('AWARE_KNOWLEDGE_TIME_REQUIRED')
    instant = datetime.fromisoformat(known_at.replace('Z', '+00:00'))
    for value in (published_on, effective_on):
        if value is not None: date.fromisoformat(value)
    item = dict(version=deepcopy(version), known_at=known_at, published_on=published_on,
                effective_on=effective_on, source_id=source_id)
    if item in history: return deepcopy(history)
    if history and instant < max(datetime.fromisoformat(r['known_at'].replace('Z', '+00:00')) for r in history):
        raise ValueError('KNOWLEDGE_HISTORY_MUST_APPEND')
    return deepcopy(history) + [item]


def derived_consolidation(source_act_ids, transformations):
    """Describe caller-supplied reconstruction, never assert it is official."""
    for values in (source_act_ids, transformations):
        if not isinstance(values, list) or not values or any(not isinstance(x, str) or not x.strip() for x in values):
            raise ValueError('SOURCE_ACTS_AND_TRANSFORMATIONS_REQUIRED')
    result = {'kind': 'derived_consolidation', 'official': False,
              'source_act_ids': sorted(set(source_act_ids)), 'transformations': list(transformations)}
    result['derivation_id'] = _hash(result)
    return result
