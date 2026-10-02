"""One-writer Jobs dispatcher. Construction performs no remote actions.

Server config, job ACL expectations, boundary/result probes and ledger are trusted
capabilities, not request fields. SQLite is a durable SINGLE HOST test/pilot ledger;
cloud integration must inject a shared atomic ledger. No Volumes atomic rename,
flock distribution, job creation, permission mutation or snapshot publication.
"""
from dataclasses import dataclass
from copy import deepcopy
import hashlib
import json
import re
import sqlite3
from pathlib import Path


def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)
def digest(v):return hashlib.sha256(canonical(v).encode()).hexdigest()
def obj(v):return v.as_dict() if hasattr(v,'as_dict') else v
def require(v,code):
    if not v:raise ValueError(code)


@dataclass(frozen=True)
class WriterConfig:
    job_id:int
    writer_principal:str
    cluster_id:str|None
    notebook_path:str
    release_id:str
    snapshot_backend_id:str
    boundary_policy_id:str
    schedule_enabled:bool=False
    compute_mode:str='existing_cluster'
    environment_version:str|None=None
    environment_dependencies:tuple=()
    def __post_init__(self):
        require(type(self.schedule_enabled) is bool,'SCHEDULE_SETTING_INVALID')
        require(type(self.job_id) is int and self.job_id>0,'JOB_ID_REQUIRED')
        require(all(isinstance(v,str) and v and 'REPLACE' not in v for v in (self.writer_principal,self.notebook_path)),'IDENTITY_COMPUTE_PATH_REQUIRED')
        require(self.compute_mode in ('existing_cluster','serverless'),'COMPUTE_MODE_INVALID')
        if self.compute_mode=='existing_cluster':
            require(isinstance(self.cluster_id,str) and self.cluster_id and 'REPLACE' not in self.cluster_id,'IDENTITY_COMPUTE_PATH_REQUIRED')
            require(self.environment_version is None and self.environment_dependencies==(),'UNUSED_ENVIRONMENT_CONFIG')
        else:
            require(self.cluster_id is None,'SERVERLESS_CLUSTER_CONFLICT')
            require(isinstance(self.environment_version,str) and re.fullmatch('[1-9][0-9]*',self.environment_version),'ENVIRONMENT_VERSION_REQUIRED')
            deps=self.environment_dependencies
            require(type(deps) is tuple and 0<len(deps)<=32 and all(isinstance(d,str) and re.fullmatch(r'[A-Za-z0-9_.-]+==[A-Za-z0-9_.+-]+',d) for d in deps),'PINNED_ENVIRONMENT_REQUIRED')
            names=[re.sub('[-_.]+','-',d.split('==')[0]).lower() for d in deps]
            require(len(names)==len(set(names)),'DUPLICATE_ENVIRONMENT_DEPENDENCY')
        require(self.notebook_path.startswith('/'),'NOTEBOOK_PATH_REQUIRED')
        require(all(isinstance(v,str) and re.fullmatch('[0-9a-f]{64}',v) for v in (self.release_id,self.snapshot_backend_id,self.boundary_policy_id)),'PINNED_CONFIG_REQUIRED')


def job_settings(config):
    """Reviewable Jobs create/reset settings; never submits them. IDs must be observed."""
    settings={'name':'sbs-radar-single-writer','max_concurrent_runs':1,'queue':{'enabled':True},'timeout_seconds':900,
        'run_as':{'service_principal_name':config.writer_principal},
        'schedule':{'quartz_cron_expression':'0 0 8 * * ?','timezone_id':'America/Lima','pause_status':'UNPAUSED' if config.schedule_enabled else 'PAUSED'},
        'parameters':[{'name':'request_id','default':'{{job.run_id}}'},{'name':'release_id','default':config.release_id}],
        'tasks':[{'task_key':'refresh','existing_cluster_id':config.cluster_id,'max_retries':0,'timeout_seconds':600,
            'notebook_task':{'notebook_path':config.notebook_path,'source':'WORKSPACE','base_parameters':{
                'request_id':'{{job.parameters.request_id}}','release_id':'{{job.parameters.release_id}}',
                'job_id':'{{job.id}}','run_id':'{{job.run_id}}','snapshot_backend_id':config.snapshot_backend_id}}}]}
    if config.compute_mode=='serverless':
        task=settings['tasks'][0];task.pop('existing_cluster_id')
        task.update(environment_key='sbs_refresh',disable_auto_optimization=True)
        settings['environments']=[{'environment_key':'sbs_refresh','spec':{
            'environment_version':config.environment_version,'dependencies':list(config.environment_dependencies)}}]
    return settings


class SqliteLedger:
    """Atomic reserve/update ledger for local POSIX disk only, never UC Volumes.

    A cloud replacement must make reserve(key, immutable_record) linearizable,
    reject conflicts, merge updates transactionally, and durably retain run IDs.
    Hostile/untrusted filesystem paths are outside this server-owned dependency.
    """
    def __init__(self,path):
        self.path=Path(path)
        require(not str(path).startswith('/Volumes/'),'LOCAL_LEDGER_ONLY')
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self._db() as db:db.execute('CREATE TABLE IF NOT EXISTS requests (key TEXT PRIMARY KEY, body TEXT NOT NULL)')
    def _db(self):return sqlite3.connect(self.path,timeout=10)
    def get(self,key):
        with self._db() as db:row=db.execute('SELECT body FROM requests WHERE key=?',(key,)).fetchone()
        return json.loads(row[0]) if row else None
    def reserve(self,key,record):
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE');row=db.execute('SELECT body FROM requests WHERE key=?',(key,)).fetchone()
            if row:
                stored=json.loads(row[0]);require(stored['request_hash']==record['request_hash'],'REQUEST_CONFLICT');return stored,False
            db.execute('INSERT INTO requests VALUES (?,?)',(key,canonical(record)));return deepcopy(record),True
    def update(self,key,changes):
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE');row=db.execute('SELECT body FROM requests WHERE key=?',(key,)).fetchone();require(row is not None,'REQUEST_NOT_FOUND');record=json.loads(row[0])
            require(set(changes)<= {'status','run_id','life_cycle_state','result_state','publication_id','error_code','execution_verified'},'LEDGER_FIELDS_INVALID')
            if record.get('run_id') is not None and 'run_id' in changes:require(record['run_id']==changes['run_id'],'RUN_ID_CONFLICT')
            record.update(changes);db.execute('UPDATE requests SET body=? WHERE key=?',(canonical(record),key));return record


class CloudDispatcher:
    def __init__(self,config,jobs,ledger,*,boundary_probe,expected_acl,evidence_mode,result_probe=None):
        require(isinstance(config,WriterConfig) and callable(boundary_probe) and evidence_mode in ('fixture','real'),'SERVER_DEPENDENCIES_REQUIRED')
        self.config=config;self.jobs=jobs;self.ledger=ledger;self.boundary_probe=boundary_probe;self.acl=deepcopy(expected_acl);self.mode=evidence_mode;self.result_probe=result_probe

    def verify(self):
        c=self.config
        try:job=obj(self.jobs.get(job_id=c.job_id));acl=obj(self.jobs.get_permissions(job_id=str(c.job_id)));boundary=obj(self.boundary_probe())
        except Exception:raise ValueError('JOB_VERIFICATION_UNAVAILABLE') from None
        require(job.get('job_id')==c.job_id and not job.get('next_page_token') and job.get('run_as_user_name')==c.writer_principal,'JOB_IDENTITY_MISMATCH')
        settings=job.get('settings',{});expected=job_settings(c)
        require(all(settings.get(k)==v for k,v in expected.items()),'JOB_SETTINGS_MISMATCH')
        forbidden=('continuous','trigger','git_source','job_clusters')
        if c.compute_mode=='existing_cluster':forbidden+=('environments',)
        require(not any(settings.get(k) for k in forbidden),'JOB_EXTRA_EXECUTION_CONFIG')
        require(acl==self.acl,'JOB_ACL_MISMATCH')
        require(isinstance(boundary,dict) and boundary.get('job_id')==c.job_id and boundary.get('writer_principal')==c.writer_principal and boundary.get('evidence_mode')==self.mode and boundary.get('policy_id')==c.boundary_policy_id and boundary.get('snapshot_backend_id')==c.snapshot_backend_id and isinstance(boundary.get('evidence_id'),str) and boundary['evidence_id'] and all(boundary.get(k) is True for k in ('exclusive_writer','ddl_and_acl_controlled','storage_authorized','snapshot_backend_atomic')),'WRITER_BOUNDARY_UNPROVEN')
        return digest({'settings':expected,'acl':acl,'boundary':boundary})

    def _key(self,request_id):
        require(isinstance(request_id,str) and re.fullmatch('[A-Za-z0-9_-]{1,128}',request_id),'REQUEST_ID_INVALID')
        # Stable logical key survives config changes; immutable request hash detects them.
        return digest({'job_id':self.config.job_id,'request_id':request_id})

    def request(self,request_id):
        """Caller first authenticates/authorizes on-demand request IDs. One POST max.

        A submission_unknown record is never retried automatically. Reconciliation
        uses the persisted deterministic token with separate explicit authorization.
        No .result() call on SDK Wait (would hide waiting/terminal semantics).
        """
        key=self._key(request_id);proof=self.verify();c=self.config
        payload={'job_id':c.job_id,'idempotency_token':key,'job_parameters':{'request_id':key,'release_id':c.release_id},'queue':{'enabled':True}}
        contract=digest(job_settings(c))
        record={'request_id':request_id,'request_hash':digest({'payload':payload,'execution_contract_sha256':contract}),'execution_contract_sha256':contract,'job_id':c.job_id,'release_id':c.release_id,'source':'on_demand','idempotency_token':key,'verification_sha256':proof,'evidence_mode':self.mode,'status':'submission_unknown','run_id':None,'cost':None}
        stored,created=self.ledger.reserve(key,record)
        if not created:return stored
        from databricks.sdk.service.jobs import QueueSettings
        try:
            response=self.jobs.run_now(job_id=c.job_id,idempotency_token=key,job_parameters=payload['job_parameters'],queue=QueueSettings(enabled=True))
            response=obj(response.response if hasattr(response,'response') else response)
            if not isinstance(response,dict):response=vars(response)
            run_id=response.get('run_id');require(type(run_id) is int and run_id>0,'RUN_ID_UNAVAILABLE')
        except Exception:return self.ledger.update(key,{'status':'submission_unknown','error_code':'SUBMISSION_UNCONFIRMED'})
        return self.ledger.update(key,{'status':'submitted','run_id':run_id})

    def _run(self,run_id):
        try:run=obj(self.jobs.get_run(run_id=run_id,include_resolved_values=True))
        except Exception:raise ValueError('RUN_OBSERVATION_UNAVAILABLE') from None
        require(run.get('job_id')==self.config.job_id and run.get('run_id')==run_id and not run.get('next_page_token'),'RUN_SCOPE_MISMATCH')
        return run

    def _execution_contract(self,run,record):
        """Actual execution snapshot, not current settings; missing => unverified.

        SDK Run does not expose historical run_as. That remains independently
        governed evidence, never inferred from a fabricated Run field.
        """
        tasks=run.get('tasks')
        if not isinstance(tasks,list) or not tasks:return 'RUN_TASK_METADATA_MISSING'
        if len(tasks)!=1 or not isinstance(tasks[0],dict):return 'RUN_TASK_CLOSURE_MISMATCH'
        t=tasks[0];expected=job_settings(self.config)['tasks'][0]
        if any(t.get(k)!=v for k,v in expected.items()):return 'RUN_TASK_SNAPSHOT_MISMATCH'
        forbidden=('depends_on','new_cluster','job_cluster_key','compute','git_source','libraries','retry_on_timeout')
        forbidden+=('existing_cluster_id',) if self.config.compute_mode=='serverless' else ('environment_key',)
        if any(t.get(k) for k in forbidden) or any(k.endswith('_task') and k!='notebook_task' and v is not None for k,v in t.items()):return 'RUN_EXTRA_EXECUTION_CONFIG'
        if run.get('overriding_parameters') or run.get('git_source') or run.get('job_clusters'):return 'RUN_EXTRA_EXECUTION_CONFIG'
        cluster=t.get('cluster_instance')
        if cluster and (self.config.compute_mode=='serverless' or cluster.get('cluster_id')!=self.config.cluster_id):return 'RUN_COMPUTE_MISMATCH'
        resolved=t.get('resolved_values')
        if not isinstance(resolved,dict) or not isinstance(resolved.get('notebook_task'),dict):return 'RUN_EFFECTIVE_PARAMETERS_MISSING'
        if set(resolved)!={'notebook_task'}:return 'RUN_EXTRA_EXECUTION_CONFIG'
        request=str(record['run_id']) if record['source']=='daily' else record['idempotency_token']
        values={'request_id':request,'release_id':record['release_id'],'job_id':str(record['job_id']),'run_id':str(record['run_id']),'snapshot_backend_id':self.config.snapshot_backend_id}
        if resolved['notebook_task']!={'base_parameters':values}:return 'RUN_EFFECTIVE_PARAMETERS_MISMATCH'
        return None

    def observe_daily(self,run_id):
        """Record an actual native periodic run; does not trigger or synthesize one."""
        require(type(run_id) is int and run_id>0,'RUN_ID_INVALID');proof=self.verify();run=self._run(run_id)
        require(run.get('trigger')=='PERIODIC','DAILY_TRIGGER_REQUIRED')
        request_id='daily-'+str(run_id);key=self._key(request_id)
        contract=digest(job_settings(self.config))
        record={'request_id':request_id,'request_hash':digest({'job_id':self.config.job_id,'run_id':run_id,'release_id':self.config.release_id,'execution_contract_sha256':contract}),'execution_contract_sha256':contract,'job_id':self.config.job_id,'release_id':self.config.release_id,'source':'daily','verification_sha256':proof,'evidence_mode':self.mode,'status':'observed','run_id':run_id,'cost':None}
        self.ledger.reserve(key,record);return self.refresh(request_id)

    def refresh(self,request_id):
        key=self._key(request_id);record=self.ledger.get(key);require(record is not None,'REQUEST_NOT_FOUND')
        require(record.get('execution_contract_sha256')==digest(job_settings(self.config)),'REQUEST_EXECUTION_CONTRACT_CONFLICT')
        if record['run_id'] is None:return record
        self.verify();run=self._run(record['run_id']);params=run.get('job_parameters',[])
        require(not params or isinstance(params,list) and len(params)==2 and {p.get('name'):p.get('value') for p in params}=={'release_id':record['release_id'],'request_id':str(record['run_id']) if record['source']=='daily' else record['idempotency_token']},'RUN_PARAMETERS_MISMATCH')
        state=run.get('state',{});life=state.get('life_cycle_state');result=state.get('result_state')
        require(life in ('PENDING','QUEUED','RUNNING','TERMINATING','TERMINATED','SKIPPED','INTERNAL_ERROR','BLOCKED','WAITING_FOR_RETRY'),'RUN_STATE_UNKNOWN')
        safe_result=result if result in ('SUCCESS','FAILED','TIMEDOUT','CANCELED','SKIPPED','INTERNAL_ERROR','UPSTREAM_FAILED','EXCLUDED','SUCCESS_WITH_FAILURES','DISABLED','MAXIMUM_CONCURRENT_RUNS_REACHED','UPSTREAM_CANCELED') else None
        status='queued' if life=='QUEUED' else 'running'
        if life in ('SKIPPED','INTERNAL_ERROR'):status='job_failed'
        elif life=='TERMINATED':status='job_succeeded_publication_unverified' if result=='SUCCESS' else 'job_failed'
        update={'status':status,'life_cycle_state':life,'result_state':safe_result}
        problem=self._execution_contract(run,record) if params else 'RUN_JOB_PARAMETERS_MISSING'
        update.update(execution_verified=problem is None,error_code=problem,publication_id=None)
        if problem:
            update['status']='execution_contract_not_verified'
            return self.ledger.update(key,update)
        if status=='job_succeeded_publication_unverified' and self.result_probe is not None:
            try:publication=obj(self.result_probe(record['run_id']))
            except Exception:publication=None
            if isinstance(publication,dict) and all(publication.get(k)==record[k] for k in ('job_id','run_id','release_id')) and publication.get('evidence_mode')==self.mode and publication.get('verified') is True and publication.get('status')=='published' and isinstance(publication.get('publication_id'),str) and re.fullmatch('[0-9a-f]{64}',publication['publication_id']):
                update.update(status='publication_verified',publication_id=publication['publication_id'])
        return self.ledger.update(key,update)
