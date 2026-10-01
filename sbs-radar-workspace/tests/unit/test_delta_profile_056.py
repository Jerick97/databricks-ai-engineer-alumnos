"""056 recorded response replay and explicit identity-assurance profile fixtures."""
from pathlib import Path
from copy import deepcopy
from dataclasses import asdict
import json
import pytest
from sbs.genie import canonical
from sbs.genie.publication import PublicationReader,validate_certificate,CertificateStore
from test_genie_publication import inputs,plan,SDK,response,metadata,governance
ROOT=Path(__file__).resolve().parents[2]
PROFILE='uc_managed_named_detail_v1'
OBS=json.loads((ROOT/'runs/sk06-delta-identity-056-result.json').read_bytes())


def scenario(profile=None):
    _,bundle=inputs();sdk=SDK(bundle);original=sdk.execute_statement
    def execute(**kw):
        result=original(**kw);name=next(t['full_name'] for t in plan().as_dict()['tables'] if '`'+t['logical_name']+'`' in kw['statement'])
        if kw['statement'].startswith('DESCRIBE DETAIL'):
            if name==OBS['metadata']['full_name']:result=deepcopy(OBS['statement'])
            else:result=response(['format','id','name','location'],['STRING']*4,[['delta','delta-'+name,name,'']])
        result['statement_id']='fixture-'+str(len(sdk.calls))
        return result
    sdk.execute_statement=execute
    def meta(name):return deepcopy(OBS['metadata']) if name==OBS['metadata']['full_name'] else metadata(name)
    g=lambda names:{**governance(names),'profile':'trusted_admin_publisher_observed_v1','identity_continuity':'not_proven','aba_prevented':False}
    options={} if profile is None else {'identity_profile':profile}
    return PublicationReader(sdk,warehouse_id='warehouse',metadata_get=meta,governance_probe=g,evidence_mode='fixture',**options),sdk


def test_recorded_empty_detail_strict_still_rejects():
    r,s=scenario()
    with pytest.raises(ValueError,match='DELTA_IDENTITY_INVALID'):r.read(plan())
    assert len(s.calls)==1


def test_explicit_profile_records_uc_only_route_provenance_and_closed_certificate(tmp_path):
    r,s=scenario(PROFILE);cert=r.read(plan());p=validate_certificate(cert,identity_profile=PROFILE)
    assert p['identity_profile']==PROFILE and p['aba_prevented'] is False
    assert len(s.calls)==32
    for table in p['tables']:
        e=table['location_evidence']
        assert e['detail_name']==table['full_name']
        assert e['source']=='uc_metadata' and e['detail_location_observation']=='empty'
        assert e['physical_location_relation_observed'] is False
    with pytest.raises(ValueError,match='IDENTITY_PROFILE'):validate_certificate(cert)
    with pytest.raises(ValueError,match='IDENTITY_PROFILE'):CertificateStore(tmp_path/'strict').put(cert)
    store=CertificateStore(tmp_path/'profile',identity_profile=PROFILE);assert store.get(store.put(cert))==cert


@pytest.mark.parametrize('field,value',[('name','other.name'),('name',None),('location',None),('location','s3://wrong'),('format','parquet'),('id','')])
def test_profile_rejects_missing_mismatched_or_conflicting_detail(field,value):
    r,s=scenario(PROFILE);execute=s.execute_statement
    def changed(**kw):
        result=execute(**kw)
        if kw['statement'].startswith('DESCRIBE DETAIL'):
            cols=[c['name'] for c in result['manifest']['schema']['columns']]
            result['result']['data_array'][0][cols.index(field)]=value
        return result
    s.execute_statement=changed
    with pytest.raises(ValueError):r.read(plan())
    assert len(s.calls)==1


def test_unknown_profile_fails_before_statements():
    with pytest.raises(ValueError,match='IDENTITY_PROFILE'):scenario('accept_any')


def test_writer_continues_eight_completed_inserts_with_explicit_profile_and_same_binding(tmp_path):
    from sbs.genie.publication_writer import PublicationWriter,load_write_plan
    from sbs.genie.publication_registry import RegistryLookup
    from test_publication_writer import config,FixtureCloud
    wp=load_write_plan(ROOT,publication_id='pilot002-016');cfg=config(wp);cfg_before=asdict(cfg);cloud=FixtureCloud(wp,cfg);original=cloud.execute_statement
    def execute(**kw):
        r=original(**kw)
        if kw['statement'].startswith('DESCRIBE DETAIL'):
            name=next(t['full_name'] for t in wp.as_dict()['tables'] if '`'+t['logical_name']+'`' in kw['statement'])
            r=response(['format','id','name','location'],['STRING']*4,[['delta','delta-'+name,name,'']],r['statement_id'])
        return r
    cloud.execute_statement=execute
    with PublicationWriter(wp,cfg,cloud,tmp_path/'journal',clock=lambda:1000) as writer:
        with pytest.raises(ValueError,match='DELTA_IDENTITY_INVALID'):writer.publish(certificate_directory=tmp_path/'cert',registry_directory=tmp_path/'registry')
    assert len(list((tmp_path/'journal').glob('*-insert-receipt.json')))==8
    binding=(tmp_path/'journal/binding.json').read_bytes();previous=len(cloud.calls)
    with PublicationWriter(wp,cfg,cloud,tmp_path/'journal',clock=lambda:1000,identity_profile=PROFILE) as writer:
        result=writer.publish(certificate_directory=tmp_path/'cert',registry_directory=tmp_path/'registry')
    assert result['status']=='published' and result['identity_profile']==PROFILE
    assert sum(s.startswith('CREATE') for s in cloud.calls)==8
    assert sum(s.startswith('INSERT') for s in cloud.calls)==8
    assert len(cloud.calls)-previous==48 and len(cloud.calls)-previous<=61
    assert (tmp_path/'journal/binding.json').read_bytes()==binding and asdict(cfg)==cfg_before
    assert RegistryLookup(tmp_path/'registry',identity_profile=PROFILE)(certificate_sha256=result['certificate_sha256'])['identity_profile']==PROFILE
    with pytest.raises(ValueError,match='IDENTITY_PROFILE'):RegistryLookup(tmp_path/'registry')(certificate_sha256=result['certificate_sha256'])


@pytest.mark.parametrize('field',['table_id','metastore_id','storage_location'])
def test_named_profile_rejects_uc_identity_drift_before_post_detail(field):
    r,s=scenario(PROFILE);get=r.metadata_get;calls=[]
    def changed(name):
        m=get(name);calls.append(name)
        if len(calls)==2:m[field]='changed'
        return m
    r.metadata_get=changed
    with pytest.raises(ValueError):r.read(plan())


@pytest.mark.parametrize('field,value',[('id','changed-delta'),('name','changed.name'),('location','s3://different')])
def test_named_profile_rejects_post_detail_identity_drift(field,value):
    r,s=scenario(PROFILE);execute=s.execute_statement;details=[]
    def changed(**kw):
        v=execute(**kw)
        if kw['statement'].startswith('DESCRIBE DETAIL'):
            details.append(1)
            if len(details)==2:
                i=[c['name'] for c in v['manifest']['schema']['columns']].index(field)
                v['result']['data_array'][0][i]=value
        return v
    s.execute_statement=changed
    with pytest.raises(ValueError):r.read(plan())
    assert len(details)==2


def test_profile_requires_explicit_trusted_publisher_governance():
    r,s=scenario(PROFILE);r.governance_probe=governance
    with pytest.raises(ValueError,match='NAMED_IDENTITY_GOVERNANCE_REQUIRED'):r.read(plan())
    assert not s.calls


@pytest.mark.parametrize('tamper',['physical_true','source','missing','unknown'])
def test_profile_certificate_cannot_claim_unobserved_route_or_omit_provenance(tamper):
    from sbs.genie.publication import Certificate
    r,s=scenario(PROFILE);p=r.read(plan()).as_dict();t=p['tables'][0]
    if tamper=='physical_true':t['location_evidence']['physical_location_relation_observed']=True
    elif tamper=='source':t['location_evidence']['source']='describe_detail'
    elif tamper=='missing':del t['location_evidence']
    else:p['identity_profile']='other'
    with pytest.raises(ValueError):validate_certificate(Certificate(canonical(p).encode()),identity_profile=PROFILE)


def test_delta_capability_defaults_do_not_accept_weaker_named_profile():
    from sbs.genie.delta import DeltaPublication
    r,s=scenario(PROFILE);cert=r.read(plan())
    with pytest.raises(ValueError,match='IDENTITY_PROFILE'):
        DeltaPublication(cert,cert.sha256,'a'*64,lambda **kw:None,lambda **kw:None)
    with pytest.raises(ValueError,match='NAMED_IDENTITY_ASSURANCE_REQUIRED'):
        DeltaPublication(cert,cert.sha256,'a'*64,lambda **kw:None,lambda **kw:None,certificate_identity_profile=PROFILE)


def test_named_profile_consumed_by_real_runtime_contract_with_explicit_doubles(tmp_path):
    from dataclasses import replace
    from test_genie_delta_runtime import setup_delta
    from test_genie_governance import setup
    from sbs.genie.governance import TrustedAdminObservedProbe
    from sbs.genie.publication import Certificate
    from sbs.genie.runtime import load_runtime_binding
    _,ctx,sdk,history,registry,_,_,_,deps=setup_delta(tmp_path)
    cap=deps.delta_publication;p=cap.certificate.as_dict()
    # Existing setup uses real-labelled doubles; this is never remote evidence.
    p['identity_profile']=PROFILE
    for t in p['tables']:
        t['location_evidence']=dict(source='uc_metadata',detail_name=t['full_name'],detail_location_observation='empty',physical_location_relation_observed=False)
    cert=Certificate(canonical(p).encode())
    registry.update(certificate_sha256=cert.sha256,identity_profile=PROFILE)
    state,collector,policy,_,_=setup()
    probe=TrustedAdminObservedProbe(collector,replace(policy,namespace=p['tables'][0]['full_name'].rsplit('.',1)[0]))
    cap=replace(cap,certificate=cert,certificate_sha256=cert.sha256,certificate_identity_profile=PROFILE,identity_access_probe=probe,assurance_profile='trusted_admin_observed_v1')
    original=history.list
    def completed(**kw):state['time']=250;return original(**kw)
    history.list=completed
    bound=load_runtime_binding(tmp_path,dependencies=replace(deps,delta_publication=cap))
    out=bound.ask_scoped('count',context=ctx)
    assert out['status']=='completed' and out['scope_verified'] is True
    proof=out['execution_provenance']
    assert proof['certificate_identity_profile']==PROFILE
    assert proof['physical_location_relation_observed'] is False and proof['aba_prevented'] is False
    state['time']=50;registry.pop('identity_profile');sdk.calls.clear()
    assert bound.ask_scoped('count',context=ctx)['status']=='unavailable' and sdk.calls==[]
