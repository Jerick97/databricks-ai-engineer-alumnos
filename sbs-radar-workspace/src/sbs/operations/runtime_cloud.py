"""Lazy read-only cloud current -> verified local candidate -> runtime promotion.

Server-owned configuration and adapters; no credentials or resource IDs from HTTP.
Polling is request driven, throttled and finite. Trusted administrator continuity
is a declared assumption, not a historical fact proven by a current metadata GET.
"""
from copy import deepcopy
import json
from pathlib import Path
import re
import threading
import time
from types import SimpleNamespace
from .cloud_dispatch import digest,obj,require
from .cloud_driver import SingleAttemptApi
from .shared_control import DeltaControl
from .volume_artifacts import VolumeArtifacts
from .runtime_release import materialize_release
from sbs.genie.server import workspace_host

FIELDS={'version','enabled','workspace_host','client_id','executor_id','control_table','control_table_id','warehouse_id','volume_prefix','backend_sha256','policy','policy_sha256','poll_seconds','max_polls','max_promotions','max_http_calls','max_sql_statements','max_files_calls','cache_root'}
POLICY={'trusted_administrators','maintenance','singleton_control','reader_access','issued_at_ms','expires_at_ms'}

def validate_config(value):
    require(isinstance(value,dict) and type(value.get('enabled')) is bool,'RUNTIME_CLOUD_CONFIG_INVALID')
    if not value['enabled']:
        require(set(value)=={'enabled'},'RUNTIME_CLOUD_CONFIG_INVALID');return deepcopy(value)
    require(set(value)==FIELDS and type(value['version']) is int and value['version']==1,'RUNTIME_CLOUD_CONFIG_INVALID')
    c=deepcopy(value);workspace_host(c['workspace_host'])
    require(isinstance(c['client_id'],str) and re.fullmatch('[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}',c['client_id']) and type(c['executor_id']) is int and c['executor_id']>0,'READER_PRINCIPAL_REQUIRED')
    require(isinstance(c['control_table'],str) and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*\.sbs_radar\.[A-Za-z_][A-Za-z0-9_]*',c['control_table']),'READER_NAMESPACE_INVALID')
    require(all(isinstance(c[k],str) and re.fullmatch('[A-Za-z0-9_-]{1,128}',c[k]) and 'REPLACE' not in c[k] for k in ('control_table_id','warehouse_id')),'READER_OBSERVED_IDS_REQUIRED')
    require(isinstance(c['volume_prefix'],str) and re.fullmatch(r'/Volumes/[A-Za-z0-9_-]+/sbs_radar/[A-Za-z0-9_-]+/sbs-refresh',c['volume_prefix']) and c['volume_prefix'].split('/')[2]==c['control_table'].split('.')[0],'READER_VOLUME_INVALID')
    require(c['backend_sha256']==digest({k:c[k] for k in ('control_table','control_table_id','warehouse_id','volume_prefix')}),'READER_BACKEND_PIN_MISMATCH')
    p=c['policy'];require(isinstance(p,dict) and set(p)==POLICY and digest(p)==c['policy_sha256'],'READER_POLICY_PIN_MISMATCH')
    require(isinstance(p['trusted_administrators'],list) and p['trusted_administrators'] and all(isinstance(x,str) and x for x in p['trusted_administrators']),'READER_POLICY_INVALID')
    require(all(isinstance(p[k],str) and p[k].strip() for k in ('maintenance','singleton_control','reader_access')) and all(type(p[k]) is int and p[k]>=0 for k in ('issued_at_ms','expires_at_ms')) and p['expires_at_ms']>p['issued_at_ms'],'READER_POLICY_INVALID')
    for key,maximum in [('poll_seconds',86400),('max_polls',1000),('max_promotions',32),('max_http_calls',4000),('max_sql_statements',1000),('max_files_calls',3000)]:
        require(type(c[key]) is int and 0<c[key]<=maximum,'READER_QUOTA_INVALID')
    require(isinstance(c['cache_root'],str) and c['cache_root'] and not Path(c['cache_root']).is_absolute() and all(re.fullmatch('[A-Za-z0-9_.-]+',p) and p not in ('.','..') for p in c['cache_root'].split('/')),'READER_CACHE_PATH_INVALID')
    return c


def select_statement(c):return 'SELECT control_id, revision, state_json FROM '+'.'.join('`'+x+'`' for x in c['control_table'].split('.'))


class ReadOnlyApi(SingleAttemptApi):
    """Exact control SELECT only; generated SDK writes fail before authentication.

    Backend SELECT/READ VOLUME grants are still required, not proven by this gate.
    """
    def __init__(self,cfg,c,*,session=None):
        super().__init__(cfg,session=session,max_calls=c['max_http_calls']);self.c=deepcopy(c)
    def do(self,method,path=None,**kw):
        c=self.c
        if method=='POST':
            body=kw.get('body')
            require(path=='/api/2.0/sql/statements' and isinstance(body,dict) and body.get('statement')==select_statement(c) and body.get('warehouse_id')==c['warehouse_id'] and not body.get('parameters') and set(body)<={'statement','warehouse_id','parameters','disposition','format','wait_timeout','row_limit','byte_limit'},'READER_WRITE_FORBIDDEN')
        else:
            exact={f"/api/2.1/unity-catalog/tables/{c['control_table']}",f"/api/2.0/sql/warehouses/{c['warehouse_id']}",'/api/2.0/preview/scim/v2/Me'}
            require(method=='GET' and isinstance(path,str) and (path in exact or re.fullmatch(r'/api/2.0/sql/statements/[A-Za-z0-9_-]+',path) or path.startswith('/api/2.0/fs/files'+c['volume_prefix']+'/runs/')),'READER_WRITE_FORBIDDEN')
        return super().do(method,path,**kw)


class CloudSnapshotReader:
    """Only current/read capability exported; no shared ledger/writer/cas API."""
    def __init__(self,c,services,*,evidence_mode,clock_ms=None):
        self._c=validate_config(c);self._services=services;self.evidence_mode=evidence_mode
        require(evidence_mode in ('real','fixture'),'READER_EVIDENCE_MODE_INVALID')
        self.clock_ms=clock_ms or (lambda:int(time.time()*1000))
        self._control=DeltaControl(services.statement_execution,table=c['control_table'],warehouse_id=c['warehouse_id'],identity_probe=self._identity,expected_table_id=c['control_table_id'],max_statements=c['max_sql_statements'])
        self.artifacts=VolumeArtifacts(services.files,prefix=c['volume_prefix'],max_calls=c['max_files_calls'])
    def _identity(self):
        c=self._c;p=c['policy'];now=self.clock_ms()
        require(type(now) is int and p['issued_at_ms']<=now<=p['expires_at_ms'],'READER_POLICY_EXPIRED')
        me=obj(self._services.current_user.me())
        require(isinstance(me,dict) and me.get('active') is True and me.get('id')==str(c['executor_id']) and me.get('userName',me.get('user_name'))==c['client_id'],'READER_PRINCIPAL_MISMATCH')
        table=obj(self._services.tables.get(c['control_table'],include_browse=False));w=obj(self._services.warehouses.get(c['warehouse_id']))
        require(isinstance(table,dict) and table.get('full_name')==c['control_table'] and table.get('table_id')==c['control_table_id'] and table.get('data_source_format')=='DELTA' and table.get('table_type')=='MANAGED' and table.get('browse_only') is not True,'READER_TABLE_MISMATCH')
        require(table.get('owner') in p['trusted_administrators'] and table.get('properties',{}).get('delta.isolationLevel')=='Serializable' and not table.get('row_filter') and isinstance(table.get('columns'),list) and table['columns'] and all(isinstance(x,dict) and not x.get('mask') for x in table['columns']),'READER_TABLE_POLICY_UNAVAILABLE')
        require(isinstance(w,dict) and w.get('id')==c['warehouse_id'] and w.get('state')=='RUNNING','READER_WAREHOUSE_NOT_RUNNING')
        return {'table_id':table['table_id'],'format':'delta','isolation':'Serializable','singleton_admin_controlled':True,'basis':'observed_current_metadata_plus_trusted_admin_assumptions'}
    def current(self):
        _,state=self._control.read()
        return deepcopy(state['current'])


def sdk_reader(c):
    """Lazy factory: validate all host/config pins BEFORE SDK credential construction."""
    c=validate_config(c)
    from databricks.sdk.core import Config
    from databricks.sdk.service.catalog import TablesAPI
    from databricks.sdk.service.sql import StatementExecutionAPI,WarehousesAPI
    from databricks.sdk.service.iam import CurrentUserAPI
    from databricks.sdk.service.files import FilesAPI
    cfg=Config(host=c['workspace_host'],auth_type='oauth-m2m',http_timeout_seconds=30)
    require(cfg.host.rstrip('/')==c['workspace_host'].rstrip('/') and cfg.auth_type=='oauth-m2m' and cfg.client_id==c['client_id'],'READER_OAUTH_IDENTITY_MISMATCH')
    api=ReadOnlyApi(cfg,c)
    services=SimpleNamespace(tables=TablesAPI(api),statement_execution=StatementExecutionAPI(api),warehouses=WarehousesAPI(api),current_user=CurrentUserAPI(api),files=FilesAPI(api))
    return CloudSnapshotReader(c,services,evidence_mode='real')


class RuntimeCloudRefresh:
    def __init__(self,service,root,c,*,reader_factory=None,clock=None):
        self.service=service;self.root=Path(root).resolve();self.c=validate_config(c);self.factory=reader_factory or sdk_reader;self.clock=clock or time.monotonic
        self.reader=None;self._lock=threading.Lock();self._last_poll=None;self.promotions=0
        self.state={'enabled':True,'status':'pending','reason':'CLOUD_NOT_CHECKED','last_checked_at':None,'last_success_at':None,'publication_id':None,'checks':0,'evidence_mode':'not_observed'}
        target=self.root/self.c['cache_root']
        require(not any(p.is_symlink() for p in (target,*target.parents) if p.is_relative_to(self.root)) and target.resolve().is_relative_to(self.root),'READER_CACHE_PATH_INVALID')
        self.destination=target
    def status(self):return deepcopy(self.state)
    def refresh_if_due(self):
        # Another request continues with its previous verified runtime while polling.
        if not self._lock.acquire(blocking=False):return self.status()
        try:
            tick=self.clock()
            if self._last_poll is not None and tick-self._last_poll<self.c['poll_seconds']:return self.status()
            if self.state['checks']>=self.c['max_polls']:
                self.state.update(status='quota_exhausted',reason='POLL_QUOTA_EXHAUSTED');return self.status()
            self._last_poll=tick
            from datetime import datetime,timezone
            now=datetime.now(timezone.utc).isoformat();self.state.update(checks=self.state['checks']+1,last_checked_at=now)
            try:
                if self.reader is None:self.reader=self.factory(deepcopy(self.c))
                receipt=self.reader.current();self.state['evidence_mode']=self.reader.evidence_mode
                if receipt is None:
                    self.state.update(status='pending',reason='NO_PUBLISHED_RELEASE');return self.status()
                if receipt['publication_id']==self.state['publication_id']:
                    self.state.update(status='current',reason=None,last_success_at=now);return self.status()
                if self.promotions>=self.c['max_promotions']:
                    self.state.update(status='quota_exhausted',reason='PROMOTION_QUOTA_EXHAUSTED');return self.status()
                local=materialize_release(self.reader.artifacts,receipt,self.destination)
                try:
                    with self.service.lock:
                        self.service.promote_release(local['state_root'],pointer=local['pointer'])
                        self.promotions+=1
                        self.state.update(status='current',reason=None,last_success_at=now,publication_id=receipt['publication_id'])
                except Exception:
                    import shutil
                    shutil.rmtree(local['state_root']);raise
            except Exception:
                # Never serialize SDK/provider text, URLs, credentials or raw SQL.
                self.state.update(status='unavailable',reason='CLOUD_REFRESH_FAILED')
            return self.status()
        finally:self._lock.release()


def attach_cloud_refresh(service,root,*,config_path=None,reader_factory=None,clock=None):
    path=Path(config_path) if config_path is not None else Path(root)/'config/runtime-cloud.json'
    if not path.exists():service.cloud_refresh=None;return service
    require(not path.is_symlink() and path.stat().st_size<=65536,'RUNTIME_CLOUD_CONFIG_INVALID')
    try:c=validate_config(json.loads(path.read_bytes()))
    except Exception:raise ValueError('RUNTIME_CLOUD_CONFIG_INVALID') from None
    if not c['enabled']:service.cloud_refresh=None;return service
    require(service.mode=='cloud','CLOUD_READER_REQUIRES_CLOUD_MODE')
    service.cloud_refresh=RuntimeCloudRefresh(service,root,c,reader_factory=reader_factory,clock=clock)
    return service
