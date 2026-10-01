import json
from pathlib import Path
from copy import deepcopy
from test_foundation_structure import bundle
from sbs.comparison.structural import compare_structural

def run(a,b):
 left,right=bundle([a]),bundle([b])
 pair=dict(pair_id='fixture-pair',family='market_conduct',before=dict(document_id='fixture',version_id=left['sha256']),after=dict(document_id='fixture',version_id=right['sha256']))
 return compare_structural(pair,left,right),left,right

def test_whitespace_view_reversible_not_quote():
 r,a,b=run('Artículo 1. Alcance\n1.1 No pagará 1000.','Artículo 1. Alcance\n1.1 No  pagará\n1000.')
 assert r['original_comparison']['changes']
 q=r['derived_comparison'][0];assert q['category']=='editorial_only_candidate'
 for side,raw in [('before',a),('after',b)]:
  view=q[side];assert view['citable'] is False
  p=r['evidence_context'][side]['provisions'][0]
  assert ''.join(raw['rawtext'][m['raw_start']:m['raw_end']] for m in view['mapping'])==p['text']
  assert ''.join(m['derived_text'] for m in view['mapping'])==view['text']

def test_meaningful_tokens_never_normalized_away():
 r,_,_=run('Artículo 1. Alcance\n1.1 No pagará 1 000.','Artículo 1. Alcance\n1.1 Pagará 1000.')
 assert r['derived_comparison'][0]['category']=='body_text_candidate'

def test_note_only_delta_separate_and_marker_not_body_change():
 r,_,_=run('Artículo 1. Alcance\n1.1 Texto.','Artículo 1. Alcance\n1.1 Texto.8\n8 Párrafo modificado por X.\n\n')
 q=r['derived_comparison'][0];assert q['category']=='editorial_only_candidate'
 assert {x['reason'] for x in q['after']['omitted_ranges']}=={'linked_editorial_note','linked_note_marker'}
 assert r['evidence_context']['after']['notes']['notes']

def test_ambiguous_note_retained_and_equality_inconclusive():
 text='Artículo 1. Alcance\n1.1 Texto.8\n1.2 Otro.8\n8 Párrafo modificado por X.\n\n'
 r,_,_=run(text,text+' ')
 q=r['derived_comparison'][0]
 assert 'Párrafo modificado' in q['after']['text'] and not q['after']['omitted_ranges']
 assert q['category']=='unresolved' and q['comparison_status']=='inconclusive'

def test_ordinal_exclusion_context_is_not_complete_unit():
 r,_,_=run('Artículo Primero.- Modificar lo siguiente:\n“\nArtículo 27. Ajeno\nTexto.\n”\nArtículo Segundo.- Otro.','Artículo Primero.- Modificar lo siguiente:\n“\nArtículo 27. Ajeno\nTexto nuevo.\n”\nArtículo Segundo.- Otro.')
 assert r['evidence_context']['after']['excluded_ranges']
 units=r['evidence_context']['after']['unit_context']
 assert any(u['related_exclusions'] and u['unit_completeness']=='partial' for u in units)
 assert all(u['exclusion_relationship']=='contextual_not_legal_ownership' for u in units)

def test_real4036_local_chain_exact_sources_and_pages():
 pins=json.loads(Path('runs/sk03-market-018-inputs.json').read_text());raw=[json.loads(Path(p).read_text()) for p in pins['hashes'] if p.endswith('result.json')]
 old=deepcopy(raw);r=compare_structural(pins['pair'],*raw);assert raw==old
 assert r['original_comparison']['no_changes'] is False
 assert r['alignment_provenance']['method']=='heuristic_textual_correspondence'
 for side,b in zip(('before','after'),raw):
  for p in r['evidence_context'][side]['provisions']:assert p['text']==b['rawtext'][p['start']:p['end']]
 assert {l['owner_label'] for l in r['evidence_context']['after']['notes']['links']} >= {'14.1','14.2','15.2(h)'}

def test_ambiguous_note_outside_owner_blocks_equality_claim():
 text='Artículo 14. A\n14.1 Texto.8\n14.2 Otro.8\nArtículo 15. B\n15.1 Cuerpo.\n8 Párrafo modificado por X.\n\n'
 r,_,_=run(text,text+' ')
 q=next(q for q in r['derived_comparison'] if q['before']['text'].startswith('Artículo 14.'))
 assert q['comparison_status']=='inconclusive' and q['category']=='unresolved'

def test_unsupported_headings_preserve_partial_raw_context():
 r,_,_=run('ÍNDICE\nCAPÍTULO I\nArtículo 1. Alcance\n3','ÍNDICE\nCAPÍTULO I\nArtículo 1. Alcance\n4')
 assert not r['derived_comparison'] and r['original_comparison']['no_changes'] is False
 assert r['evidence_context']['after']['excluded_ranges']

def test_numeric_page_like_body_line_and_punctuation_are_retained():
 r,_,_=run('Artículo 1. Alcance\n1.1 Importe\n1000\nPagar.','Artículo 1. Alcance\n1.1 Importe\n100\n¿Pagar?')
 q=r['derived_comparison'][0];assert '1000' in q['before']['text'] and '¿Pagar?' in q['after']['text']
 assert q['category']=='body_text_candidate'

def test_prescribed_address_is_body_candidate_not_furniture():
 address='Los Laureles Nº 214 - Lima 27 - Perú   Telf.: (511) 6309000'
 a='Artículo 1. Lugar\n1.1 La sede obligatoria es la siguiente:\n'+address+'\n1.2 Se presentará allí la solicitud.'
 b='Artículo 1. Lugar\n1.1 La sede obligatoria es la siguiente:\n1.2 Se presentará allí la solicitud.'
 r,_,_=run(a,b);q=r['derived_comparison'][0]
 assert ' '.join(address.split()) in q['before']['text'] and q['category']=='body_text_candidate'
 assert q['derived_equal'] is False and not q['before']['omitted_ranges']
 assert 'unverified_page_furniture_retained' in q['before']['uncertainty']

def test_real_address_lines_are_not_deleted_without_layout_evidence():
 pins=json.loads(Path('runs/sk03-market-018-inputs.json').read_text());raw=[json.loads(Path(p).read_text()) for p in pins['hashes'] if p.endswith('result.json')]
 r=compare_structural(pins['pair'],*raw);seen=0
 for q in r['derived_comparison']:
  for side in ('before','after'):
   view=q[side]
   assert all(o['reason']!='identified_page_furniture' for o in view['omitted_ranges'])
   if 'Los Laureles Nº 214' in view['text']:
    seen+=1;assert 'unverified_page_furniture_retained' in view['uncertainty']
 assert seen>0
