import importlib
from pathlib import Path
import copy
import pytest
ROOT=Path(__file__).resolve().parents[2]


def pilot():return importlib.import_module('sbs.comparison.pilot')


def test_verified_pilot_subsets_partial_deterministic():
    m=pilot();a=m.build_pilot(ROOT);b=m.build_pilot(ROOT)
    assert a==b
    assert {x['provision_id'] for x in a['items']}=={'art20.3','art27','art29.1.4'}
    for item in a['items']:
        assert item['change_set']['evidence']['coverage']=='partial'
        assert item['change_set']['review_status']=='unreviewed'
        assert item['changes'][0]['kind']=='literal_modification'
        assert item['alignments']==[{'before':[item['provision_id']],'after':[item['provision_id']],'method':'explicit'}]
        assert not item['no_changes'] and item['annotation']['human_gold'] is False
        for side in ['before','after']:
            b=item['bundles'][side];c=item[side]
            assert b['rawtext'][c['start']:c['end']]==c['text']
            assert b['layer']=='structural_provisions'
    art=next(x for x in a['items'] if x['provision_id']=='art29.1.4')
    assert art['before']['text'].startswith('4. ') and art['after']['text'].startswith('4. ')
    assert art['annotation']['citation_derivation']=='exact_subspan_of_reviewed_29.1_context'


@pytest.mark.parametrize('field,value',[('quote_raw','inventado'),('page',999),('version_id','wrong')])
def test_reject_bad_annotation_against_sealed_bundle(field,value):
    m=pilot();item=m.build_pilot(ROOT)['items'][0]
    citation=copy.deepcopy(item['annotation']['review_citations']['before']);citation[field]=value
    with pytest.raises(ValueError):m.structural_bundle(item['bundles']['before'],citation,item['provision_id'])

def test_structural_span_ids_never_alias_raw_page_citations():
    import json
    raw={r['citation']['citation_id'] for r in json.loads((ROOT/'data/retrieval/sk04-real-001/records.json').read_text())}
    items=pilot().build_pilot(ROOT)['items']
    selected=[x[side] for x in items for side in ('before','after')]
    assert len({x['citation_id'] for x in selected})==6
    assert not raw.intersection(x['citation_id'] for x in selected)
    for item in items:
        for side in ('before','after'):
            assert item['bundles'][side]['annotation_provenance']['parent_citation_id']==item['annotation']['review_citations'][side]['citation_id']
