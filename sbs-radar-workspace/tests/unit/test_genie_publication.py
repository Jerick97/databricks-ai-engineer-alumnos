"""Publication contracts using fixtures only; no cloud evidence."""
import json
from copy import deepcopy
from pathlib import Path
import pytest
from sbs.genie import TABLES, COLUMNS, digest
from sbs.genie.publication import prepare_plan, PublicationReader, CertificateStore
ROOT=Path(__file__).resolve().parents[2]

def inputs():
    directory=ROOT/'runs/sk06-pilot-002'
    bundle=json.loads((directory/'manifest.json').read_text())
    bundle['tables']={t:[json.loads(x) for x in (directory/(t+'.jsonl')).read_text().splitlines()] for t in TABLES}
    config=json.loads((ROOT/'config/genie-pilot-002.json').read_text())
    return config,bundle

def plan():
    c,b=inputs();return prepare_plan(c,b,{t:7 for t in TABLES})

def response(names,types,rows,statement_id='stmt'):
    data=[[('true' if v else 'false') if type(v) is bool else str(v) if v is not None else None for v in row] for row in rows]
    return {'statement_id':statement_id,'status':{'state':'SUCCEEDED'},'manifest':{'format':'JSON_ARRAY','schema':{'columns':[{'name':n,'type_name':t,'position':i} for i,(n,t) in enumerate(zip(names,types))]},'total_row_count':len(data),'total_chunk_count':1,'truncated':False,'chunks':[{'chunk_index':0,'row_offset':0,'row_count':len(data)}]},'result':{'chunk_index':0,'row_offset':0,'row_count':len(data),'data_array':data}}

class SDK:
    def __init__(self,bundle):self.bundle=bundle;self.calls=[];self.mutate=lambda x:x
    def execute_statement(self,statement,warehouse_id,**kw):
        self.calls.append(statement)
        table=next(t for t in TABLES if '`'+t+'`' in statement)
        if statement.startswith('DESCRIBE DETAIL'):r=response(['format','id','location'],['STRING']*3,[['delta','delta-'+table,'s3://sealed/'+table]])
        elif statement.startswith('DESCRIBE HISTORY'):r=response(['version'],['LONG'],[[7],[8]])
        else:r=response(COLUMNS,['BOOLEAN' if n in ('synthetic','human_approved') else 'STRING' for n in COLUMNS],[[row[n] for n in COLUMNS] for row in self.bundle['tables'][table]])
        return self.mutate(r)

def metadata(name):return {'full_name':name,'table_id':'uc-'+name.split('.')[-1],'metastore_id':'meta','data_source_format':'DELTA','table_type':'MANAGED','storage_location':'s3://sealed/'+name.split('.')[-1],'row_filter':None,'columns':[]}
def governance(names):return {'evidence_id':'fixture-controls','mode':'fixture','ddl_identity_controlled':True,'retention_controlled':True,'select_authorized':True,'policies_absent':True,'source_tables':names}
def reader(sdk,**kwargs):return PublicationReader(sdk,warehouse_id='warehouse',metadata_get=metadata,governance_probe=governance,evidence_mode='fixture',**kwargs)

def test_full_pilot_readback_certificate_and_immutable_store(tmp_path):
    c,b=inputs();sdk=SDK(b);cert=reader(sdk).read(plan());d=cert.as_dict()
    assert d['version']==2 and d['evidence_mode']=='fixture' and not d['aba_prevented']
    assert len(d['tables'])==8 and len(sdk.calls)==32
    assert d['snapshot']==b['snapshot_hash']
    assert all(t['content_sha256']==digest(b['tables'][t['logical_name']]) for t in d['tables'])
    store=CertificateStore(tmp_path);store.put(cert);assert store.get(cert.sha256)==cert
    d['snapshot']='tampered';assert cert.as_dict()['snapshot']==b['snapshot_hash']
    with pytest.raises(ValueError):store.get('../escape')

@pytest.mark.parametrize('version',[True,-1,'7',7.5])
def test_invalid_version(version):
    c,b=inputs()
    with pytest.raises(ValueError):prepare_plan(c,b,{t:version for t in TABLES})

def test_rejects_injected_names_and_modified_export():
    c,b=inputs();c['catalog']='bad; DROP TABLE x'
    with pytest.raises(ValueError):prepare_plan(c,b,{t:7 for t in TABLES})
    c,b=inputs();b['tables']['documents'][0]['id']='altered'
    with pytest.raises(ValueError):prepare_plan(c,b,{t:7 for t in TABLES})

@pytest.mark.parametrize('change',[lambda r:r['manifest'].update(truncated=True),lambda r:r['status'].update(state='FAILED'),lambda r:r['manifest'].update(total_row_count=999),lambda r:r.update(statement_id=''),lambda r:r['manifest']['schema']['columns'][0].update(type_name='BINARY')])
def test_rejects_bad_statement_response(change):
    _,b=inputs();sdk=SDK(b)
    def mutate(r):change(r);return r
    sdk.mutate=mutate
    with pytest.raises(ValueError):reader(sdk).read(plan())

def test_missing_governance_rejected_before_execution():
    _,b=inputs();sdk=SDK(b);r=reader(sdk);r.governance_probe=lambda names:{}
    with pytest.raises(ValueError):r.read(plan())
    assert not sdk.calls

def test_duplicate_readback_ids_rejected():
    _,b=inputs();sdk=SDK(b)
    def mutate(r):
        if r['manifest']['schema']['columns'][0]['name']=='id' and len(r['result']['data_array'])>1:r['result']['data_array'][1][0]=r['result']['data_array'][0][0]
        return r
    sdk.mutate=mutate
    with pytest.raises(ValueError):reader(sdk).read(plan())


def test_chunked_readback_fetches_exact_offsets():
    _,b=inputs();sdk=SDK(b);original=sdk.execute_statement;pending={}
    def execute(*a,**kw):
        r=original(*a,**kw)
        if kw['statement'].startswith('SELECT') and len(r['result']['data_array'])>1:
            rows=r['result']['data_array'];total=len(rows)
            r['manifest'].update(total_chunk_count=2,chunks=[{'chunk_index':0,'row_offset':0,'row_count':1},{'chunk_index':1,'row_offset':1,'row_count':total-1}])
            r['result'].update(data_array=rows[:1],row_count=1)
            pending['chunk']={'chunk_index':1,'row_offset':1,'row_count':total-1,'data_array':rows[1:]}
        return r
    sdk.execute_statement=execute;sdk.get_statement_result_chunk_n=lambda sid,index:deepcopy(pending['chunk'])
    assert reader(sdk).read(plan()).as_dict()['evidence_mode']=='fixture'
    sdk.get_statement_result_chunk_n=lambda sid,index:dict(pending['chunk'],row_offset=0)
    with pytest.raises(ValueError,match='CHUNK_IDENTITY'):reader(sdk).read(plan())


def test_identity_changed_and_masks_rejected():
    _,b=inputs();sdk=SDK(b);r=reader(sdk);calls=[]
    def get(name):
        m=metadata(name);calls.append(name)
        if len(calls)==2:m['table_id']='different'
        return m
    r.metadata_get=get
    with pytest.raises(ValueError,match='TABLE_IDENTITY_CHANGED'):r.read(plan())
    r=reader(SDK(b));r.metadata_get=lambda n:dict(metadata(n),columns=[{'mask':{'function_name':'mask'}}])
    with pytest.raises(ValueError,match='TABLE_POLICY'):r.read(plan())


def test_pending_is_polled_bounded_and_terminal_failure_not_retried():
    _,b=inputs();sdk=SDK(b);original=sdk.execute_statement;current={}
    def execute(*a,**kw):
        current['response']=original(*a,**kw)
        return {'statement_id':'stmt','status':{'state':'PENDING'}}
    sdk.execute_statement=execute;sdk.get_statement=lambda sid:current['response']
    reader(sdk).read(plan())
    sdk.get_statement=lambda sid:{'statement_id':sid,'status':{'state':'RUNNING'}}
    with pytest.raises(ValueError,match='STATEMENT_TIMEOUT'):reader(sdk,max_polls=2).read(plan())


def test_caps_and_store_corruption(tmp_path):
    _,b=inputs()
    with pytest.raises(ValueError,match='STATEMENT_QUOTA'):reader(SDK(b),max_statements=1).read(plan())
    cert=reader(SDK(b)).read(plan());store=CertificateStore(tmp_path);store.put(cert)
    (tmp_path/(cert.sha256+'.json')).write_text('{}')
    with pytest.raises(ValueError,match='CERTIFICATE_CORRUPTED'):store.get(cert.sha256)


def test_wrong_version_and_detail_type_rejected():
    _,b=inputs();sdk=SDK(b)
    def mutate(r):
        if r['manifest']['schema']['columns'][0]['name']=='version':r['result']['data_array']=[['8'],['9']]
        return r
    sdk.mutate=mutate
    with pytest.raises(ValueError,match='DELTA_VERSION_NOT_OBSERVED'):reader(sdk).read(plan())
    def detailtype(r):
        if r['manifest']['schema']['columns'][0]['name']=='format':r['manifest']['schema']['columns'][0]['type_name']='BINARY'
        return r
    sdk.mutate=detailtype
    with pytest.raises(ValueError,match='DETAIL_SCHEMA'):reader(sdk).read(plan())

@pytest.mark.parametrize('mutation', ['empty','missing','duplicate','logical','extra'])
def test_untrusted_serialized_plan_closed_before_capabilities(mutation):
    from sbs.genie.publication import PublicationPlan
    from sbs.genie import canonical
    p=plan().as_dict()
    if mutation=='empty':p['tables']=[]
    elif mutation=='missing':p['tables'].pop()
    elif mutation=='duplicate':p['tables'][-1]=p['tables'][0]
    elif mutation=='logical':p['tables'][0]['logical_name']='versions'
    else:p['unexpected']=True
    _,bundle=inputs();sdk=SDK(bundle)
    with pytest.raises(ValueError):reader(sdk).read(PublicationPlan(canonical(p).encode()))
    assert sdk.calls==[]


def test_final_chunk_cannot_advertise_successor():
    _,bundle=inputs();sdk=SDK(bundle)
    def mutate(r):
        r['result']['next_chunk_index']=1
        return r
    sdk.mutate=mutate
    with pytest.raises(ValueError,match='CONTINUATION'):reader(sdk).read(plan())


@pytest.mark.parametrize('field,value',[('evidence_mode','invalid'),('mode','interval'),('tables',[]),('version',True)])
def test_store_validates_closed_certificate_on_write_and_read(tmp_path,field,value):
    from sbs.genie.publication import Certificate,sha
    from sbs.genie import canonical
    _,bundle=inputs();p=reader(SDK(bundle)).read(plan()).as_dict();p[field]=value
    raw=canonical(p).encode();cert=Certificate(raw);store=CertificateStore(tmp_path)
    with pytest.raises(ValueError):store.put(cert)
    (tmp_path/(sha(raw)+'.json')).write_bytes(raw)
    with pytest.raises(ValueError):store.get(sha(raw))

@pytest.mark.parametrize('field,value',[('next_chunk_index',True),('next_chunk_index',0),('next_chunk_internal_link','/wrong'),('next_chunk_internal_link','')])
def test_contradictory_continuation_rejected(field,value):
    _,bundle=inputs();sdk=SDK(bundle)
    def mutate(r):
        r['result'][field]=value
        return r
    sdk.mutate=mutate
    with pytest.raises(ValueError,match='CONTINUATION'):reader(sdk).read(plan())


def test_manifest_successor_is_exact_and_optional():
    from sbs.genie.publication import _continuation
    _continuation({},0,2,'stmt')  # Manifest drives fetching when optional links are absent.
    _continuation({'next_chunk_index':1,'next_chunk_internal_link':'/api/2.0/sql/statements/stmt/result/chunks/1'},0,2,'stmt')
    for chunk in ({'next_chunk_index':2},{'next_chunk_index':0},{'next_chunk_internal_link':'/api/2.0/sql/statements/other/result/chunks/1'}):
        with pytest.raises(ValueError,match='CONTINUATION'):_continuation(chunk,0,2,'stmt')


@pytest.mark.parametrize('mutation',['nested_mode','proof_missing','unknown','relabeled','sql_hash','row_count'])
def test_certificate_nested_closure(tmp_path,mutation):
    from sbs.genie.publication import Certificate
    from sbs.genie import canonical
    _,bundle=inputs();p=reader(SDK(bundle)).read(plan()).as_dict();t=p['tables'][0]
    if mutation=='nested_mode':t['evidence'][0]['evidence_mode']='real'
    elif mutation=='proof_missing':t['evidence'].pop()
    elif mutation=='unknown':t['extra']=True
    elif mutation=='relabeled':t['logical_name']='versions'
    elif mutation=='sql_hash':t['evidence'][0]['sql_sha256']='0'*64
    else:t['row_count']+=1
    with pytest.raises(ValueError,match='CERTIFICATE'):CertificateStore(tmp_path).put(Certificate(canonical(p).encode()))
