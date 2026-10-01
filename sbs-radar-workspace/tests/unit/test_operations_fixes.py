"""Isolated tiny capture doubles: no PDF rebuild, network or model calls."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
import sbs.operations as m


def runner(base,identity='plan-A',rows=None):
    original=base/'original';original.write_bytes(b'fixture')
    plan=m.SealedPlan({'sources':[{'document_id':'doc-A','url':'https://example.test/a'}]}, {'https://example.test/a':original},{'https://example.test/a':m.sha(b'fixture')},identity)
    r=m.RefreshRunner(plan,base/'state')
    data=rows if rows is not None else [{'source_id':'source-1','document_id':'doc-A','family':'cybersecurity','sha256':'a'*64,'rawtext_sha256':'b'*64,'extraction_config_hash':'c'*64,'extractor':'fixture','quality':'partial'}]
    r._capture=lambda *a,**kw:(deepcopy(data),{'bytes':1,'requests':0})
    return r


def hook(ctx):
    p=ctx['stage']/ctx['hook'];p.write_text('fixture')
    return {'status':'validated','mode':'real','artifact_path':p.name,'sha256':m.sha(p.read_bytes())}
HOOKS={k:hook for k in ('SK03','SK04','SK06')}


@pytest.mark.parametrize('name',['runs','releases','foundation','backlog.json','current.json','.refresh.lock','last_attempt.json'])
def test_state_symlinks_rejected_without_outside_writes(tmp_path,name):
    r=runner(tmp_path);r.root.mkdir();outside=tmp_path/'outside';outside.mkdir()
    (r.root/name).symlink_to(outside,target_is_directory=True)
    with pytest.raises(ValueError,match='STATE_PATH'):r.run(run_id='escape')
    assert list(outside.iterdir())==[]


def test_changed_plan_same_bytes_revalidates(tmp_path):
    a=runner(tmp_path);a.bootstrap_capture();before=a.current()
    b=runner(tmp_path,'plan-B');out=b.run(run_id='new-plan')
    assert out['status']=='pending_validation' and out['plan_changed'] is True
    assert b.current()==before


def test_metadata_and_removal_revalidate(tmp_path):
    a=runner(tmp_path);rows=a._capture()[0]
    second=deepcopy(rows[0]);second.update(source_id='source-2',document_id='doc-B');rows.append(second)
    a=runner(tmp_path,rows=rows);a.bootstrap_capture()
    changed=deepcopy(rows[:1]);changed[0]['family']='market_conduct'
    b=runner(tmp_path,rows=changed);out=b.run(run_id='remove',hooks=HOOKS)
    assert out['status']=='published' and out['removed_sources']==['source-2']
    assert len(b._release()['sources'])==1


def test_same_run_different_plan_conflicts(tmp_path):
    runner(tmp_path).run(run_id='same')
    with pytest.raises(ValueError,match='RUN_PLAN_CONFLICT'):runner(tmp_path,'plan-B').run(run_id='same')


def test_postcommit_cleanup_distinct_and_recoverable(tmp_path,monkeypatch):
    r=runner(tmp_path);r.bootstrap_capture();before=r.current();atomic=m.atomic
    def fail(path,value):
        if Path(path).name=='backlog.json' and value.get('items')==[]:raise OSError('secret')
        return atomic(path,value)
    monkeypatch.setattr(m,'atomic',fail)
    out=r.run(run_id='committed',hooks=HOOKS,force_revalidate=True)
    assert out['status']=='published_cleanup_pending' and out['publication_committed'] is True
    assert r.current()!=before and (r.root/'last_success.json').exists()
    assert 'secret' not in json.dumps(out)
    monkeypatch.setattr(m,'atomic',atomic)
    recovered=r.run(run_id='recovered',hooks=HOOKS,force_revalidate=True)
    assert recovered['status']=='published'
    assert json.loads((r.root/'backlog.json').read_text())['items']==[]


def test_real_hook_labels_do_not_establish_production_acceptance(tmp_path):
    r=runner(tmp_path);out=r.run(run_id='real-label',hooks=HOOKS)
    assert out['real_preparation_completed'] is True
    assert out['production_validated'] is False and out['e2e_acceptance']=='not_evaluated'
    assert r._release()['production_validated'] is False


def test_fault_after_pointer_replace_still_reports_commit(tmp_path,monkeypatch):
    r=runner(tmp_path);r.bootstrap_capture();atomic=m.atomic
    def fail(path,value):
        atomic(path,value)
        if Path(path).name=='current.json':raise OSError('after replace')
    monkeypatch.setattr(m,'atomic',fail)
    out=r.run(run_id='pointer-commit',hooks=HOOKS,force_revalidate=True)
    assert out['status']=='published_cleanup_pending' and out['publication_committed'] is True
    assert out['current']==r.current()


def test_removal_only_empty_capture_requires_downstream_validation(tmp_path):
    r=runner(tmp_path);r.bootstrap_capture();before=r.current()
    empty=runner(tmp_path,rows=[]);out=empty.run(run_id='remove-all')
    assert out['status']=='pending_validation' and out['removed_sources']==['source-1']
    assert empty.current()==before


def test_same_plan_label_changed_manifest_conflicts(tmp_path):
    r=runner(tmp_path);r.run(run_id='existing')
    r.plan.manifest['config_revision']='new'
    with pytest.raises(ValueError,match='RUN_PLAN_CONFLICT'):r.run(run_id='existing')


def test_atomic_and_lock_no_follow_parent_or_leaf(tmp_path):
    outside=tmp_path/'outside';outside.mkdir();link=tmp_path/'linked';link.symlink_to(outside,target_is_directory=True)
    with pytest.raises(ValueError,match='STATE_PATH'):m.atomic(link/'value.json',{})
    leaf=tmp_path/'leaf';leaf.symlink_to(outside/'missing')
    with pytest.raises(ValueError,match='STATE_PATH'):m.atomic(leaf,{})
    with pytest.raises(ValueError,match='STATE_PATH'):
        with m.exclusive_lock(link):pass
    assert list(outside.iterdir())==[]


def test_unchanged_and_precommit_failure_preserve_previous(tmp_path):
    r=runner(tmp_path);r.bootstrap_capture();before=r.current()
    unchanged=r.run(run_id='unchanged')
    assert unchanged['status']=='unchanged_bytes' and r.current()==before
    assert r.run(run_id='unchanged')==unchanged
    failed=r.run(run_id='precommit',hooks=HOOKS,force_revalidate=True,fail_at='before_publish')
    assert failed['status']=='failed' and failed['publication_committed'] is False
    assert r.current()==before
