"""SK04 local retrieval primitives; real inference is supplied by SK05 adapters.

ServerScope must be constructed by the trusted server from SK08 authorization,
never from a query/PDF/client payload. This module does not authenticate callers.
Fixture vectors/counters prove mechanics only. No model, provider, cloud resource
or corpus-quality claim is bundled. Citations refer to SK02 extracted raw text,
not proof of extraction fidelity to the original PDF. Returned trace omits text.
"""
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import math
import re
from typing import Protocol

from sbs.contracts import validate_contract
from sbs.models import TokenCounter, preflight_budget, validate_embeddings


def _hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _positive(value):
    return type(value) is int and value > 0


def chunk_spans(artifact: dict, *, family: str, counter: TokenCounter,
                model_identity: str, limit: int, prefix: str = '', context_chars: int = 0):
    """Preserve verified input provision boundaries; refuse oversized units.

    Consumes an SK02-shaped raw artifact with explicit provision/page boundaries.
    It deliberately does not silently split or truncate a provision to fit. A
    caller requiring a different unit must create a versioned segmentation.
    Unicode offsets are Python code points, [start,end). Page joins, unverified
    semantic boundaries and excluded gaps are retained as limitations/metadata.
    Counter owns complete serialization, including special tokens.
    """
    if family not in ('cybersecurity', 'market_conduct') or type(context_chars) is not int or context_chars < 0:
        raise ValueError('invalid_chunk_configuration')
    if not isinstance(prefix, str):
        raise ValueError('invalid_prefix')
    raw = artifact['rawtext']
    if hashlib.sha256(raw.encode()).hexdigest() != artifact['rawtext_sha256']:
        raise ValueError('rawtext_hash_mismatch')
    pages = artifact['pages']
    previous = -1
    for page in pages:
        if (type(page['start']) is not int or type(page['end']) is not int
                or not 0 <= page['start'] <= page['end'] <= len(raw)
                or page['start'] < previous or not _positive(page['page'])):
            raise ValueError('invalid_page_offsets')
        previous = page['end']
    result, ids, previous, gaps = [], set(), 0, []
    provisions = sorted(artifact['provisions'], key=lambda p: (p['start'], p['end']))
    identities = {(p['document_id'], p['version_id']) for p in provisions}
    if len(identities) > 1:
        raise ValueError('mixed_document_artifact')
    for provision in provisions:
        if not validate_contract('Provision', provision)['valid']:
            raise ValueError('invalid_provision')
        start, end = provision['start'], provision['end']
        if (start < previous or end > len(raw) or raw[start:end] != provision['text']
                or provision['citation_id'] in ids):
            raise ValueError('invalid_literal_or_overlapping_span')
        touched = [p['page'] for p in pages if p['start'] < end and p['end'] > start]
        start_pages = [p['page'] for p in pages if p['start'] <= start < p['end']]
        if not touched or start_pages != [provision['page']]:
            raise ValueError('invalid_citation_page')
        if start > previous:
            gaps.append((previous, start))
        emb_start = max(0, start-context_chars)
        emb_text = raw[emb_start:end]
        parts = (prefix, emb_text)
        budget = preflight_budget(parts, limit, model_identity=model_identity, counter=counter)
        if budget['status'] != 'ready':
            raise ValueError('budget_exceeded_or_tokenizer_pending:explicit_adaptation_required')
        limitations = list(artifact.get('quality', {}).get('limitations', []))
        limitations += ['semantic_boundaries_not_certified', 'layout_table_review_pending']
        if len(touched) > 1:
            limitations.append('page_seam_review_pending')
        result.append({'family': family, 'citation': deepcopy(provision), 'pages': touched,
                       'embedding_start': emb_start, 'embedding_text': emb_text,
                       'input_parts': parts, 'budget': budget, 'limitations': sorted(set(limitations)),
                       'source': {k: artifact[k] for k in ('sha256', 'rawtext_sha256', 'extractor', 'config_hash')},
                       'strategy': {'id': 'span-limpio-contexto-v1', 'version': 1,
                                    'adaptation': 'preserve_input_units', 'context_chars': context_chars},
                       'literal_sha256': hashlib.sha256(provision['text'].encode()).hexdigest()})
        ids.add(provision['citation_id'])
        previous = end
    if previous < len(raw):
        gaps.append((previous, len(raw)))
    for row in result:
        row['excluded_offsets'] = gaps.copy()
    return result


@dataclass(frozen=True)
class ServerScope:
    """Server-owned authorization snapshot, not a client-selectable filter."""
    families: frozenset[str]
    document_versions: frozenset[tuple[str, str]]

    def __post_init__(self):
        object.__setattr__(self, 'families', frozenset(self.families))
        object.__setattr__(self, 'document_versions', frozenset(tuple(v) for v in self.document_versions))

    def permits(self, row):
        citation = row['citation']
        return (row['family'] in self.families and
                (citation['document_id'], citation['version_id']) in self.document_versions)


class EmbeddingAdapter(Protocol):
    """SK05-pinned adapter. Implementations own tokenizer preflight and transport.

    Document inputs are complete parts (prefix, contextual text); adapters must
    preserve them, enforce limits and refuse provider truncation. Returned vectors
    must belong to identity. The caller explicitly chooses/calls an adapter;
    merely constructing retrieval code never executes paid inference.
    """
    identity: str
    dimension: int

    def embed_documents(self, inputs: list[tuple[str, ...]]) -> list[list[float]]: ...
    def embed_query(self, query: str) -> list[float]: ...


def _validate_records(rows, model_identity):
    ids = set()
    for row in rows:
        c = row['citation']
        if not validate_contract('Provision', c)['valid']:
            raise ValueError('invalid_provision')
        if c['citation_id'] in ids:
            raise ValueError('duplicate_citation_identity')
        ids.add(c['citation_id'])
        if (row['literal_sha256'] != hashlib.sha256(c['text'].encode()).hexdigest()
                or row['embedding_start'] > c['start']
                or row['embedding_text'][c['start']-row['embedding_start']:] != c['text']
                or tuple(row['input_parts'])[1:] != (row['embedding_text'],)
                or row['budget']['status'] != 'ready'
                or row['budget']['model_identity'] != model_identity):
            raise ValueError('chunk_integrity_or_identity_mismatch')
    identities = {_hash({'extractor': r['source']['extractor'],
                         'strategy': r['strategy'], 'prefix': r['input_parts'][0],
                         'tokenizer': r['budget']['tokenizer'],
                         'tokenizer_revision': r['budget']['tokenizer_revision'],
                         'limit': r['budget']['limit']}) for r in rows}
    if len(identities) > 1:
        raise ValueError('mixed_chunk_identity')


class LocalIndex:
    """Detached immutable snapshot; rebuild (don't overwrite) when identity changes.

    Accept only chunk_spans records whose literal digest and complete input are
    intact. This verifies structural integrity, not external source authenticity.
    """
    def __init__(self, records, vectors, *, dimension, model_identity, actual_identity,
                 complete=True):
        if not _positive(dimension) or not isinstance(model_identity, str) or not model_identity.strip():
            raise ValueError('invalid_index_identity')
        if actual_identity != model_identity:
            raise ValueError('embedding_identity_mismatch')
        rows = deepcopy(list(records))
        _validate_records(rows, model_identity)
        if rows:
            checked = validate_embeddings(vectors, expected_count=len(rows), dimension=dimension,
                                          expected_identity=model_identity, actual_identity=actual_identity)
            if any(math.hypot(*v) == 0 or not math.isfinite(math.hypot(*v)) for v in checked):
                raise ValueError('invalid_vector_norm')
        else:
            if list(vectors):
                raise ValueError('embedding_count_mismatch')
            checked = ()
        self._rows = tuple(rows)
        self._vectors = checked
        self.dimension = dimension
        self.model_identity = model_identity
        self.complete = bool(complete)
        self.index_hash = _hash({'rows': rows, 'vectors': checked, 'model_identity': model_identity,
                                 'dimension': dimension, 'complete': self.complete})

    @classmethod
    def from_adapter(cls, records, adapter: EmbeddingAdapter, *, complete=True):
        rows = deepcopy(list(records))
        _validate_records(rows, adapter.identity)
        vectors = adapter.embed_documents([tuple(r['input_parts']) for r in rows]) if rows else []
        return cls(rows, vectors, dimension=adapter.dimension, model_identity=adapter.identity,
                   actual_identity=adapter.identity, complete=complete)


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def _ranking(values, allowed=None):
    result, seen = [], set()
    for identifier, score in values:
        if not isinstance(identifier, str) or not _finite(score):
            raise ValueError('invalid_ranking_score')
        if allowed is not None and identifier not in allowed:
            continue
        if identifier not in seen:
            result.append((identifier, float(score)))
            seen.add(identifier)
    return result


def rrf(*rankings, k=60):
    """Fuse independent ranked lists once; deduplicate identity per input list."""
    if not _positive(k):
        raise ValueError('invalid_rrf_k')
    scores = Counter()
    for ranking in rankings:
        for rank, (identifier, _) in enumerate(_ranking(ranking), 1):
            scores[identifier] += 1/(k+rank)
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))


def _terms(text):
    return re.findall(r'\w+', text.casefold())


def _bm25(query, rows, k1=1.5, b=.75):
    documents = [Counter(_terms(row['citation']['text'])) for row in rows]
    lengths = [sum(doc.values()) for doc in documents]
    average = sum(lengths)/len(lengths) if lengths else 0
    frequencies = Counter(term for doc in documents for term in doc)
    scores = []
    for row, doc, length in zip(rows, documents, lengths):
        score = 0.
        for term in set(_terms(query)):
            if not doc[term]:
                continue
            idf = math.log(1 + (len(rows)-frequencies[term]+.5)/(frequencies[term]+.5))
            score += idf * doc[term]*(k1+1)/(doc[term]+k1*(1-b+b*length/average))
        if score > 0:
            scores.append((row['citation']['citation_id'], score))
    return sorted(scores, key=lambda item: (-item[1], item[0]))


def retrieve(index: LocalIndex, query: str, context: dict, scope: ServerScope, *,
             query_vector=None, query_identity=None, adapter: EmbeddingAdapter | None = None,
             top_k=5, candidate_k=20, reranker=None, native_rrf=None,
             counterparts=None, neighbors=None, rrf_k=60):
    """Return {status,evidence,trace,limitations}; never a no-changes conclusion.

    Reranker(query, detached_authorized_rows) returns one finite score per row.
    Native RRF is an already fused server result; internal lists are unavailable
    and no second fusion runs. Explicit citation-ID alignments can add normative
    counterparts outside top-k; callers derive these maps from SK03, never text.
    All expansion is restricted to the authorized comparison pair. Scope filtering
    happens before BM25 statistics, vector scoring and reranker invocation.
    """
    if not validate_contract('QueryContext', context)['valid']:
        raise ValueError('invalid_query_context')
    if not isinstance(scope, ServerScope) or not isinstance(query, str) or not query.strip():
        raise ValueError('invalid_query_or_server_scope')
    if not _positive(top_k) or not _positive(candidate_k) or not _positive(rrf_k):
        raise ValueError('invalid_retrieval_limits')
    if query_vector is not None and adapter is not None:
        raise ValueError('ambiguous_query_embedding_source')
    pair = deepcopy(context['pair'])
    pair_ids = {(pair[side]['document_id'], pair[side]['version_id']) for side in ('before', 'after')}
    trace = {'index_hash': index.index_hash, 'model_identity': index.model_identity,
             'lexical': [], 'vector': [], 'fusion': [], 'reranked': None,
             'fusion_method': 'native_rrf' if native_rrf is not None else 'rrf',
             'counterparts': [], 'neighbors': [],
             'configuration': {'rrf_k': rrf_k, 'top_k': top_k, 'candidate_k': candidate_k,
                               'bm25_k1': 1.5, 'bm25_b': .75, 'dimension': index.dimension}}
    limitations = ['retrieval_does_not_establish_global_coverage']
    def finish(status, selected=()):
        rows = list(selected)
        citations = [{k: v for k, v in row['citation'].items() if k != 'synthetic'} for row in rows]
        limits = sorted(set(limitations + [v for row in rows for v in row['limitations']]))
        evidence = {'evidence_id': _hash([index.index_hash, pair, citations, limits]),
                    'evidence_version': '1', 'pair': pair, 'citations': citations,
                    'coverage': 'partial', 'limitations': limits,
                    'synthetic': any(row['citation']['synthetic'] for row in rows)}
        if not validate_contract('EvidencePack', evidence)['valid']:
            raise ValueError('invalid_output_evidence')
        return {'status': status, 'evidence': evidence, 'trace': trace, 'limitations': limits}
    if context['family'] not in scope.families or not pair_ids.intersection(scope.document_versions):
        limitations.append('access_denied')
        return finish('access_denied')
    authorized = [(row, vector) for row, vector in zip(index._rows, index._vectors)
                  if scope.permits(row) and row['family'] == context['family']
                  and (row['citation']['document_id'], row['citation']['version_id']) in pair_ids
                  and row['citation']['source_kind'] == 'normative']
    rows = [row for row, _ in authorized]
    by_id = {row['citation']['citation_id']: row for row in rows}
    if not index.complete:
        limitations.append('index_incomplete')
    if not rows:
        limitations.append('no_authorized_candidates')
        return finish('index_incomplete' if not index.complete else 'empty')
    if native_rrf is not None:
        trace['lexical'], trace['vector'] = None, None
        limitations.append('native_internal_rankings_unavailable')
        fused = _ranking(native_rrf, by_id)[:candidate_k]
    else:
        if adapter is not None:
            if adapter.identity != index.model_identity or adapter.dimension != index.dimension:
                raise ValueError('embedding_identity_mismatch')
            try:
                query_vector = adapter.embed_query(query)
                query_identity = adapter.identity
            except Exception:
                limitations.append('query_embedding_failed')
                return finish('technical_error')
        if query_vector is None:
            raise ValueError('query_embedding_required')
        q = validate_embeddings([query_vector], expected_count=1, dimension=index.dimension,
                                expected_identity=index.model_identity, actual_identity=query_identity)[0]
        norm = math.hypot(*q)
        if not norm or not math.isfinite(norm):
            raise ValueError('invalid_query_vector_norm')
        trace['lexical'] = _bm25(query, rows)[:candidate_k]
        vector_scores = []
        for row, vector in authorized:
            vector_norm = math.hypot(*vector)
            score = sum((x/norm)*(y/vector_norm) for x, y in zip(q, vector))
            vector_scores.append((row['citation']['citation_id'], score))
        trace['vector'] = sorted(vector_scores, key=lambda item: (-item[1], item[0]))[:candidate_k]
        fused = rrf(trace['lexical'], trace['vector'], k=rrf_k)[:candidate_k]
    trace['fusion'] = fused
    ranked = fused
    if reranker is not None and fused:
        try:
            candidates = [deepcopy(by_id[identifier]) for identifier, _ in fused]
            scores = list(reranker(query, candidates))
            if len(scores) != len(candidates) or not all(_finite(s) for s in scores):
                raise ValueError('invalid_reranker_response')
            ranked = sorted([(identifier, float(score)) for (identifier, _), score in zip(fused, scores)],
                            key=lambda item: (-item[1], item[0]))
            trace['reranked'] = ranked
        except Exception:
            limitations.append('reranker_failed')
            return finish('technical_error')
    elif reranker is None:
        limitations.append('reranker_not_executed')
    if not ranked:
        limitations.append('no_authorized_candidates')
        return finish('index_incomplete' if not index.complete else 'empty')
    selected = dict((identifier, by_id[identifier]) for identifier, _ in ranked[:top_k])
    for name, mapping in (('counterparts', counterparts), ('neighbors', neighbors)):
        for identifier in list(selected):
            for target in (mapping or {}).get(identifier, ()):
                row = by_id.get(target)
                if row is None:
                    limitations.append(name + '_unavailable')
                    continue
                if name == 'counterparts':
                    origin = by_id[identifier]['citation']
                    citation = row['citation']
                    if (origin['document_id'], origin['version_id']) == (citation['document_id'], citation['version_id']):
                        limitations.append('invalid_counterpart_alignment')
                        continue
                if target not in selected:
                    selected[target] = row
                    trace[name].append(target)
    present = {(r['citation']['document_id'], r['citation']['version_id']) for r in selected.values()}
    if not pair_ids.issubset(present):
        limitations.append('counterpart_missing')
    return finish('index_incomplete' if not index.complete else 'partial', selected.values())
