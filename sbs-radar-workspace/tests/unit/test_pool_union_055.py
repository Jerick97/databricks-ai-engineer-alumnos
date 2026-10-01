"""Pure pool mechanics of experiment055, no quality claims or model call."""
import importlib.util
from pathlib import Path


def load():
    p=Path(__file__).resolve().parents[2]/'runs/sk04-pool-union-055.py'
    assert p.exists(), 'Missing explicit causal pool experiment'
    spec=importlib.util.spec_from_file_location('pool055',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def test_union_restores_single_branch_candidates_without_double_rrf():
    m=load();lex=[(f'l{i:02}',20-i) for i in range(20)];vec=[(f'v{i:02}',20-i) for i in range(20)]
    pool=m.pools(lex,vec)
    assert len(pool['baseline20'])==20 and len(pool['union'])==40
    assert pool['baseline20']==pool['union'][:20]
    assert set(pool['union'])=={x for x,_ in lex+vec}
    assert pool['union'][:4]==['l00','v00','l01','v01']


def test_union_deduplicates_by_id_and_preserves_overlap_rank():
    m=load();p=m.pools([('b',2),('a',1)],[('a',2),('c',1)])
    assert p['union']==['a','b','c']
    assert len(p['union'])==len(set(p['union']))
