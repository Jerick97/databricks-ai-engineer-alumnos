"""Real prepared corpus: presentation must not alter retrieval identities or labels."""
import re
from test_runtime_release import prepared
from sbs.runtime import LocalService


def test_prepared_labels_are_readable_without_changing_retrieval_prefix(prepared):
    service=LocalService.from_release(prepared.root,pointer=prepared.current())
    pairs=service.catalog()['pairs']
    assert {p['title'] for p in pairs}=={'Resolución SBS 504-2021','Resolución SBS 3274-2017'}
    structural=0
    for pair in pairs:
        assert pair['before_label'].startswith('Copia A · ')
        assert pair['after_label'].startswith('Copia B · ')
        for provision in pair['provisions']:
            entry=service.entry(pair['id'],provision['id'])
            # Existing labels feed the uncached query prefix and remain unchanged.
            origin=service._comparison_item(entry['context']).get('focus_origin')
            suffix={'SK03_structural_heuristic':' · correspondencia estructural heurística, cobertura parcial','SK03_AI_annotated_subset':' · anotación IA validada','SK03_raw_page_focus':' · página física, correspondencia semántica pendiente'}[origin]
            assert entry['label']==provision['id']+suffix
            if provision.get('evidence_origin')=='SK03_structural_heuristic':
                structural+=1
                assert provision['label']!=entry['label']
                assert not re.search(r'[0-9a-f]{16}',provision['label'])
                assert 'cobertura parcial' in provision['label']
            comparison=service.comparison(pair['id'],provision['id'])
            assert comparison['title']==provision['label']
            assert comparison['before']['source_id']==entry['context']['pair']['before']['version_id']
            assert comparison['after']['source_id']==entry['context']['pair']['after']['version_id']
            assert comparison['status']=='unreviewed'
        assert pair['identity_details']['before_version_id']==entry['context']['pair']['before']['version_id']
        assert pair['identity_details']['after_version_id']==entry['context']['pair']['after']['version_id']
    assert structural>0


def test_display_fallbacks_do_not_invent_article_kind_or_dates():
    from sbs.operations.runtime_release import document_display_name,structural_display_name
    assert structural_display_name({'unit_kind':'final_provision','number':'PRIMERA'})=='Disposición final PRIMERA'
    assert structural_display_name({'unit_kind':'resolution_article','number':'SEGUNDO'})=='Artículo resolutivo SEGUNDO'
    assert structural_display_name({})=='Disposición seleccionada'
    assert document_display_name('unknown-document')=='Documento normativo'
