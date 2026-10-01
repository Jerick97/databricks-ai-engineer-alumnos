"""Synthetic component fixtures: no real normative or legal-quality claim."""
import copy
import hashlib
import importlib.util
import pytest
from sbs.contracts import validate_contract

PAIR = {'pair_id': 'synthetic-pair', 'family': 'cybersecurity',
        'before': {'document_id': 'synthetic-doc', 'version_id': 'v1'},
        'after': {'document_id': 'synthetic-doc', 'version_id': 'v2'}}


def bundle(side, entries):
    raw, provisions = '', []
    for pid, text in entries:
        start = len(raw)
        raw += text + '\n'
        provisions.append(dict(PAIR[side], citation_id=f'{side}-{pid}', provision_id=pid,
                               page=1, start=start, end=start + len(text), text=text,
                               source_kind='normative', synthetic=True))
    return {'layer': 'structural_provisions', 'extractor': 'synthetic-v1',
            'config_hash': 'c' * 64, 'sha256': ('a' if side == 'before' else 'b') * 64,
            'rawtext': raw, 'rawtext_sha256': hashlib.sha256(raw.encode()).hexdigest(),
            'provisions': provisions, 'quality': {'status': 'complete', 'limitations': []}}


def compare(*args, **kwargs):
    assert importlib.util.find_spec('sbs.comparison') is not None, 'SK03 missing'
    from sbs.comparison import compare as impl
    return impl(*args, **kwargs)


def test_renumbering_and_deterministic_evidence():
    before, after = bundle('before', [('art1', 'Texto')]), bundle('after', [('art9', 'Texto')])
    result = compare(PAIR, before, after, coverage='complete')
    assert [c['kind'] for c in result['changes']] == ['renumbered_or_moved']
    assert result == compare(PAIR, before, after, coverage='complete')
    assert validate_contract('ChangeSet', result['change_set'])['valid']
    assert [c['citation_id'] for c in result['change_set']['evidence']['citations']] == ['after-art9', 'before-art1']
    assert result['provenance']['before']['config_hash'] == before['config_hash']


@pytest.mark.parametrize('left,right,kind', [
    ([('a', 'Uno Dos')], [('b', 'Uno'), ('c', 'Dos')], 'split'),
    ([('b', 'Uno'), ('c', 'Dos')], [('a', 'Uno Dos')], 'merged'),
    ([('a', 'Uno')], [('a', 'Dos')], 'literal_modification')])
def test_explicit_alignments(left, right, kind):
    alignment = [{'before': [p for p, _ in left], 'after': [p for p, _ in right]}]
    result = compare(PAIR, bundle('before', left), bundle('after', right), alignment, coverage='complete')
    assert [c['kind'] for c in result['changes']] == [kind]
    assert len(result['changes'][0]['citation_ids']) == len(left) + len(right)


def test_duplicate_exact_text_is_ambiguous_even_at_same_number():
    result = compare(PAIR, bundle('before', [('a', 'igual'), ('b', 'igual')]),
                     bundle('after', [('a', 'igual'), ('b', 'igual')]), coverage='complete')
    assert not result['changes'] and not result['alignments']
    assert result['candidates'] and result['no_changes'] is False
    assert result['change_set']['processing_status'] == 'partial'


def test_unmatched_changed_number_is_candidate_not_certain_addition_deletion():
    result = compare(PAIR, bundle('before', [('a', 'antes')]),
                     bundle('after', [('b', 'despues')]), coverage='complete')
    assert result['candidates'] and not result['changes'] and not result['no_changes']


def test_partial_annex_and_raw_pages_block_global_no_changes():
    before, after = bundle('before', [('a', 'igual')]), bundle('after', [('a', 'igual')])
    assert compare(PAIR, before, after, coverage='complete')['no_changes'] is True
    after['quality'] = {'status': 'partial', 'limitations': ['annex_missing']}
    result = compare(PAIR, before, after, coverage='complete')
    assert result['no_changes'] is False
    assert 'annex_missing' in result['change_set']['evidence']['limitations']
    after['quality'] = {'status': 'complete', 'limitations': []}
    after['layer'] = 'raw_pages'
    assert compare(PAIR, before, after, coverage='complete')['no_changes'] is False


@pytest.mark.parametrize('corrupt', ['offset', 'identity', 'bundle', 'alignment', 'duplicate'])
def test_reject_incompatible_inputs(corrupt):
    before, after = bundle('before', [('a', 'igual')]), bundle('after', [('a', 'igual')])
    alignments = None
    if corrupt == 'offset': after['provisions'][0]['text'] = 'falso'
    if corrupt == 'identity': after['provisions'][0]['version_id'] = 'foreign'
    if corrupt == 'bundle': after['rawtext_sha256'] = '0' * 64
    if corrupt == 'alignment': alignments = [{'before': ['absent'], 'after': ['a']}]
    if corrupt == 'duplicate': after['provisions'].append(copy.deepcopy(after['provisions'][0]))
    with pytest.raises(ValueError): compare(PAIR, before, after, alignments, coverage='complete')


def test_temporal_history_keeps_retroactive_knowledge_and_derived_status():
    from sbs.comparison import record_temporal, derived_consolidation
    first = record_temporal([], version=PAIR['before'], known_at='2026-01-01T00:00:00Z',
                            published_on='2025-12-01', effective_on='2026-02-01', source_id='act1')
    history = record_temporal(first, version=PAIR['before'], known_at='2026-03-01T00:00:00Z',
                             published_on='2025-12-01', effective_on='2026-01-01', source_id='correction1')
    assert len(first) == 1 and len(history) == 2
    assert history[0]['effective_on'] == '2026-02-01'
    assert history[1]['known_at'] != history[1]['effective_on']
    derived = derived_consolidation(['act1', 'correction1'], ['apply correction'])
    assert derived['official'] is False and derived['kind'] == 'derived_consolidation'
    assert derived['source_act_ids'] == ['act1', 'correction1']


@pytest.mark.parametrize('side,kind', [('before', 'deleted'), ('after', 'added')])
def test_one_sided_difference_requires_complete_coverage(side, kind):
    inputs = {s: bundle(s, [('a', 'igual')] + ([('b', 'extra')] if s == side else []))
              for s in ('before', 'after')}
    result = compare(PAIR, **inputs, coverage='complete')
    assert [c['kind'] for c in result['changes']] == [kind]
    partial = compare(PAIR, **inputs)
    assert not partial['changes'] and partial['candidates']
    assert validate_contract('ChangeSet', partial['change_set'])['valid']


def test_bundle_config_changes_artifact_identity_and_inputs_are_untouched():
    before, after = bundle('before', [('a', 'igual')]), bundle('after', [('a', 'igual')])
    original = copy.deepcopy((before, after, PAIR))
    first = compare(PAIR, before, after, coverage='complete')
    assert (before, after, PAIR) == original
    after['config_hash'] = 'd' * 64
    second = compare(PAIR, before, after, coverage='complete')
    assert first['change_set']['change_set_id'] != second['change_set']['change_set_id']


def test_alignment_overlap_and_many_to_many_rejected():
    before = bundle('before', [('a', 'one'), ('b', 'two')])
    after = bundle('after', [('c', 'three'), ('d', 'four')])
    for alignments in ([{'before': ['a', 'b'], 'after': ['c', 'd']}],
                       [{'before': ['a'], 'after': ['c']}, {'before': ['a'], 'after': ['d']}]):
        with pytest.raises(ValueError): compare(PAIR, before, after, alignments)


def test_temporal_unknown_dates_and_invalid_history():
    from sbs.comparison import record_temporal, derived_consolidation
    kwargs = dict(version=PAIR['before'], known_at='2026-01-01T00:00:00Z',
                  published_on=None, effective_on=None, source_id='act')
    history = record_temporal([], **kwargs)
    assert history[0]['published_on'] is None and history[0]['effective_on'] is None
    assert record_temporal(history, **kwargs) == history
    for override in ({'known_at': '2026-01-01'}, {'known_at': '2025-01-01T00:00:00Z'},
                     {'published_on': 'not-a-date'}, {'source_id': ''}):
        with pytest.raises(ValueError): record_temporal(history, **(kwargs | override))
    with pytest.raises(ValueError): derived_consolidation([], ['apply'])
