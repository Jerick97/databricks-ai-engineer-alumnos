from copy import deepcopy
import runpy
from pathlib import Path
import pytest
from test_foundation_structure import bundle
from sbs.comparison.structural import _view
ROOT=Path(__file__).resolve().parents[2]
old=runpy.run_path(str(ROOT/'runs/sk03-map-compaction-027-before/structural.py'))['_view']

def context(p,notes=None):return {'notes':notes or {'notes':[],'links':[],'unresolved':[]},'unit_context':[{'provision_id':p['provision_id'],'related_exclusions':[]}]}

@pytest.mark.parametrize('raw',['Uno dos tres.','  Uno\t dos  tres.\n','Uno\n\ndos tres.','Uno\u00a0dos.','Texto  íntegro\ncontinúa. '])
def test_exact_reconstruction_and_compaction(raw):
 b=bundle([raw]);p=b['provisions'][0];c=context(p)
 prior=old(b,p,c);after=_view(b,p,c)
 assert {k:v for k,v in prior.items() if k!='mapping'}=={k:v for k,v in after.items() if k!='mapping'}
 assert ''.join(raw[m['raw_start']:m['raw_end']] for m in after['mapping'])==raw
 assert ''.join(m['derived_text'] for m in after['mapping'])==after['text']
 for i,m in enumerate(after['mapping']):
  assert m['derived_end']-m['derived_start']==len(m['derived_text'])
  if i:assert m['raw_start']==after['mapping'][i-1]['raw_end'] and m['derived_start']==after['mapping'][i-1]['derived_end']
  if m['operation']=='retain':assert raw[m['raw_start']:m['raw_end']]==m['derived_text']
  if i:assert not(m['operation']=='retain' and after['mapping'][i-1]['operation']=='retain')
 assert len(after['mapping'])<=len(prior['mapping'])
 if raw=='Uno dos tres.':assert len(after['mapping'])==1<len(prior['mapping'])


def test_omission_and_true_replacements_not_coalesced():
 raw='Uno  X dos.';b=bundle([raw]);p=b['provisions'][0]
 c=context(p,{'notes':[],'unresolved':[],'links':[{'note_id':'n','owner_provision_id':p['provision_id'],'marker_span':{'start':5,'end':6,'citation_id':'c'}}]})
 prior=old(b,p,c);after=_view(b,p,c)
 assert after['text']==prior['text'] and after['omitted_ranges']==prior['omitted_ranges']
 for op in ['omit','replace']:
  assert [m for m in after['mapping'] if m['operation']==op]==[m for m in prior['mapping'] if m['operation']==op and raw[m['raw_start']:m['raw_end']]!=m['derived_text']]
 assert ''.join(raw[m['raw_start']:m['raw_end']] for m in after['mapping'])==raw
