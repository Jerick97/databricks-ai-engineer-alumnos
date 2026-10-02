import hashlib,json
from copy import deepcopy
import pytest
from sbs.foundation.structure import structuralize, structural_alignments
from sbs.comparison import compare

def bundle(pages):
 raw='\n'.join(pages);out=[];offset=0;h=hashlib.sha256(raw.encode()).hexdigest()
 for i,text in enumerate(pages,1):
  out.append(dict(page=i,start=offset,end=offset+len(text),error=None));offset+=len(text)+1
 return dict(sha256=h,rawtext=raw,rawtext_sha256=h,extractor='fixture-raw-v1',config_hash='a'*64,layer='raw_pages',pages=out,quality={'status':'partial','limitations':['layout_table_review_pending']},provisions=[dict(citation_id=hashlib.sha256((h+str(p['page'])).encode()).hexdigest(),provision_id=f"raw-page-{p['page']}",document_id='fixture',version_id=h,page=p['page'],start=p['start'],end=p['end'],text=raw[p['start']:p['end']],source_kind='normative',synthetic=True) for p in out])

def test_cross_page_exact_and_new_identity():
 b=bundle(['CAPÍTULO I\nArtículo 1. Alcance\nContenido sigue','continuación literal.\nArtículo 2. Deberes\nTexto final.'])
 old=deepcopy(b);r=structuralize(b)
 assert b==old and r['layer']=='structural_provisions'
 assert len(r['provisions'])==2
 q=r['provisions'][0];assert q['text']==b['rawtext'][q['start']:q['end']]
 assert 'continuación literal.' in q['text']
 assert r['structure']['spans'][q['provision_id']]['pages']==[1,2]
 assert set(p['citation_id'] for p in r['provisions']).isdisjoint(p['citation_id'] for p in b['provisions'])
 assert r==structuralize(b) and r['quality']['status']=='partial'

@pytest.mark.parametrize('line',['Artículo 1. Alcance ........ 3','1 Artículo 1. Alcance','“Artículo 1. Alcance','| Artículo 1. Alcance |','según Artículo 1. Alcance','Artículo 1.','artículo 1. citado anteriormente'])
def test_non_heading_never_becomes_provision(line):
 r=structuralize(bundle([line+'\ncontenido']))
 assert r['provisions']==[]

def test_duplicate_index_quoted_annex_headers_are_not_adopted():
 raw='ÍNDICE\nArtículo 1. Alcance .... 2\nRESUELVE:\nCAPÍTULO I\nArtículo 1. Alcance\nA.\nArtículo 1. Alcance\nB.\nANEXO A\nArtículo 2. Tabla\ncelda'
 r=structuralize(bundle([raw]));assert r['provisions']==[]
 assert 'ambiguous_duplicate_headers' in r['quality']['limitations']


def test_page_boundary_not_a_provision_boundary_and_context_separates_duplicates():
 r=structuralize(bundle(['CAPÍTULO I\nArtículo 1. Alcance\nA','B\nCAPÍTULO II\nArtículo 1. Alcance\nC']))
 assert len(r['provisions'])==2
 assert 'CAPÍTULO II' not in r['provisions'][0]['text']
 assert structural_alignments(r,r)==[] # same version cannot be compared


def test_match_headers_not_page_or_numbers_alone():
 a=structuralize(bundle(['CAPÍTULO I\nArtículo 1. Alcance\nAntes.\nArtículo 2. Deber\nX.']))
 b=structuralize(bundle(['CAPÍTULO I\nArtículo 1. Alcance\nDespués.\nArtículo 2. Otro título\nY.']))
 matches=structural_alignments(a,b);assert len(matches)==1
 pair=dict(pair_id='fixture-pair',family='market_conduct',before={'document_id':'fixture','version_id':a['sha256']},after={'document_id':'fixture','version_id':b['sha256']})
 r=compare(pair,a,b,matches)
 assert len(r['changes'])==1 and r['changes'][0]['kind']=='literal_modification'
 assert r['change_set']['evidence']['coverage']=='partial'


def test_corrupt_offset_hash_and_empty_pages_rejected():
 b=bundle(['Artículo 1. Alcance\ntexto']);b['rawtext']+='bad'
 with pytest.raises(ValueError):structuralize(b)
 b=bundle(['Artículo 1. Alcance\ntexto']);b['pages'][0]['start']=True
 with pytest.raises(ValueError):structuralize(b)


def test_multi_line_quoted_article_and_footnote_are_not_headings():
 b=bundle(['Artículo 1. Alcance\nLa norma cita: “\nArtículo 8. Regla ajena\ntexto”.\n1 Artículo modificado por resolución.\nArtículo 2. Deber\nTexto.'])
 r=structuralize(b);assert len(r['provisions'])==2
 assert 'ancillary_text_retained' in r['quality']['limitations']


def test_renumbering_is_pending_not_automatic_by_title_or_page():
 a=structuralize(bundle(['Artículo 1. Alcance\nMismo texto.']))
 b=structuralize(bundle(['Artículo 2. Alcance\nMismo texto.']))
 assert structural_alignments(a,b)==[]


def test_line_references_and_index_page_numbers_no_fake_articles():
 b=bundle(['ÍNDICE\nArtículo 1. Alcance 4\nArtículo 2. Plazo 5\nRESUELVE:\nCAPÍTULO I\nArtículo 1. Alcance\nsegún el artículo 2.\n2 Párrafo modificado por norma.\nArtículo 2. Plazo\nTexto.'])
 r=structuralize(b)
 assert len(r['provisions'])==2
 assert len(r['structure']['rejected_candidates'])==2
 assert all(p['synthetic'] for p in r['provisions'])


def test_missing_article_prefix_with_matching_subnumber_is_boundary_not_fake_article():
 b=bundle(['Artículo 16. Reportes\n16.1 Texto.\n17. Absolución de consultas\n17.1 Contenido diferente.\nCAPÍTULO VII\nArtículo 18. Trato\nTexto.'])
 r=structuralize(b);assert len(r['provisions'])==2
 assert '17. Absolución' not in r['provisions'][0]['text']
 assert any(x['reason']=='numbered_heading_without_article_prefix' for x in r['structure']['rejected_candidates'])


def test_index_chapter_with_page_numbers_on_next_line_stays_excluded():
 r=structuralize(bundle(['ÍNDICE\nCAPÍTULO I\nArtículo 1. Alcance\n3\nCAPÍTULO II\nArtículo 2. Deberes\n5']))
 assert r['provisions']==[]

@pytest.mark.parametrize('mutate',['missing','duplicate','collision'])
def test_parent_closure_must_be_complete_unique(mutate):
 b=bundle(['Artículo 1. Alcance\nTexto.','Artículo 2. Deberes\nTexto.'])
 if mutate=='missing':b['provisions'].pop()
 elif mutate=='duplicate':b['provisions'].append(deepcopy(b['provisions'][0]))
 else:b['provisions'][1]['citation_id']=b['provisions'][0]['citation_id']
 with pytest.raises(ValueError):structuralize(b)


def test_distinct_document_helper_rejects_implicit_correspondence():
 a=bundle(['Artículo 1. Objeto\nA']);b=bundle(['Artículo 1. Objeto\nB']);b['provisions'][0]['document_id']='other-instrument'
 with pytest.raises(ValueError,match='IDENTITY'):structural_alignments(structuralize(a),structuralize(b))


def test_lowercase_continuation_is_not_dispositions_heading():
 r=structuralize(bundle(['Artículo 3. Procedimiento\nSe aplican las\ndisposiciones del proceso y sus requisitos.\nÚltima frase.\nDISPOSICIONES COMPLEMENTARIAS FINALES\nPrimera.- Otro texto.']))
 assert 'Última frase.' in r['provisions'][0]['text']
 assert 'DISPOSICIONES COMPLEMENTARIAS FINALES' not in r['provisions'][0]['text']


def test_real_article19_reaches_full_structural_heading():
 from pathlib import Path
 pins=json.loads(Path('runs/sk03-market-018-inputs.json').read_text())
 for p in pins['hashes']:
  if p.endswith('result.json'):
   b=json.loads(Path(p).read_text());s=structuralize(b)
   q=next(q for q in s['provisions'] if s['structure']['spans'][q['provision_id']]['number']=='19')
   assert q['end']==b['rawtext'].index('DISPOSICIONES COMPLEMENTARIAS FINALES')


def test_final_provisions_keep_two_paragraphs_and_section_scope():
 r=structuralize(bundle(['Artículo Primero.- Aprobar.\nDISPOSICIONES COMPLEMENTARIAS FINALES\nPrimera.- Regla.\nSegunda.- Párrafo uno.\n\nPárrafo dos añadido.\nDISPOSICIONES COMPLEMENTARIAS TRANSITORIAS\nSegunda.- Distinta.\nArtículo Segundo.- Resolver.']))
 spans=r['structure']['spans'];final=[q for q in r['provisions'] if spans[q['provision_id']].get('unit_kind')=='final_provision']
 assert len(final)==2
 assert any('Párrafo dos añadido.' in q['text'] for q in final)
 assert len(r['provisions'])==5 # two final + one transitional + two resolution articles
 assert len({q['provision_id'] for q in r['provisions']})==5
 assert len({spans[q['provision_id']]['key'] for q in r['provisions']})==5


def test_ordinal_resolution_and_embedded_numeric_have_distinct_scopes():
 r=structuralize(bundle(['RESUELVE:\nArtículo Primero.- Aprobar norma.\nCAPÍTULO I\nArtículo 1. Alcance\nTexto.\nArtículo Segundo.– Publicar.']))
 assert len(r['provisions'])==3
 assert {d['unit_kind'] for d in r['structure']['spans'].values()}=={'resolution_article','numbered_article'}


def test_final_labels_outside_explicit_section_not_promoted():
 r=structuralize(bundle(['Segunda.- Lista ajena.\nArtículo 1. Objeto\nSegunda.- Ejemplo dentro del artículo.']))
 assert len(r['provisions'])==1


def test_excluded_ranges_are_recoverable_disjoint_and_complete_complement():
 b=bundle(['Preámbulo.\nArtículo 1. Alcance\nTexto.\nANEXO A\nTabla no segmentada.'])
 r=structuralize(b);ranges=r['structure']['excluded_ranges']
 allspans=sorted([(q['start'],q['end']) for q in r['provisions']]+[(q['start'],q['end']) for q in ranges])
 assert allspans[0][0]==0 and allspans[-1][1]==len(b['rawtext'])
 assert all(a[1]==z[0] for a,z in zip(allspans,allspans[1:]))
 for q in ranges:
  assert q['text']==b['rawtext'][q['start']:q['end']] and q['pages'] and q['reason']
 assert 'Tabla no segmentada.' in ''.join(q['text'] for q in ranges)


def test_quoted_ordinal_and_index_final_sections_not_promoted():
 r=structuralize(bundle(['ÍNDICE\nDISPOSICIONES COMPLEMENTARIAS FINALES\nPrimera.- 7\nRESUELVE:\nArtículo Primero.- Se cita “\nArtículo Segundo.- Ajeno.\n”\nArtículo Tercero.- Publicar.']))
 assert len(r['provisions'])==2
 assert all(d['unit_kind']=='resolution_article' for d in r['structure']['spans'].values())


def test_numeric_header_inside_resolution_article_is_excluded_not_owned_instrument():
 r=structuralize(bundle(['Artículo Cuarto.- Sustituir texto:\nArtículo 23. Norma citada\ncontenido.\nArtículo Sétimo.- Plazo.']))
 assert len(r['provisions'])==2
 assert all(x['unit_kind']=='resolution_article' for x in r['structure']['spans'].values())
 assert any(x['reason']=='embedded_numeric_without_explicit_section' for x in r['structure']['rejected_candidates'])


def test_unclosed_quote_ordinal_boundary_is_recoverable_not_absorbed():
 r=structuralize(bundle(['Artículo Tercero.- Se cita “\ncontenido sin cierre extraído.\nArtículo Cuarto.- Publicación.']))
 assert 'Artículo Cuarto' not in r['provisions'][0]['text']
 assert any('Artículo Cuarto' in x['text'] for x in r['structure']['excluded_ranges'])


@pytest.mark.parametrize('delimiter',['-','–','—'])
def test_ordinal_dash_without_dot_only_in_explicit_section(delimiter):
 r=structuralize(bundle([f'Tercera{delimiter} Lista fuera.\nDISPOSICIONES COMPLEMENTARIAS FINALES\nSegunda.- Texto.\nTercera{delimiter} Texto distinto.\nCuarta.- Final.']))
 finals=[q for q in r['provisions'] if r['structure']['spans'][q['provision_id']]['unit_kind']=='final_provision']
 assert len(finals)==3
 third=next(q for q in finals if r['structure']['spans'][q['provision_id']]['number']=='Tercera')
 assert third['text'].startswith('Tercera'+delimiter) and 'Lista fuera' not in third['text']
 assert 'Lista fuera' in ''.join(q['text'] for q in r['structure']['excluded_ranges'])


def test_real504_third_final_is_separate_without_raw_repunctuation():
 from pathlib import Path
 inv=json.loads(Path('runs/sk02-cyber-boundary-020-invocation.json').read_text())
 for p in inv['source_parents']:
  if p.endswith('result.json'):
   raw=json.loads(Path(p).read_text());out=structuralize(raw)
   finals={out['structure']['spans'][q['provision_id']]['number']:q for q in out['provisions'] if out['structure']['spans'][q['provision_id']]['unit_kind']=='final_provision'}
   third=finals['Tercera'];assert third['text'].startswith('Tercera- En caso')
   assert finals['Segunda']['end']==third['start'] and third['end']==finals['Cuarta']['start']
   assert third['text']==raw['rawtext'][third['start']:third['end']]
