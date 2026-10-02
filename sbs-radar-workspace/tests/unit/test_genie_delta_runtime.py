"""Delta integration contracts using explicit doubles; never cloud evidence."""
import pytest
from sbs.genie import ScopedCatalog
from test_genie_publication import inputs,plan,reader,SDK


def test_catalog_delta_versions_are_explicit_and_exact():
    config,bundle=inputs()
    versions={config['table_prefix']+'.'+t['logical_name']:t['delta_version'] for t in plan().as_dict()['tables']}
    catalog=ScopedCatalog(bundle,config['contexts'],table_prefix=config['table_prefix'],delta_versions=versions)
    sql=catalog.references(config['contexts'][0])['provision_count']['sql']
    assert 'VERSION AS OF 7 WHERE' in sql


def test_pinned_delta_capability_rejects_fixture_certificates():
    from sbs.genie.delta import DeltaPublication
    cert=reader(SDK(inputs()[1])).read(plan())
    with pytest.raises(ValueError,match='REAL'):
        DeltaPublication(cert,cert.sha256,'a'*64,lambda **k:None,lambda **k:None)


def setup_delta(tmp_path):
    import json
    from copy import deepcopy
    from test_genie_runtime import copy_inputs
    from test_genie import SDK as GenieSDK,grant
    from test_genie_provenance import History
    from test_genie_publication import governance,metadata
    from sbs.genie.publication import PublicationReader
    from sbs.genie.delta import DeltaPublication
    from sbs.genie.runtime import load_runtime_binding,ServerDependencies
    from sbs.genie.provenance import literalize_reference
    config=copy_inputs(tmp_path);config.update(warehouse_id='warehouse',space_id='space')
    (tmp_path/'config/genie-pilot-002.json').write_text(json.dumps(config))
    _,bundle=inputs()
    # Deliberately real-labelled doubles exercise rejection/acceptance code only.
    # They are NOT authenticated remote evidence and must never enter deployment.
    def gov(names):return {**governance(names),'mode':'real'}
    publication_sdk=SDK(bundle);submit=publication_sdk.execute_statement
    def unique_statement(**kw):
        out=submit(**kw);out['statement_id']='publication-'+str(len(publication_sdk.calls));return out
    publication_sdk.execute_statement=unique_statement
    cert=PublicationReader(publication_sdk,warehouse_id='warehouse',metadata_get=metadata,governance_probe=gov,evidence_mode='real').read(plan())
    registry=dict(certificate_sha256=cert.sha256,mapping_sha256=config['mapping_sha256'],status='active',
        evidence_mode='real',readback_execution_verified=True,publisher_identity='TEST DOUBLE',attestation_id='TEST ONLY',valid_from_ms=3,valid_until_ms=9999999999999)
    registry.update(publisher_warehouse_id='publisher-warehouse',publisher_executor_id=2,
        readback_executions=[dict(statement_id=e['statement_id'],observed_sql_sha256=e['sql_sha256'],warehouse_id='publisher-warehouse',
            executor_id=2,status='FINISHED',is_final=True,started_at_ms=1,ended_at_ms=2,history_record_sha256='a'*64)
            for t in cert.as_dict()['tables'] for e in t['evidence']])
    calls=[];overrides={};identity_overrides={}
    def lookup(**kw):calls.append(('registry',kw));return deepcopy(registry)
    def identity(**kw):
        calls.append(('identity',kw));fields=('full_name','uc_table_id','metastore_id','delta_table_id','location_sha256','delta_version','schema_sha256')
        tables=[{k:t[k] for k in fields} for t in cert.as_dict()['tables'] if t['full_name'] in kw['source_tables']]
        tables[0].update(identity_overrides)
        return dict(evidence_mode='real',valid_from_ms=0,valid_until_ms=9999999999999,executor_id=1,warehouse_id='warehouse',space_id='space',evidence_id='TEST ONLY',
            select_authorized=True,backend_select_only=True,ddl_identity_controlled=True,retention_controlled=True,policies_absent=True,tables=tables,**{})|deepcopy(overrides)
    capability=DeltaPublication(cert,cert.sha256,config['mapping_sha256'],lookup,identity)
    catalog=ScopedCatalog(bundle,config['contexts'],table_prefix=config['table_prefix'],delta_versions=capability.versions)
    ctx=config['contexts'][0];query=catalog.references(ctx)['provision_count']
    history=History(dict(query_id='q',query_text=literalize_reference(query['sql'],query['parameters']),status='FINISHED',is_final=True,
        warehouse_id='warehouse',executed_as_user_id=1,statement_type='SELECT',query_start_time_ms=100,execution_end_time_ms=200,query_source={'genie_space_id':'space'}))
    sdk=GenieSDK(rows=[['2']]);original=sdk.get_message_query_result
    def result(**kw):
        out=original(**kw);out['statement_response']['manifest']['schema']={'columns':[{'name':'provision_row_count'}]};return out
    sdk.get_message_query_result=result
    grants=grant();grants['snapshot']=config['snapshot']
    deps=ServerDependencies(sdk,history,lambda:grants,None,1,capability)
    binding=load_runtime_binding(tmp_path,dependencies=deps)
    return binding,ctx,sdk,history,registry,overrides,identity_overrides,calls,deps


def test_v2_binding_preserves_snapshots_and_fixed_versions_without_write_interval(tmp_path):
    binding,ctx,sdk,history,registry,gov,ident,calls,deps=setup_delta(tmp_path)
    assert calls==[] and sdk.calls==[] and history.calls==[]
    out=binding.ask_scoped('count',context=ctx)
    assert out['status']=='completed' and out['scope_verified'] is True and out['rows']==[['2']]
    assert out['snapshot']==binding.genie_snapshot!=out['rag_snapshot']==binding.rag_snapshot
    assert out['context']==ctx and out['lineage']['snapshot']==binding.genie_snapshot
    proof=out['execution_provenance']
    assert proof['publication_mode']=='delta_version' and proof['aba_prevented'] is False
    assert proof['table_bindings'][0]['delta_version']==7
    assert 'VERSION AS OF 7' in out['query']
    assert [x[0] for x in calls]==['registry','identity','registry','identity']
    # New DML can coexist; only version 7 and identity/access attestations matter.
    gov['latest_data_version']=8
    assert binding.ask_scoped('count',context=ctx)['status']=='completed'


@pytest.mark.parametrize('replacement',['','VERSION AS OF 8','TIMESTAMP AS OF \'2026-01-01\'','VERSION AS OF :v','VERSION AS OF -1','VERSION AS OF 7.0'])
def test_v2_executed_temporal_clause_must_match(tmp_path,replacement):
    binding,ctx,sdk,history,*_=setup_delta(tmp_path)
    history.row['query_text']=history.row['query_text'].replace('VERSION AS OF 7',replacement)
    out=binding.ask_scoped('count',context=ctx)
    assert out['status']=='conflict' and out['scope_verified'] is False and out['rows']==[]


@pytest.mark.parametrize('field,value',[('status','revoked'),('readback_execution_verified',False),('publisher_identity',''),('valid_until_ms',0),('evidence_mode','fixture'),('certificate_sha256','a'*64)])
def test_registry_rejection_precedes_genie(tmp_path,field,value):
    binding,ctx,sdk,history,registry,*_=setup_delta(tmp_path);registry[field]=value
    out=binding.ask_scoped('count',context=ctx)
    assert out['status']=='unavailable' and out['rows']==[] and sdk.calls==[] and history.calls==[]


@pytest.mark.parametrize('field,value',[('select_authorized',False),('backend_select_only',False),('ddl_identity_controlled',False),('retention_controlled',False),('policies_absent',False),('executor_id',2),('evidence_mode','fixture')])
def test_current_governance_required_before_genie(tmp_path,field,value):
    binding,ctx,sdk,history,registry,gov,*_=setup_delta(tmp_path);gov[field]=value
    assert binding.ask_scoped('count',context=ctx)['status']=='unavailable'
    assert sdk.calls==[]


@pytest.mark.parametrize('field,value',[('uc_table_id','replaced'),('delta_table_id','replaced'),('delta_version',8),('delta_version',True),('location_sha256','0'*64)])
def test_replaced_or_unverifiable_table_rejected(tmp_path,field,value):
    binding,ctx,sdk,history,registry,gov,ident,*_=setup_delta(tmp_path);ident[field]=value
    assert binding.ask_scoped('count',context=ctx)['status']=='unavailable' and sdk.calls==[]


def test_post_execution_revocation_and_context_crossing(tmp_path):
    binding,ctx,sdk,history,registry,gov,ident,calls,deps=setup_delta(tmp_path)
    from copy import deepcopy
    changed=deepcopy(ctx);changed['target_date']='2026-01-01'
    assert binding.ask_scoped('count',context=changed)['status']=='conflict' and calls==[]
    original=history.list
    def revoke(**kw):registry['status']='revoked';return original(**kw)
    history.list=revoke
    assert binding.ask_scoped('count',context=ctx)['status']=='conflict'


def test_delta_bad_pin_and_local_snapshot_fail(tmp_path):
    from sbs.genie.delta import DeltaPublication
    from sbs.genie.runtime import load_runtime_binding,ServerDependencies
    binding,ctx,sdk,history,registry,gov,ident,calls,deps=setup_delta(tmp_path)
    cap=deps.delta_publication
    with pytest.raises(ValueError,match='PIN'):
        DeltaPublication(cap.certificate,'0'*64,cap.mapping_sha256,cap.registry_lookup,cap.identity_access_probe)
    wrong=DeltaPublication(cap.certificate,cap.certificate_sha256,'0'*64,cap.registry_lookup,cap.identity_access_probe)
    with pytest.raises(ValueError,match='LOCAL_PIN'):
        load_runtime_binding(tmp_path,dependencies=ServerDependencies(sdk,history,lambda:{},None,1,wrong))
    assert calls==[]


@pytest.mark.parametrize('mutation',['missing','sql','warehouse','executor','duplicate','cache','truncated'])
def test_readback_requires_independent_history_not_only_submitted_sql(tmp_path,mutation):
    binding,ctx,sdk,history,registry,*_=setup_delta(tmp_path)
    proofs=registry['readback_executions']
    if mutation=='missing':registry.pop('readback_executions')
    elif mutation=='sql':proofs[0]['observed_sql_sha256']='0'*64
    elif mutation=='warehouse':proofs[0]['warehouse_id']='other'
    elif mutation=='executor':proofs[0]['executor_id']=True
    elif mutation=='duplicate':proofs[1]['statement_id']=proofs[0]['statement_id']
    elif mutation=='cache':proofs[0]['cache_query_id']='cached'
    else:proofs.pop()
    assert binding.ask_scoped('count',context=ctx)['status']=='unavailable' and sdk.calls==[]


def test_v2_pending_ids_never_consult_capabilities(tmp_path):
    from sbs.genie.runtime import load_runtime_binding
    from test_genie_runtime import ROOT
    binding,ctx,sdk,history,registry,gov,ident,calls,deps=setup_delta(tmp_path)
    pending=load_runtime_binding(ROOT,dependencies=deps)
    assert pending.ask_scoped('count',context=ctx)['status']=='unavailable'
    assert calls==[] and sdk.calls==[] and history.calls==[]


@pytest.mark.parametrize('value',[True,1.0])
def test_observed_executor_requires_exact_integer(tmp_path,value):
    binding,ctx,sdk,history,*_=setup_delta(tmp_path)
    history.row['executed_as_user_id']=value
    assert binding.ask_scoped('count',context=ctx)['status']=='conflict'


@pytest.mark.parametrize('end',[4,201,9999999999001])
def test_publication_readback_precedes_registry_period(tmp_path,end):
    binding,ctx,sdk,history,registry,*_=setup_delta(tmp_path)
    registry['valid_from_ms']=3
    registry['readback_executions'][0].update(started_at_ms=end-1,ended_at_ms=end)
    assert binding.ask_scoped('count',context=ctx)['status']=='unavailable' and sdk.calls==[]
