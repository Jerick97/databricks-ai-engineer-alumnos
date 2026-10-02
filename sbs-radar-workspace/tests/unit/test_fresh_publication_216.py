from pathlib import Path
import copy,datetime,importlib.util,json
from types import SimpleNamespace
import numpy as np
import pytest
from sbs.genie.fresh_publication_081 import SessionReader,Journal,SET_CACHE
from sbs.genie.publication import _detail,_detail_identity,NAMED_IDENTITY_PROFILE
ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('fresh216test',ROOT/'runs/sk06-sk11-fresh-216.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Cursor:
 def __init__(self,columns,row):self.description=[(c['name'],c['type_name'],None,None,None,None,None) for c in columns];self.rows=[row];self.calls=[];self.query_id=None
 def execute(self,sql):self.calls.append(sql);self.query_id='query-'+str(len(self.calls))
 def fetchmany(self,size):out=self.rows[:size];self.rows=self.rows[size:];return out

def raw_fixture():
 f=json.loads((ROOT/'runs/sk06-fresh-215-detail-fixture.json').read_text());row=copy.deepcopy(f['row'])
 types={x['column']:x['type'] for x in f['types']}
 for i,c in enumerate(f['columns']):
  if types[c['name']]=='numpy.ndarray':row[i]=np.array(row[i],dtype=object)
  elif types[c['name']]=='datetime.datetime':row[i]=datetime.datetime.fromisoformat(row[i])
 return f,row

def reader(tmp_path,cls,cursor,**kw):
 journal=Journal(tmp_path.resolve()/'journal',plan_sha256='a'*64)
 r=cls(cursor,journal,allowed_sql=['DESCRIBE DETAIL pinned'],warehouse_id='warehouse',metadata_get=lambda _:None,governance_probe=lambda _:None,evidence_mode='fixture',identity_profile=NAMED_IDENTITY_PROFILE,**kw)
 r.disable_cache();return r,journal

def test_real_detail_shape_baseline_rejects_ndarray_and_adapter_retains_schema(tmp_path):
 f,row=raw_fixture();baseline,j=reader(tmp_path/'old',SessionReader,Cursor(f['columns'],row))
 with pytest.raises(ValueError,match='VALUE_TYPE_UNSUPPORTED'):baseline._execute('DESCRIBE DETAIL pinned')
 j.close();r,j=reader(tmp_path/'new',m.ArraySessionReader216,Cursor(f['columns'],row));columns,rows,proof=r._execute('DESCRIBE DETAIL pinned')
 assert columns==f['columns'];d=_detail(columns,rows)
 assert _detail_identity(d,columns,{'full_name':d['name'],'storage_location':'s3://fixture'},NAMED_IDENTITY_PROFILE)['detail_location_observation']=='empty'
 for name in ('partitionColumns','clusteringColumns','tableFeatures','properties','statistics'):
  i=next(i for i,c in enumerate(columns) if c['name']==name);assert json.loads(rows[0][i])==f['row'][i]
 assert proof['statement_id']=='query-2' and proof['row_count']==1 and j.count==2
 saved=json.loads((tmp_path/'new/journal/result-02.json').read_text());assert saved['proof']==proof and saved['normalized_rows']==rows;j.close()

def test_real_array_recursion_and_unobserved_standalone_scalar_not_coerced():
 v=[('key',np.array(['a','b'])),{'nested':np.array([1,2])}]
 assert m.array_values(v)==[('key',['a','b']),{'nested':[1,2]}]
 scalar=np.int64(7);assert m.array_values(scalar) is scalar

@pytest.mark.parametrize('cap',[1,20])
def test_adapter_keeps_bytecap_for_arrays(tmp_path,cap):
 columns=[{'name':'array','type_name':'ARRAY','position':0}];r,j=reader(tmp_path,m.ArraySessionReader216,Cursor(columns,[np.array(['x'*50])]),max_bytes=cap)
 with pytest.raises(ValueError,match='BYTE_CAP'):r._execute('DESCRIBE DETAIL pinned')
 assert j.count==2;j.close()

def test_prior_three_sql_retained_and_no_new_start():
 out=m.prior_zero_sql(ROOT,m.prepare(ROOT));assert out['aggregate_prior_fresh_sql_reserved']==3 and out['prior_session215_sql_reserved']==2 and out['prior_session213_sql_reserved']==1
 source=(ROOT/'runs/sk06-sk11-fresh-216.py').read_text();assert 'aggregate_fresh_sql_reserved=3+journal.count' in source and 'allow_start=False' in source


def test_all_eight_tables_with_real_arrays_and_map_tuples(tmp_path):
    from test_genie_publication import inputs,plan,SDK,metadata,governance
    from sbs.genie.publication import _sqls,STRICT_IDENTITY_PROFILE
    from sbs.genie.publication_registry import HistoryRegistryBuilder,PublisherPolicy
    cfg,bundle=inputs();sdk=SDK(bundle);history={}
    from test_fresh_publication_081 import Cursor as BaseCursor
    class Typed(BaseCursor):
        def execute(self,sql):
            super().execute(sql)
            if sql==SET_CACHE:return self
            result=sdk.execute_statement(statement=sql,warehouse_id='warehouse')
            columns=result['manifest']['schema']['columns']
            self.description=[(c['name'],c['type_name'].lower(),None,None,None,None,None) for c in columns]
            self.rows=[]
            for row in result['result']['data_array']:
                self.rows.append(tuple((v=='true' if c['type_name']=='BOOLEAN' else int(v) if c['type_name']=='LONG' else v) for c,v in zip(columns,row)))
            if sql.startswith('DESCRIBE'):
                self.description.extend([('array_column','ARRAY',None,None,None,None,None),('map_column','MAP',None,None,None,None,None)])
                self.rows=[tuple(row)+(np.array(['feature1','feature2']),[('key','value')]) for row in self.rows]
            history[self.query_id]=dict(query_id=self.query_id,query_text=sql,warehouse_id='warehouse',executed_as_user_id=42,status='FINISHED',is_final=True,statement_type='SELECT' if sql.startswith('SELECT') else 'OTHER',query_start_time_ms=10,execution_end_time_ms=20)
            return self
    p=plan();sql=[s for t in p.as_dict()['tables'] for s in _sqls(t)+[_sqls(t)[0]]]
    journal=Journal(tmp_path.resolve()/'081',plan_sha256='a'*64);cursor=Typed()
    r=m.ArraySessionReader216(cursor,journal,allowed_sql=sql,warehouse_id='warehouse',metadata_get=metadata,governance_probe=governance,evidence_mode='fixture',identity_profile=STRICT_IDENTITY_PROFILE)
    r.disable_cache();cert=r.read(p)
    policy=PublisherPolicy(cert.sha256,cfg['mapping_sha256'],bundle['snapshot_hash'],bundle['config_hash'],'fixture','warehouse',42,1000,1000,'fixture')
    api=SimpleNamespace(list=lambda **kw:dict(res=[history[kw['filter_by'].statement_ids[0]]],has_next_page=False))
    builder=HistoryRegistryBuilder(api,policy,clock=lambda:100)
    assert len(builder.build(cert).as_dict()['history_records'])==32
    assert len(cert.as_dict()['tables'])==8 and journal.count==33 and len(cursor.calls)==33
    assert all(t['content_sha256']==__import__('sbs.genie',fromlist=['digest']).digest(bundle['tables'][t['logical_name']]) for t in cert.as_dict()['tables'])
    history['query-4']['cache_query_id']='old'
    with pytest.raises(ValueError,match='NOT_VERIFIED'):builder.build(cert)

