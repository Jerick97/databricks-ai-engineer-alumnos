from pathlib import Path
import pytest
from sbs.genie.publication_writer import load_write_plan

ROOT=Path(__file__).resolve().parents[2]

def test_sealed_export_plan_has_exact_eight_tables_and_no_schema_mutation():
    plan=load_write_plan(ROOT,publication_id='pilot002-016')
    p=plan.as_dict()
    assert len(p['tables'])==8
    assert sum(t['row_count'] for t in p['tables'])==164
    assert all(t['create_sql'].startswith('CREATE TABLE ') for t in p['tables'])
    assert all('IF NOT EXISTS' not in t['create_sql'] for t in p['tables'])
    assert all(t['insert_sql'].startswith('INSERT INTO ') for t in p['tables'])
    assert 'CREATE SCHEMA' not in str(p)

from types import SimpleNamespace
from copy import deepcopy
import json
from sbs.genie import TABLES,COLUMNS,canonical
from sbs.genie.publication_writer import WriterConfig,PublicationWriter,preflight,sdk_writer,WritePlan
from sbs.genie.publication_registry import RegistryLookup
from test_genie_publication import response

@pytest.fixture(scope='module')
def sealed():return load_write_plan(ROOT,publication_id='pilot002-016')

def config(plan,**kw):
    args=dict(host='https://fixture.cloud.databricks.com',schema_name='neptuno_manuel_arguelles.sbs_radar',schema_id='schema-fixture',warehouse_id='warehouse-fixture',executor_id=42,owner='owner@example.test',plan_sha256=plan.sha256,policy=dict(trusted_administrators='fixture trusted administrators',exclusive_maintenance='fixture sole publisher throughout readback',retention='fixture versions retained',no_inherited_abac='fixture declared no inherited ABAC',issued_at_ms=1,expires_at_ms=900000),evidence_mode='fixture')
    return WriterConfig(**(args|kw))

class Missing(ValueError):error_code='TABLE_DOES_NOT_EXIST'
class FixtureCloud:
    """Adapter fixture executes plan effects in memory; never cloud proof."""
    def __init__(self,plan,cfg):
        self.plan=plan.as_dict();self.cfg=cfg;self.tables_data={};self.calls=[];self.records={};self.versions={};self.loss=None;self.corrupt=False;self.history_bad=False;self.state='RUNNING';self.owner=cfg.owner
        self.statement_execution=self;self.query_history=self
        self.tables=SimpleNamespace(get=self.gettable)
        self.schemas=SimpleNamespace(get=lambda n:dict(full_name=n,schema_id=cfg.schema_id,owner=self.owner))
        self.catalogs=SimpleNamespace(get=lambda n:dict(name=n,owner=self.owner))
        self.permissions=SimpleNamespace(get=lambda *a:dict(object_id='/sql/warehouses/'+cfg.warehouse_id,access_control_list=[dict(user_name=cfg.owner,all_permissions=[dict(permission_level='CAN_USE')])]))
        self.current_user=SimpleNamespace(me=lambda:dict(id=str(cfg.executor_id),user_name=cfg.owner))
        self.warehouses=SimpleNamespace(get=lambda n:dict(id=n,state=self.state))
    def gettable(self,name):
        t=name.split('.')[-1]
        if t not in self.tables_data:raise Missing()
        return dict(full_name=name,owner=self.cfg.owner,table_id='uc-'+t,metastore_id='meta-fixture',storage_location='s3://fixture/'+t,data_source_format='DELTA',table_type='MANAGED',properties={'sbs.publication_id':self.plan['publication_id'],'sbs.snapshot':self.plan['snapshot']},columns=[dict(name=c,type_name='BOOLEAN' if c in ('synthetic','human_approved') else 'STRING') for c in COLUMNS])
    def execute_statement(self,statement,warehouse_id,**kw):
        assert warehouse_id==self.cfg.warehouse_id
        self.calls.append(statement);sid='fixture-'+str(len(self.calls));t=next(t for t in TABLES if '`'+t+'`' in statement)
        rec=dict(query_id=sid,query_text=statement,warehouse_id=warehouse_id,executed_as_user_id=42,status='FINISHED',is_final=True,query_start_time_ms=100,execution_end_time_ms=200,statement_type='SELECT' if statement.startswith('SELECT') else 'OTHER')
        self.records[sid]=rec
        if statement.startswith('CREATE TABLE'):
            if self.loss=='before_create':raise ConnectionError('fixture sensitive error')
            assert t not in self.tables_data
            self.tables_data[t]=[];self.versions[t]=5
            if self.loss=='after_create':self.loss=None;raise ConnectionError('fixture sensitive error')
            return dict(statement_id=sid,status=dict(state='SUCCEEDED'))
        if statement.startswith('INSERT'):
            if self.loss=='before_insert':raise ConnectionError('fixture sensitive error')
            target=next(r for r in self.plan['tables'] if r['logical_name']==t)
            assert [p.as_dict() for p in kw['parameters']]==target['parameters']
            self.tables_data[t].extend(deepcopy(target['rows']));self.versions[t]=9
            if self.corrupt:self.tables_data[t][0]['payload_json']='corrupt'
            if self.loss=='after_insert':self.loss=None;raise ConnectionError('fixture sensitive error')
            return dict(statement_id=sid,status=dict(state='SUCCEEDED'))
        if statement.startswith('DESCRIBE DETAIL'):return response(['format','id','location'],['STRING']*3,[['delta','delta-'+t,'s3://fixture/'+t]],sid)
        if statement.startswith('DESCRIBE HISTORY'):return response(['version','userId'],['LONG','STRING'],[[self.versions[t],str(42)]],sid)
        assert 'VERSION AS OF '+str(self.versions[t]) in statement
        return response(COLUMNS,['BOOLEAN' if c in ('synthetic','human_approved') else 'STRING' for c in COLUMNS],[[r[c] for c in COLUMNS] for r in self.tables_data[t]],sid)
    def list(self,filter_by,**kw):
        r=deepcopy(self.records[filter_by.statement_ids[0]])
        if self.history_bad:r['query_text']='SELECT 1'
        return dict(res=[r],has_next_page=False)

def run(plan,tmp,cloud=None,cfg=None):
    cfg=cfg or config(plan);cloud=cloud or FixtureCloud(plan,cfg)
    with PublicationWriter(plan,cfg,cloud,tmp/'journal',clock=lambda:1000) as w:
        out=w.publish(certificate_directory=tmp/'cert',registry_directory=tmp/'registry')
    return out,cloud

def test_all_real_export_rows_parameterized_and_observed_versions(sealed,tmp_path):
    out,cloud=run(sealed,tmp_path)
    assert out['status']=='published' and out['evidence_mode']=='fixture'
    assert set(out['versions'].values())=={9} # never assumed version zero/one
    assert len(cloud.calls)==80
    assert sum(s.startswith(('CREATE','INSERT')) for s in cloud.calls)==16
    assert len(cloud.tables_data)==8
    assert sum(map(len,cloud.tables_data.values()))==164
    assert RegistryLookup(tmp_path/'registry')(certificate_sha256=out['certificate_sha256'])['status']=='active'
    assert not out['genie_space_ready'] and not out['reader_governance_verified']
    assert all(not any(x in s for x in ('DROP ','OVERWRITE','CREATE SCHEMA','GRANT ')) for s in cloud.calls)

@pytest.mark.parametrize('loss',['after_create','after_insert'])
def test_lost_committed_response_reconciles_without_second_post(sealed,tmp_path,loss):
    cfg=config(sealed);cloud=FixtureCloud(sealed,cfg);cloud.loss=loss
    out,_=run(sealed,tmp_path,cloud,cfg)
    assert out['status']=='published'
    assert sum(s.startswith(('CREATE','INSERT')) for s in cloud.calls)==16

@pytest.mark.parametrize('loss',['before_create','before_insert'])
def test_unknown_effect_remains_pending_and_never_resubmits(sealed,tmp_path,loss):
    cfg=config(sealed);cloud=FixtureCloud(sealed,cfg);cloud.loss=loss
    with pytest.raises(ValueError,match='MUTATION_UNCONFIRMED'):run(sealed,tmp_path,cloud,cfg)
    prior=sum(s.startswith(('CREATE','INSERT')) for s in cloud.calls)
    cloud.loss=None
    with pytest.raises(ValueError,match='MUTATION_UNCONFIRMED'):run(sealed,tmp_path,cloud,cfg)
    assert sum(s.startswith(('CREATE','INSERT')) for s in cloud.calls)==prior
    assert not (tmp_path/'registry').exists()

def test_unrelated_existing_table_never_adopted(sealed,tmp_path):
    cfg=config(sealed);cloud=FixtureCloud(sealed,cfg);cloud.tables_data['reviews']=[]
    with pytest.raises(ValueError,match='EXISTING_TABLE_REFUSED'):run(sealed,tmp_path,cloud,cfg)
    assert not cloud.calls

@pytest.mark.parametrize('bad',['stopped','owner','expired','acl','identity'])
def test_observed_preconditions_fail_before_any_sql(sealed,tmp_path,bad):
    cfg=config(sealed);cloud=FixtureCloud(sealed,cfg)
    if bad=='stopped':cloud.state='STOPPED'
    if bad=='owner':cloud.owner='another'
    if bad=='expired':cfg=config(sealed,policy=cfg.policy|{'expires_at_ms':999})
    if bad=='acl':cloud.permissions.get=lambda *a:dict(access_control_list=[])
    if bad=='identity':cloud.current_user.me=lambda:dict(id=True,user_name=cfg.owner)
    with pytest.raises(ValueError):run(sealed,tmp_path,cloud,cfg)
    assert not cloud.calls

@pytest.mark.parametrize('bad',['content','history'])
def test_invalid_data_or_independent_history_never_certified(sealed,tmp_path,bad):
    cfg=config(sealed);cloud=FixtureCloud(sealed,cfg)
    if bad=='content':cloud.corrupt=True
    else:cloud.history_bad=True
    with pytest.raises(ValueError):run(sealed,tmp_path,cloud,cfg)
    assert not (tmp_path/'registry').exists()

def test_replay_reads_without_mutating_again(sealed,tmp_path):
    out,cloud=run(sealed,tmp_path);out2,_=run(sealed,tmp_path,cloud)
    assert out2['versions']==out['versions']
    assert sum(s.startswith(('CREATE','INSERT')) for s in cloud.calls)==16


def test_tampered_sql_even_with_new_pin_rejected_without_remote(sealed,tmp_path):
    p=sealed.as_dict();p['tables'][0]['create_sql']='DROP TABLE dangerous';bad=WritePlan(canonical(p).encode());cfg=config(bad);cloud=FixtureCloud(bad,cfg)
    with pytest.raises(ValueError,match='WRITE_SQL_INVALID'):PublicationWriter(bad,cfg,cloud,tmp_path/'journal')
    assert not cloud.calls

def test_preflight_and_sdk_factory_no_network(sealed,tmp_path):
    assert preflight(sealed)['status']=='pending_configuration'
    cfg=config(sealed,evidence_mode='real')
    with sdk_writer(sealed,cfg,tmp_path/'journal',sdk_config=SimpleNamespace(host=cfg.host,authenticate=lambda:(_ for _ in ()).throw(AssertionError('no auth in constructor')))) as writer:
        assert writer.reader.statements==0
    assert preflight(sealed,cfg)['total_sql_success_path']==80

def test_replaced_identity_on_resume_is_rejected_without_insert(sealed,tmp_path):
    cfg=config(sealed);cloud=FixtureCloud(sealed,cfg);cloud.loss='before_insert'
    with pytest.raises(ValueError):run(sealed,tmp_path,cloud,cfg)
    old=cloud.gettable
    cloud.tables.get=lambda n:old(n)|{'table_id':'replaced'}
    with pytest.raises(ValueError,match='TABLE_IDENTITY_CHANGED'):run(sealed,tmp_path,cloud,cfg)
    assert sum(s.startswith('INSERT') for s in cloud.calls)==1

def test_stopped_after_first_mutation_blocks_next_sql(sealed,tmp_path):
    cfg=config(sealed);cloud=FixtureCloud(sealed,cfg);original=cloud.execute_statement
    def execute(**kw):
        r=original(**kw);cloud.state='STOPPED';return r
    cloud.execute_statement=execute
    with pytest.raises(ValueError,match='WAREHOUSE_NOT_RUNNING'):run(sealed,tmp_path,cloud,cfg)
    assert len(cloud.calls)==1

def test_generated_sql_parses_databricks_and_values_are_not_embedded(sealed):
    import sqlglot
    for t in sealed.as_dict()['tables']:
        assert len(sqlglot.parse(t['create_sql'],read='databricks'))==1
        assert len(sqlglot.parse(t['insert_sql'],read='databricks'))==1
        assert 'payload_json' in t['insert_sql'] and t['parameters']
        for p in t['parameters']:
            if p['name'].endswith('_payload_json'):assert p['value'] not in t['insert_sql']

def test_journal_symlink_refused(sealed,tmp_path):
    cfg=config(sealed);cloud=FixtureCloud(sealed,cfg)
    other=tmp_path/'other';other.mkdir();(tmp_path/'journal').symlink_to(other,target_is_directory=True)
    with pytest.raises(OSError):run(sealed,tmp_path,cloud,cfg)
    assert not cloud.calls

def test_generated_sdk_services_over_single_attempt_http_fixture(sealed,tmp_path,monkeypatch):
    """Real SDK serialization over fixture HTTP; this is not remote evidence."""
    import requests
    from io import BytesIO
    cfg=config(sealed,evidence_mode='real');cloud=FixtureCloud(sealed,cfg)
    paths=[]
    class Raw(BytesIO):
        def read(self,amt=None,decode_content=None):return super().read(amt)
    class Wire:
        status_code=200
        headers={}
        def __init__(self,p):self.raw=Raw(json.dumps(p).encode())
        def close(self):pass
    class Session:
        adapters={}
        def mount(self,*args):pass
        def request(self,method,url,**kw):
            from urllib.parse import unquote
            from databricks.sdk.service.sql import StatementParameterListItem
            path=unquote(url.split('.com',1)[1]);paths.append((method,path))
            if method=='POST':
                b=kw['json'];args={k:v for k,v in b.items() if k not in ('statement','warehouse_id')}
                if 'parameters' in args:args['parameters']=[StatementParameterListItem(**p) for p in args['parameters']]
                return Wire(cloud.execute_statement(b['statement'],b['warehouse_id'],**args))
            if path.endswith('/Me'):p={'id':'42','userName':cfg.owner}
            elif '/schemas/' in path:p=cloud.schemas.get(path.rsplit('/',1)[1])
            elif '/catalogs/' in path:p=cloud.catalogs.get(path.rsplit('/',1)[1])
            elif '/permissions/' in path:p=cloud.permissions.get()
            elif '/warehouses/' in path:p=cloud.warehouses.get(path.rsplit('/',1)[1])
            elif '/tables/' in path:
                try:p=cloud.tables.get(path.rsplit('/',1)[1])
                except Missing:
                    r=Wire(dict(error_code='TABLE_DOES_NOT_EXIST',message='fixture'));r.status_code=404;return r
            elif path.endswith('/history/queries'):
                assert kw['params']['filter_by.warehouse_ids']==[cfg.warehouse_id]
                p=dict(res=[cloud.records[kw['params']['filter_by.statement_ids'][0]]],has_next_page=False)
            else:raise AssertionError(path)
            return Wire(p)
    monkeypatch.setattr(requests,'Session',Session)
    with sdk_writer(sealed,cfg,tmp_path/'journal',sdk_config=SimpleNamespace(host=cfg.host,workspace_id=None,authenticate=lambda:dict(Authorization='fixture-not-secret'))) as w:
        w.clock=lambda:1000
        out=w.publish(certificate_directory=tmp_path/'cert',registry_directory=tmp_path/'registry')
    assert out['status']=='published'
    # mode is the factory capability label, not proof supplied by this test.
    assert len(paths)<=512 and sum(m=='POST' for m,p in paths)==80
    assert sum(p.endswith('/history/queries') for m,p in paths)==32
