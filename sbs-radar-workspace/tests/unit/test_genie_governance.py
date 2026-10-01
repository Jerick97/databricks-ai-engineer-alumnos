"""Trusted-admin profile tests are local doubles, not authenticated cloud proof."""
def test_explicit_profile_types_exist():
    from sbs.genie.governance import TrustedAdminPolicy,UcAccessCollector,TrustedAdminObservedProbe
    assert TrustedAdminPolicy and UcAccessCollector and TrustedAdminObservedProbe

from copy import deepcopy
import pytest
from sbs.genie.governance import TrustedAdminPolicy,UcAccessCollector,TrustedAdminObservedProbe,ScimReaderResolver


def setup():
    state={'time':50,'status':'active','table_id':'uc-provisions','privilege':'SELECT','roles':[],'groups':['readers'],'acl':'CAN_USE','calls':[]}
    def clock():return state['time']
    def identity(id):return dict(id=id,active=True,application_id='app-reader',groups=[{'value':str(i),'display':g} for i,g in enumerate(state['groups'])],roles=state['roles'])
    def group(id):return dict(id=id,display_name=state['groups'][int(id)])
    resolver=ScimReaderResolver(identity,group,clock=clock)
    def table(name,**kw):
        state['calls'].append('table')
        return dict(full_name=name,table_id=state['table_id'],metastore_id='meta',storage_location='s3://sealed/provisions',owner='trusted-owner',table_type='MANAGED',data_source_format='DELTA',columns=[{'name':'id'}])
    def grants(**kw):
        state['calls'].append(kw)
        privilege={'CATALOG':'USE_CATALOG','SCHEMA':'USE_SCHEMA','TABLE':state['privilege']}[kw['securable_type']]
        return dict(privilege_assignments=[dict(principal='readers',privileges=[dict(privilege=privilege,inherited_from_name='catalog.sbs_radar',inherited_from_type='SCHEMA')])])
    def acl(id):return dict(object_id='/sql/warehouses/'+id,object_type='warehouses',access_control_list=[dict(group_name='readers',all_permissions=[dict(permission_level=state['acl'],inherited=True)])])
    collector=UcAccessCollector(table_get=table,catalog_get=lambda n:{'name':n,'owner':'trusted-owner'},schema_get=lambda n:{'full_name':n,'owner':'trusted-owner'},effective_grants_get=grants,warehouse_permissions_get=acl,subject_resolver=resolver,clock=clock)
    policy=TrustedAdminPolicy('test-policy','catalog.sbs_radar',('trusted-owner',),'Supervised namespace maintenance','Admins declare no applicable ABAC',0,1000,500,lambda **kw:state['status'])
    probe=TrustedAdminObservedProbe(collector,policy)
    kw=dict(source_tables=['catalog.sbs_radar.provisions'],executor_id=1,warehouse_id='warehouse',space_id='space',started_at_ms=50,ended_at_ms=50)
    return state,collector,policy,probe,kw


def test_explicit_assumptions_separate_from_observed_prepost():
    state,c,p,f,kw=setup();probe=f.new_session();before=probe(**kw)
    state['time']=200;after=probe(**(kw|dict(started_at_ms=100,ended_at_ms=150)))
    assert before['phase']=='before' and after['phase']=='after'
    assert after['identity_continuity']=='not_proven' and after['aba_prevented'] is False
    assert 'valid_from_ms' not in after and 'delta_table_id' not in after['observation']['tables'][0]
    assert after['assumptions']['basis']=='server_operational_assumption_not_observed_history'
    assert after['observation']['policy_visibility'].endswith('abac_not_observed')


@pytest.mark.parametrize('field,value',[('privilege','MODIFY'),('privilege','ALL_PRIVILEGES'),('roles',[{'value':'account_admin'}]),('acl','CAN_MANAGE'),('groups',['account users']),('status','revoked'),('time',1001)])
def test_rejection_of_wrong_grants_identity_or_policy(field,value):
    state,c,p,f,kw=setup();state[field]=value
    with pytest.raises(ValueError):f.new_session()(**kw)


@pytest.mark.parametrize('mutation',['identity','grant','expired','revoked'])
def test_post_observation_drift_expiry_revocation(mutation):
    state,c,p,f,kw=setup();probe=f.new_session();probe(**kw);state['time']=200
    if mutation=='identity':state['table_id']='new-id'
    elif mutation=='grant':state['privilege']='MODIFY'
    elif mutation=='expired':state['time']=700
    else:state['status']='revoked'
    with pytest.raises(ValueError):probe(**(kw|dict(started_at_ms=100,ended_at_ms=150)))


def test_inherited_pagination_and_aliases_are_not_assumed():
    state,c,p,f,kw=setup();original=c.grants
    def pages(**kwargs):
        if 'page_token' not in kwargs:return dict(privilege_assignments=[],next_page_token='next')
        return original(**kwargs)
    c.grants=pages
    assert f.new_session()(**kw)['backend_select_only_observed'] is True
    state['groups']=['account users']
    with pytest.raises(ValueError):f.new_session()(**kw)
    c.grants=lambda **kw:dict(privilege_assignments=[],next_page_token='repeat')
    with pytest.raises(ValueError,match='PAGINATION'):f.new_session()(**kw)


def test_types_memberships_and_no_get_from_constructor():
    state,c,p,f,kw=setup();assert state['calls']==[]
    with pytest.raises(ValueError):f.new_session()(**(kw|{'executor_id':True}))
    with pytest.raises(ValueError,match='SESSION'):f(**kw)
    c.subject_resolver=lambda **kw:dict(executor_id=1,active=True,principals=['readers'],roles=[],membership_complete=True,observed_at_ms=50,evidence_id='configured')
    with pytest.raises(ValueError,match='MEMBERSHIP'):f.new_session()(**kw)


def test_scim_reported_indirect_groups_no_role_claim():
    resolver=ScimReaderResolver(lambda id:dict(id=id,active=True,applicationId='client',groups=[{'value':'7','display':'clone','type':'indirect'}]),lambda id:dict(id=id,displayName='clone'),clock=lambda:50)
    r=resolver(executor_id=1)
    assert r['principals']==['client','clone'] and r['role_visibility']=='roles_not_reported'
    assert 'users' not in r['principals'] and r['membership_scope']=='full_scim_resource_reported_groups'


def test_observed_profile_runtime_integration_and_isolated_requests(tmp_path):
    from test_genie_delta_runtime import setup_delta
    from sbs.genie.delta import DeltaPublication
    from sbs.genie.runtime import load_runtime_binding
    from dataclasses import replace
    binding,ctx,sdk,history,registry,gov,ident,calls,deps=setup_delta(tmp_path)
    state,c,p,f,kw=setup();namespace=deps.delta_publication.certificate.as_dict()['tables'][0]['full_name'].rsplit('.',1)[0]
    p=replace(p,namespace=namespace);probe=TrustedAdminObservedProbe(c,p)
    cap=replace(deps.delta_publication,identity_access_probe=probe,assurance_profile='trusted_admin_observed_v1')
    original=history.list
    def completed(**kw):state['time']=250;return original(**kw)
    history.list=completed
    bound=load_runtime_binding(tmp_path,dependencies=replace(deps,delta_publication=cap))
    assert state['calls']==[] and sdk.calls==[]
    out=bound.ask_scoped('count',context=ctx)
    assert out['status']=='completed' and out['scope_verified'] is True
    proof=out['execution_provenance'];assert proof['assurance_profile']=='trusted_admin_observed_v1'
    assert proof['access_assurance']['phase']=='after' and proof['identity_continuity']=='not_proven'
    assert out['snapshot']!=out['rag_snapshot']
    # A new call must have its own before/after observations, not prior state.
    state['time']=50
    assert bound.ask_scoped('count',context=ctx)['status']=='completed'
    state['time']=50;state['table_id']='replacement';sdk.calls.clear()
    assert bound.ask_scoped('count',context=ctx)['status']=='unavailable' and sdk.calls==[]


def test_no_silent_strict_profile_replacement(tmp_path):
    from test_genie_delta_runtime import setup_delta
    from dataclasses import replace
    _,_,_,_,_,_,_,_,deps=setup_delta(tmp_path)
    assert deps.delta_publication.assurance_profile=='strict_interval_v1'
    with pytest.raises(ValueError,match='CAPABILITY'):
        replace(deps.delta_publication,assurance_profile='trusted_admin_observed_v1')


def test_parent_owner_and_visible_policy_reject():
    state,c,p,f,kw=setup();c.schema_get=lambda n:{'owner':'readers'}
    with pytest.raises(ValueError,match='OWNER'):f.new_session()(**kw)
    state,c,p,f,kw=setup();original=c.table_get
    def masked(*a,**kw):return original(*a,**kw)|{'row_filter':{'function_name':'mask'}}
    c.table_get=masked
    with pytest.raises(ValueError,match='POLICY'):f.new_session()(**kw)


def test_post_observations_must_bracket_history_not_claim_coverage():
    state,c,p,f,kw=setup();probe=f.new_session();probe(**kw);state['time']=200
    with pytest.raises(ValueError,match='BRACKET'):probe(**(kw|dict(started_at_ms=1,ended_at_ms=2)))


def test_provider_errors_are_safe_and_permission_denied_distinct():
    state,c,p,f,kw=setup()
    def denied(*a,**k):raise PermissionError('sensitive-provider-detail')
    c.table_get=denied
    with pytest.raises(PermissionError,match='^GOVERNANCE_GET_DENIED$'):f.new_session()(**kw)
    def unavailable(*a,**k):raise RuntimeError('sensitive-provider-detail')
    c.table_get=unavailable
    with pytest.raises(ValueError,match='^GOVERNANCE_GET_UNAVAILABLE$'):f.new_session()(**kw)



def test_wrong_warehouse_acl_is_not_relabelled_as_requested():
    state,c,p,f,kw=setup();original=c.warehouse_permissions
    c.warehouse_permissions=lambda id:original('different')
    with pytest.raises(ValueError,match='ACL'):f.new_session()(**kw)


def test_sdk_empty_intermediate_grants_page_is_preserved():
    from databricks.sdk.service.catalog import EffectivePermissionsList
    state,c,p,f,kw=setup();original=c.grants
    def pages(**kwargs):
        if 'page_token' not in kwargs:return EffectivePermissionsList(privilege_assignments=[],next_page_token='next')
        return EffectivePermissionsList.from_dict(original(**kwargs))
    c.grants=pages
    assert f.new_session()(**kw)['select_authorized_observed'] is True


def test_sdk_empty_terminal_page_does_not_erase_prior_grants():
    from databricks.sdk.service.catalog import EffectivePermissionsList
    state,c,p,f,kw=setup();original=c.grants
    def pages(**kwargs):
        if 'page_token' in kwargs:return EffectivePermissionsList(privilege_assignments=[])
        return EffectivePermissionsList.from_dict(original(**kwargs)|{'next_page_token':'last'})
    c.grants=pages
    assert f.new_session()(**kw)['select_authorized_observed'] is True


def test_sdk_explicit_empty_groups_direct_reader_full_collector():
    from databricks.sdk.service.iam import ServicePrincipal
    state,c,p,f,kw=setup()
    c.subject_resolver=ScimReaderResolver(lambda id:ServicePrincipal(id=id,active=True,application_id='app-reader',groups=[],roles=[]),lambda id:pytest.fail('no groups to resolve'),clock=lambda:50)
    original=c.grants
    def direct(**kwargs):
        out=original(**kwargs);out['privilege_assignments'][0]['principal']='app-reader';return out
    c.grants=direct
    c.warehouse_permissions=lambda id:dict(object_id='/sql/warehouses/'+id,object_type='warehouses',access_control_list=[dict(service_principal_name='app-reader',all_permissions=[dict(permission_level='CAN_USE')])])
    result=f.new_session()(**kw)
    assert result['select_authorized_observed'] is True
    assert result['observation']['subject']['principals']==['app-reader']
    assert result['observation']['subject']['role_visibility']=='roles_not_reported'


def test_raw_missing_groups_and_grants_still_reject():
    state,c,p,f,kw=setup()
    c.grants=lambda **kwargs:{'next_page_token':'next'}
    with pytest.raises(ValueError,match='INCOMPLETE'):f.new_session()(**kw)
    resolver=ScimReaderResolver(lambda id:{'id':id,'active':True,'applicationId':'app-reader'},lambda id:{},clock=lambda:50)
    with pytest.raises(ValueError,match='INCOMPLETE'):resolver(executor_id=1)
