import importlib
import json
from pathlib import Path
import hashlib
import pytest
ROOT=Path(__file__).resolve().parents[2]


def ops():return importlib.import_module('sbs.operations')


def test_six_pdf_reuse_and_recovery_no_original_mutation(tmp_path):
    m=ops();plan=m.load_sealed_plan(ROOT)
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in plan.originals.values()}
    runner=m.RefreshRunner(plan,tmp_path/'state')
    baseline=runner.bootstrap_capture()
    original_pointer=runner.current()
    assert baseline['release_scope']=='capture_only' and len(baseline['sources'])==6
    result=runner.run(run_id='same-bytes')
    assert result['status']=='unchanged_bytes' and result['cost'] is None
    assert result['network_requests']==0 and runner.current()==original_pointer
    result=runner.run(run_id='failure',fail_at='before_publish',force_revalidate=True)
    assert result['status'] in ('failed','pending_validation') and runner.current()==original_pointer
    assert len(json.loads((tmp_path/'state/backlog.json').read_text())['items'])==6
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in hashes.items())


def test_idempotent_run_id_and_invalid_ids(tmp_path):
    m=ops();r=m.RefreshRunner(m.load_sealed_plan(ROOT),tmp_path)
    a=r.run(run_id='one');b=r.run(run_id='one')
    assert a==b and a['status']=='pending_validation'
    with pytest.raises(ValueError):r.run(run_id='../escape')


def test_lock_and_caps(tmp_path):
    m=ops();plan=m.load_sealed_plan(ROOT)
    with pytest.raises(ValueError):m.RefreshRunner(plan,tmp_path,max_sources=5)
    runner=m.RefreshRunner(plan,tmp_path)
    with m.exclusive_lock(tmp_path):
        with pytest.raises(RuntimeError,match='LOCK_BUSY'):runner.run(run_id='locked')


def test_failed_capture_preserves_release_and_error_sanitized(tmp_path):
    m=ops();r=m.RefreshRunner(m.load_sealed_plan(ROOT),tmp_path)
    r.bootstrap_capture();before=r.current()
    def fail(*a,**k):raise RuntimeError('secret untrusted URL')
    result=r.run(run_id='bad-capture',fetcher=fail)
    assert result['status']=='failed' and r.current()==before
    assert 'secret' not in json.dumps(result)


def test_validated_hooks_atomic_promotion_and_injected_failure(tmp_path):
    m=ops();r=m.RefreshRunner(m.load_sealed_plan(ROOT),tmp_path)
    r.bootstrap_capture();before=r.current()
    def hook(context):
        p=context['stage']/('prepared-'+context['hook']+'.json');p.write_text('{"fixture":true}')
        return {'status':'validated','artifact_path':str(p.relative_to(context['stage'])),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'mode':'fixture'}
    hooks={k:hook for k in ['SK03','SK04','SK06']}
    failed=r.run(run_id='fail-publish',hooks=hooks,force_revalidate=True,fail_at='before_publish')
    assert failed['status']=='failed' and r.current()==before
    result=r.run(run_id='publish',hooks=hooks,force_revalidate=True)
    assert result['status']=='published' and r.current()!=before
    assert result['production_validated'] is False
    assert not json.loads((tmp_path/'backlog.json').read_text())['items']


def test_prepared_artifact_tampering_detected(tmp_path):
    m=ops();r=m.RefreshRunner(m.load_sealed_plan(ROOT),tmp_path)
    def hook(context):
        p=context['stage']/context['hook'];p.write_text('fixture')
        return {'status':'validated','artifact_path':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'mode':'fixture'}
    result=r.run(run_id='prepared',hooks={k:hook for k in ['SK03','SK04','SK06']})
    assert result['status']=='published'
    (tmp_path/'runs/prepared/stage/SK03').write_text('altered')
    with pytest.raises(ValueError,match='INTEGRITY'):r.current()


def test_network_budget_rejects_before_call(tmp_path):
    m=ops();r=m.RefreshRunner(m.load_sealed_plan(ROOT),tmp_path,max_total_bytes=1);calls=[]
    def fetch(*a,**k):calls.append(1);return b'%PDF-',a[0]
    result=r.run(run_id='cap',fetcher=fetch)
    assert result['status']=='failed' and calls==[] and result['network_requests']==0


def test_only_changed_sha_enters_downstream_backlog(tmp_path):
    m=ops();plan=m.load_sealed_plan(ROOT);r=m.RefreshRunner(plan,tmp_path)
    r.bootstrap_capture();before=r.current();first=next(iter(plan.originals))
    def fixture_fetch(url,**kwargs):
        data=plan.originals[url].read_bytes()
        return data+(b'\n% isolated byte-change fixture\n' if url==first else b''),url
    result=r.run(run_id='changed-one',fetcher=fixture_fetch)
    assert result['status']=='pending_validation' and result['changed_sources']==['source-1']
    assert r.current()==before
    assert len(json.loads((tmp_path/'backlog.json').read_text())['items'])==1


def test_relocated_six_pdf_snapshot_never_reads_original_repo(tmp_path,monkeypatch):
    import shutil
    from sbs.paths import project_path,HISTORICAL_ROOT
    m=ops();relocated=tmp_path/'relocated';relocated.mkdir()
    for name in ['sk02-repository-capture.json','sk02-amendments-capture.json']:
        source=ROOT/'runs'/name
        capture=json.loads(source.read_text())
        paths=[source,Path(capture['manifest']),*[Path(x['original_path']) for x in capture['sources']]]
        for path in paths:
            path=project_path(ROOT,path)
            dest=relocated/path.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest)
    # The module was imported from the test checkout; emulate its relocated
    # bundled schema directory as it would resolve in an installed snapshot.
    import sbs.contracts
    shutil.copytree(ROOT/'contracts',relocated/'contracts')
    monkeypatch.setattr(sbs.contracts,'_CONTRACT_ROOT',relocated/'contracts')
    original_open=Path.open
    def no_original_reads(path,mode='r',*args,**kwargs):
        if 'r' in mode and any(path.resolve().is_relative_to(p) for p in (ROOT,HISTORICAL_ROOT)):
            raise AssertionError('ORIGINAL_REPOSITORY_READ_FORBIDDEN')
        return original_open(path,mode,*args,**kwargs)
    monkeypatch.setattr(Path,'open',no_original_reads)
    plan=m.load_sealed_plan(relocated)
    assert len(plan.originals)==6 and all(p.is_relative_to(relocated) for p in plan.originals.values())
    runner=m.RefreshRunner(plan,relocated/'isolated-state')
    assert len(runner.bootstrap_capture()['sources'])==6
    assert runner.run(run_id='relocated-reuse')['status']=='unchanged_bytes'


@pytest.mark.parametrize('pointer',[{'release_id':'../../outside','sha256':'a'*64},{'release_id':'/tmp/outside','sha256':'a'*64},{'release_id':'a'*63,'sha256':'a'*64},{'release_id':None,'sha256':'a'*64},{'release_id':'a'*64,'sha256':None},[],None])
def test_current_pointer_rejects_invalid_shape_before_release_read(tmp_path,monkeypatch,pointer):
    m=ops();runner=m.RefreshRunner(m.load_sealed_plan(ROOT),tmp_path)
    (tmp_path/'current.json').write_text(json.dumps(pointer))
    reads=[];original_read=Path.read_bytes
    def reject_release_read(path,*a,**k):
        reads.append(path);raise AssertionError('RELEASE_READ_BEFORE_POINTER_VALIDATION')
    monkeypatch.setattr(Path,'read_bytes',reject_release_read)
    with pytest.raises(ValueError,match='RELEASE_POINTER_INVALID'):runner.current()
    assert not reads


def test_corrupted_pointer_restore_recovers_previous_release(tmp_path):
    m=ops();runner=m.RefreshRunner(m.load_sealed_plan(ROOT),tmp_path)
    runner.bootstrap_capture();pointer=runner.current();raw=(tmp_path/'current.json').read_bytes()
    (tmp_path/'current.json').write_text('{corrupted')
    with pytest.raises(ValueError,match='RELEASE_POINTER_INVALID'):runner.current()
    (tmp_path/'current.json').write_bytes(raw)
    assert runner.current()==pointer


def test_current_pointer_rejects_release_symlink_escape_before_read(tmp_path,monkeypatch):
    m=ops();state=tmp_path/'state';state.mkdir();outside=tmp_path/'outside';outside.mkdir()
    runner=m.RefreshRunner(m.load_sealed_plan(ROOT),state)
    (state/'releases').mkdir();(state/'releases'/('a'*64)).symlink_to(outside,target_is_directory=True)
    (state/'current.json').write_text(json.dumps({'release_id':'a'*64,'sha256':'a'*64}))
    def forbid_read(*a,**k):raise AssertionError('ESCAPED_RELEASE_READ')
    monkeypatch.setattr(Path,'read_bytes',forbid_read)
    with pytest.raises(ValueError,match='RELEASE_POINTER_INVALID'):runner.current()
