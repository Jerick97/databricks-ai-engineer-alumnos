"""025 regression: wrapped annex references are not annex-region headings."""
import json
from pathlib import Path
import pytest
from test_foundation_structure import bundle
from sbs.foundation.structure import structuralize
from sbs.comparison.pilot import build_pilot
from sbs.paths import project_path
ROOT=Path(__file__).resolve().parents[2]

@pytest.mark.parametrize('reference',['Anexo N° 1-A del Reglamento.','Anexo N° 2 del Reglamento, así como las penalidades','ANEXO N° 4 DEL REGLAMENTO, EN LO QUE CORRESPONDA.'])
def test_wrapped_reference_preserves_article_and_next(reference):
 raw='CAPÍTULO I\nArtículo 13. Tasas\nSegún lo indicado en el\n'+reference+'\nArtículo 27. Seguros\n27.1 Texto.\nArtículo 29. Pago\n29.1 Texto.'
 result=structuralize(bundle([raw]))
 assert [v['number'] for v in result['structure']['spans'].values()]==['13','27','29']
 assert reference in result['provisions'][0]['text']

@pytest.mark.parametrize('heading',['ANEXO A','ANEXO N° 1–A','ANEXO Nº 561','Anexo N° 2','ANEXO N° 17: TABLA DE INFORMACIÓN','ANEXO 82\nCÁLCULO DE LA TASA EFECTIVA','ÍNDICE'])
def test_actual_region_stays_blocked(heading):
 result=structuralize(bundle(['Artículo 1. Inicio\nTexto.\n'+heading+'\nCAPÍTULO II\nArtículo 27. Tabla\n27.1 Celda.']))
 assert [v['number'] for v in result['structure']['spans'].values()]==['1']

@pytest.mark.parametrize('side',['before','after'])
@pytest.mark.parametrize('provision',['art27','art29.1.4'])
def test_real_market_reference_covered(side,provision):
 item=next(x for x in build_pilot(ROOT)['items'] if x['provision_id']==provision)
 target=item[side]
 entries=[x for f in ['sk02-repository-capture.json','sk02-amendments-capture.json'] for x in json.loads((ROOT/'runs'/f).read_text())['sources']]
 entry=next(x for x in entries if x['source']['version_id']==target['version_id'])
 raw=json.loads(project_path(ROOT,entry['result_path']).read_text()); result=structuralize(raw)
 number=provision[3:].split('.')[0]
 candidates=[p for p in result['provisions'] if result['structure']['spans'][p['provision_id']]['number']==number]
 assert len(candidates)==1
 p=candidates[0]
 assert p['start']<=target['start']<target['end']<=p['end']
 assert p['text']==raw['rawtext'][p['start']:p['end']]
 assert result['structure']['spans'][p['provision_id']]['pages']==[x['page'] for x in raw['pages'] if x['start']<p['end'] and x['end']>p['start']]

@pytest.mark.parametrize('heading',['ANEXO N° 1 — REQUISITOS','ANEXO II','ANEXO N° 1 REQUISITOS','ANEXO XXIV','Anexo Nº 87 – Condiciones','ANEXO B TABLA'])
def test_ambiguous_annex_never_adopts_following_article(heading):
 r=structuralize(bundle(['CAPÍTULO I\nArtículo 1. Inicio\nTexto.\n'+heading+'\nArtículo 27. Requisitos\n27.1 Celda.']))
 assert [v['number'] for v in r['structure']['spans'].values()]==['1']
 assert heading not in r['provisions'][0]['text']


def test_reference_shape_without_sentence_continuation_stays_uncertain():
 r=structuralize(bundle(['Artículo 1. Inicio\nTexto terminado.\nANEXO N° 4 DEL REGLAMENTO.\nArtículo 27. Tabla\nTexto.']))
 assert [v['number'] for v in r['structure']['spans'].values()]==['1']
