import pytest
from sbs.retrieval.development import compile_inputs

class Cache:
 identity='model';prefix='prefix:';context_chars=0;limit=3;tokenizer='fixture';revision='a'*40
 def lookup(self,parts,identity):return {'vector':[1]} if identity=='model' and parts==('prefix:','abc') else None
class Counter:
 tokenizer='fixture';revision='a'*40;model_identity='model'
 def count(self,parts):return len(''.join(parts))

def test_exact_input_only_cache_and_no_truncation():
 passages=[dict(passage_id='id',document_id='d',version_id='v',start=0,end=3,quote='abc')]
 rows=compile_inputs(passages,{('d','v'):'abc'},Cache(),Counter())
 assert rows[0]['cache_status']=='exact_hit' and rows[0]['budget']['status']=='exceeded'
 assert rows[0]['input_parts']==['prefix:','abc'] and rows[0]['embedding_text']=='abc'
 passages[0]['quote']='abd'
 with pytest.raises(ValueError):compile_inputs(passages,{('d','v'):'abc'},Cache(),Counter())

def test_same_identifier_changed_text_misses_cache():
 p=dict(passage_id='id',document_id='d',version_id='v',start=0,end=3,quote='abd')
 row=compile_inputs([p],{('d','v'):'abd'},Cache(),Counter())[0]
 assert row['cache_status']=='miss' and row['budget']['status']=='exceeded'


def test_real_dataset_schema_sources_partial_judgments_and_exact_inputs():
    from pathlib import Path
    import json,hashlib
    from jsonschema import Draft202012Validator
    from sbs.retrieval.development import build_dataset
    from sbs.evaluation import retrieval_metrics
    root=Path(__file__).resolve().parents[2];d=build_dataset(root)
    schema=json.loads((root/'context/evaluation-018/records.schema.json').read_text())
    assert len(d['questions'])==3 and len(d['pairs'])==2 and d['manifest']['sources']==6
    for plural,kind in [('questions','question'),('passages','passage'),('judgments','judgment'),('pairs','pair')]:
        for row in d[plural]:Draft202012Validator(schema['$defs'][kind]).validate(row)
    pmap={p['passage_id']:p for p in d['passages']}
    for p in d['passages']:
        raw=(root/p['rawtext_path']).read_text();assert p['quote']==raw[p['start']:p['end']]
        assert hashlib.sha256(raw.encode()).hexdigest()==p['rawtext_sha256']
    from sbs.foundation.structure import structuralize
    expected={}
    for path in d['manifest']['source_files']:
        if path.endswith('/result.json') and path.startswith('data/foundation-repository/'):
            raw_bundle=json.loads((root/path).read_text())
            for unit in structuralize(raw_bundle)['provisions']:
                expected[unit['citation_id']]=(unit['document_id'],unit['version_id'],unit['start'],unit['end'],unit['text'])
    actual={pid:(p['document_id'],p['version_id'],p['start'],p['end'],p['quote']) for pid,p in pmap.items() if d['passage_metadata'][pid]['origin']=='automatic_structural'}
    assert actual==expected and len(actual)==225
    assert len(d['judgments'])==6 and all(j['grade']==1 and j['passage_id'] in pmap for j in d['judgments'])
    assert d['manifest']['holdout']==[] and d['manifest']['exhaustive'] is False
    assert all(d['passage_metadata'][j['passage_id']]['origin']=='reused_ai_annotated_subspan' for j in d['judgments'])
    for q,rels in d['qrels_partial']['qrels'].items():
        metrics=retrieval_metrics([],rels,5,d['qrels_partial']['counterparts'][q]);assert metrics['recall']['value']==0 and metrics['recall']['denominator']==2
    for row in d['embedding_inputs']:
        assert row['input_sha256']==hashlib.sha256(''.join(row['input_parts']).encode()).hexdigest()
        assert row['embedding_text']==pmap[row['passage_id']]['quote'] # context_chars0 observed, no truncation
    market=[g for g in d['automatic_gaps'] if g['query_id'].startswith('market')]
    assert len(market)==4 and all(g['status']=='automatic_article_covering_reference' for g in market)
    for gap in market:
        target=pmap[gap['fallback_passage_id']]
        assert len(gap['automatic_covering_units'])==1
        auto=pmap[gap['automatic_covering_units'][0]]
        assert d['passage_metadata'][auto['passage_id']]['origin']=='automatic_structural'
        assert (auto['document_id'],auto['version_id'])==(target['document_id'],target['version_id'])
        assert auto['start']<=target['start']<target['end']<=auto['end']
        assert auto['quote'][target['start']-auto['start']:target['end']-auto['start']]==target['quote']


def test_model_counter_mismatch_blocks_compilation():
    class Other(Counter):model_identity='different'
    p=dict(passage_id='id',document_id='d',version_id='v',start=0,end=3,quote='abc')
    with pytest.raises(ValueError,match='identity'):compile_inputs([p],{('d','v'):'abc'},Cache(),Other())


def test_dataset_write_once_and_no_vector_payload(tmp_path):
    from pathlib import Path
    import json,hashlib
    from sbs.retrieval.development import write_dataset
    root=Path(__file__).resolve().parents[2];dest=tmp_path/'dataset'
    summary,artifacts=write_dataset(root,dest)
    assert summary['cache_misses']==231 and summary['query_cache_hits']==3
    assert len(summary['corpus_views']['automatic_structural'])==225
    assert len(summary['corpus_views']['reused_ai_annotated_subspan'])==6
    assert summary['input_tokens']==106278 and summary['max_input_tokens']==2595
    assert summary['cache_hits']==0 and summary['over_limit']==[]
    assert summary['candidate_strategy']['indexed'] is False
    # v8 inventory is the exact union of six sealed structural outputs.
    assert summary['passages']==231 and summary['negative_judgments']==0
    assert all(hashlib.sha256((dest/p).read_bytes()).hexdigest()==a['sha256'] for p,a in artifacts.items())
    inputs=json.loads((dest/'embedding_inputs.json').read_text());assert all('vector' not in row and row['execution_status']=='not_executed' for row in inputs)
    with pytest.raises(ValueError,match='EXISTS'):write_dataset(root,dest)


def test_annotation_paths_in_new_dataset_are_project_relative():
    from pathlib import Path
    from sbs.retrieval.development import build_dataset
    d=build_dataset(Path(__file__).resolve().parents[2])
    for ref in d['reference_provenance'].values():
        for c in ref['annotation']['review_citations'].values():
            assert not Path(c['original_path']).is_absolute()
            assert not Path(c['rawtext_path']).is_absolute()
