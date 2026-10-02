"""Synthetic fixtures only; these tests do not adjudicate legal references."""
import copy
import math
import pytest
from sbs.evaluation import evaluate, retrieval_metrics, check_leakage, freeze_protocol, verify_protocol


def fixture():
    reference = {'kind': 'synthetic_fixture', 'review_provenance': {'actor': 'claimed-human'},
                 'families': {'A': {'changes': ['a', 'b'], 'critical': ['b'], 'insufficient_cases': ['i']},
                              'B': {'changes': [], 'critical': [], 'insufficient_cases': []}}}
    runs = [{'run_id': 'r', 'family': 'A', 'detected': ['a', 'a', 'b'],
             'citations': [{'faithful': True, 'localizable': True}], 'flagged_insufficient': ['i'],
             'times': [{'case_id': 't', 'baseline': 10, 'agent': 1, 'review': 15}]}]
    return reference, runs


def test_unique_counts_family_gates_and_total_review_time():
    ref, runs = fixture()
    report = evaluate(runs, ref)
    a, b = report['families']['A'], report['families']['B']
    assert (a['tp'], a['fp'], a['fn']) == (2, 0, 0)
    assert a['recall'] == {'numerator': 2, 'denominator': 2, 'value': 1.0, 'status': 'passed'}
    assert a['time_saving']['value'] == pytest.approx(-.6)
    assert a['time_saving']['status'] == 'failed'
    assert b['recall']['status'] == b['critical']['status'] == 'not_evaluated'
    assert report['status'] == 'failed'
    assert report['human_acceptance']['status'] == 'not_evaluated'
    assert report['legal_certification'] is False


def test_no_macro_average_hides_failure_and_critical_empty_not_pass():
    ref, runs = fixture()
    runs[0]['detected'] = ['a', 'spurious']
    a = evaluate(runs, ref)['families']['A']
    assert (a['tp'], a['fp'], a['fn']) == (1, 1, 1)
    assert a['critical']['numerator'] == 1
    assert a['critical']['status'] == 'failed'
    assert a['precision']['value'] == .5


def test_citation_and_insufficiency_failures():
    ref, runs = fixture()
    runs[0]['citations'][0]['localizable'] = False
    runs[0]['flagged_insufficient'] = []
    a = evaluate(runs, ref)['families']['A']
    assert a['citations']['status'] == a['insufficiency']['status'] == 'failed'
    runs[0]['citations'] = []
    assert evaluate(runs, ref)['families']['A']['citations']['status'] == 'not_evaluated'


@pytest.mark.parametrize('bad', [float('nan'), float('inf'), -1, True])
def test_invalid_time_rejected(bad):
    ref, runs = fixture()
    runs[0]['times'][0]['review'] = bad
    with pytest.raises(ValueError):
        evaluate(runs, ref)


def test_time_pairing_and_zero_baseline():
    ref, runs = fixture()
    runs[0]['times'][0]['baseline'] = 0
    assert evaluate(runs, ref)['families']['A']['time_saving']['status'] == 'not_evaluated'
    runs[0]['times'].append(copy.deepcopy(runs[0]['times'][0]))
    with pytest.raises(ValueError):
        evaluate(runs, ref)


def test_retrieval_explicit_qrels_counterparts():
    result = retrieval_metrics(['x', 'before', 'after'], {'before': 2, 'after': 1}, 3,
                               {'p': {'before': ['before'], 'after': ['after']}})
    assert result['recall']['value'] == result['counterparts']['value'] == 1
    assert 0 < result['ndcg']['value'] < 1
    assert retrieval_metrics([], {}, 2)['recall']['status'] == 'not_evaluated'
    assert retrieval_metrics(['before'], {'before': 1, 'after': 1}, 1,
                             {'p': {'before': ['before'], 'after': ['after']}})['counterparts']['value'] == 0


@pytest.mark.parametrize('ranking,qrels,k', [(['a', 'a'], {'a': 1}, 1), ([], {}, 0),
    ([], {}, True), ([], {'a': -1}, 1), ([], {'a': math.nan}, 1), ([], {'a': math.inf}, 1)])
def test_invalid_retrieval_rejected(ranking, qrels, k):
    with pytest.raises(ValueError):
        retrieval_metrics(ranking, qrels, k)


def pair(pid, before, after):
    return {'pair_id': pid, 'before': {'document_id': before, 'version_id': before+'v'},
            'after': {'document_id': after, 'version_id': after+'v'}}


def test_pair_and_document_version_leakage():
    assert check_leakage([pair('p1', 'a', 'b')], [pair('p2', 'c', 'd')])['status'] == 'passed'
    assert check_leakage([pair('p1', 'a', 'b')], [pair('p2', 'b', 'd')])['status'] == 'failed'
    p = pair('p3', 'x', 'y'); p['before']['version_id'] = 'av'
    assert check_leakage([pair('p1', 'a', 'b')], [p])['status'] == 'failed'
    with pytest.raises(ValueError):
        check_leakage([{'pair_id': 'partial'}], [])


def test_freeze_hash_and_tampering():
    protocol = {'corpus_hash': 'abc', 'questions_hash': 'def', 'k': [2],
                'qrels': {'q': {'a': 1, 'b': 1}},
                'counterparts': {'q': {'p': {'before': ['a'], 'after': ['b']}}},
                'thresholds': {'recall': .8, 'ndcg': .7, 'counterparts': 1},
                'partitions': {'tune': [pair('p1', 'a', 'b')], 'holdout': [pair('p2', 'c', 'd')]}}
    frozen = freeze_protocol(protocol)
    assert verify_protocol(frozen)
    protocol['k'] = [99]
    assert '99' not in frozen['json']
    altered = dict(frozen, json=frozen['json'] + ' ')
    assert not verify_protocol(altered)
    protocol['k'] = [0]
    with pytest.raises(ValueError):
        freeze_protocol(protocol)


def test_protocol_requires_counterpart_qrels():
    with pytest.raises(ValueError):
        freeze_protocol({'corpus_hash': 'c', 'questions_hash': 'q', 'k': [1],
                         'qrels': {'q': {'a': 1}},
                         'thresholds': {'recall': .5, 'ndcg': .5, 'counterparts': 1},
                         'partitions': {'tune': [pair('p1', 'a', 'b')], 'holdout': [pair('p2', 'c', 'd')]}})


def test_derivative_alias_against_document_is_leakage():
    p = pair('p2', 'c', 'd')
    p['before']['related_ids'] = ['a']
    assert check_leakage([pair('p1', 'a', 'b')], [p])['status'] == 'failed'


def test_empty_prediction_precision_and_untrusted_provenance():
    ref, runs = fixture()
    ref['kind'] = 'human_adjudicated'
    runs[0]['detected'] = []
    report = evaluate(runs, ref)
    assert report['families']['A']['precision']['status'] == 'not_evaluated'
    assert report['families']['A']['recall']['value'] == 0
    assert report['human_acceptance']['status'] == 'not_evaluated'
    assert report['provenance_authenticated'] is False


def test_ai_review_provenance_retained_without_claiming_human_authentication():
    ref, runs = fixture()
    ref['kind'] = 'ai_independent_review'
    ref['review_provenance'] = {'actor': 'gpt-6-astra', 'model': 'gpt-6-astra',
        'effort': 'high', 'rubric': 'SK09/revision-ia-v1', 'source_hashes': {'original': 'a'*64}}
    report = evaluate(runs, ref)
    assert report['review_provenance'] == ref['review_provenance']
    ref['review_provenance']['source_hashes']['original'] = 'b'*64
    assert report['review_provenance']['source_hashes']['original'] == 'a'*64
    assert report['provenance_authenticated'] is False
    assert report['human_acceptance']['status'] == 'not_evaluated'


def test_citation_boolean_judgments_do_not_pass_evidence_or_claim_coverage():
    ref, runs = fixture()
    a = evaluate(runs, ref)['families']['A']
    assert a['citations']['basis'] == 'supplied_judgments'
    assert a['citation_evidence']['status'] == 'not_evaluated'
    assert a['claim_coverage']['status'] == 'not_evaluated'


def test_raw_retrieval_measurements_do_not_apply_unfrozen_thresholds():
    report = retrieval_metrics(['a'], {'a': 1, 'b': 1}, 1)
    assert report['recall']['value'] == .5
    assert report['recall']['status'] == 'measured'
    assert report['ndcg']['status'] == 'measured'
    assert report['counterparts']['status'] == 'not_evaluated'
    assert report['acceptance'] == 'not_evaluated'
