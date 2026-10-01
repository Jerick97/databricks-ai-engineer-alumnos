"""SK09 deterministic technical evaluation; no legal adjudication or network I/O.

``evaluate(runs, reference)`` takes materialized mappings, not global file IDs.
Reference: kind, optional review_provenance, families mapping to unique change IDs,
critical IDs (subset), insufficient_cases. Runs: run_id, family, detected IDs,
citations with Boolean faithful/localizable judgements, flagged_insufficient IDs,
and times with unique case_id plus baseline/agent/review seconds (review includes
corrections). IDs are scoped by family; retries of change IDs count only once.
Citation judgements and reference provenance are supplied assertions, not verified
credentials. A technical report never approves legal or institutional impact.

Retrieval qrels map passage IDs to finite nonnegative relevance (linear DCG gain).
Counterpart qrels map pair IDs to before/after lists of relevant passage IDs.
Frozen protocols return canonical JSON and SHA256; callers own persistence. No
holdout material is exported into prompts and this module never builds prompts.
"""
import hashlib
import json
import math
from copy import deepcopy
from statistics import median


NOT_EVALUATED = 'not_evaluated'


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError('Expected finite nonnegative number')
    return value


def _ids(values):
    if not isinstance(values, (list, tuple, set)) or any(not isinstance(v, str) or not v for v in values):
        raise ValueError('Expected nonempty string IDs')
    return set(values)


def _ratio(n, d, threshold=1):
    value = n / d if d else None
    return {'numerator': n, 'denominator': d, 'value': value,
            'status': NOT_EVALUATED if value is None else 'passed' if value >= threshold else 'failed'}


def _status(statuses):
    statuses = list(statuses)
    return 'failed' if 'failed' in statuses else NOT_EVALUATED if not statuses or NOT_EVALUATED in statuses else 'passed'


def evaluate(runs, reference):
    """Evaluate materialized runs against a reference, independently per family.

    Time saving is median of paired fractional savings, counting agent + review.
    Zero-baseline pairs remain visible but make that family's time gate unevaluated.
    Missing families/critical subsets/citations are never implicitly perfect.
    """
    families = reference['families']
    if not isinstance(families, dict):
        raise ValueError('families must be a mapping')
    grouped = {family: [] for family in families}
    run_ids = set()
    for run in runs:
        if run['family'] not in grouped or not isinstance(run['run_id'], str) or not run['run_id'] or run['run_id'] in run_ids:
            raise ValueError('Unknown family or duplicate/invalid run ID')
        run_ids.add(run['run_id'])
        grouped[run['family']].append(run)
    report = {}
    for family, ref in families.items():
        gold, critical = _ids(ref['changes']), _ids(ref.get('critical', []))
        insufficient = _ids(ref.get('insufficient_cases', []))
        if not critical <= gold:
            raise ValueError('Critical IDs must belong to reference changes')
        detected, flagged, citations, times = set(), set(), [], []
        for run in grouped[family]:
            detected |= _ids(run.get('detected', []))
            flagged |= _ids(run.get('flagged_insufficient', []))
            citations.extend(run.get('citations', []))
            times.extend(run.get('times', []))
        for citation in citations:
            if any(type(citation.get(key)) is not bool for key in ('faithful', 'localizable')):
                raise ValueError('Citations require Boolean judgements')
        time_ids, savings, excluded = set(), [], 0
        paired = []
        for row in times:
            case_id = row['case_id']
            if not isinstance(case_id, str) or not case_id or case_id in time_ids:
                raise ValueError('Time samples must have unique paired case IDs')
            time_ids.add(case_id)
            baseline, agent, review = (_number(row[key]) for key in ('baseline', 'agent', 'review'))
            total = agent + review
            _number(total)
            saving = (baseline - total) / baseline if baseline else None
            if saving is not None and not math.isfinite(saving):
                raise ValueError('Time ratio must be finite')
            paired.append({'case_id': case_id, 'baseline': baseline, 'agent_plus_review': total, 'saving': saving})
            if saving is None:
                excluded += 1
            else:
                savings.append(saving)
        value = median(savings) if savings and not excluded else None
        tp, fp, fn = len(gold & detected), len(detected - gold), len(gold - detected)
        omitted = len(critical - detected)
        metrics = {
            'recall': _ratio(tp, len(gold), .95), 'precision': _ratio(tp, len(detected), .90),
            'critical': {'numerator': omitted, 'denominator': len(critical), 'value': omitted if critical else None,
                         'status': NOT_EVALUATED if not critical else 'failed' if omitted else 'passed'},
            'citations': _ratio(sum(c['faithful'] and c['localizable'] for c in citations), len(citations)),
            'insufficiency': _ratio(len(insufficient & flagged), len(insufficient)),
            'time_saving': {'value': value, 'denominator': len(times), 'valid_pairs': len(savings),
                            'zero_baseline_pairs': excluded, 'pairs': paired,
                            'status': NOT_EVALUATED if value is None else 'passed' if value >= .30 else 'failed'},
        }
        metrics['citations']['basis'] = 'supplied_judgments'
        metrics['citation_evidence'] = {'status': NOT_EVALUATED,
            'reason': 'Boolean judgments do not verify original sources, locators or version identity'}
        metrics['claim_coverage'] = {'status': NOT_EVALUATED,
            'reason': 'Expected material claims and their evidence coverage are not measured by this harness'}
        report[family] = dict(metrics, tp=tp, fp=fp, fn=fn, sample_runs=len(grouped[family]),
                              missing_change_ids=sorted(gold - detected), false_positive_ids=sorted(detected - gold),
                              omitted_critical_ids=sorted(critical - detected),
                              status=_status(metric['status'] for metric in metrics.values()))
    provenance = reference.get('review_provenance', {})
    if not isinstance(provenance, dict):
        raise ValueError('Review provenance must be a mapping')
    return {'report_kind': 'technical_only', 'reference_kind': reference.get('kind', 'unspecified'),
            'review_provenance': deepcopy(provenance),
            'provenance_authenticated': False, 'legal_certification': False,
            'human_acceptance': {'status': NOT_EVALUATED, 'reason': 'No human adjudication performed; this does not block the authorized AI pilot review or conversation'},
            'families': report, 'status': _status(row['status'] for row in report.values()),
            'rag_acceptance': {'status': NOT_EVALUATED, 'reason': 'Separate frozen real-corpus benchmark required'},
            'cost': None}


def _k(k):
    if type(k) is not int or k <= 0:
        raise ValueError('k must be a positive integer')


def retrieval_metrics(ranking, qrels, k, counterparts=None):
    """Return Recall@k, linear-gain nDCG@k and complete pair coverage.

    Scores are measurements only, never RAG acceptance without a frozen protocol.
    Duplicate rankings are rejected even outside the top-k window.
    """
    _k(k)
    unique = _ids(ranking)
    if len(unique) != len(ranking):
        raise ValueError('Ranking cannot contain duplicates')
    if not isinstance(qrels, dict):
        raise ValueError('Explicit qrels mapping required')
    _ids(list(qrels))
    for grade in qrels.values():
        _number(grade)
    relevant = {p for p, grade in qrels.items() if grade > 0}
    top = ranking[:k]
    recall = _ratio(len(set(top) & relevant), len(relevant))
    # Scale gains to avoid overflow while preserving the normalized metric.
    scale = max(qrels.values(), default=0) or 1
    dcg = sum((qrels.get(p, 0) / scale) / math.log2(i + 2) for i, p in enumerate(top))
    ideal = sum((g / scale) / math.log2(i + 2) for i, g in enumerate(sorted(qrels.values(), reverse=True)[:k]))
    pairs, complete = counterparts or {}, 0
    for sides in pairs.values():
        before, after = _ids(sides['before']), _ids(sides['after'])
        if not before or not after or not (before | after) <= relevant or before & after:
            raise ValueError('Counterpart qrels need distinct relevant before/after passages')
        complete += bool(before & set(top)) and bool(after & set(top))
    result = {'k': k, 'recall': recall, 'ndcg': _ratio(dcg, ideal), 'counterparts': _ratio(complete, len(pairs)),
              'acceptance': NOT_EVALUATED}
    for key in ('recall', 'ndcg', 'counterparts'):
        result[key]['status'] = 'measured' if result[key]['value'] is not None else NOT_EVALUATED
    return result


def check_leakage(tune, holdout):
    """Reject incomplete pairs; flag shared pair/doc/version/derivation identities.

    Each side supplies document_id/version_id; optional related_ids can identify
    derivatives or neighboring provisions. Identity discovery is the caller's job.
    """
    def identities(pairs):
        result, seen_pairs = set(), set()
        for pair in pairs:
            pid = pair.get('pair_id')
            if not isinstance(pid, str) or not pid or pid in seen_pairs:
                raise ValueError('Unique complete pair IDs required')
            seen_pairs.add(pid)
            result.add(('pair', pid))
            for side in ('before', 'after'):
                item = pair.get(side, {})
                for key in ('document_id', 'version_id'):
                    value = item.get(key)
                    if not isinstance(value, str) or not value:
                        raise ValueError('Both pair sides need document/version identities')
                    result.add(('identity', value))
                for value in _ids(item.get('related_ids', [])):
                    result.add(('identity', value))
        return result
    shared = identities(tune) & identities(holdout)
    return {'status': 'failed' if shared else 'passed', 'shared_identities': [list(x) for x in sorted(shared)]}


def freeze_protocol(protocol):
    """Validate and hash a caller-owned JSON protocol; never write prompts/files."""
    for key in ('corpus_hash', 'questions_hash'):
        if not isinstance(protocol.get(key), str) or not protocol[key]:
            raise ValueError('Corpus/question hashes required')
    if not isinstance(protocol.get('k'), list) or not protocol['k']:
        raise ValueError('Frozen k values required')
    for k in protocol['k']:
        _k(k)
    thresholds = protocol.get('thresholds', {})
    if not thresholds or not {'recall', 'ndcg', 'counterparts'} <= thresholds.keys():
        raise ValueError('Numeric retrieval thresholds required')
    for threshold in thresholds.values():
        if _number(threshold) > 1:
            raise ValueError('Retrieval thresholds must be in [0,1]')
    qrels = protocol.get('qrels')
    if not isinstance(qrels, dict) or not qrels:
        raise ValueError('Explicit query qrels required')
    counterparts = protocol.get('counterparts')
    if not isinstance(counterparts, dict) or set(counterparts) != set(qrels):
        raise ValueError('Counterpart qrels required for every query')
    for query, passages in qrels.items():
        if not counterparts[query]:
            raise ValueError('Each query needs counterpart qrels')
        retrieval_metrics([], passages, 1, counterparts[query])
    partitions = protocol['partitions']
    if not partitions['tune'] or not partitions['holdout']:
        raise ValueError('Nonempty tune and holdout partitions required')
    if check_leakage(partitions['tune'], partitions['holdout'])['status'] != 'passed':
        raise ValueError('Partition leakage')
    payload = json.dumps(protocol, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
    return {'json': payload, 'sha256': hashlib.sha256(payload.encode()).hexdigest()}


def verify_protocol(frozen):
    """Check integrity and schema; this does not authenticate who froze a protocol."""
    try:
        return (hashlib.sha256(frozen['json'].encode()).hexdigest() == frozen['sha256']
                and freeze_protocol(json.loads(frozen['json'])) == frozen)
    except (KeyError, TypeError, ValueError):
        return False
