"""Executable prepare -> durable readback -> shared CAS publication entry point.

Inject trusted FilesAPI-backed store and SnapshotWriter; no SDK client creation,
cloud resource provisioning, grants, embedding inference, or runtime promotion.
The local RefreshRunner pointer describes preparation only, never cloud success.
"""
from pathlib import Path
import json
import tempfile
from contextlib import nullcontext
from . import RefreshRunner,verify_closure,sha,atomic
from .preparers import build_real_hooks
from .cloud_dispatch import require


def prepare_and_publish(project_root,plan,*,run_id,artifact_store,writer,local_parent=None,annotations=(),fail_at=None,capture_mode='sealed',capture_state_root=None,fetcher=None):
    require(type(run_id) is int and run_id>0,'RUN_ID_REQUIRED')
    require(capture_mode in ('sealed','remote'),'CAPTURE_MODE_INVALID')
    require(capture_mode!='remote' or capture_state_root is not None,'REMOTE_STATE_REQUIRED')
    previous=writer.current();previous_id=previous['release_id'] if previous else None
    if previous is not None and previous.get('run_id')==run_id:
        require(type(previous.get('run_id')) is int and type(previous.get('job_id')) is int and previous['job_id']==writer.job_id,'PUBLICATION_IDENTITY_INVALID')
        artifacts=artifact_store.recover(previous.get('manifest_path'),previous.get('manifest_sha256'))
        publication=writer.confirm_current(run_id,artifacts)
        return {'status':'published','publication':publication,'artifact_manifest':publication['manifest_path'],'recovered':True,'shared_publication':True,'runtime_promoted':False,'cloud_e2e_validated':False,'cost':None}
    with (nullcontext(capture_state_root) if capture_mode=='remote' else tempfile.TemporaryDirectory(prefix='sbs-cloud-prepare-',dir=local_parent)) as temp:
        state=Path(temp) if capture_mode=='remote' else Path(temp)/'state';runner=RefreshRunner(plan,state)
        if capture_mode=='remote' and (not state.exists() or state.is_dir() and not any(state.iterdir())) and hasattr(writer,'latest_capture_checkpoint'):
            checkpoint=writer.latest_capture_checkpoint(previous['publication_id'] if previous else None)
            if checkpoint is not None:
                from .capture_recovery import recover_pending_capture
                recover_pending_capture(plan,state,receipt=checkpoint,artifact_store=artifact_store)
        if capture_mode=='remote' and previous is not None:
            locator=state/'last_shared_publication.json'
            if not state.exists() or state.is_dir() and not any(state.iterdir()):
                from .capture_recovery import recover_published_capture
                recover_published_capture(project_root,plan,state,receipt=previous,artifact_store=artifact_store)
            require(locator.is_file() and not locator.is_symlink(),'REMOTE_CAPTURE_STATE_RECOVERY_REQUIRED')
            local=json.loads(locator.read_bytes())
            require(local.get('publication_id')==previous.get('publication_id'),'REMOTE_CAPTURE_STATE_RECOVERY_REQUIRED')
            current=runner.current()
            if local.get('local_pointer')!=current:
                # Only the exact prepared run may resume after upload/CAS failure.
                # Another run or an unrelated local pointer cannot skip history.
                record_path=state/'runs'/('job-'+str(run_id))/'result.json'
                require(record_path.is_file() and not record_path.is_symlink(),'REMOTE_CAPTURE_STATE_RECOVERY_REQUIRED')
                record=json.loads(record_path.read_bytes())
                require(record.get('run_id')=='job-'+str(run_id) and record.get('status')=='published' and record.get('publication_committed') is True and record.get('previous')==local.get('local_pointer') and record.get('current')==current,'REMOTE_CAPTURE_STATE_RECOVERY_REQUIRED')
        from .remote_refresh import run_refresh
        prepared=run_refresh(project_root,plan,state,run_id='job-'+str(run_id),capture_mode=capture_mode,fetcher=fetcher,annotations=annotations,fail_at=fail_at)
        if prepared['status']!='published':
            checkpoint=None
            if capture_mode=='remote' and prepared['status']=='pending_validation':
                from .capture_recovery import stage_pending_capture
                from . import plan_fingerprint
                require(callable(getattr(writer,'save_capture_checkpoint',None)),'CAPTURE_DURABLE_WRITER_REQUIRED')
                staged=stage_pending_capture(plan,state,run_id=run_id,base_publication=previous['publication_id'] if previous else None,artifact_store=artifact_store)
                checkpoint=writer.save_capture_checkpoint(run_id,base_publication=previous['publication_id'] if previous else None,plan_fingerprint=plan_fingerprint(plan),staged=staged)
            return {'status':prepared['status'],'pending_hooks':prepared['pending_hooks'],'error_code':prepared['error_code'],'shared_publication':False,'capture_durable':checkpoint is not None,'capture_checkpoint':checkpoint,'capture_mode':capture_mode,'capture_state_root':str(state) if capture_mode=='remote' else None,'cost':None}
        pointer=runner.current();release_path=state/'releases'/pointer['release_id']/'release.json';release=json.loads(release_path.read_bytes())
        require(release.get('real_preparation_completed') is True,'REAL_PREPARATION_REQUIRED')
        closure={str(release_path.relative_to(state)):sha(release_path.read_bytes())}
        for item in release['prepared'].values():
            for path,expected in {**item['closure'],item['artifact_path']:item['sha256']}.items():
                require(path not in closure or closure[path]==expected,'LOCAL_CLOSURE_CONFLICT');closure[path]=expected
        verify_closure(state,closure)
        counts={k:json.loads((state/v['artifact_path']).read_bytes())['payload'] for k,v in release['prepared'].items()}
        evidence={'sources':len(release['sources']),'comparisons':len(counts['SK03']['comparisons']),'records':len(counts['SK04']['records']),'embedding_calls':counts['SK04']['embedding_calls'],'curated_provisions':len(counts['SK06']['bundle']['tables']['provisions'])}
        staged=artifact_store.stage(str(run_id),state,closure)
        # All remote bytes including manifest are verified before acquiring fence/CAS.
        require(artifact_store.verify(staged['artifacts']),'REMOTE_CLOSURE_UNVERIFIED')
        fence=writer.claim(run_id)
        publication=writer.publish(run_id,fence,previous=previous_id,release_id=staged['release_id'],artifacts=staged['artifacts'])
        require(publication.get('status')=='published','SHARED_PUBLICATION_UNCONFIRMED')
        if capture_mode=='remote':atomic(state/'last_shared_publication.json',{'publication_id':publication['publication_id'],'local_pointer':pointer})
        return {'status':publication['status'],'publication':publication,'artifact_manifest':staged['manifest_path'],'counts':evidence,'shared_publication':True,'runtime_promoted':False,'cloud_e2e_validated':False,'cost':None}
