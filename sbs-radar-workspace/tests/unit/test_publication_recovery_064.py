"""064 contracts: replay immutable responses, never resubmit SQL."""
import pytest

def test_checkpoint_precedes_history_failure(tmp_path):
    from test_publication_writer import config,FixtureCloud,load_write_plan,ROOT
    from sbs.genie.publication_writer import PublicationWriter
    plan=load_write_plan(ROOT,publication_id='pilot002-016');cfg=config(plan);cloud=FixtureCloud(plan,cfg)
    def broken(**kw):raise ValueError('history unavailable')
    cloud.query_history.list=broken
    with PublicationWriter(plan,cfg,cloud,tmp_path/'journal',clock=lambda:1000) as w:
        with pytest.raises(ValueError):w.publish(certificate_directory=tmp_path/'cert',registry_directory=tmp_path/'registry')
    assert list((tmp_path/'cert').glob('*.json')),'Readback certificate must survive failed registry GET'


def recorded_inputs():
    from pathlib import Path
    import json,datetime
    from sbs.genie.publication_writer import load_write_plan
    root=Path(__file__).resolve().parents[2];capture=root/'runs/sk06-recovery-064-capture'
    read=lambda p:json.loads(p.read_bytes())
    report=read(capture/'result.json');config=read(root/'deployment/phase-s-017.json')
    plan=load_write_plan(root,publication_id=config['publication_id'])
    return plan,dict(history=read(root/'runs/sk06-phase-s-064-history.json')['queries'],
        statements={r['statement_id']:r for r in (read(p) for p in capture.glob('statement-*.json'))},
        origins={r['query_id']:r for r in (read(p)['res'][0] for p in capture.glob('origin-*.json'))},
        origin_statements={r['statement_id']:r for r in (read(p) for p in (root/'runs').glob('sk06-readback-056-*.json')) if 'statement_id' in r},
        metadata={r['full_name']:r for r in (read(p) for p in capture.glob('table-*.json'))},
        metadata_at_ms=int(datetime.datetime.fromisoformat(report['at']).timestamp()*1000),
        journal_identities={t['logical_name']:read(root/('deployment/state/phase-s-017/journal/'+t['logical_name']+'-identity.json')) for t in plan.as_dict()['tables']},
        ledger=read(root/'deployment/state/phase-s-017/sql-budget-050.json'),
        # Explicit fixture governance; not a deployable attestation.
        governance=dict(mode='real',profile='trusted_admin_publisher_observed_v1',identity_continuity='not_proven',aba_prevented=False,ddl_identity_controlled=True,retention_controlled=True,select_authorized=True,policies_absent=True,evidence_id='FIXTURE ONLY: not current governance'),
        warehouse_id=config['writer']['warehouse_id'],executor_id=config['writer']['executor_id'],owner=config['writer']['owner'])


def test_real_captured_reconstruction_no_sql_retains_cache_and_old_times():
    from sbs.genie.publication_recovery import reconstruct_certificate
    from sbs.genie.publication import validate_certificate,REPLAY_IDENTITY_PROFILE
    plan,kw=recorded_inputs();cert=reconstruct_certificate(plan,**kw);p=cert.as_dict()
    assert sum(t['row_count'] for t in p['tables'])==164
    assert p['replay_evidence']['select_bracketed_by_detail'] is False
    assert all(t['evidence'][2]['statement_id'] in kw['origins'] for t in p['tables'])
    assert all(r['cached_history']['cache_query_id']==r['origin_history']['query_id'] for r in p['replay_evidence']['cached_reads'])
    with pytest.raises(ValueError):validate_certificate(cert)
    validate_certificate(cert,identity_profile=REPLAY_IDENTITY_PROFILE)


@pytest.mark.parametrize('kind',['result','cache','origin_sql','origin_actor','origin_cache','ledger','uc','detail'])
def test_reconstruction_tamper_rejected(kind):
    from sbs.genie.publication_recovery import reconstruct_certificate
    plan,k=recorded_inputs();o=next(iter(k['origins'].values()))
    if kind=='result':next(iter(k['origin_statements'].values()))['result']['data_array'][0][0]='tampered'
    elif kind=='cache':next(r for r in k['history'] if r.get('cache_query_id'))['cache_query_id']='missing'
    elif kind=='origin_sql':o['query_text']='SELECT 1'
    elif kind=='origin_actor':o['executed_as_user_id']=False
    elif kind=='origin_cache':o['cache_query_id']='unresolved'
    elif kind=='ledger':k['ledger']['submissions'][-1]['statement_sha256']='0'*64
    elif kind=='uc':next(iter(k['metadata'].values()))['table_id']='changed'
    else:
        row=sorted(k['history'],key=lambda r:r['query_start_time_ms'])[-32]
        result=k['statements'][row['query_id']];cols=result['manifest']['schema']['columns'];idx=next(i for i,c in enumerate(cols) if c['name']=='id');result['result']['data_array'][0][idx]='changed'
    with pytest.raises((ValueError,KeyError)):reconstruct_certificate(plan,**k)


def test_registry_origin_only_explicit_age_and_current_metadata(tmp_path):
    from sbs.genie.publication_recovery import reconstruct_certificate
    from sbs.genie.publication import REPLAY_IDENTITY_PROFILE
    from sbs.genie.publication_registry import PublisherPolicy,HistoryRegistryBuilder,RegistryAdmin,RegistryLookup
    plan,k=recorded_inputs();cert=reconstruct_certificate(plan,**k);p=plan.as_dict();history={r['query_id']:r for r in k['history']};history.update(k['origins']);calls=[]
    class H:
        def list(self,**kw):
            sid=kw['filter_by'].statement_ids[0];calls.append(sid);return {'res':[history[sid]],'has_next_page':False}
    now=k['metadata_at_ms'];policy=PublisherPolicy(cert.sha256,p['mapping_sha256'],p['snapshot'],p['config_hash'],k['owner'],k['warehouse_id'],k['executor_id'],300000,7200000)
    entry=HistoryRegistryBuilder(H(),policy,clock=lambda:now,identity_profile=REPLAY_IDENTITY_PROFILE).build(cert)
    assert len(calls)==32 and all(not r.get('cache_query_id') for r in entry.as_dict()['history_records'])
    assert set(k['origins'])<=set(calls)
    RegistryAdmin(tmp_path,administrator=k['owner'],identity_profile=REPLAY_IDENTITY_PROFILE).publish(entry)
    assert RegistryLookup(tmp_path,identity_profile=REPLAY_IDENTITY_PROFILE)(certificate_sha256=cert.sha256)['publication_evidence_origin']=='replay_existing_statements'
    with pytest.raises(ValueError):RegistryLookup(tmp_path)(certificate_sha256=cert.sha256)
    with pytest.raises(ValueError,match='METADATA_EXPIRED'):HistoryRegistryBuilder(H(),policy,clock=lambda:now+60001,identity_profile=REPLAY_IDENTITY_PROFILE).build(cert)
    from dataclasses import replace
    with pytest.raises(ValueError,match='TIME_OUTSIDE_POLICY'):HistoryRegistryBuilder(H(),replace(policy,max_readback_age_ms=300000),clock=lambda:now,identity_profile=REPLAY_IDENTITY_PROFILE).build(cert)


@pytest.mark.parametrize('field,value',[('select_bracketed_by_detail',True),('original_uc_observations_available',True),('origin','fixture')])
def test_replay_certificate_rejects_false_temporal_claims(field,value):
    from sbs.genie.publication_recovery import reconstruct_certificate
    from sbs.genie.publication import REPLAY_IDENTITY_PROFILE,Certificate,validate_certificate
    from sbs.genie import canonical
    plan,k=recorded_inputs();p=reconstruct_certificate(plan,**k).as_dict();p['replay_evidence'][field]=value
    with pytest.raises(ValueError):validate_certificate(Certificate(canonical(p).encode()),identity_profile=REPLAY_IDENTITY_PROFILE)


def test_replay_consumer_explicit_profile_with_current_access_fixture():
    from dataclasses import replace
    from sbs.genie.publication_recovery import reconstruct_certificate
    from sbs.genie.publication import REPLAY_IDENTITY_PROFILE
    from sbs.genie.publication_registry import PublisherPolicy,HistoryRegistryBuilder
    from sbs.genie.delta import DeltaPublication
    from test_genie_governance import setup
    from sbs.genie.governance import TrustedAdminObservedProbe
    plan,k=recorded_inputs();cert=reconstruct_certificate(plan,**k);p=plan.as_dict();now=k['metadata_at_ms'];rows={r['query_id']:r for r in k['history']};rows.update(k['origins'])
    class H:
        def list(self,**kw):return {'res':[rows[kw['filter_by'].statement_ids[0]]],'has_next_page':False}
    policy=PublisherPolicy(cert.sha256,p['mapping_sha256'],p['snapshot'],p['config_hash'],k['owner'],k['warehouse_id'],k['executor_id'],300000,7200000)
    registry=HistoryRegistryBuilder(H(),policy,clock=lambda:now,identity_profile=REPLAY_IDENTITY_PROFILE).build(cert).as_dict()['registry']
    state,c,ap,_,_=setup();state['time']=now
    name=p['tables'][2]['full_name'];m=k['metadata'][name]
    c.table_get=lambda name,**kw:{**m,'owner':'trusted-owner'}
    ap=replace(ap,namespace=p['schema_name'],issued_at_ms=now-1,expires_at_ms=now+100000)
    probe=TrustedAdminObservedProbe(c,ap)
    with pytest.raises(ValueError):DeltaPublication(cert,cert.sha256,p['mapping_sha256'],lambda **kw:registry,probe)
    cap=DeltaPublication(cert,cert.sha256,p['mapping_sha256'],lambda **kw:registry,probe,assurance_profile='trusted_admin_observed_v1',certificate_identity_profile=REPLAY_IDENTITY_PROFILE)
    out=cap.for_request().verify(source_tables=[name],started_at_ms=now,ended_at_ms=now,executor_id=1,warehouse_id='warehouse',space_id='space')
    assert out['publication_evidence_origin']=='replay_existing_statements' and out['select_bracketed_by_detail'] is False


def test_finalize_recovery_fixture_current_gets_and_no_sql(tmp_path):
    from pathlib import Path
    import json
    from sbs.genie.publication_recovery import finalize_recovery
    from sbs.genie.publication_writer import WriterConfig
    from sbs.genie.publication import CertificateStore,REPLAY_IDENTITY_PROFILE
    plan,k=recorded_inputs();root=Path(__file__).resolve().parents[2];cfg=json.loads((root/'deployment/phase-s-017.json').read_bytes());auth=json.loads((root/'deployment/phase-s-058-authorization.json').read_bytes())
    config=WriterConfig(**cfg['writer'],policy={**cfg['server_policy_assumptions_unobserved'],'issued_at_ms':auth['issued_at_ms'],'expires_at_ms':auth['expires_at_ms']})
    now=k['metadata_at_ms'];obs=dict(me={'id':str(config.executor_id),'userName':config.owner},schema={'full_name':config.schema_name,'schema_id':config.schema_id,'owner':config.owner},catalog={'name':config.schema_name.split('.')[0],'owner':config.owner},warehouse={'id':config.warehouse_id,'state':'RUNNING'},permissions={'object_id':'/sql/warehouses/'+config.warehouse_id,'access_control_list':[{'user_name':config.owner,'all_permissions':[{'permission_level':'CAN_USE'}]}]})
    history={r['query_id']:r for r in k['history']};history.update(k['origins']);calls=[]
    class H:
        def list(self,**kw):
            sid=kw['filter_by'].statement_ids[0];calls.append(sid);return {'res':[history[sid]],'has_next_page':False}
    for key in ('governance','warehouse_id','executor_id','owner'):k.pop(key)
    result=finalize_recovery(plan,config,**k,observations=obs,query_history=H(),clock=lambda:now,certificate_directory=tmp_path/'cert',registry_directory=tmp_path/'registry',max_readback_age_ms=7200000)
    assert result['status']=='published' and result['sql_submissions']==0 and len(calls)==32
    cert=CertificateStore(tmp_path/'cert',identity_profile=REPLAY_IDENTITY_PROFILE).get(result['certificate_sha256'])
    assert cert.as_dict()['replay_evidence']['current_metadata_at_ms']==now
    with pytest.raises(ValueError,match='METADATA_EXPIRED'):
        finalize_recovery(plan,config,**k,observations=obs,query_history=H(),clock=lambda:now+60001,certificate_directory=tmp_path/'expired',registry_directory=tmp_path/'expired-registry',max_readback_age_ms=7200000)
    assert not (tmp_path/'expired').exists()
