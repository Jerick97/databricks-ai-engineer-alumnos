from pathlib import Path
import importlib.util,copy
from types import SimpleNamespace
import pytest
ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('fresh215test',ROOT/'runs/sk06-sk11-fresh-215.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Journal:
 def __init__(self):self.rows=[]
 def save(self,name,row):self.rows.append((name,copy.deepcopy(row)))
def setup():
 row={'query_id':'sid','query_text':m.SET_CACHE,'warehouse_id':'warehouse','executed_as_user_id':123,'status':'FINISHED','is_final':False}
 return row,SimpleNamespace(warehouse_id='warehouse',executor_id=123),Journal(),SimpleNamespace(check=lambda:None)
def test_set_nonfinal_then_final_records_both_without_sql():
 row,cfg,j,b=setup();rows=[row,{**row,'is_final':True}];calls=[];sleep=[]
 history=SimpleNamespace(_get=lambda sid:calls.append(sid) or rows.pop(0))
 out=m.poll_set_history(history,'sid',cfg,j,b,sleep=sleep.append)
 assert out['is_final'] is True and calls==['sid','sid'] and sleep==[2] and len(j.rows)==2 and j.rows[0][1]['is_final'] is False
@pytest.mark.parametrize('field,value',[('executed_as_user_id',456),('query_id','other'),('query_text','SELECT secret'),('warehouse_id','other'),('cache_query_id','cached'),('status','FAILED')])
def test_wrong_history_rejected_and_saved_before_acceptance(field,value):
 row,cfg,j,b=setup();row.update({field:value,'is_final':True})
 with pytest.raises(ValueError):m.poll_set_history(SimpleNamespace(_get=lambda sid:row),'sid',cfg,j,b,sleep=lambda _:pytest.fail('must not wait'))
 assert j.rows[0][1][field]==value

def test_set_poll_exhaustion_bounded_to_twelve_gets():
 row,cfg,j,b=setup();calls=[]
 with pytest.raises(ValueError,match='NOT_FINAL'):m.poll_set_history(SimpleNamespace(_get=lambda sid:calls.append(sid) or row),'sid',cfg,j,b,sleep=lambda _:None)
 assert len(calls)==len(j.rows)==12

def test_readback_finality_poll_preserves_original_validator(monkeypatch):
 row,cfg,j,b=setup();row['query_text']='SELECT allowed';values=[row,{**row,'is_final':True}]
 monkeypatch.setattr(m.HistoryRegistryBuilder,'_get',lambda self,sid:values.pop(0))
 policy=m.PublisherPolicy(certificate_sha256='0'*64,mapping_sha256='0'*64,snapshot='0'*64,config_hash='0'*64,publisher_identity='owner',warehouse_id='warehouse',executor_id=123,ttl_ms=300000,max_readback_age_ms=300000)
 h=m.FinalReadbackHistory(SimpleNamespace(list=lambda:None),policy,journal=j,budget=b,allowed_sql=['SELECT allowed'],sleep=lambda _:None)
 assert h._get('sid')['is_final'] is True and len(j.rows)==2
 assert m.FinalReadbackHistory.build is m.HistoryRegistryBuilder.build
 row['executed_as_user_id']=456;values.append(row)
 with pytest.raises(ValueError,match='IDENTITY'):h._get('sid')

def test_prior_exactly_one_set_preserved_and_new_session_accounted():
 p=m.prepare(ROOT);out=m.prior_zero_sql(ROOT,p)
 assert out['prior_sql_reserved']==0 and out['prior_session213_sql_reserved']==1 and out['aggregate_prior_fresh_sql_reserved']==1
 assert out['legacy_scope112']['limit']==112 and out['prior_session_closed_requires_new_SET'] is True
 source=(ROOT/'runs/sk06-sk11-fresh-215.py').read_text();assert 'aggregate_fresh_sql_reserved=1+journal.count' in source and 'allow_start=False' in source
 assert "state=root/'deployment/state/fresh-readback-215'" in source

def test_zero_rows_then_final_is_bounded_get_only_and_duplicates_rejected():
 row,cfg,j,b=setup();row['is_final']=True
 policy=m.PublisherPolicy(certificate_sha256='0'*64,mapping_sha256='0'*64,snapshot='0'*64,config_hash='0'*64,publisher_identity='owner',warehouse_id='warehouse',executor_id=123,ttl_ms=300000,max_readback_age_ms=300000)
 pages=[{'res':[],'has_next_page':False},{'res':[row],'has_next_page':False}];calls=[]
 def listing(**kw):calls.append(kw);return pages.pop(0)
 h=m.EmptyAwareHistory(SimpleNamespace(list=listing),policy)
 assert m.poll_set_history(h,'sid',cfg,j,b,sleep=lambda _:None)['is_final'] is True
 assert len(calls)==2 and j.rows[0][1]['state']=='no_rows_yet'
 pages.append({'res':[row,row],'has_next_page':False})
 with pytest.raises(ValueError,match='EXACT_PUBLISHER_HISTORY_REQUIRED'):h._get('sid')
