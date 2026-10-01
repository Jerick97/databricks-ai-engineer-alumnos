"""Rebuild minimum historical capture state from a trusted published Files receipt.

No original fetch, live SQLite export, inference, or shared publication. Only
published history is recoverable here; unpublished backlog remains a separate gap.
"""
import json
import os
from pathlib import Path
import tempfile
from . import RefreshRunner,atomic,canonical,sha,plan_fingerprint
from .cloud_dispatch import require
from .runtime_release import materialize_release,load_release
from sbs.foundation.store import database


def recover_published_capture(project,plan,target,*,receipt,artifact_store):
    require(isinstance(receipt,dict) and all(k in receipt for k in ('publication_id','manifest_path','manifest_sha256','release_id','artifacts_sha256')),'REMOTE_CAPTURE_STATE_RECOVERY_REQUIRED')
    target=Path(target)
    require(not any(p.is_symlink() for p in (target,*target.parents)),'CAPTURE_RECOVERY_PATH_INVALID')
    require(not target.exists() or target.is_dir() and not any(target.iterdir()),'CAPTURE_RECOVERY_REQUIRES_EMPTY_STATE')
    target.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='capture-recovery-',dir=target.parent) as staging:
        materialized=materialize_release(artifact_store,receipt,Path(staging))
        state=materialized['state_root'];pointer=materialized['pointer']
        model=json.loads((Path(project)/'config/pilot-model-bundle.json').read_bytes())
        require(sha(canonical(model['bundle']))==model['bundle_hash'],'CAPTURE_RECOVERY_MODEL_PIN')
        # Full existing original/extraction/pair/curation checks, not hashes alone.
        load_release(state,pointer=pointer,model_identity=model['bundle_hash'])
        release=json.loads((state/'releases'/pointer['release_id']/'release.json').read_bytes())
        require(release['plan_id']==plan.identity and release['plan_fingerprint']==plan_fingerprint(plan),'CAPTURE_RECOVERY_PLAN_MISMATCH')
        item=release['prepared']['SK06'];payload=json.loads((state/item['artifact_path']).read_bytes())['payload']
        documents=[json.loads(row['payload_json']) for row in payload['bundle']['tables']['documents']]
        entries={(x['document_id'],x['url']):x for x in plan.manifest['sources']}
        db=database(state/'foundation')
        try:
            with db:
                for source in documents:
                    entry=entries.get((source['document_id'],source['url']))
                    require(entry is not None and all(entry[k]==source[k] for k in ('family','source_kind','synthetic')),'CAPTURE_RECOVERY_SOURCE_MISMATCH')
                    identity=sha(canonical([source['document_id'],source['family'],source['sha256']]))
                    # Original captured_at is preserved; this is not a new GET.
                    attempt=db.execute('INSERT INTO attempts(run,requested_url,captured_at,status) VALUES(?,?,?,?)',(canonical('restore-'+receipt['publication_id']).decode(),source['url'],source['captured_at'],'restored_published')).lastrowid
                    db.execute('INSERT OR IGNORE INTO documents VALUES(?,?)',(identity,canonical(source).decode()))
                    db.execute('INSERT INTO captures VALUES(?,?,?,?,?,?)',(attempt,identity,source['url'],source['url'],canonical(source).decode(),canonical({'basis':'published_closure_restore','publication_id':receipt['publication_id']}).decode()))
                    summary=next(x for x in release['sources'] if x['source_key']==sha(canonical([source['document_id'],source['url']])) and x['sha256']==source['sha256'])
                    derived=state/'foundation/derived'/source['sha256']/sha(summary['extractor'].encode())/summary['extraction_config_hash']
                    result=json.loads((derived/'result.json').read_bytes())
                    key=sha(canonical([source['sha256'],summary['extractor'],summary['extraction_config_hash']]))
                    db.execute('INSERT OR IGNORE INTO extraction_artifacts VALUES(?,?)',(key,sha(canonical(result))))
        finally:db.close()
        atomic(state/'current.json',pointer)
        atomic(state/'last_shared_publication.json',{'publication_id':receipt['publication_id'],'local_pointer':pointer})
        evidence={'publication_id':receipt['publication_id'],'manifest_path':receipt['manifest_path'],'manifest_sha256':receipt['manifest_sha256'],'historical_documents_restored':len(documents),'fresh_remote_capture':False,'unpublished_attempts_restored':False,'unpublished_backlog':'not_recoverable_from_published_closure'}
        atomic(state/'capture_recovery.json',evidence)
        require(RefreshRunner(plan,state).current()==pointer,'CAPTURE_RECOVERY_POINTER_INVALID')
        # Atomic local install; shared state is read-only throughout recovery.
        if target.exists():target.rmdir()
        os.replace(state,target)
        return evidence


# Closed logical schema. This serializes rows under one SQLite read transaction,
# never copies a live database/WAL or requires POSIX semantics from UC Volumes.
TABLES={'attempts':('id','run','requested_url','captured_at','status','error'),
        'documents':('identity','source'),
        'captures':('attempt_id','identity','requested_url','final_url','source','metadata'),
        'extraction_artifacts':('artifact_key','result_sha256'),
        'extraction_attempts':('id','artifact_key','started_at','status','result')}


def stage_pending_capture(plan,state,*,run_id,base_publication,artifact_store):
    import sqlite3
    from sbs.foundation import extract
    from sbs.foundation.store import object_path
    state=Path(state);runner=RefreshRunner(plan,state);pointer=runner.current()
    result=json.loads((state/'runs'/('job-'+str(run_id))/'result.json').read_bytes())
    success=json.loads((state/'last_capture_success.json').read_bytes())
    require(result['status']=='pending_validation' and success['run_id']==result['run_id']=='job-'+str(run_id),'COMPLETE_PENDING_CAPTURE_REQUIRED')
    with sqlite3.connect(state/'foundation/foundation.sqlite3') as db:
        db.execute('BEGIN')
        tables={table:db.execute('SELECT '+','.join(columns)+' FROM '+table+' ORDER BY 1 LIMIT 10001').fetchall() for table,columns in TABLES.items()}
    require(all(len(rows)<=10000 for rows in tables.values()),'CAPTURE_HISTORY_ROW_CAP')
    descriptor={'version':1,'run_id':run_id,'base_publication':base_publication,'plan_id':plan.identity,'plan_fingerprint':plan_fingerprint(plan),'tables':tables,'status':'pending_validation'}
    require(len(canonical(descriptor))<=4*1024*1024,'CAPTURE_HISTORY_BYTES_CAP')
    closure={}
    def add(path):closure[str(path.relative_to(state))]=sha(path.read_bytes())
    release=runner._release();add(state/'releases'/pointer['release_id']/'release.json')
    for item in release.get('prepared',{}).values():
        closure.update(item['closure']);closure[item['artifact_path']]=item['sha256']
    for row in tables['captures']:
        source=json.loads(row[4]);bundle=extract(source,root=state/'foundation')
        derived=state/'foundation/derived'/source['sha256']/sha(bundle['extractor'].encode())/bundle['config_hash']
        for path in (object_path(state/'foundation',source['sha256']),derived/'result.json',derived/'rawtext.txt'):add(path)
    for name in ('current.json','last_shared_publication.json','last_attempt.json','last_capture_success.json','last_success.json','backlog.json','runs/job-'+str(run_id)+'/result.json','runs/job-'+str(run_id)+'/started.json',*('runs/job-'+str(run_id)+'/stage/'+k+'.json' for k in ('SK03','SK04','SK06'))):
        path=state/name
        if path.exists():add(path)
    atomic(state/'capture-checkpoint.json',descriptor);add(state/'capture-checkpoint.json')
    return artifact_store.stage('capture-'+str(run_id),state,closure)


def recover_pending_capture(plan,target,*,receipt,artifact_store):
    from .shared_control import _capture_receipt
    from .volume_artifacts import relative
    from . import verify_closure
    from sbs.foundation import extract
    from sbs.contracts import validate_contract
    _capture_receipt(receipt)
    require(receipt['plan_fingerprint']==plan_fingerprint(plan),'CAPTURE_RECOVERY_PLAN_MISMATCH')
    target=Path(target)
    require(not any(p.is_symlink() for p in (target,*target.parents)) and (not target.exists() or target.is_dir() and not any(target.iterdir())),'CAPTURE_RECOVERY_REQUIRES_EMPTY_STATE')
    artifacts=artifact_store.recover(receipt['manifest_path'],receipt['manifest_sha256'])
    require(sha(canonical(artifacts))==receipt['artifacts_sha256'],'CAPTURE_RECOVERY_ARTIFACTS_MISMATCH')
    raw=artifact_store._read(receipt['manifest_path']);require(sha(raw)==receipt['manifest_sha256'],'CAPTURE_RECOVERY_MANIFEST_CHANGED')
    manifest=json.loads(raw);base=receipt['manifest_path'].rsplit('/',1)[0]
    target.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='pending-capture-recovery-',dir=target.parent) as temp:
        state=Path(temp)/'state';state.mkdir();closure={}
        for name,item in manifest['files'].items():
            relative(name);require(not name.endswith(('.sqlite3','.sqlite3-wal','.sqlite3-shm')),'LIVE_DATABASE_FORBIDDEN')
            data=artifact_store._read(base+'/'+name,item['bytes']);require(sha(data)==item['sha256'],'CAPTURE_RECOVERY_READBACK_CHANGED')
            path=state/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);closure[name]=item['sha256']
        verify_closure(state,closure)
        descriptor=json.loads((state/'capture-checkpoint.json').read_bytes())
        require(set(descriptor)=={'version','run_id','base_publication','plan_id','plan_fingerprint','tables','status'} and type(descriptor['version']) is int and descriptor['version']==1 and type(descriptor['run_id']) is int and descriptor['run_id']==receipt['run_id'] and descriptor['base_publication']==receipt['base_publication'] and descriptor['plan_id']==plan.identity and descriptor['plan_fingerprint']==plan_fingerprint(plan) and descriptor['status']=='pending_validation','CAPTURE_DESCRIPTOR_INVALID')
        tables=descriptor['tables'];require(isinstance(tables,dict) and set(tables)==set(TABLES) and len(canonical(descriptor))<=4*1024*1024,'CAPTURE_HISTORY_INVALID')
        db=database(state/'foundation')
        try:
            with db:
                for table,columns in TABLES.items():
                    rows=tables[table];require(isinstance(rows,list) and len(rows)<=10000 and all(isinstance(row,list) and len(row)==len(columns) for row in rows),'CAPTURE_HISTORY_INVALID')
                    db.executemany('INSERT INTO '+table+' ('+','.join(columns)+') VALUES('+','.join('?' for _ in columns)+')',rows)
        finally:db.close()
        allowed={(e['document_id'],e['url'],e['family']) for e in plan.manifest['sources']}
        for row in tables['captures']:
            source=json.loads(row[4]);require(validate_contract('SourceDocument',source)['valid'] and (source['document_id'],source['url'],source['family']) in allowed,'CAPTURE_RECOVERY_SOURCE_MISMATCH')
            extract(source,root=state/'foundation')
        current=RefreshRunner(plan,state).current();record=json.loads((state/'runs'/('job-'+str(receipt['run_id']))/'result.json').read_bytes())
        require(record['status']=='pending_validation' and record['run_id']=='job-'+str(receipt['run_id']) and record['current']==current and record['plan_fingerprint']==plan_fingerprint(plan),'CAPTURE_RECOVERY_RESULT_INVALID')
        evidence={'checkpoint_id':receipt['checkpoint_id'],'unpublished_attempts_restored':True,'fresh_remote_capture':False,'scope':'complete_capture_pending_downstream','historical_attempts':len(tables['attempts'])}
        atomic(state/'capture_recovery.json',evidence)
        if target.exists():target.rmdir()
        os.replace(state,target)
        return evidence
