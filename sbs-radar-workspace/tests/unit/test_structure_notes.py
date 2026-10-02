import hashlib,json
from copy import deepcopy
from pathlib import Path
import pytest
from sbs.foundation.structure_notes import extract_note_links

def h(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def fixture(text):
 sha=hashlib.sha256(text.encode()).hexdigest()
 raw=dict(rawtext=text,rawtext_sha256=sha,sha256=sha,layer='raw_pages',pages=[dict(page=1,start=0,end=len(text))])
 p=dict(citation_id='parent',document_id='fixture',version_id=sha,source_kind='normative',synthetic=True,page=1,start=0,end=len(text),text=text,provision_id='raw-page-1')
 raw['provisions']=[p]
 import re
 headers=list(re.finditer(r'(?m)^Artículo (\d+)\. .*$',text));ps=[];spans={}
 for i,m in enumerate(headers):
  end=headers[i+1].start() if i+1<len(headers) else len(text);pid='a'+m[1]
  q=dict(p,provision_id=pid,citation_id=pid,start=m.start(),end=end,text=text[m.start():end]);ps.append(q);spans[pid]={'context':'document','number':m[1]}
 structural=dict(raw,layer='structural_provisions',provisions=ps,structure={'parent_bundle_sha256':h(raw),'spans':spans})
 return raw,structural

def test_note_inside_next_article_links_to_marker_not_proximity():
 raw,s=fixture('Artículo 14. A\n14.1 Texto.8\nArtículo 15. B\n15.1 Cuerpo.\n8 Párrafo modificado por la Resolución SBS Nº 100-2024.\nContinúa la nota.\n\n')
 original=deepcopy((raw,s));r=extract_note_links(raw,s)
 assert (raw,s)==original and len(r['notes'])==1 and len(r['links'])==1
 link=r['links'][0];assert link['owner_provision_id']=='a14' and link['owner_label']=='14.1'
 assert link['status']=='unique_textual_match' and 'Continúa la nota.' in r['notes'][0]['citation']['text']
 assert r['notes'][0]['citation']['citation_id']!='a15'
 assert raw['rawtext'][link['marker_span']['start']:link['marker_span']['end']]=='8'

@pytest.mark.parametrize('body',['14.1 Valor 8.','14.1 Valor 2.8','14.1 Conforme artículo 8.'])
def test_ordinary_number_is_not_marker(body):
 r=extract_note_links(*fixture('Artículo 14. A\n'+body+'\n8 Párrafo modificado por la Resolución SBS Nº 1-2024.\n\n'))
 assert len(r['notes'])==1 and not r['links'] and r['unresolved']

def test_duplicate_marker_and_note_remain_unresolved():
 for tail in ['14.2 Segundo.8\n','']:
  text='Artículo 14. A\n14.1 Texto.8\n'+tail+'8 Párrafo modificado por la Resolución SBS Nº 1-2024.\n\n'
  if not tail:text+='8 Párrafo modificado por la Resolución SBS Nº 2-2024.\n\n'
  r=extract_note_links(*fixture(text));assert not r['links'] and r['unresolved']

def test_scope_does_not_link_across_chapter():
 r=extract_note_links(*fixture('CAPÍTULO I\nArtículo 1. A\n1.1 Texto.8\nCAPÍTULO II\nArtículo 2. B\n8 Párrafo modificado por la Resolución SBS Nº 1-2024.\n\n'))
 assert not r['links'] and r['unresolved']

def test_missing_note_end_boundary_is_pending():
 r=extract_note_links(*fixture('Artículo 1. A\n1.1 Texto.8\n8 Párrafo modificado por la Resolución SBS Nº 1-2024.\nresto sin frontera'))
 assert r['notes'] and not r['links'] and r['notes'][0]['boundary_status']=='unresolved'

@pytest.mark.parametrize('mutate',['raw','structural','parent'])
def test_identity_and_offsets_are_checked(mutate):
 raw,s=fixture('Artículo 1. A\n1.1 Texto.8\n8 Párrafo modificado por la Resolución SBS Nº 1-2024.\n\n')
 if mutate=='raw':raw['rawtext']+='x'
 elif mutate=='structural':s['provisions'][0]['text']='inventado'
 else:s['structure']['parent_bundle_sha256']='0'*64
 with pytest.raises(ValueError):extract_note_links(raw,s)

def test_real_4036_notes_and_exact_spans():
 pins=json.loads(Path('runs/sk03-market-018-inputs.json').read_text());paths=[p for p in pins['hashes'] if p.endswith('result.json')]
 for side,path in zip(('before','after'),paths):
  raw=json.loads(Path(path).read_text());s=json.loads(Path('runs/sk02-structure-019-fix-'+side+'.json').read_text());r=extract_note_links(raw,s)
  for n in r['notes']:
   c=n['citation'];assert c['text']==raw['rawtext'][c['start']:c['end']]
  if side=='after':
   links={l['marker']:l for l in r['links']}
   assert links['8']['owner_label']=='14.1' and links['9']['owner_label']=='14.2' and links['10']['owner_label']=='15.2(h)'

@pytest.mark.parametrize('body',['14.1 Importe S/ 2.8','14.1 Fecha 29.06.2024','14.1 Conforme art.8','14.1 Véase num.8','14.1 Valor 8.2','14.1 Referencia núm.8'])
def test_date_amount_abbreviated_reference_not_marker(body):
 r=extract_note_links(*fixture('Artículo 14. A\n'+body+'\n8 Párrafo modificado por la Resolución SBS Nº 1-2024.\n\n'))
 assert not r['links'] and r['notes'] and r['unresolved']

def test_repeated_number_in_distinct_sections_links_only_own_scope():
 text='CAPÍTULO I\nArtículo 1. A\n1.1 Texto.8\n8 Párrafo modificado por la Resolución SBS Nº 1-2024.\n\nCAPÍTULO II\nArtículo 2. B\n2.1 Texto.8\n8 Párrafo modificado por la Resolución SBS Nº 2-2024.\n\n'
 r=extract_note_links(*fixture(text));assert {x['owner_label'] for x in r['links']}=={'1.1','2.1'} and not r['unresolved']

def test_citation_identity_includes_document_and_pages_crossing():
 raw,s=fixture('Artículo 1. A\n1.1 Texto.8\n8 Párrafo modificado por la Resolución SBS Nº 1-2024.\nContinúa.\n\n')
 split=raw['rawtext'].index('Continúa.')-1
 raw['pages']=[dict(page=1,start=0,end=split),dict(page=2,start=split+1,end=len(raw['rawtext']))]
 s['pages']=deepcopy(raw['pages']);s['structure']['parent_bundle_sha256']=h(raw)
 r=extract_note_links(raw,s);assert r['notes'][0]['citation']['pages']==[1,2]
 old=r['notes'][0]['note_id']
 for b in (raw,s):
  for p in b['provisions']:p['document_id']='different-document'
 s['structure']['parent_bundle_sha256']=h(raw)
 assert extract_note_links(raw,s)['notes'][0]['note_id']!=old

def test_note_identity_tracks_raw_extraction_bundle():
 raw,s=fixture('Artículo 1. A\n1.1 Texto.8\n8 Párrafo modificado por X.\n\n')
 a=extract_note_links(raw,s);assert a==extract_note_links(raw,s)
 raw['extractor']='other';raw['config_hash']='b'*64;s['structure']['parent_bundle_sha256']=h(raw)
 b=extract_note_links(raw,s)
 assert a['notes'][0]['note_id']!=b['notes'][0]['note_id']
 assert a['notes'][0]['marker_span']['citation_id']!=b['notes'][0]['marker_span']['citation_id']

@pytest.mark.parametrize('line',['Artículo Segundo.- Nueva obligación.','15.2 Nueva obligación.','h) Nueva obligación.'])
def test_ambiguous_body_continuation_blocks_note_removal(line):
 text='Artículo 14. A\n14.1 Texto.8\n8 Párrafo modificado por X.\n'+line+'\n\n'
 r=extract_note_links(*fixture(text));n=r['notes'][0]
 assert not r['links'] and n['boundary_status']=='unresolved'
 assert line not in n['citation']['text']
 assert line in n['continuation_candidate']['text']
 assert r['unresolved'][0]['candidate_owners']

@pytest.mark.parametrize('ordinal',['Primero','Primera','Segundo','Segunda','Tercero','Tercera','Cuarto','Cuarta','Quinto','Quinta','Sexto','Sexta','Sétimo','Sétima','Setimo','Setima','Séptimo','Séptima','Septimo','Septima','Octavo','Octava','Noveno','Novena','Décimo','Décima','Decimo','Decima'])
def test_supported_ordinal_vocabulary_stays_outside_note(ordinal):
 line='Artículo '+ordinal+'.- Nueva obligación.'
 r=extract_note_links(*fixture('Artículo 14. A\n14.1 Texto.8\n8 Párrafo modificado por X.\n'+line+'\n\n'))
 n=r['notes'][0]
 assert n['boundary_status']=='unresolved' and not r['links']
 assert line not in n['citation']['text'] and line in n['continuation_candidate']['text']
