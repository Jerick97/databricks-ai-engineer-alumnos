"""Explicit server-owned binding for a future authorized cloud writer.

No SDK construction or network in preflight. Execution uses generated SDK service
serializers over a bounded single-attempt HTTP transport and normal SDK auth.
Trusted administrator declarations are assumptions, not remotely observed facts.
"""
from dataclasses import dataclass,fields,MISSING
from pathlib import Path
from types import SimpleNamespace
from io import BytesIO
from urllib.parse import urlsplit
import hashlib,json,re,time,sys
from .cloud_dispatch import WriterConfig,CloudDispatcher,canonical,digest,obj,require
from .shared_control import DeltaControl,SharedLedger,SnapshotWriter
from .volume_artifacts import VolumeArtifacts
from .cloud_writer import prepare_and_publish


def sha(raw):return hashlib.sha256(raw).hexdigest()
def hex64(v):return isinstance(v,str) and re.fullmatch('[0-9a-f]{64}',v)

@dataclass(frozen=True)
class DriverConfig:
    writer:WriterConfig
    control_table:str
    control_table_id:str
    warehouse_id:str
    volume_prefix:str
    expected_acl:dict
    policy:dict
    release_manifest:str
    capture_mode:str="sealed"
    capture_state_root:str|None=None

    @classmethod
    def from_dict(cls,data):
        require(isinstance(data,dict) and {f.name for f in fields(cls) if f.default is MISSING}<=set(data)<={f.name for f in fields(cls)},'DRIVER_CONFIG_FIELDS')
        values=dict(data);w=values['writer'];require(isinstance(w,dict) and not(set(w)-{f.name for f in fields(WriterConfig)}),'WRITER_CONFIG_FIELDS')
        w=dict(w)
        if 'environment_dependencies' in w:
            require(isinstance(w['environment_dependencies'],list),'ENVIRONMENT_DEPENDENCIES_INVALID');w['environment_dependencies']=tuple(w['environment_dependencies'])
        try:values['writer']=WriterConfig(**w);return cls(**values)
        except (TypeError,KeyError):raise ValueError('DRIVER_CONFIG_INVALID') from None

    def __post_init__(self):
        require(self.capture_mode in ('sealed','remote'),'CAPTURE_MODE_INVALID')
        require(self.capture_mode!='remote' or isinstance(self.capture_state_root,str) and Path(self.capture_state_root).is_absolute() and not self.capture_state_root.startswith('/Volumes/'),'REMOTE_LOCAL_STATE_REQUIRED')
        require(isinstance(self.writer,WriterConfig),'WRITER_CONFIG_INVALID')
        require(isinstance(self.control_table,str) and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*\.sbs_radar\.[A-Za-z_][A-Za-z0-9_]*',self.control_table),'CONTROL_NAMESPACE_INVALID')
        require(all(isinstance(v,str) and v and 'REPLACE' not in v for v in (self.control_table_id,self.warehouse_id)),'OBSERVED_IDS_REQUIRED')
        require(isinstance(self.volume_prefix,str) and re.fullmatch(r'/Volumes/[A-Za-z0-9_-]+/sbs_radar/[A-Za-z0-9_-]+/sbs-refresh',self.volume_prefix),'VOLUME_PREFIX_INVALID')
        require(self.volume_prefix.split('/')[2]==self.control_table.split('.')[0],'CONTROL_VOLUME_CATALOG_MISMATCH')
        require(isinstance(self.expected_acl,dict) and self.expected_acl.get('object_id')=='/jobs/'+str(self.writer.job_id) and isinstance(self.expected_acl.get('access_control_list'),list),'JOB_ACL_REQUIRED')
        require(isinstance(self.policy,dict) and set(self.policy)=={'trusted_administrators','maintenance','exclusive_writer','singleton_control','storage_authorized','issued_at_ms','expires_at_ms'},'ADMIN_POLICY_INVALID')
        p=self.policy
        require(isinstance(p['trusted_administrators'],list) and p['trusted_administrators'] and all(isinstance(v,str) and v for v in p['trusted_administrators']),'ADMIN_POLICY_INVALID')
        require(all(isinstance(p[k],str) and p[k].strip() for k in ('maintenance','exclusive_writer','singleton_control','storage_authorized')),'ADMIN_ASSUMPTIONS_REQUIRED')
        require(all(type(p[k]) is int and p[k]>=0 for k in ('issued_at_ms','expires_at_ms')) and p['expires_at_ms']>p['issued_at_ms'],'ADMIN_POLICY_TIME_INVALID')
        require(digest(p)==self.writer.boundary_policy_id,'ADMIN_POLICY_PIN_MISMATCH')
        require(digest(self.backend_identity())==self.writer.snapshot_backend_id,'BACKEND_PIN_MISMATCH')
        require(isinstance(self.release_manifest,str) and not self.release_manifest.startswith('/') and all(re.fullmatch('[A-Za-z0-9_.-]+',x) and x not in ('.','..') for x in self.release_manifest.split('/')),'RELEASE_MANIFEST_PATH_INVALID')

    def backend_identity(self):return dict(control_table=self.control_table,control_table_id=self.control_table_id,warehouse_id=self.warehouse_id,volume_prefix=self.volume_prefix)


def preflight(config):
    """Local-only readiness explanation; does not instantiate SDK/authenticate."""
    if config is None:return {'status':'pending_configuration','missing':['observed Job/run and compute configuration','dedicated Delta table identity and preseed','authorized Volume prefix','pinned Job ACL and trusted-administrator declarations','release manifest hash and server config hash'],'cloud_executed':False,'cost':None}
    if not isinstance(config,DriverConfig):config=DriverConfig.from_dict(config)
    return {'status':'configured_not_verified','cloud_executed':False,'compute_mode':getattr(config.writer,'compute_mode','existing_cluster'),'capture_mode':config.capture_mode,'schedule_enabled':config.writer.schedule_enabled,'pending':['current SDK metadata/ACL/subject observations','Serializable property and exact singleton SQL readback','authorized writer execution and complete artifact readback'],'cost':None}


class SafeHttpError(ValueError):
    def __init__(self,code):super().__init__('SDK_HTTP_FAILED');self.error_code=code


class SingleAttemptApi:
    """Generated SDK service .do interface, one HTTP send, no retry or redirects.

    Authentication may refresh OAuth by the normal SDK mechanism. This transport
    does not claim a limit on auth-provider internal traffic, only workspace API
    requests. No retry_timeout_seconds=0 fiction (SDK treats it as its default).
    """
    def __init__(self,config,*,session=None,max_calls=4000,max_response_bytes=32*1024*1024):
        import requests
        u=urlsplit(config.host)
        require(u.scheme=='https' and u.hostname and u.path in ('','/') and not any((u.username,u.password,u.query,u.fragment)),'WORKSPACE_HOST_INVALID')
        require(type(max_calls) is int and 0<max_calls<=4000 and type(max_response_bytes) is int and 0<max_response_bytes<=32*1024*1024,'HTTP_CAP_INVALID')
        self._cfg=config;self.session=session or requests.Session();self.calls=0;self.max_calls=max_calls;self.max_bytes=max_response_bytes
        if session is None:
            for adapter in self.session.adapters.values():require(adapter.max_retries.total==0,'HTTP_RETRIES_NOT_DISABLED')
    def do(self,method,path=None,*,query=None,headers=None,body=None,raw=False,data=None,response_headers=None,**extra):
        require(not extra and isinstance(path,str) and path.startswith('/api/') and '..' not in path and '?' not in path and '#' not in path,'SDK_PATH_INVALID')
        allowed=(method=='GET' or (method=='POST' and path=='/api/2.0/sql/statements') or (method=='PUT' and path.startswith(('/api/2.0/fs/files/Volumes/','/api/2.0/fs/directories/Volumes/'))))
        require(allowed,'SDK_OPERATION_NOT_ALLOWED');require(self.calls<self.max_calls,'SDK_QUOTA_EXCEEDED');self.calls+=1
        params={k:str(v).lower() if type(v) is bool else v for k,v in (query or {}).items()}
        try:
            response=self.session.request(method,self._cfg.host.rstrip('/')+path,params=params,headers={**(headers or {}),**self._cfg.authenticate()},json=body,data=data,timeout=(10,60),allow_redirects=False,stream=True)
        except Exception:raise ValueError('SDK_TRANSPORT_UNCONFIRMED') from None
        try:
            if not 200<=response.status_code<300:
                # Existing file conflict is the only error requiring reconciliation.
                raise SafeHttpError('RESOURCE_ALREADY_EXISTS' if response.status_code==409 and method=='PUT' else 'UNCLASSIFIED_ERROR')
            try:content=response.raw.read(self.max_bytes+1,decode_content=True)
            except Exception:raise ValueError('SDK_RESPONSE_READ_UNCONFIRMED') from None
            require(len(content)<=self.max_bytes,'SDK_RESPONSE_CAP_EXCEEDED')
            if raw:return {'contents':BytesIO(content),**{k:response.headers.get(k) for k in (response_headers or [])}}
            if not content:return {}
            try:return json.loads(content)
            except Exception:raise ValueError('SDK_JSON_INVALID') from None
        finally:
            # Cleanup must not leak provider text or mask an existing safe code.
            failed=sys.exc_info()[0] is not None
            try:response.close()
            except Exception:
                if not failed:raise ValueError('SDK_RESPONSE_CLOSE_UNCONFIRMED') from None


def sdk_services(config,*,session=None):
    """Normal Config.authenticate; generated serializers, no WorkspaceClient retry layer."""
    from databricks.sdk.service.jobs import JobsAPI
    from databricks.sdk.service.catalog import TablesAPI
    from databricks.sdk.service.sql import StatementExecutionAPI,WarehousesAPI
    from databricks.sdk.service.compute import ClustersAPI
    from databricks.sdk.service.iam import CurrentUserAPI
    from databricks.sdk.service.files import FilesAPI
    api=SingleAttemptApi(config,session=session)
    return SimpleNamespace(api=api,jobs=JobsAPI(api),tables=TablesAPI(api),statement_execution=StatementExecutionAPI(api),warehouses=WarehousesAPI(api),clusters=ClustersAPI(api),current_user=CurrentUserAPI(api),files=FilesAPI(api))


class CloudDriver:
    def __init__(self,config,services,*,evidence_mode,clock=None):
        require(isinstance(config,DriverConfig) and evidence_mode in ('fixture','real'),'DRIVER_DEPENDENCIES_REQUIRED')
        self.config=config;self.services=services;self.mode=evidence_mode;self.clock=clock or (lambda:int(time.time()*1000));self.observations={}
        self.control=DeltaControl(services.statement_execution,table=config.control_table,warehouse_id=config.warehouse_id,identity_probe=self.identity,expected_table_id=config.control_table_id)
        self.ledger=SharedLedger(self.control)
        self.artifacts=VolumeArtifacts(services.files,prefix=config.volume_prefix)
        self.dispatcher=CloudDispatcher(config.writer,services.jobs,self.ledger,boundary_probe=self.boundary,expected_acl=config.expected_acl,evidence_mode=evidence_mode)
        self.writer=SnapshotWriter(self.control,job_id=config.writer.job_id,writer_guard=self.writer_guard,artifact_validator=self.artifacts.verify,artifact_prefix=config.volume_prefix)
    def _policy(self):
        p=self.config.policy;require(digest(p)==self.config.writer.boundary_policy_id,'ADMIN_POLICY_PIN_MISMATCH');now=self.clock()
        require(type(now) is int and p['issued_at_ms']<=now<=p['expires_at_ms'],'ADMIN_POLICY_EXPIRED')
        return p
    def identity(self):
        c=self.config;p=self._policy()
        try:t=obj(self.services.tables.get(c.control_table,include_browse=False));warehouse=obj(self.services.warehouses.get(c.warehouse_id))
        except Exception:raise ValueError('CONTROL_METADATA_UNAVAILABLE') from None
        require(isinstance(t,dict) and t.get('full_name')==c.control_table and t.get('table_id')==c.control_table_id and t.get('table_type')=='MANAGED' and t.get('data_source_format')=='DELTA' and t.get('browse_only') is not True,'CONTROL_TABLE_IDENTITY_MISMATCH')
        require(t.get('owner') in p['trusted_administrators'] and t.get('properties',{}).get('delta.isolationLevel')=='Serializable','CONTROL_SERIALIZABLE_NOT_OBSERVED')
        require(not t.get('row_filter') and isinstance(t.get('columns'),list) and t['columns'] and all(isinstance(col,dict) and not col.get('mask') for col in t['columns']),'CONTROL_POLICY_UNSUPPORTED')
        require(isinstance(warehouse,dict) and warehouse.get('id')==c.warehouse_id and warehouse.get('state')=='RUNNING','WAREHOUSE_NOT_RUNNING')
        evidence={'uc_table_id':t['table_id'],'owner':t['owner'],'table_metadata_sha256':digest(t),'isolation':t['properties']['delta.isolationLevel'],'warehouse_state':warehouse['state'],'observed_at_ms':self.clock()}
        self.observations['control']=evidence
        return {'table_id':t['table_id'],'format':'delta','isolation':t['properties']['delta.isolationLevel'],'singleton_admin_controlled':True,'basis':'observed_metadata_plus_pinned_trusted_admin_assumption','singleton_rows':'verified_separately_by_DeltaControl_SELECT_limit2','evidence_id':digest(evidence)}
    def boundary(self):
        # No invented audit capability: explicit pinned admin policy + observed IDs.
        c=self.config;p=self._policy();identity=self.identity()
        return {'job_id':c.writer.job_id,'writer_principal':c.writer.writer_principal,'evidence_mode':self.mode,'policy_id':c.writer.boundary_policy_id,'snapshot_backend_id':c.writer.snapshot_backend_id,'evidence_id':digest({'identity':identity,'policy':p}),'exclusive_writer':True,'ddl_and_acl_controlled':True,'storage_authorized':True,'snapshot_backend_atomic':True,'basis':'trusted_administrator_declarations_not_global_exclusivity_scan','assumptions':p}
    def writer_guard(self,job_id,run_id):
        c=self.config;require(type(job_id) is int and job_id==c.writer.job_id and type(run_id) is int and run_id>0,'WRITER_ID_INVALID')
        self.dispatcher.verify();run=self.dispatcher._run(run_id)
        require(type(run.get('job_id')) is int and type(run.get('run_id')) is int,'RUN_ID_TYPE_INVALID')
        try:me=obj(self.services.current_user.me())
        except Exception:raise ValueError('EXECUTOR_OBSERVATION_UNAVAILABLE') from None
        require(isinstance(me,dict) and me.get('active') is True and me.get('userName',me.get('user_name'))==c.writer.writer_principal,'EXECUTOR_IDENTITY_MISMATCH')
        if getattr(c.writer,'compute_mode','existing_cluster')=='existing_cluster':
            cluster=obj(self.services.clusters.get(c.writer.cluster_id));require(cluster.get('cluster_id')==c.writer.cluster_id and cluster.get('state')=='RUNNING','CLUSTER_NOT_RUNNING')
        require(run.get('state',{}).get('life_cycle_state')=='RUNNING','WRITER_RUN_NOT_RUNNING')
        _,state=self.control.read();records=[r for r in state['requests'].values() if r.get('job_id')==job_id and r.get('run_id')==run_id]
        require(len(records)==1 and records[0].get('release_id')==c.writer.release_id and records[0].get('evidence_mode')==self.mode,'RUN_REGISTRATION_INVALID')
        require(self.dispatcher._execution_contract(run,records[0]) is None,'RUN_EXECUTION_CONTRACT_UNVERIFIED')
        self.observations['run']={'job_id':job_id,'run_id':run_id,'executor':c.writer.writer_principal,'run_sha256':digest(run),'observed_at_ms':self.clock(),'historical_run_as':'not_exposed_by_SDK'}
        return True
    def execute(self,project_root,plan,*,run_id,local_parent=None):
        c=self.config;root=Path(project_root).resolve();path=root/c.release_manifest
        require(path.resolve().is_relative_to(root) and not path.is_symlink(),'RELEASE_MANIFEST_ESCAPE')
        raw=path.read_bytes();require(sha(raw)==c.writer.release_id,'RELEASE_PIN_MISMATCH');m=json.loads(raw)
        require(isinstance(m,dict) and isinstance(m.get('files'),dict) and m['files'],'RELEASE_MANIFEST_INVALID')
        for relative,expected in m['files'].items():
            p=root/relative;require(isinstance(relative,str) and not Path(relative).is_absolute() and '..' not in Path(relative).parts and p.resolve().is_relative_to(root) and not p.is_symlink() and sha(p.read_bytes())==expected,'RELEASE_FILE_MISMATCH')
        # Daily runs have no on-demand ledger reservation. Observe/register that
        # actual periodic run using existing dispatcher checks; never starts a Job.
        self.dispatcher.verify();run=self.dispatcher._run(run_id)
        if run.get('trigger')=='PERIODIC':self.dispatcher.observe_daily(run_id)
        self.writer_guard(c.writer.job_id,run_id)
        result=prepare_and_publish(root,plan,run_id=run_id,artifact_store=self.artifacts,writer=self.writer,local_parent=local_parent,capture_mode=c.capture_mode,capture_state_root=c.capture_state_root)
        return {**result,'evidence_mode':self.mode,'observations':self.observations,'admin_assumptions':c.policy,'cloud_acceptance':False}


def bind_driver(config,services,*,evidence_mode,clock=None):return CloudDriver(config,services,evidence_mode=evidence_mode,clock=clock)


def load_config(path,expected_sha256):
    """Server-delivered file and pin; never accepts credentials in this schema."""
    require(hex64(expected_sha256),'CONFIG_PIN_REQUIRED');p=Path(path)
    require(p.is_file() and not p.is_symlink() and p.stat().st_size<=65536,'CONFIG_FILE_INVALID')
    raw=p.read_bytes();require(sha(raw)==expected_sha256,'CONFIG_PIN_MISMATCH')
    try:data=json.loads(raw)
    except Exception:raise ValueError('CONFIG_JSON_INVALID') from None
    return DriverConfig.from_dict(data)


def execute_from_config(config,project_root,*,job_id,run_id,release_id,profile=None):
    """Future authorized notebook binding. Calling this may issue SQL/files writes.

    IDs originate from trusted Jobs dynamic context, corroborated against current
    authenticated subject and Jobs API, not treated as authentication themselves.
    """
    require(type(job_id) is int and job_id==config.writer.job_id and type(run_id) is int and run_id>0 and release_id==config.writer.release_id,'JOB_CONTEXT_MISMATCH')
    from databricks.sdk.core import Config
    from . import load_sealed_plan
    from dataclasses import replace
    root=Path(project_root).resolve();plan=load_sealed_plan(root)
    pairs_config=json.loads((root/'config/genie-pilot-002.json').read_bytes());pairs={v['pair']['pair_id']:v['pair'] for v in pairs_config['contexts']};plan=replace(plan,pairs=tuple(pairs.values()))
    # No credentials are printed/persisted; normal SDK profile or default auth.
    cfg=Config(profile=profile) if profile else Config()
    services=sdk_services(cfg)
    try:return bind_driver(config,services,evidence_mode='real').execute(root,plan,run_id=run_id)
    finally:services.api.session.close()
