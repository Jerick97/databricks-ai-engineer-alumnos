"""SK04 synthetic algorithm fixtures; no semantic/corpus/model validation."""
import copy
import hashlib
import json
import math
import pytest
from sbs.models import TokenCounter
from sbs.contracts import validate_contract
from sbs.retrieval import chunk_spans, LocalIndex, ServerScope, retrieve, rrf

PAIR = {'pair_id': 'fixture-pair', 'family': 'cybersecurity',
        'before': {'document_id': 'doc', 'version_id': 'v1'},
        'after': {'document_id': 'doc', 'version_id': 'v2'}}
CTX = {'context_id': 'fixture-context', 'family': 'cybersecurity', 'pair': PAIR,
       'target_date': None, 'selected_provision_id': None}
COUNTER = TokenCounter('fixture-character-counter', 'v1', 'fixture-model',
                       lambda parts: sum(map(len, parts)) + 2)
SCOPE = ServerScope(frozenset({'cybersecurity'}), frozenset({('doc', 'v1'), ('doc', 'v2')}))


def artifact(version='v2', texts=('ciber seguridad', 'reporte mensual')):
    raw, provisions, pages = '', [], []
    for n, text in enumerate(texts):
        start = len(raw)
        raw += text
        provisions.append(dict(citation_id=f'{version}-{n}', document_id='doc', version_id=version,
                               provision_id=f'art{n}', start=start, end=len(raw), text=text,
                               page=n+1, source_kind='normative', synthetic=True))
        pages.append({'page': n+1, 'start': start, 'end': len(raw), 'error': None})
    return dict(rawtext=raw, rawtext_sha256=hashlib.sha256(raw.encode()).hexdigest(),
                sha256='a'*64, extractor='fixture-extractor', config_hash='b'*64,
                provisions=provisions, pages=pages,
                quality={'status': 'partial', 'limitations': ['fixture_only']})


def chunks(a=None, **kw):
    return chunk_spans(a or artifact(), family='cybersecurity', counter=COUNTER,
                       model_identity='fixture-model', limit=100, **kw)


def index(records=None, vectors=None, **kw):
    records = records if records is not None else chunks()
    vectors = vectors if vectors is not None else [[1., 0.] for _ in records]
    return LocalIndex(records, vectors, dimension=2, model_identity='fixture-model',
                      actual_identity='fixture-model', **kw)


def query(idx=None, **kw):
    return retrieve(idx or index(), 'ciber', CTX, SCOPE, query_vector=[1., 0.],
                    query_identity='fixture-model', **kw)


def test_clean_spans_unicode_context_and_budget():
    a = artifact(texts=('á🙂 uno', 'dos'))
    result = chunks(a, prefix='P:', context_chars=3)
    assert result[1]['citation']['text'] == 'dos'
    assert result[1]['embedding_text'] == 'uno' + 'dos'
    assert result[1]['input_parts'] == ('P:', 'unodos')
    assert result[1]['citation']['start'] == len('á🙂 uno')
    assert result[1]['pages'] == [2]
    assert result[1]['budget']['input_tokens'] == 10
    assert result[0]['citation']['end'] == result[1]['citation']['start']
    with pytest.raises(ValueError, match='budget_exceeded'):
        chunk_spans(a, family='cybersecurity', counter=COUNTER, model_identity='fixture-model', limit=3)


@pytest.mark.parametrize('corruption', ['raw_hash', 'literal', 'overlap', 'page'])
def test_chunk_rejects_unverifiable_source(corruption):
    a = artifact()
    if corruption == 'raw_hash': a['rawtext_sha256'] = '0'*64
    if corruption == 'literal': a['provisions'][0]['text'] = 'false'
    if corruption == 'overlap': a['provisions'].append(copy.deepcopy(a['provisions'][0]))
    if corruption == 'page': a['provisions'][0]['page'] = 9
    with pytest.raises(ValueError): chunks(a)


def test_rrf_once_and_dedup_and_native_passthrough():
    scores = rrf([('a', 9), ('a', 8), ('b', 1)], [('b', 2), ('a', 1)], k=60)
    assert dict(scores)['a'] == pytest.approx(1/61 + 1/62)
    assert dict(scores)['b'] == pytest.approx(1/62 + 1/61)
    result = query(native_rrf=[('v2-1', 0.314)], reranker=lambda q, rows: [0.8]*len(rows))
    assert result['trace']['fusion'] == [('v2-1', 0.314)]
    assert result['trace']['lexical'] is None
    assert result['trace']['fusion_method'] == 'native_rrf'


def test_bm25_vector_fusion_real_reranker_interface_and_trace():
    seen = []
    def rerank(q, rows):
        seen.extend(r['citation']['citation_id'] for r in rows)
        return [float(n) for n in range(len(rows))]
    result = query(reranker=rerank)
    assert seen
    assert result['trace']['lexical'][0][0] == 'v2-0'
    assert result['trace']['vector'][0][1] == pytest.approx(1.)
    assert result['trace']['reranked'][0][1] == 1.
    assert 'ciber seguridad' not in json.dumps(result['trace'])
    assert validate_contract('EvidencePack', result['evidence'])['valid']
    assert result['evidence']['coverage'] == 'partial'
    assert 'reranker_not_executed' in query()['limitations']


def test_scope_before_rank_rerank_neighbors_and_counterparts():
    records = chunks() + chunks(artifact('v1', ('anterior',)))
    hidden = copy.deepcopy(records[0]); hidden['citation']['citation_id'] = 'secret'
    hidden['family'] = 'market_conduct'
    records.append(hidden)
    seen = []
    result = query(index(records), top_k=1, counterparts={'v2-0': ['v1-0', 'secret']},
                   neighbors={'v2-0': ['secret', 'v2-1']},
                   reranker=lambda q, rows: seen.extend(rows) or [float(r['citation']['citation_id'] == 'v2-0') for r in rows])
    ids = {c['citation_id'] for c in result['evidence']['citations']}
    assert {'v2-0', 'v1-0', 'v2-1'} <= ids
    assert 'secret' not in ids and 'secret' not in json.dumps(result['trace'])
    assert all(r['family'] == 'cybersecurity' for r in seen)
    assert result['status'] == 'partial'


def test_empty_denied_incomplete_error_are_distinct():
    assert query(index([], []))['status'] == 'empty'
    assert query(index(complete=False))['status'] == 'index_incomplete'
    empty_scope = ServerScope(frozenset(), frozenset())
    denied = retrieve(index(), 'q', CTX, empty_scope, query_vector=[1., 0.], query_identity='fixture-model')
    assert denied['status'] == 'access_denied'
    def broken(*args): raise RuntimeError('sensitive provider error')
    error = query(reranker=broken)
    assert error['status'] == 'technical_error'
    assert 'sensitive' not in json.dumps(error)
    assert all(x.get('no_changes') is not True for x in [denied, error])


@pytest.mark.parametrize('vectors', [[[1., 0.]], [[1., math.nan], [1., 0.]],
                                    [[1.], [1.]], [[0., 0.], [1., 0.]]])
def test_index_rejects_invalid_vectors(vectors):
    with pytest.raises(ValueError): index(vectors=vectors)


def test_identity_duplicate_bad_query_and_reranker_validation():
    with pytest.raises(ValueError):
        LocalIndex(chunks(), [[1., 0.]]*2, dimension=2, model_identity='a', actual_identity='b')
    with pytest.raises(ValueError): index(chunks()+chunks())
    for scorer in (lambda q,r: [], lambda q,r: [math.nan]*len(r), lambda q,r: [True]*len(r)):
        assert query(reranker=scorer)['status'] == 'technical_error'


def test_index_detaches_inputs_and_changes_identity():
    rows = chunks()
    idx = index(rows)
    rows[0]['citation']['text'] = 'tampered'
    assert query(idx)['evidence']['citations'][0]['text'] == 'ciber seguridad'
    other = chunks(prefix='different')
    assert idx.index_hash != index(other).index_hash


def test_adapter_is_explicit_and_queries_validate_identity():
    class FixtureAdapter:
        identity = 'fixture-model'
        dimension = 2
        def embed_documents(self, inputs): return [[1., 0.] for _ in inputs]
        def embed_query(self, query): return [1., 0.]
    idx = LocalIndex.from_adapter(chunks(), FixtureAdapter())
    result = retrieve(idx, 'ciber', CTX, SCOPE, adapter=FixtureAdapter())
    assert result['status'] == 'partial'
    with pytest.raises(ValueError, match='identity'):
        retrieve(idx, 'ciber', CTX, SCOPE, query_vector=[1., 0.], query_identity='foreign')


def test_filtered_document_not_sent_to_reranker_or_ranked():
    rows = chunks() + chunks(artifact('v1', ('top secret ciber',)))
    scope = ServerScope(frozenset({'cybersecurity'}), frozenset({('doc', 'v2')}))
    seen = []
    result = retrieve(index(rows), 'ciber', CTX, scope, query_vector=[1., 0.],
                      query_identity='fixture-model', counterparts={'v2-0': ['v1-0']},
                      reranker=lambda q, r: seen.extend(r) or [1.]*len(r))
    assert all(r['citation']['version_id'] == 'v2' for r in seen)
    assert 'v1-0' not in json.dumps(result['trace'])
    assert 'counterpart_missing' in result['limitations']


def test_mixed_tokenizer_or_chunk_configuration_rejected():
    rows = chunks()
    rows[1]['budget']['tokenizer_revision'] = 'foreign-revision'
    with pytest.raises(ValueError, match='mixed_chunk_identity'): index(rows)


def test_native_rrf_does_not_invoke_query_adapter_and_filters_ids():
    class Forbidden:
        def embed_query(self, query): raise AssertionError('not authorized')
    result = retrieve(index(), 'ciber', CTX, SCOPE, adapter=Forbidden(),
                      native_rrf=[('foreign', 99.), ('v2-0', .2), ('v2-0', .1)])
    assert result['trace']['fusion'] == [('v2-0', .2)]
    denied = retrieve(index(), 'ciber', CTX, ServerScope(frozenset(), frozenset()), adapter=Forbidden())
    assert denied['status'] == 'access_denied'


def test_adapter_never_receives_incompatible_budget_inputs():
    class Forbidden:
        identity = 'other-model'
        dimension = 2
        def embed_documents(self, inputs): raise AssertionError('must reject before inference')
    with pytest.raises(ValueError, match='identity'):
        LocalIndex.from_adapter(chunks(), Forbidden())


def test_bm25_statistics_use_only_authorized_pair():
    rows = chunks() + chunks(artifact('v1', ('ciber ciber ciber',)))
    scope = ServerScope(frozenset({'cybersecurity'}), frozenset({('doc', 'v2')}))
    result = retrieve(index(rows), 'ciber', CTX, scope, query_vector=[1., 0.], query_identity='fixture-model')
    assert result['trace']['lexical'] == [('v2-0', pytest.approx(math.log(2)))]
    assert result['trace']['configuration']['rrf_k'] == 60


def test_cosine_computes_each_norm_once(monkeypatch):
    import sbs.retrieval as module
    idx = index()
    original = math.hypot
    calls = []
    def counted(*values):
        calls.append(values)
        return original(*values)
    monkeypatch.setattr(module.math, 'hypot', counted)
    result = query(idx)
    assert len(calls) == 3  # one query, one per authorized candidate
    assert all(score == pytest.approx(1.) for _, score in result['trace']['vector'])
