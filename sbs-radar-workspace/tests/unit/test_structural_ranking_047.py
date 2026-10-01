"""047 projection/scoping mechanics only, synthetic vectors, no semantic claims."""
import copy
import hashlib
import pytest
from sbs.retrieval.structural_ranking import project_records, scoped_variants, POLICY
from sbs.retrieval import LocalIndex, rrf
from test_retrieval import artifact,chunks,PAIR

def fixture():
    a=artifact(texts=('ciber seguridad','ciber mensual'));c=chunks(a)
    passages=[dict(passage_id=r['citation']['citation_id'],document_id='doc',version_id='v2',start=r['citation']['start'],end=r['citation']['end'],page=r['citation']['page'],quote=r['citation']['text'],rawtext_sha256=a['rawtext_sha256']) for r in c]
    metadata={r['citation']['citation_id']:dict(family='cybersecurity',provision_id=r['citation']['provision_id'],pages=r['pages'],origin='fixture') for r in c}
    inputs=[dict(passage_id=r['citation']['citation_id'],input_parts=list(r['input_parts']),embedding_start=r['embedding_start'],embedding_text=r['embedding_text'],budget=r['budget']) for r in c]
    return a,passages,metadata,inputs

def test_projection_retains_literal_ids_parts_offsets_and_pages():
    a,p,m,i=fixture();rows=project_records(p,m,i,{('doc','v2'):a},synthetic=True)
    assert [r['citation']['citation_id'] for r in rows]==[x['passage_id'] for x in p]
    for row,passage,inp in zip(rows,p,i):
        assert row['citation']['text']==passage['quote']==a['rawtext'][passage['start']:passage['end']]
        assert row['input_parts']==inp['input_parts']
        assert row['citation']['start']==passage['start'] and row['pages']==m[passage['passage_id']]['pages']
    LocalIndex(rows,[[1.,0.],[0.,1.]],dimension=2,model_identity='fixture-model',actual_identity='fixture-model')

@pytest.mark.parametrize('field',['quote','page','rawtext_sha256'])
def test_projection_rejects_mutated_literal(field):
    a,p,m,i=fixture();p[0][field]='invalid'
    with pytest.raises(ValueError):project_records(p,m,i,{('doc','v2'):a},synthetic=True)

def test_scopes_before_all_stages_and_no_expansion():
    a,p,m,i=fixture();rows=project_records(p,m,i,{('doc','v2'):a},synthetic=True)
    outside=copy.deepcopy(rows[0]);outside['family']='market_conduct';outside['citation']['citation_id']='outsider';outside['citation']['version_id']='v3'
    idx=LocalIndex(rows+[outside],[[1.,0.],[0.,1.],[1.,0.]],dimension=2,model_identity='fixture-model',actual_identity='fixture-model')
    result=scoped_variants(idx,'ciber',PAIR,[1.,0.])
    assert set(result['eligible_ids'])=={r['citation']['citation_id'] for r in rows}
    for ranking in result['rankings'].values():assert 'outsider' not in [x[0] for x in ranking]
    assert result['rankings']['rrf']==rrf(result['rankings']['lexical'],result['rankings']['vector'],k=60)[:20]
    assert result['trace']['counterparts']==result['trace']['neighbors']==[]
    assert POLICY['target_expansion'] is False

def test_lexical_baseline_float_order_bound_preserves_exact_ids():
    import math
    from sbs.retrieval.structural_ranking import lexical_matches
    old=[{'passage_id':'a','score':12.0},{'passage_id':'b','score':10.0}]
    assert lexical_matches('uno dos tres',[('a',math.nextafter(12.,13.)),('b',10.)],old)
    assert not lexical_matches('uno dos tres',[('a',12.01),('b',10.)],old)
    assert not lexical_matches('uno dos tres',[('b',12.),('a',10.)],old)

def test_anchored_read_rejects_resealed_dataset_and_changed_result(tmp_path):
    import json
    from sbs.retrieval.structural_ranking import anchored_read
    original={'config_hash':'original','rawtext_sha256':'unchanged'}
    p=tmp_path/'result.json';p.write_text(json.dumps(original));pin=hashlib.sha256(p.read_bytes()).hexdigest()
    assert anchored_read(tmp_path,'result.json',pin)==original
    p.write_text(json.dumps({**original,'config_hash':'0'*64}))
    with pytest.raises(ValueError,match='ANCHORED_INPUT_HASH'):anchored_read(tmp_path,'result.json',pin)
    p.write_text(json.dumps({'files':{'malicious':'resealed'}}))
    with pytest.raises(ValueError,match='ANCHORED_INPUT_HASH'):anchored_read(tmp_path,'result.json',pin)
