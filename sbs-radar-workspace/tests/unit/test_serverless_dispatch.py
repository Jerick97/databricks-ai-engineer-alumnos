from dataclasses import replace
from copy import deepcopy
import pytest
from sbs.operations.cloud_dispatch import WriterConfig,job_settings,CloudDispatcher,SqliteLedger
from test_cloud_dispatch import Jobs,boundary,config

def serverless():
    return replace(config(),cluster_id=None,compute_mode='serverless',environment_version='4',
                   environment_dependencies=('pypdf==6.13.3','databricks-sdk==0.102.0'))

def test_serverless_settings_are_explicit_and_roundtrip_sdk():
    from databricks.sdk.service.jobs import JobSettings
    s=job_settings(serverless());t=s['tasks'][0]
    assert 'existing_cluster_id' not in t and t['environment_key']=='sbs_refresh'
    assert t['disable_auto_optimization'] is True and t['max_retries']==0
    assert s['environments']==[{'environment_key':'sbs_refresh','spec':{'environment_version':'4','dependencies':['pypdf==6.13.3','databricks-sdk==0.102.0']}}]
    assert JobSettings.from_dict(s).as_dict()==s
    assert s['schedule']['pause_status']=='PAUSED'

@pytest.mark.parametrize('fields',[{'cluster_id':'cluster'}, {'environment_version':None},
    {'environment_dependencies':()}, {'environment_dependencies':['pypdf==6.13.3']},
    {'environment_dependencies':('pypdf>=6',)}, {'environment_dependencies':('pypdf==6.13.3','pypdf==6.13.3')}])
def test_serverless_rejects_implicit_or_ambiguous_config(fields):
    with pytest.raises(ValueError):replace(serverless(),**fields)

def test_existing_compute_does_not_accept_unused_environment():
    with pytest.raises(ValueError):replace(config(),environment_version='4')

def setup(tmp_path):
    c=serverless();j=Jobs();j.settings=job_settings(c)
    d=CloudDispatcher(c,j,SqliteLedger(tmp_path/'ledger.db'),boundary_probe=boundary,
        expected_acl={'access_control_list':[]},evidence_mode='fixture')
    return d,j

def test_serverless_daily_run_contract_without_classic_cluster(tmp_path):
    d,j=setup(tmp_path);r=d.observe_daily(99)
    assert r['execution_verified'] is True and not j.calls

@pytest.mark.parametrize('mutate',[lambda t:t.update(existing_cluster_id='other'),
    lambda t:t.update(new_cluster={'spark_version':'x'}),lambda t:t.update(environment_key='other'),
    lambda t:t.update(disable_auto_optimization=False)])
def test_actual_run_cannot_switch_compute(tmp_path,mutate):
    d,j=setup(tmp_path);get=j.get_run
    def altered(*a,**kw):
        r=get(*a,**kw);mutate(r['tasks'][0]);return r
    j.get_run=altered
    assert d.observe_daily(99)['execution_verified'] is False

def test_current_environment_drift_rejected_before_submission(tmp_path):
    d,j=setup(tmp_path);j.settings=deepcopy(j.settings)
    j.settings['environments'][0]['spec']['dependencies'].append('new==1.0')
    with pytest.raises(ValueError):d.request('new')
    assert not j.calls

@pytest.mark.parametrize('operation',['request','refresh','daily'])
def test_persisted_request_cannot_be_reinterpreted_after_environment_change(tmp_path,operation):
    d,j=setup(tmp_path)
    if operation=='daily':d.observe_daily(99)
    else:d.request('same')
    changed=replace(d.config,environment_version='5')
    j.settings=job_settings(changed)
    other=CloudDispatcher(changed,j,d.ledger,boundary_probe=boundary,
        expected_acl={'access_control_list':[]},evidence_mode='fixture')
    calls=len(j.calls)
    with pytest.raises(ValueError,match='CONFLICT|CONTRACT'):
        if operation=='daily':other.observe_daily(99)
        elif operation=='request':other.request('same')
        else:other.refresh('same')
    assert len(j.calls)==calls
