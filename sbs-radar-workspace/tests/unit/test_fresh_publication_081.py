"""081 contract tests: no network, no current cloud evidence."""
import json
from types import SimpleNamespace
import pytest
from sbs.genie.fresh_publication_081 import SessionReader, Journal, SET_CACHE, publish_generation
from sbs.genie.publication import NAMED_IDENTITY_PROFILE

class Cursor:
    def __init__(self):
        self.calls=[]; self.query_id=None; self.description=[('id','string',None,None,None,None,True)]; self.rows=[]
    def execute(self,sql):
        self.calls.append(sql); self.query_id=f'query-{len(self.calls)}'; return self
    def fetchmany(self,size):
        rows=self.rows[:size];self.rows=self.rows[size:];return rows

def reader(tmp_path,cursor=None):
    c=cursor or Cursor();j=Journal(tmp_path/'081',plan_sha256='a'*64)
    r=SessionReader(c,j,allowed_sql=['SELECT pinned'],warehouse_id='warehouse',metadata_get=lambda _:None,governance_probe=lambda _:None,evidence_mode='fixture',identity_profile=NAMED_IDENTITY_PROFILE)
    return r,c,j

def test_session_set_precedes_exact_query_and_normalizes_typed_rows(tmp_path):
    r,c,j=reader(tmp_path);r.disable_cache();c.rows=[('one',)]
    cols,rows,proof=r._execute('SELECT pinned')
    assert c.calls==[SET_CACHE,'SELECT pinned'] and rows==[['one']]
    assert cols[0]['type_name']=='STRING' and proof['statement_id']=='query-2'
    assert j.count==2

def test_sql_not_admitted_without_set_or_outside_plan(tmp_path):
    r,c,j=reader(tmp_path)
    with pytest.raises(ValueError,match='CACHE'):r._execute('SELECT pinned')
    r.disable_cache()
    with pytest.raises(ValueError,match='SQL'):r._execute('SELECT arbitrary')
    assert c.calls==[SET_CACHE]

def test_lost_response_is_reserved_once_and_reopen_does_not_resend(tmp_path):
    class Lost(Cursor):
        def execute(self,sql):super().execute(sql);raise TimeoutError('do not expose')
    r,c,j=reader(tmp_path,Lost())
    with pytest.raises(ValueError,match='UNCONFIRMED'):r.disable_cache()
    assert j.count==1 and len(c.calls)==1
    j.close()
    with pytest.raises(ValueError,match='RECONCILIATION'):Journal(tmp_path/'081',plan_sha256='a'*64)

def test_rejects_oversized_rows_and_changed_query_id(tmp_path):
    r,c,j=reader(tmp_path);r.disable_cache();c.rows=[('x',)]*3;r.max_rows=2
    with pytest.raises(ValueError,match='ROW_CAP'):r._execute('SELECT pinned')

def test_journal_caps_and_pin_are_durable(tmp_path):
    j=Journal(tmp_path/'081',plan_sha256='a'*64)
    for i in range(33):j.reserve(str(i))
    with pytest.raises(ValueError,match='QUOTA'):j.reserve('extra')
    assert len(list((tmp_path/'081').glob('intent-*.json')))==33

def test_publication_does_not_advance_pointer_on_failed_readback(tmp_path):
    # Structural validation precedes IO: a malformed entry cannot publish anything.
    calls=[]
    with pytest.raises(ValueError):publish_generation(None,{},rotation={},read=lambda _:b'',put=lambda *a,**kw:calls.append(a),journal=Journal(tmp_path/'081',plan_sha256='a'*64))
    assert calls==[]


def test_eight_table_typed_connector_readback_and_independent_history(tmp_path):
    from test_genie_publication import inputs,plan,SDK,metadata,governance
    from sbs.genie.publication import _sqls,STRICT_IDENTITY_PROFILE
    from sbs.genie.publication_registry import HistoryRegistryBuilder,PublisherPolicy
    cfg,bundle=inputs();sdk=SDK(bundle);history={}
    class Typed(Cursor):
        def execute(self,sql):
            super().execute(sql)
            if sql==SET_CACHE:return self
            result=sdk.execute_statement(statement=sql,warehouse_id='warehouse')
            columns=result['manifest']['schema']['columns']
            self.description=[(c['name'],c['type_name'].lower(),None,None,None,None,None) for c in columns]
            self.rows=[]
            for row in result['result']['data_array']:
                self.rows.append(tuple((v=='true' if c['type_name']=='BOOLEAN' else int(v) if c['type_name']=='LONG' else v) for c,v in zip(columns,row)))
            history[self.query_id]=dict(query_id=self.query_id,query_text=sql,warehouse_id='warehouse',executed_as_user_id=42,status='FINISHED',is_final=True,statement_type='SELECT' if sql.startswith('SELECT') else 'OTHER',query_start_time_ms=10,execution_end_time_ms=20)
            return self
    p=plan();sql=[s for t in p.as_dict()['tables'] for s in _sqls(t)+[_sqls(t)[0]]]
    journal=Journal(tmp_path/'081',plan_sha256='a'*64);cursor=Typed()
    r=SessionReader(cursor,journal,allowed_sql=sql,warehouse_id='warehouse',metadata_get=metadata,governance_probe=governance,evidence_mode='fixture',identity_profile=STRICT_IDENTITY_PROFILE)
    r.disable_cache();cert=r.read(p)
    policy=PublisherPolicy(cert.sha256,cfg['mapping_sha256'],bundle['snapshot_hash'],bundle['config_hash'],'fixture','warehouse',42,1000,1000,'fixture')
    api=SimpleNamespace(list=lambda **kw:dict(res=[history[kw['filter_by'].statement_ids[0]]],has_next_page=False))
    builder=HistoryRegistryBuilder(api,policy,clock=lambda:100)
    assert len(builder.build(cert).as_dict()['history_records'])==32
    assert len(cert.as_dict()['tables'])==8 and journal.count==33 and len(cursor.calls)==33
    assert all(t['content_sha256']==__import__('sbs.genie',fromlist=['digest']).digest(bundle['tables'][t['logical_name']]) for t in cert.as_dict()['tables'])
    history['query-4']['cache_query_id']='old'
    with pytest.raises(ValueError,match='NOT_VERIFIED'):builder.build(cert)


def test_real_pinned_connector_transport_has_one_http_attempt_and_no_drain(monkeypatch):
    # Requires isolated official wheel; no sockets, credentials, or workspace IO.
    pytest.importorskip('databricks.sql.client')
    import databricks.sql
    assert databricks.sql.__version__=='4.2.6'
    from databricks.sql.auth import thrift_http_client
    from sbs.genie.connector_transport_081 import guarded_transport,Budget
    calls=[];events=[]
    class Response:
        status=200;reason='fixture';headers={}
        def read(self,n):return b'x'*n
        def close(self):events.append('close')
        def release_conn(self):events.append('release')
        def drain_conn(self):raise AssertionError('unbounded drain')
    class Pool:
        def request(self,*args,**kwargs):calls.append(kwargs);return Response()
    monkeypatch.setattr(thrift_http_client,'HTTPSConnectionPool',lambda *a,**kw:Pool())
    monkeypatch.setattr(thrift_http_client,'detect_and_parse_proxy',lambda *a,**kw:(None,None))
    budget=Budget(max_calls=1);cls=guarded_transport(thrift_http_client.THttpClient,budget,max_response_bytes=4)
    from databricks.sql.types import SSLOptions
    transport=cls(SimpleNamespace(add_headers=lambda _:None),'https://fixture.invalid/sql',ssl_options=SSLOptions())
    transport.setCustomHeaders({'User-Agent':'fixture'});transport.open();transport.write(b'fixture');transport.flush()
    assert calls[0]['retries'] is False and calls[0]['redirect'] is False
    assert transport.read(4)==b'xxxx'
    with pytest.raises(ValueError,match='CAP'):transport.read(1)
    with pytest.raises(ValueError,match='HTTP_CAP'):transport.flush()
    transport.close();assert events==['close','release'] and len(calls)==1


def test_status_create_only_cannot_undo_revocation(tmp_path):
    from sbs.genie.fresh_publication_081 import initialize_snapshot_status
    calls=[]
    def put(*a,**kw):calls.append(kw);raise FileExistsError()
    with pytest.raises(ValueError,match='REVOKED'):initialize_snapshot_status('a'*64,read=lambda _:b'{"status":"revoked"}',put=put,journal=Journal(tmp_path/'081',plan_sha256='a'*64))
    assert calls==[{'overwrite':False}]


@pytest.mark.parametrize('failure',['none','generation_readback','lost_pointer'])
def test_protected_generation_stage_readback_pointer_order(tmp_path,failure):
    # Historical captured data is transformed solely into a local protocol fixture.
    # This does not change the captured files or claim fresh cloud execution.
    from test_publication_rotation_078 import setup
    from sbs.genie import canonical,digest
    from sbs.genie.publication import Certificate
    from sbs.genie.publication_registry import RegistryEntry,PublisherPolicy,_entry
    from sbs.genie.publication_rotation import snapshot_binding,invariant_policy
    reader0,_,now,old,ap,_=setup();p=old.as_dict();c=p['certificate']
    c.pop('replay_evidence');c['identity_profile']=NAMED_IDENTITY_PROFILE
    cert=Certificate(canonical(c).encode());pol=PublisherPolicy(**{**p['policy'],'certificate_sha256':cert.sha256,'max_readback_age_ms':300000})
    histories=p['history_records']
    for row in histories:row.update(query_start_time_ms=now[0]-20,execution_end_time_ms=now[0]-10)
    entry=RegistryEntry(canonical(_entry(cert,pol,histories,now[0],NAMED_IDENTITY_PROFILE)).encode())
    binding=snapshot_binding(cert,pol.mapping_sha256)
    rotation=dict(snapshot_binding_sha256=binding,policy_invariants_sha256=digest(invariant_policy(ap)),publisher_identity=pol.publisher_identity,publisher_executor_id=pol.executor_id,warehouse_id=pol.warehouse_id)
    data={binding+'.status.json':canonical(dict(binding_sha256=binding,status='active')).encode()};events=[]
    def put(name,raw,*,overwrite):
        events.append(('put',name,overwrite));data[name]=raw
        if name=='current.json' and failure=='lost_pointer':raise TimeoutError()
    def read(name):
        events.append(('read',name))
        if failure=='generation_readback' and name in data and not name.endswith('.status.json'):return b'corrupt'
        return data[name]
    kwargs=dict(rotation=rotation,read=read,put=put,journal=Journal(tmp_path/'081',plan_sha256='a'*64),clock=lambda:now[0])
    if failure=='generation_readback':
        with pytest.raises(ValueError,match='READBACK'):publish_generation(entry,ap,**kwargs)
        assert 'current.json' not in data
    else:
        pin=publish_generation(entry,ap,**kwargs)
        assert json.loads(data['current.json'])['generation_sha256']==pin
        puts=[x for x in events if x[0]=='put'];assert [p[2] for p in puts]==[False,True]
        assert events.index(('read',pin+'.json'))<events.index(('put','current.json',True))


@pytest.mark.parametrize('field,value',[('owner','other@example.invalid'),('executor_id',1),('warehouse_id','different'),('plan_sha256','0'*64),('host','https://other.invalid')])
def test_preflight_validates_effective_phase_writer_before_cloud(monkeypatch,field,value):
    import importlib.util
    from pathlib import Path
    root=Path(__file__).resolve().parents[2]
    spec=importlib.util.spec_from_file_location('fresh081_contract',root/'runs/sk06-sk11-fresh-081.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    original=module.read
    def altered(root,path):
        data=original(root,path)
        if path=='deployment/phase-s-017.json':data['writer'][field]=value
        return data
    monkeypatch.setattr(module,'read',altered)
    with pytest.raises(ValueError,match='FRESH_'):module.prepare(root)


def test_global_observed_table_identity_drift_blocks_finalization():
    from sbs.genie.fresh_publication_081 import require_governance_stable
    before=dict(table_metadata_sha256='a'*64,source_tables=['pinned'])
    require_governance_stable(before,dict(before))
    for after in [dict(before,table_metadata_sha256='b'*64),dict(before,source_tables=['other']),{}]:
        with pytest.raises(ValueError,match='GLOBAL_TABLE'):require_governance_stable(before,after)
