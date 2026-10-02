"""Offline provisioning payloads and a single-host, durable one-effect executor.

No clients, authentication or network at import/build time. Callbacks are trusted
server capabilities: authorize rechecks current approval and budget; observe must
GET/read back and validate the exact step, returning None only for proven absence.
This local journal is not distributed fencing. Use one controlled provisioning host.
"""
from pathlib import Path
from types import SimpleNamespace
import fcntl, json, os
from .cloud_dispatch import canonical, digest, require, job_settings
from .shared_control import initial_state

TABLE='neptuno_manuel_arguelles.sbs_radar.refresh_control'
WAREHOUSE='828756322bedff37'
PRINCIPAL='33b6f37c-7e6a-489f-b313-f886418b0319'
DEPENDENCIES=('jsonschema==4.26.0','pypdf==6.13.3','requests==2.32.5','databricks-sdk==0.102.0','numpy==2.4.3','tokenizers==0.22.2','sqlglot==30.20.0')

def control_steps():
    create=f"CREATE TABLE {TABLE} (control_id STRING NOT NULL, revision BIGINT NOT NULL, state_json STRING NOT NULL) USING DELTA TBLPROPERTIES ('delta.isolationLevel' = 'Serializable')"
    seed=f"INSERT INTO {TABLE} VALUES ('control', 0, '{canonical(initial_state())}')"
    return [{'step_id':name,'operation':'sql_once','payload':{'warehouse_id':WAREHOUSE,'statement':sql},'precondition':condition} for name,sql,condition in (
        ('create_control',create,'fresh GET TABLE_DOES_NOT_EXIST; warehouse RUNNING; authorized exact DDL'),
        ('seed_control',seed,'same GET-bound table ID; exact schema/Serializable/owner; whole-table SELECT proves zero rows; exclusive administrator maintenance'))]

def creation_settings(*,notebook_path,release_id,snapshot_backend_id,boundary_policy_id):
    # Creation has no observed Job ID yet; never instantiate WriterConfig with a fake ID.
    import re
    require(isinstance(notebook_path,str) and notebook_path.startswith('/Shared/sbs-radar/') and '..' not in notebook_path,'NOTEBOOK_NAMESPACE_INVALID')
    require(all(isinstance(v,str) and re.fullmatch('[0-9a-f]{64}',v) for v in (release_id,snapshot_backend_id,boundary_policy_id)),'OBSERVED_BINDINGS_REQUIRED')
    return job_settings(SimpleNamespace(writer_principal=PRINCIPAL,notebook_path=notebook_path,release_id=release_id,snapshot_backend_id=snapshot_backend_id,boundary_policy_id=boundary_policy_id,schedule_enabled=False,compute_mode='serverless',cluster_id=None,environment_version='4',environment_dependencies=DEPENDENCIES))

def _write_new(path,value):
    raw=(canonical(value)+'\n').encode()
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    try:
        with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
        parent=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(parent)
        finally:os.close(parent)
    except Exception:raise ValueError('JOURNAL_PERSISTENCE_FAILED') from None

def step_once(journal,step,*,authorize,observe,effect):
    """Execute one approved immutable step. Ambiguity permits only observation.

    authorize must approve digest(step), immutable payload, current identity,
    prerequisites and window before *each* effect. effect must disable retries;
    its response never establishes success. observe validates complete metadata,
    SQL singleton or file bytes as appropriate; an exception blocks/reconciles.
    No shipped remote adapter: root review must supply and pin these capabilities.
    """
    require(isinstance(step,dict) and set(step)=={'step_id','operation','payload','precondition'},'STEP_INVALID')
    require(step['step_id'] in ('create_control','seed_control','import_notebook','upload_bundle','upload_config','create_job','set_job_acl'),'STEP_NOT_ALLOWED')
    require(all(callable(c) for c in (authorize,observe,effect)),'CAPABILITIES_REQUIRED')
    authorize()
    root=Path(journal).absolute()
    require(root.is_dir() and all(not p.is_symlink() for p in (root,*root.parents)),'JOURNAL_DIRECTORY_INVALID')
    key=digest(step); intent=root/(key+'.intent.json'); receipt=root/(key+'.observed.json')
    # A single root lock also serializes different payloads for the same step name.
    lock=os.open(root/'.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    try:
        fcntl.flock(lock,fcntl.LOCK_EX)
        for p in root.glob('*.intent.json'):
            require(not p.is_symlink(),'JOURNAL_SYMLINK')
            previous=json.loads(p.read_bytes())
            require(previous['step']['step_id']!=step['step_id'] or previous['step_sha256']==key,'STEP_PLAN_CONFLICT')
        observed=observe()
        if observed is not None:
            require(isinstance(observed,dict) and observed,'OBSERVATION_INVALID')
            result={'status':'confirmed_by_readback','step_sha256':key,'observation':observed,'cloud_acceptance':False}
            if not receipt.exists():_write_new(receipt,result)
            return result
        if intent.exists():return {'status':'outcome_unknown','step_sha256':key,'action':'readback_only','cloud_acceptance':False}
        authorize()
        _write_new(intent,{'step_sha256':key,'step':step,'status':'intent_before_effect'})
        try:
            authorize() # window may have expired during durable persistence
            effect(json.loads(canonical(step['payload'])))
        except Exception:
            return {'status':'outcome_unknown','step_sha256':key,'action':'readback_only','cloud_acceptance':False}
        try:observed=observe()
        except Exception:observed=None
        if observed is None:return {'status':'outcome_unknown','step_sha256':key,'action':'readback_only','cloud_acceptance':False}
        require(isinstance(observed,dict) and observed,'OBSERVATION_INVALID')
        result={'status':'confirmed_by_readback','step_sha256':key,'observation':observed,'cloud_acceptance':False}
        _write_new(receipt,result)
        return result
    finally:os.close(lock)
