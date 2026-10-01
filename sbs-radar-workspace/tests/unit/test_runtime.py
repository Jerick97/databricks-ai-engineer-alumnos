import pytest
from sbs.runtime import create_service

@pytest.fixture(scope='module')
def service():
    return create_service()

def test_real_cache_catalog_and_comparisons_without_inference(service):
    c=service.catalog()
    assert len(c['families'])==2 and len(c['pairs'])==2
    for p in c['pairs']:
        for v in p['provisions']:
            d=service.comparison(p['id'],v['id'])
            assert d['before']['text'] and d['after']['text']
            assert d['status']=='unreviewed' and d['limitations']
            for citation in d['citations']:
                assert service.source(citation['source_id']).read_bytes().startswith(b'%PDF')
    assert service.generator is None

def test_scope_and_source_ids_fail_closed(service):
    with pytest.raises(KeyError):service.source('/etc/passwd')
    with pytest.raises(KeyError):service.comparison('cyber-504','art27')
    with pytest.raises(KeyError):service.comparison('unknown')

def test_cached_queries_retain_pinned_identity(service):
    assert service.index.index_hash==service.index_payload['index_hash']
    assert len(service.query_cache)==3
    assert service.generator is None

def test_no_silent_all_provisions_default(service):
    with pytest.raises(KeyError):service.comparison('market-3274',None)

def test_selected_article_is_explicit_evidence_even_without_semantic_focus_match(service):
    # Offline integration: real cached query vector, reranker deliberately absent;
    # this tests focus expansion, not model quality or RRF+reranker acceptance.
    context=service.entry('cyber-504','art20.3')['context']
    out=service.rag(next(iter(service.query_cache)),context)
    selected=service.comparisons[('cybersecurity','art20.3')]['citations']
    assert {c['citation_id'] for c in selected}.issubset({c['citation_id'] for c in out['evidence']['citations']})
    assert out['trace']['selected_provision_expansion']['origin']=='SK03_AI_annotated_subset'
    for c in out['evidence']['citations']:
        assert service.originals[(c['document_id'],c['version_id'])][c['start']:c['end']]==c['text']

def test_authorized_views_filter_before_sources_and_chat(service):
    actor={'authenticated':True,'subject':'limited-user','role':'reader','families':['cybersecurity']}
    view=service.for_actor(actor)
    assert [p['id'] for p in view.catalog()['pairs']]==['cyber-504']
    market=service.entry('market-3274','art27')['before']['version_id']
    with pytest.raises(PermissionError):view.source(market)
    with pytest.raises(PermissionError):view.comparison('market-3274','art27')
    with pytest.raises(PermissionError):view.ask('sid','antes','cyber-504','art20.3',True)
    assert service.generator is None
    with pytest.raises(PermissionError):service.for_actor({**actor,'authenticated':False})
