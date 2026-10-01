"""SK06 synthetic fixtures; no live Genie verification."""
import importlib
import importlib.util
import json
import pytest


def api():
    assert importlib.util.find_spec('sbs.genie'), 'SK06 component missing'
    return importlib.import_module('sbs.genie')


def source():
    return dict(document_id='fixture', version_id='a'*64, sha256='a'*64,
                family='cybersecurity', source_kind='normative', synthetic=True,
                url='https://example.org/a.pdf', captured_at='2026-01-01T00:00:00Z',
                published_on=None, effective_on=None,
                date_unknown_reasons={'published_on':'unknown','effective_on':'unknown'})


def config():
    return dict(namespace='sbs_radar', warehouse_id='warehouse', space_id='own-space',
                snapshot='snapshot', max_polls=3, poll_seconds=0)


def grant():
    return dict(warehouse_id='warehouse', state='RUNNING', warehouse_type='PRO',
                can_use=True, tables_read=True, genie_access=True,
                read_only_backend=True, scope_verified=True, snapshot='snapshot')


class SDK:
    def __init__(self, status='COMPLETED', sql='SUCCEEDED', rows=None):
        self.status,self.sql,self.rows=status,sql,[] if rows is None else rows
        self.calls=[]
    def start_conversation(self, **kw):
        self.calls.append(('start',kw)); return {'conversation_id':'c','message_id':'m'}
    def create_message(self, **kw):
        self.calls.append(('followup',kw)); return {'conversation_id':'c','message_id':'m2'}
    def get_message(self, **kw):
        self.calls.append(('get',kw)); return dict(kw,status=self.status,attachments=[{'query':{'query':'SELECT 1'}}])
    def get_message_query_result(self, **kw):
        return {'statement_response':{'statement_id':'q','status':{'state':self.sql},
                'manifest':{'total_row_count':len(self.rows)},'result':{'data_array':self.rows}}}


def test_curate_deterministic_and_ai_is_never_human(tmp_path):
    m=api(); review={'run_id':'r','findings':[], 'ai_reference':{'human_gold':False}}
    a=m.curate([source()], [], [], review, [], config(), mode='fixture')
    assert a == m.curate([source()], [], [], review, [], config(), mode='fixture')
    assert a['tables']['documents'][0]['published_on'] is None
    assert a['tables']['reviews'][0]['human_approved'] is False
    m.export_bundle(a,tmp_path)
    assert len(list(tmp_path.glob('*.jsonl'))) >= 7
    assert len(m.example_queries()) == len(m.BENCHMARKS) == 5
    assert len(m.verify_examples(a)) == 5


def test_corpus_and_references_rejected():
    m=api()
    with pytest.raises(ValueError):m.curate([source()],[],[],{},[],config(),mode='real')
    pair={'pair_id':'p','family':'cybersecurity','before':{'document_id':'fixture','version_id':'x'},'after':{'document_id':'fixture','version_id':'y'}}
    with pytest.raises(ValueError):m.curate([source()],[pair],[],{},[],config(),mode='fixture')


@pytest.mark.parametrize('field,value', [('warehouse_id',''),('state','STOPPED'),('can_use',None),('tables_read',False),('read_only_backend',False),('scope_verified',False),('snapshot','stale')])
def test_preflight_blocks_without_remote_calls(field,value):
    m=api(); c=config(); g=grant()
    (c if field=='warehouse_id' else g)[field]=value
    sdk=SDK(); r=m.GenieAdapter(sdk,c,lambda:g).ask('count')
    assert r['status'] in ('blocked','denied','conflict') and not sdk.calls


@pytest.mark.parametrize('message,sql,expected', [('COMPLETED','SUCCEEDED','empty'),('COMPLETED','FAILED','error'),('FAILED','SUCCEEDED','error'),('CANCELLED','SUCCEEDED','cancelled'),('EXECUTING_QUERY','SUCCEEDED','timeout')])
def test_runtime_states(message,sql,expected):
    m=api(); sdk=SDK(message,sql)
    r=m.GenieAdapter(sdk,config(),grant).ask('count')
    assert r['status']==expected and r['conversation_id']=='c'
    assert len([x for x in sdk.calls if x[0]=='get'])<=3
    if expected=='empty':assert r['query_id']=='q' and r['coverage']=='unverified'


def test_followup_retains_ids_and_snapshot():
    m=api(); sdk=SDK(rows=[['2']]); adapter=m.GenieAdapter(sdk,config(),grant)
    r=adapter.ask('count'); f=adapter.ask('same family',conversation_id=r['conversation_id'])
    assert f['status']=='completed' and f['message_id']=='m2' and f['snapshot']=='snapshot'
    assert sdk.calls[-2][0]=='followup'


def test_no_arbitrary_sql_route_and_parameter_binding():
    m=api()
    with pytest.raises(ValueError):m.allowed_query('DROP TABLE documents',{})
    sql,params=m.allowed_query('documents_by_family',{'family':"x'; DROP TABLE documents; --"})
    assert 'DROP' not in sql and ':family' in sql and 'DROP' in params['family']


def test_denied_exceptions_sanitized():
    m=api(); sdk=SDK()
    def denied(**kw):raise PermissionError('secret-token')
    sdk.start_conversation=denied
    r=m.GenieAdapter(sdk,config(),grant).ask('count')
    assert r['status']=='denied' and 'secret' not in json.dumps(r)


def test_real_preparation_checks_inputs_and_retains_six_sources():
    from pathlib import Path
    m=api()
    assert hasattr(m,'prepare_project'), 'real preparation missing'
    root=Path(__file__).resolve().parents[2]
    bundle,c=m.prepare_project(root)
    assert bundle['mode']=='real' and len(bundle['tables']['documents'])==6
    assert len(bundle['tables']['pairs'])==2 and len(bundle['tables']['changes'])==2
    assert {r['family'] for r in bundle['tables']['documents']}=={'market_conduct','cybersecurity'}
    assert c['warehouse_id'] is None and c['space_id'] is None
    assert all(r['synthetic'] is False for r in bundle['tables']['documents'])
    assert all(r['synthetic'] is True for r in bundle['tables']['processes'])
    assert all(r['human_approved'] is False for r in bundle['tables']['reviews'])


def test_partial_result_is_not_empty():
    m=api();sdk=SDK()
    sdk.get_message_query_result=lambda **kw:{'statement_response':{'statement_id':'q','status':{'state':'SUCCEEDED'},'manifest':{'total_row_count':10},'result':{}}}
    assert m.GenieAdapter(sdk,config(),grant).ask('count')['status']=='partial'


def test_unknown_followup_not_sent():
    m=api();sdk=SDK()
    assert m.GenieAdapter(sdk,config(),grant).ask('next',conversation_id='other')['status']=='conflict'
    assert sdk.calls==[]

# R1 regression: trusted context + executed SQL + rows, not echoed context/hash.
def scoped_fixture():
    from copy import deepcopy
    m=api(); assert hasattr(m,'ScopedCatalog'), 'scoped result verification missing'
    docs=[];pairs=[];provisions=[];contexts=[]
    for family,doc,letters in [('cybersecurity','cyber','ab'),('market_conduct','market','cd')]:
        for v in letters:
            d=source();d.update(document_id=doc,family=family,version_id=v*64,sha256=v*64);docs.append(d)
            provisions.append(dict(document_id=doc,version_id=v*64,provision_id='art20.3',citation_id=doc+v,page=1,start=0,end=4,text='test',source_kind='normative',synthetic=True))
        pair=dict(pair_id='pair-'+doc,family=family,before=dict(document_id=doc,version_id=letters[0]*64),after=dict(document_id=doc,version_id=letters[1]*64));pairs.append(pair)
        contexts.append(dict(context_id='ctx-'+doc,family=family,pair=pair,target_date=None,selected_provision_id='art20.3'))
    b=m.curate(docs,pairs,[],{},[],config(),mode='fixture',provisions=provisions)
    catalog=m.ScopedCatalog(b,contexts,table_prefix='test_catalog.sbs_radar')
    plan=catalog.references(contexts[0])['provision_count']
    sdk=SDK(rows=[['2']])
    sdk.get_message=lambda **kw:dict(kw,status='COMPLETED',attachments=[{'query':{'query':plan['sql']}}])
    sdk.get_message_query_result=lambda **kw:{'statement_response':{'statement_id':'q','status':{'state':'SUCCEEDED'},'manifest':{'total_row_count':1,'schema':{'columns':[{'name':'provision_row_count','type_name':'LONG','position':0}]}},'result':{'data_array':sdk.rows}}}
    receipt=dict(query_id='q',statement=plan['sql'],parameters=deepcopy(plan['parameters']),source_tables=plan['source_tables'],snapshot=b['snapshot_hash'],state='SUCCEEDED')
    c=config();c['snapshot']=b['snapshot_hash']
    def permissions():return dict(grant(),snapshot=b['snapshot_hash'])
    adapter=m.GenieAdapter(sdk,c,permissions,scope_catalog=catalog,execution_probe=lambda q:deepcopy(receipt))
    return adapter,contexts,sdk,receipt,catalog


def test_scoped_valid_aggregate_has_independently_verified_context():
    adapter,contexts,sdk,receipt,catalog=scoped_fixture()
    out=adapter.ask_scoped('¿Cuántas filas documentales de esa disposición?',context=contexts[0])
    assert out['status']=='completed' and out['scope_verified'] is True
    assert out['context']==contexts[0] and out['rows']==[['2']]
    assert out['columns']==['provision_row_count'] and out['query_id']=='q'
    assert out['kind']=='structured_query_result' and 'evidence' not in out
    assert out['source_tables']==['test_catalog.sbs_radar.provisions']


def test_scoped_wrong_family_same_snapshot_rejected():
    adapter,contexts,sdk,receipt,catalog=scoped_fixture()
    other=catalog.references(contexts[1])['provision_count']
    receipt.update(statement=other['sql'],parameters=other['parameters'])
    out=adapter.ask_scoped('count',context=contexts[0])
    assert out['status']=='conflict' and out['scope_verified'] is False and out['rows']==[]


def test_scoped_global_aggregate_without_where_rejected():
    adapter,contexts,sdk,receipt,catalog=scoped_fixture()
    receipt['statement']='SELECT COUNT(*) AS provision_row_count FROM test_catalog.sbs_radar.provisions'
    receipt['parameters']={}
    assert adapter.ask_scoped('count',context=contexts[0])['status']=='conflict'


@pytest.mark.parametrize('field,value',[('statement',None),('source_tables',[]),('query_id','unrelated'),('parameters',{}),('snapshot','old'),('state','FAILED')])
def test_scoped_missing_or_wrong_execution_provenance_rejected(field,value):
    adapter,contexts,sdk,receipt,catalog=scoped_fixture();receipt[field]=value
    assert adapter.ask_scoped('count',context=contexts[0])['status']=='conflict'


@pytest.mark.parametrize('rows',[None,{},[['bad']],[['9']],[['2','cybersecurity']]])
def test_scoped_malformed_or_false_aggregate_rejected(rows):
    adapter,contexts,sdk,receipt,catalog=scoped_fixture();sdk.rows=rows
    out=adapter.ask_scoped('count',context=contexts[0])
    assert out['status'] in ('conflict','error') and out['scope_verified'] is False


def test_scoped_context_not_in_trusted_registry_is_rejected_before_query():
    adapter,contexts,sdk,receipt,catalog=scoped_fixture()
    contexts[0]['selected_provision_id']='injected'
    assert adapter.ask_scoped('count',context=contexts[0])['status']=='conflict'
    assert not sdk.calls


def test_scoped_denied_permissions_still_block():
    adapter,contexts,sdk,receipt,catalog=scoped_fixture()
    adapter.probe=lambda:dict(grant(),snapshot=adapter.config['snapshot'],can_use=False)
    assert adapter.ask_scoped('count',context=contexts[0])['status']=='denied'
    assert not sdk.calls


def test_scoped_reference_parameters_bind_all_context_fields():
    adapter,contexts,sdk,receipt,catalog=scoped_fixture()
    params=receipt['parameters'];ctx=contexts[0]
    assert params['family']==ctx['family'] and params['provision_id']==ctx['selected_provision_id']
    for side in ('before','after'):
        for k in ('document_id','version_id'):assert params[side+'_'+k]==ctx['pair'][side][k]
    assert params['corpus_hash']==catalog.corpus_hash


def test_scoped_missing_dependencies_fails_closed():
    m=api();assert hasattr(m.GenieAdapter,'ask_scoped'), 'scoped API missing'
    assert m.GenieAdapter(SDK(),config(),grant).ask_scoped('count',context={})['status']=='conflict'


def test_scoped_listing_rejects_other_family_row_even_same_corpus_hash():
    adapter,contexts,sdk,receipt,catalog=scoped_fixture()
    plan=catalog.references(contexts[0])['provision_list']
    receipt.update(statement=plan['sql'],parameters=plan['parameters'])
    rows=catalog.references(contexts[1])['provision_list']['rows']
    def returned(**kw):
        return {'statement_response':{'statement_id':'q','status':{'state':'SUCCEEDED'},'manifest':{'total_row_count':len(rows),'schema':{'columns':[{'name':c} for c in plan['columns']]}},'result':{'data_array':rows}}}
    sdk.get_message_query_result=returned
    assert adapter.ask_scoped('list',context=contexts[0])['status']=='conflict'
    rows[:]=plan['rows']
    out=adapter.ask_scoped('list',context=contexts[0])
    assert out['status']=='completed' and out['scope_verified'] is True
    assert out['lineage']['pair']==contexts[0]['pair']


def test_scoped_schema_absence_is_conflict():
    adapter,contexts,sdk,receipt,catalog=scoped_fixture()
    sdk.get_message_query_result=lambda **kw:{'statement_response':{'statement_id':'q','status':{'state':'SUCCEEDED'},'manifest':{'total_row_count':1},'result':{'data_array':[['2']]}}}
    assert adapter.ask_scoped('count',context=contexts[0])['status']=='conflict'


def test_scoped_registry_is_defensive_copy():
    adapter,contexts,sdk,receipt,catalog=scoped_fixture()
    original=json.loads(json.dumps(contexts[0]))
    contexts[0]['family']='market_conduct'
    assert adapter.ask_scoped('count',context=original)['status']=='completed'


def test_scoped_no_provenance_probe_and_malformed_context_rejected():
    adapter,contexts,sdk,receipt,catalog=scoped_fixture()
    adapter.execution_probe=None
    assert adapter.ask_scoped('count',context=contexts[0])['status']=='conflict'
    adapter.execution_probe=lambda _:receipt
    for ctx in (None,[],{'family':'cybersecurity'}):
        assert adapter.ask_scoped('count',context=ctx)['status']=='conflict'
    assert sdk.calls==[]


def test_scoped_reference_sql_executes_family_pair_provision_predicates_locally():
    import sqlite3
    adapter,contexts,sdk,receipt,catalog=scoped_fixture()
    db=sqlite3.connect(':memory:')
    db.create_function('get_json_object',2,lambda payload,path:json.loads(payload).get(path[2:]))
    db.execute('CREATE TABLE provisions(id TEXT, family TEXT, corpus_hash TEXT, payload_json TEXT)')
    for ctx in contexts:
        plan=catalog.references(ctx)['provision_list']
        db.executemany('INSERT INTO provisions VALUES(?,?,?,?)',plan['rows'])
    for ctx in contexts:
        for plan in catalog.references(ctx).values():
            sql=plan['sql'].replace('test_catalog.sbs_radar.provisions','provisions')
            result=[[str(v) for v in row] for row in db.execute(sql,plan['parameters'])]
            assert result==plan['rows']
    db.close()


def test_prepare_project_relocated_never_reads_either_old_root(tmp_path,monkeypatch):
    import json,shutil
    from pathlib import Path
    from sbs.paths import project_path,HISTORICAL_ROOT
    from sbs.genie import prepare_project
    import sbs.contracts
    root=Path(__file__).resolve().parents[2];target=tmp_path/'snapshot';target.mkdir()
    paths=['runs/astra-normative-review-003.json','runs/sk05-workspace-preflight.json']
    for name in ('runs/sk02-repository-capture.json','runs/sk02-amendments-capture.json'):
        paths.append(name);capture=json.loads((root/name).read_text());paths.append(capture['manifest'])
        paths.extend(e[k] for e in capture['sources'] for k in ('original_path','result_path','rawtext_path'))
    for value in paths:
        source=project_path(root,value);dest=target/source.relative_to(root);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
    shutil.copytree(root/'contracts',target/'contracts');monkeypatch.setattr(sbs.contracts,'_CONTRACT_ROOT',target/'contracts')
    original_open=Path.open
    def guard(path,mode='r',*args,**kw):
        if 'r' in mode and any(path.resolve().is_relative_to(p) for p in (root,HISTORICAL_ROOT)):
            raise AssertionError('OLD_ROOT_READ_FORBIDDEN')
        return original_open(path,mode,*args,**kw)
    monkeypatch.setattr(Path,'open',guard)
    bundle,_=prepare_project(target)
    assert len(bundle['tables']['documents'])==6
    assert all(not Path(f['path']).is_absolute() for f in bundle['input_files'])


@pytest.mark.parametrize('escape',['unknown_absolute','historical_parent','historical_prefix','relative_parent','symlink'])
def test_prepare_project_relocation_rejects_escape_before_file_read(tmp_path,monkeypatch,escape):
    from pathlib import Path
    import json
    from sbs.paths import HISTORICAL_ROOT
    from sbs.genie import prepare_project
    target=tmp_path/'snapshot';(target/'runs').mkdir(parents=True)
    outside=tmp_path/'outside.json';outside.write_text('{}')
    candidates={'unknown_absolute':str(outside),'historical_parent':str(HISTORICAL_ROOT/'..'/'outside.json'),
                'historical_prefix':str(HISTORICAL_ROOT)+'-other/data.json','relative_parent':'../outside.json','symlink':'link.json'}
    (target/'link.json').symlink_to(outside)
    (target/'runs/sk02-repository-capture.json').write_text(json.dumps({'manifest':candidates[escape],'manifest_sha256':'0'*64,'sources':[]}))
    original_open=Path.open
    def guard(path,mode='r',*a,**kw):
        if 'r' in mode and not path.resolve().is_relative_to(target):raise AssertionError('OUTSIDE_READ_FORBIDDEN')
        return original_open(path,mode,*a,**kw)
    monkeypatch.setattr(Path,'open',guard)
    with pytest.raises(ValueError):prepare_project(target)
