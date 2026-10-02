import runpy
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[2]

def test_scope_before_scoring_and_fixed_pool(monkeypatch):
 import sbs.retrieval
 seen=[]
 def score(q,rows):seen.extend(rows);return [(r['citation']['citation_id'],float(i+1)) for i,r in enumerate(rows)][::-1]
 monkeypatch.setattr(sbs.retrieval,'_bm25',score)
 api=runpy.run_path(str(ROOT/'skills/sbs-rag-hibrido/scripts/rank_development.py'))
 passages=[{'passage_id':str(i),'document_id':d,'version_id':v,'quote':'text'} for i,(d,v) in enumerate([('d','a'),('d','b'),('x','a'),('d','c'),('d','a')])]
 metadata={str(i):{'family':('other' if i==4 else 'f')} for i in range(5)}
 pair={'family':'f','before':{'document_id':'d','version_id':'a'},'after':{'document_id':'d','version_id':'b'}}
 result=api['scoped_rank']('q','f',pair,passages,metadata)
 assert result['eligible_ids']==['0','1']
 assert [r['citation']['citation_id'] for r in seen]==['0','1']
 assert result['pool_top20']==['1','0']
 with pytest.raises(ValueError):api['scoped_rank']('q','other',pair,passages,metadata)
