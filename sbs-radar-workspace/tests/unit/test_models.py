"""SK05 component tests. Token counts are explicit fixtures, not real tokenizers."""
import importlib
import json
from dataclasses import FrozenInstanceError

import pytest


def api():
    module = importlib.import_module('sbs.models')
    assert hasattr(module, 'ModelManifest'), 'SK05 manifest not implemented'
    return module


def bundle():
    return dict(bundle_id='test', revision='1', embedding_model='test-embed',
                embedding_revision='v1', tokenizer='test-tokenizer', dimension=2,
                reranker_model='test-rank', reranker_revision='v1',
                generation_model='test-gen', generation_revision='v1',
                chunking_version='test-chunks-v1', parameters={
                    'corpus_hash': 'test-corpus', 'extractor_version': 'test-extractor',
                    'tokenizer_revision': 'v1', 'document_prefix': 'passage: ',
                    'query_prefix': 'query: ', 'normalization': 'none',
                    'strategy_id': 'span-limpio-contexto-v1', 'strategy_version': '1'})


def test_manifest_detaches_inputs_and_refuses_overwrite(tmp_path):
    m = api()
    source = bundle()
    manifest = m.ModelManifest.from_bundle(source)
    source['parameters']['query_prefix'] = 'changed'
    exported = manifest.bundle
    exported['parameters']['query_prefix'] = 'changed again'
    assert manifest.bundle['parameters']['query_prefix'] == 'query: '
    with pytest.raises(FrozenInstanceError):
        manifest.canonical_json = '{}'
    path = tmp_path / 'bundle.json'
    manifest.save(path)
    original = path.read_bytes()
    with pytest.raises(FileExistsError):
        manifest.save(path)
    assert path.read_bytes() == original
    assert json.loads(original)['bundle_hash'] == manifest.bundle_hash


def test_hash_is_order_independent_and_changes_for_model_or_prefix():
    m = api()
    base = bundle()
    one = m.ModelManifest.from_bundle(base)
    assert m.ModelManifest.from_bundle(dict(reversed(list(base.items())))).bundle_hash == one.bundle_hash
    for field, value in [('embedding_model', 'other'), ('embedding_revision', 'v2')]:
        other = bundle(); other[field] = value
        assert m.ModelManifest.from_bundle(other).bundle_hash != one.bundle_hash
    other = bundle(); other['parameters']['document_prefix'] = 'different'
    assert m.ModelManifest.from_bundle(other).bundle_hash != one.bundle_hash


def test_manifest_rejects_missing_identity_and_nonfinite_parameters():
    m = api()
    for field in ['corpus_hash', 'tokenizer_revision', 'normalization']:
        invalid = bundle(); del invalid['parameters'][field]
        with pytest.raises(ValueError):
            m.ModelManifest.from_bundle(invalid)
    invalid = bundle(); invalid['parameters']['price'] = float('nan')
    with pytest.raises(ValueError):
        m.ModelManifest.from_bundle(invalid)


def test_budget_rejects_overflow_and_reserves_generation_output():
    m = api()
    # Literal full-input fixture: article 900 + context/prefix/specials 20.
    counter = m.TokenCounter('fixture', 'v1', 'model-v1', lambda parts: 920)
    result = m.preflight_budget(('full article plus context and prefix',), 512,
                                counter=counter, model_identity='model-v1')
    assert result['status'] == 'exceeded'
    assert result['input_tokens'] == 920
    assert result['excess_tokens'] == 408
    counter = m.TokenCounter('fixture', 'v1', 'model-v1', lambda parts: 500)
    assert m.preflight_budget(('complete prompt',), 512, counter=counter,
        model_identity='model-v1', reserved_output=12)['status'] == 'ready'
    assert m.preflight_budget(('complete prompt',), 512, counter=counter,
        model_identity='model-v1', reserved_output=13)['status'] == 'exceeded'


def test_budget_counts_pair_and_blocks_missing_or_incompatible_tokenizer():
    m = api()
    def pair_count(parts):
        assert parts == ('full query', 'full passage')
        return 11  # Fixture includes pair separator and special tokens.
    counter = m.TokenCounter('fixture', 'v1', 'rank-v1', pair_count)
    assert m.preflight_budget(('full query', 'full passage'), 10, counter=counter,
        model_identity='rank-v1')['status'] == 'exceeded'
    assert m.preflight_budget(('prompt',), 10, model_identity='gen-v1')['status'] == 'pending_tokenizer'
    with pytest.raises(ValueError):
        m.preflight_budget(('prompt',), 10, counter=counter, model_identity='other')
    for bad in [-1, True, 1.5]:
        badcounter = m.TokenCounter('fixture', 'v1', 'rank-v1', lambda parts: bad)
        with pytest.raises(ValueError):
            m.preflight_budget(('prompt',), 10, counter=badcounter, model_identity='rank-v1')


@pytest.mark.parametrize('vectors', [[], [[1.0]], [[1.0, float('nan')]],
    [[1.0, float('inf')]], [[1.0, True]], [[1.0, '2']], None])
def test_rejects_invalid_embedding_results(vectors):
    m = api()
    with pytest.raises(ValueError):
        m.validate_embeddings(vectors, expected_count=1, dimension=2,
                              expected_identity='bundle-a', actual_identity='bundle-a')


def test_same_dimensions_do_not_override_identity():
    m = api()
    with pytest.raises(ValueError):
        m.validate_embeddings([[1.0, 2.0]], expected_count=1, dimension=2,
                              expected_identity='bundle-a', actual_identity='bundle-b')
    assert m.validate_embeddings([[1.0, 2.0]], expected_count=1, dimension=2,
        expected_identity='bundle-a', actual_identity='bundle-a') == ((1.0, 2.0),)

# Adapter boundary tests use explicit transport/token-count fixtures; smoke is separate.
def adapter_api():
    import importlib.util
    assert importlib.util.find_spec('sbs.models.databricks'), 'SK05 adapter not implemented'
    return importlib.import_module('sbs.models.databricks')


def adapter_bundle():
    data = bundle()
    data.update(embedding_model='databricks-qwen3-embedding-0-6b', dimension=32,
                tokenizer='Qwen/Qwen3-Embedding-0.6B')
    data['parameters'].update(tokenizer_revision='a'*40, tokenizer_sha256='b'*64,
                              document_prefix='', query_prefix='Instruct: ',
                              expected_response_model='databricks-qwen3-embedding-0-6b',
                              query_instruction='Retrieve SBS passages relevant to the query.')
    return api().ModelManifest.from_bundle(data)


class FixtureTokenizer:
    repo_id = 'Qwen/Qwen3-Embedding-0.6B'
    revision = 'a'*40
    sha256 = 'b'*64
    def count(self, text):
        return len(text.split()) + 2  # Explicit fixture, includes two specials.


def good_response():
    return {'model':'databricks-qwen3-embedding-0-6b', 'data':[
        {'index':1, 'embedding':[2.0]*32}, {'index':0, 'embedding':[1.0]*32}],
        'usage':{'prompt_tokens':8,'total_tokens':8,'secret':'must not propagate'}}


def test_adapter_reorders_and_reports_usage_without_arbitrary_metadata():
    m=adapter_api()
    adapter=m.DatabricksEmbeddingAdapter(adapter_bundle(), FixtureTokenizer(),
        transport=lambda body:good_response(), max_calls=1, max_tokens=256)
    result=adapter.embed(['texto uno','texto dos'])
    assert result['embeddings'][0] == (1.0,)*32
    assert result['usage'] == {'prompt_tokens':8,'total_tokens':8}
    assert result['cost'] is None
    with pytest.raises(ValueError,match='call_quota'):
        adapter.embed(['texto uno'])


def test_adapter_documents_omit_instruction_queries_count_it():
    m=adapter_api(); bodies=[]
    def transport(body):
        bodies.append(body)
        return {'model':'databricks-qwen3-embedding-0-6b',
                'data':[{'index':0,'embedding':[1.0]*32}]}
    adapter=m.DatabricksEmbeddingAdapter(adapter_bundle(), FixtureTokenizer(),
        transport=transport,max_calls=2,max_tokens=256)
    document=adapter.embed(['plain text'])
    query=adapter.embed(['plain text'],role='query')
    assert bodies[0] == {'input':['plain text'],'dimensions':32}
    assert bodies[1]['instruction'] == 'Retrieve SBS passages relevant to the query.'
    assert query['local_input_tokens'] > document['local_input_tokens']
    assert query['usage'] == {'prompt_tokens':None,'total_tokens':None}


def test_adapter_no_transport_for_token_overflow_or_invalid_dimension():
    m=adapter_api()
    def forbidden(body):
        pytest.fail('transport called despite preflight failure')
    adapter=m.DatabricksEmbeddingAdapter(adapter_bundle(),FixtureTokenizer(),
        transport=forbidden,max_calls=1,max_tokens=3)
    with pytest.raises(ValueError,match='token_quota'):
        adapter.embed(['four complete input words'])
    data=adapter_bundle().bundle;data['dimension']=33
    with pytest.raises(ValueError,match='dimension'):
        m.DatabricksEmbeddingAdapter(api().ModelManifest.from_bundle(data),FixtureTokenizer(),
            transport=forbidden,max_calls=1,max_tokens=256)


def test_adapter_failed_request_consumes_quota_and_sanitizes_error():
    m=adapter_api()
    class SecretError(Exception):
        error_code='PERMISSION_DENIED'
    def denied(body):raise SecretError('SECRET-do-not-print')
    adapter=m.DatabricksEmbeddingAdapter(adapter_bundle(),FixtureTokenizer(),
        transport=denied,max_calls=1,max_tokens=256)
    with pytest.raises(m.EmbeddingServiceError) as caught:
        adapter.embed(['public text'])
    assert str(caught.value) == 'PERMISSION_DENIED'
    assert caught.value.__cause__ is None
    with pytest.raises(ValueError,match='call_quota'):
        adapter.embed(['public text'])


@pytest.mark.parametrize('change',[ 'wrong_model','duplicate_index','nan','wrong_count'])
def test_adapter_rejects_malformed_service_responses(change):
    m=adapter_api();response=good_response()
    if change=='wrong_model':response['model']='another-model'
    if change=='duplicate_index':response['data'][1]['index']=1
    if change=='nan':response['data'][0]['embedding'][0]=float('nan')
    if change=='wrong_count':response['data'].pop()
    adapter=m.DatabricksEmbeddingAdapter(adapter_bundle(),FixtureTokenizer(),
        transport=lambda body:response,max_calls=1,max_tokens=256)
    with pytest.raises(ValueError):adapter.embed(['one','two'])


def test_pinned_tokenizer_verifies_hash_disables_truncation(tmp_path):
    m=adapter_api()
    from tokenizers import Tokenizer,models,pre_tokenizers
    import hashlib
    tokenizer=Tokenizer(models.WordLevel({'[UNK]':0,'one':1},unk_token='[UNK]'))
    tokenizer.pre_tokenizer=pre_tokenizers.Whitespace()
    tokenizer.enable_truncation(1)
    path=tmp_path/'tokenizer.json';tokenizer.save(str(path))
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    pinned=m.PinnedQwenTokenizer(path,revision='a'*40,sha256=digest)
    assert pinned.count('one one one') == 3
    with pytest.raises(ValueError,match='tokenizer_hash'):
        m.PinnedQwenTokenizer(path,revision='a'*40,sha256='0'*64)
    with pytest.raises(ValueError,match='revision'):
        m.PinnedQwenTokenizer(path,revision='main',sha256=digest)


def test_adapter_rejects_tokenizer_identity_mismatch():
    m=adapter_api();counter=FixtureTokenizer();counter.revision='c'*40
    with pytest.raises(ValueError,match='tokenizer_identity'):
        m.DatabricksEmbeddingAdapter(adapter_bundle(),counter,transport=lambda body:{},
                                    max_calls=1,max_tokens=256)


def test_single_shot_transport_uses_sdk_auth_and_never_follows_redirects(monkeypatch):
    m=adapter_api()
    from types import SimpleNamespace
    sent=[]
    class Session:
        def post(self,url,**kwargs):
            sent.append((url,kwargs))
            return SimpleNamespace(status_code=302)
        def close(self):pass
    monkeypatch.setattr('requests.Session',Session)
    client=SimpleNamespace(config=SimpleNamespace(host='https://workspace.example',
        authenticate=lambda:{'Authorization':'test-secret'}))
    transport=m.SingleShotTransport(client)
    with pytest.raises(m.EmbeddingServiceError) as caught:
        transport({'input':['public'],'dimensions':32})
    assert len(sent)==1
    assert sent[0][0]=='https://workspace.example/serving-endpoints/databricks-qwen3-embedding-0-6b/invocations'
    assert sent[0][1]['allow_redirects'] is False
    assert sent[0][1]['headers']['Authorization']=='test-secret'
    assert str(caught.value)=='HTTP_302'


def test_adapter_sk04_wrappers_preserve_complete_input_and_stable_identity():
    m=adapter_api();bodies=[]
    def transport(body):
        bodies.append(body)
        return {'model':'databricks-qwen3-embedding-0-6b',
                'data':[{'index':i,'embedding':[float(i+1)]*32} for i in range(len(body['input']))]}
    manifest=adapter_bundle()
    adapter=m.DatabricksEmbeddingAdapter(manifest,FixtureTokenizer(),transport=transport,
        max_calls=2,max_tokens=256)
    assert getattr(adapter,'identity',None)==manifest.bundle_hash
    assert adapter.dimension==32
    vectors=adapter.embed_documents([('prefijo: ','contexto con artículo íntegro'),('', 'segundo texto')])
    assert bodies[0]['input']==['prefijo: contexto con artículo íntegro','segundo texto']
    assert vectors==[[1.0]*32,[2.0]*32]
    query=adapter.embed_query('¿Qué dispone?')
    assert query==[1.0]*32
    assert bodies[1]['input']==['¿Qué dispone?']
    assert bodies[1]['instruction']=='Retrieve SBS passages relevant to the query.'
    assert adapter.identity==manifest.bundle_hash
    assert adapter.token_counter.count(('prefijo: ','contexto con artículo íntegro'))==7
    assert adapter.query_token_counter.count(('¿Qué dispone?',))>adapter.token_counter.count(('¿Qué dispone?',))


def test_adapter_sk04_wrapper_rejects_non_tuple_parts_before_inference():
    m=adapter_api()
    def forbidden(body):pytest.fail('must not invoke malformed document input')
    adapter=m.DatabricksEmbeddingAdapter(adapter_bundle(),FixtureTokenizer(),transport=forbidden,
        max_calls=1,max_tokens=256)
    with pytest.raises(ValueError,match='document_parts'):
        adapter.embed_documents(['silently iterating characters is forbidden'])


@pytest.mark.parametrize('change,stage',[('model','response_model'),('index','response_indices'),('dimension','response_vectors')])
def test_adapter_keeps_allowlisted_diagnostics_for_failed_response(change,stage):
    m=adapter_api();response=good_response()
    response['arbitrary_secret']='must never appear in diagnostics'
    if change=='model':response['model']='unexpected-model'
    if change=='index':response['data'][1]['index']=1
    if change=='dimension':response['data'][1]['embedding'].pop()
    adapter=m.DatabricksEmbeddingAdapter(adapter_bundle(),FixtureTokenizer(),
        transport=lambda body:response,max_calls=1,max_tokens=256)
    with pytest.raises(ValueError):adapter.embed(['one','two'])
    diagnostic=getattr(adapter,'last_attempt',{})
    assert diagnostic.get('stage')==stage
    assert diagnostic['response_count']==2
    assert diagnostic['usage']=={'prompt_tokens':8,'total_tokens':8}
    assert 'must never appear' not in json.dumps(diagnostic)
    assert 'embedding' not in diagnostic
    assert diagnostic['latency_seconds']>=0


def test_response_model_identity_is_pinned_separately_from_endpoint():
    m=adapter_api()
    data=adapter_bundle().bundle
    data['parameters']['expected_response_model']='qwen3-embedding-0-6b-112025'
    manifest=api().ModelManifest.from_bundle(data)
    response=good_response();response['model']='qwen3-embedding-0-6b-112025'
    adapter=m.DatabricksEmbeddingAdapter(manifest,FixtureTokenizer(),
        transport=lambda body:response,max_calls=1,max_tokens=256)
    result=adapter.embed(['one','two'])
    assert result['model']=='qwen3-embedding-0-6b-112025'
    assert result['endpoint']=='databricks-qwen3-embedding-0-6b'
    assert result['expected_response_model']=='qwen3-embedding-0-6b-112025'
    assert result['embeddings']==((1.0,)*32,(2.0,)*32)
    assert adapter.identity!=adapter_bundle().bundle_hash


@pytest.mark.parametrize('reported',['qwen3-embedding-0-6b-112025-extra',
    'qwen3-embedding-0-6b-122025','databricks-qwen3-embedding-0-6b',
    'system.ai.qwen3-embedding-0-6b'])
def test_response_model_pin_never_accepts_prefixes_or_endpoint_alias(reported):
    m=adapter_api();data=adapter_bundle().bundle
    data['parameters']['expected_response_model']='qwen3-embedding-0-6b-112025'
    response=good_response();response['model']=reported
    adapter=m.DatabricksEmbeddingAdapter(api().ModelManifest.from_bundle(data),FixtureTokenizer(),
        transport=lambda body:response,max_calls=1,max_tokens=256)
    with pytest.raises(ValueError,match='embedding_model_mismatch'):
        adapter.embed(['one','two'])
    assert adapter.last_attempt['stage']=='response_model'
    assert adapter.last_attempt['expected_response_model']=='qwen3-embedding-0-6b-112025'


def test_missing_response_model_pin_blocks_before_network():
    m=adapter_api();data=adapter_bundle().bundle
    data['parameters'].pop('expected_response_model',None)
    with pytest.raises(ValueError,match='missing_expected_response_model'):
        m.DatabricksEmbeddingAdapter(api().ModelManifest.from_bundle(data),FixtureTokenizer(),
            transport=lambda body:pytest.fail('no unpinned inference'),max_calls=1,max_tokens=256)
