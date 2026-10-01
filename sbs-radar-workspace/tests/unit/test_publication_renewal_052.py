"""052 fixture-only continuation of an expired, partially created publication."""
from dataclasses import asdict, replace
import json
import pytest
from sbs.genie import canonical, digest
from sbs.genie import publication_writer as pw
from test_publication_writer import config, FixtureCloud, load_write_plan, ROOT

@pytest.fixture
def partial(tmp_path):
    plan=load_write_plan(ROOT,publication_id='pilot002-016')
    old=config(plan,policy=config(plan).policy|{'issued_at_ms':1,'expires_at_ms':500})
    cloud=FixtureCloud(plan,old)
    original=cloud.execute_statement
    def stop_after_empty(**kw):
        result=original(**kw)
        if kw['statement'].startswith('SELECT'):raise RuntimeError('fixture interruption after third SQL')
        return result
    cloud.execute_statement=stop_after_empty
    with pw.PublicationWriter(plan,old,cloud,tmp_path/'journal',clock=lambda:100) as writer:
        with pytest.raises(ValueError,match='STATEMENT_SUBMISSION_FAILED'):
            writer.publish(certificate_directory=tmp_path/'cert',registry_directory=tmp_path/'registry')
    cloud.execute_statement=original
    assert len(cloud.calls)==3 and cloud.tables_data['documents']==[]
    new=replace(old,policy=old.policy|{'issued_at_ms':500,'expires_at_ms':900000})
    budget=tmp_path/'sql-budget.json'
    budget.write_text(json.dumps({'limit':112,'reserved':3,'prior_sql_evidence':'fixture-three-observed','submissions':[]}))
    return plan,old,new,cloud,budget


def renew(partial,tmp_path,**kw):
    plan,old,new,_,budget=partial
    function=getattr(pw,'renew_policy_window',None)
    assert callable(function), 'Missing explicit window renewal: direct config change mismatches durable binding'
    return function(plan,old,new,tmp_path/'journal',budget_path=budget,
                    expected_budget_sha256=digest(json.loads(budget.read_text())),
                    authorize=lambda:new,authorization_sha256='a'*64,clock=lambda:1000,**kw)


def test_direct_new_window_reproduces_binding_mismatch(partial,tmp_path):
    plan,_,new,cloud,_=partial
    with pw.PublicationWriter(plan,new,cloud,tmp_path/'journal',clock=lambda:1000) as writer:
        with pytest.raises(ValueError,match='JOURNAL_BINDING_MISMATCH'):
            writer.publish(certificate_directory=tmp_path/'cert',registry_directory=tmp_path/'registry')
    assert len(cloud.calls)==3


def test_explicit_renewal_preserves_journal_and_resumes_without_duplicate_create(partial,tmp_path):
    plan,old,new,cloud,budget=partial
    original={p.name:p.read_bytes() for p in (tmp_path/'journal').iterdir()}
    before=budget.read_bytes()
    result=renew(partial,tmp_path)
    assert result['old_binding']=={'plan_sha256':plan.sha256,'config_sha256':digest(asdict(old))}
    assert result['new_binding']=={'plan_sha256':plan.sha256,'config_sha256':digest(asdict(new))}
    assert budget.read_bytes()==before
    assert all((tmp_path/'journal'/n).read_bytes()==v for n,v in original.items())
    with pw.PublicationWriter(plan,new,cloud,tmp_path/'journal',clock=lambda:1000) as writer:
        out=writer.publish(certificate_directory=tmp_path/'cert',registry_directory=tmp_path/'registry')
    assert out['status']=='published'
    assert sum(s.startswith('CREATE TABLE') for s in cloud.calls)==8
    assert sum(s.startswith('INSERT') for s in cloud.calls)==8
    assert json.loads(budget.read_text())['reserved']==len(cloud.calls)
    assert json.loads(budget.read_text())['limit']==112


@pytest.mark.parametrize('field,value', [('owner','different@example.test'),('host','https://different.example'),
    ('schema_id','other'),('warehouse_id','other'),('executor_id',99),('max_http_calls',511),('evidence_mode','real'),('plan_sha256','f'*64)])
def test_resource_or_plan_drift_rejected(partial,tmp_path,field,value):
    plan,old,new,cloud,budget=partial
    changed=replace(new,**{field:value})
    with pytest.raises(ValueError):renew((plan,old,changed,cloud,budget),tmp_path)
    assert len(cloud.calls)==3


@pytest.mark.parametrize('key',['trusted_administrators','exclusive_maintenance','retention','no_inherited_abac'])
def test_policy_assumptions_drift_rejected(partial,tmp_path,key):
    plan,old,new,cloud,budget=partial
    changed=replace(new,policy=new.policy|{key:'changed'})
    with pytest.raises(ValueError):renew((plan,old,changed,cloud,budget),tmp_path)


def test_old_binding_cannot_branch_after_renewal(partial,tmp_path):
    renew(partial,tmp_path)
    plan,old,new,cloud,budget=partial
    branch=replace(new,policy=new.policy|{'expires_at_ms':950000})
    with pytest.raises(ValueError,match='JOURNAL_BINDING_MISMATCH'):
        renew((plan,old,branch,cloud,budget),tmp_path)


def test_cap_exhaustion_after_renewal_does_not_submit(partial,tmp_path):
    plan,old,new,cloud,budget=partial
    b=json.loads(budget.read_text());b['reserved']=112;b['submissions']=[{'statement_sha256':'e'*64} for _ in range(109)];budget.write_text(json.dumps(b))
    renew(partial,tmp_path)
    with pw.PublicationWriter(plan,new,cloud,tmp_path/'journal',clock=lambda:1000) as writer:
        with pytest.raises(ValueError):writer.publish(certificate_directory=tmp_path/'cert',registry_directory=tmp_path/'registry')
    assert len(cloud.calls)==3
