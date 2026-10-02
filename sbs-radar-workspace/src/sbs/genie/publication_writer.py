"""Explicit, resumable, single-attempt publication of a sealed eight-table export.

Server capabilities only. No SQL/network in plan/preflight. An ambiguous mutation
is NEVER submitted again: subsequent calls observe its exact effect or stay
pending. Existing unrelated tables are never adopted, overwritten or dropped.
Trusted administrators and exclusive publication maintenance are assumptions,
not history inferred from current metadata. This does not create a Genie space.
"""
from dataclasses import dataclass, asdict, replace
from pathlib import Path
from urllib.parse import urlsplit
import fcntl,json,re,time
from . import TABLES,COLUMNS,canonical,digest
from .publication import require,sha,obj,prepare_plan,PublicationReader,CertificateStore,_rows,STRICT_IDENTITY_PROFILE,identity_profile_check
from .publication_registry import _directory,_read,_append,PublisherPolicy,HistoryRegistryBuilder,RegistryAdmin


def quote(name):return '.'.join('`'+v+'`' for v in name.split('.'))
def now_ms():return int(time.time()*1000)
def text(v):return isinstance(v,str) and bool(v.strip())
def hash64(v):return isinstance(v,str) and re.fullmatch('[0-9a-f]{64}',v) is not None


@dataclass(frozen=True)
class WritePlan:
    payload:bytes
    @property
    def sha256(self):return sha(self.payload)
    def as_dict(self):return json.loads(self.payload)


def _plan(config,bundle,mapping,publication_id):
    require(isinstance(publication_id,str) and re.fullmatch('[a-zA-Z0-9_-]{8,64}',publication_id),'PUBLICATION_ID_INVALID')
    # Validate the existing export contract; zero here is validation scaffolding,
    # never a proposed or certified remote version.
    validated=prepare_plan(config,bundle,{t:0 for t in TABLES}).as_dict()
    tables=[]
    for t in validated['tables']:
        name=t['logical_name'];rows=bundle['tables'][name];parameters=[];values=[]
        for i,row in enumerate(rows):
            cells=[]
            for c in COLUMNS:
                v=row[c]
                if v is None:cells.append('NULL')
                elif type(v) is bool:cells.append('TRUE' if v else 'FALSE')
                else:
                    key=f'p{i}_{c}';cells.append(':'+key);parameters.append(dict(name=key,type='STRING',value=v))
            values.append('('+', '.join(cells)+')')
        require(rows,'EMPTY_EXPORT_TABLE_UNSUPPORTED')
        full=t['full_name'];q=quote(full)
        create='CREATE TABLE '+q+' ('+', '.join('`'+c+'` '+('BOOLEAN' if c in ('synthetic','human_approved') else 'STRING') for c in COLUMNS)+") USING DELTA TBLPROPERTIES ('sbs.publication_id' = '"+publication_id+"', 'sbs.snapshot' = '"+config['snapshot']+"')"
        insert='INSERT INTO '+q+' ('+', '.join('`'+c+'`' for c in COLUMNS)+') VALUES '+', '.join(values)
        require(len(canonical(dict(statement=insert,parameters=parameters)).encode())<=2_000_000,'INSERT_PAYLOAD_CAP')
        tables.append(dict(logical_name=name,full_name=full,row_count=len(rows),expected_sha256=t['expected_sha256'],create_sql=create,insert_sql=insert,parameters=parameters,rows=rows))
    return WritePlan(canonical(dict(version=1,publication_id=publication_id,snapshot=config['snapshot'],config_hash=bundle['config_hash'],mapping_sha256=mapping['mapping_sha256'],schema_name=config['table_prefix'],tables=tables)).encode())


def load_write_plan(root,*,publication_id,config_path='config/genie-pilot-002.json',expected_config_sha256=None):
    from .runtime import _load
    config,bundle,mapping,_=_load(Path(root).resolve(),config_path,expected_config_sha256)
    return _plan(config,bundle,mapping,publication_id)


@dataclass(frozen=True)
class WriterConfig:
    host:str
    schema_name:str
    schema_id:str
    warehouse_id:str
    executor_id:int
    owner:str
    plan_sha256:str
    policy:dict
    evidence_mode:str='real'
    max_http_calls:int=512

    def __post_init__(self):
        u=urlsplit(self.host)
        require(u.scheme=='https' and u.hostname and u.path in ('','/') and not any((u.username,u.password,u.query,u.fragment)),'HOST_INVALID')
        require(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*\.sbs_radar',self.schema_name or ''),'SCHEMA_INVALID')
        require(all(text(v) for v in (self.schema_id,self.warehouse_id,self.owner)) and type(self.executor_id) is int and self.executor_id>=0 and hash64(self.plan_sha256),'WRITER_PINS_REQUIRED')
        require(self.evidence_mode in ('real','fixture') and type(self.max_http_calls) is int and 1<=self.max_http_calls<=512,'WRITER_CAP_INVALID')
        p=self.policy
        require(isinstance(p,dict) and set(p)=={'trusted_administrators','exclusive_maintenance','retention','no_inherited_abac','issued_at_ms','expires_at_ms'},'WRITER_POLICY_INVALID')
        require(all(text(p[k]) for k in ('trusted_administrators','exclusive_maintenance','retention','no_inherited_abac')),'ADMIN_DECLARATIONS_REQUIRED')
        require(type(p['issued_at_ms']) is int and type(p['expires_at_ms']) is int and 0<=p['issued_at_ms']<p['expires_at_ms'],'WRITER_POLICY_TIME_INVALID')


def preflight(plan,config=None):
    require(isinstance(plan,WritePlan),'WRITE_PLAN_REQUIRED')
    p=plan.as_dict()
    if config is not None:
        require(isinstance(config,WriterConfig) and config.plan_sha256==plan.sha256 and config.schema_name==p['schema_name'],'WRITE_PLAN_PIN_MISMATCH')
    return dict(status='pending_configuration' if config is None else 'configured_not_observed',plan_sha256=plan.sha256,snapshot=p['snapshot'],tables={t['logical_name']:t['row_count'] for t in p['tables']},mutation_submissions=16,read_submissions_success_path=64,total_sql_success_path=80,history_gets=32,max_http_calls=512,cloud_executed=False,cost=None,pending=['authorized execution','current writer identity/schema ownership and RUNNING warehouse','exclusive maintenance/retention/ABAC declarations','observed Delta versions and full readback','independent publisher Query History','separate reader SELECT-only governance and Genie space configuration'])


class _RunningStatements:
    """RUNNING observation immediately before each SQL POST, reads included.
    There is no atomic GET+SQL API; external shutdown races remain an explicit
    trusted-maintenance limitation, not a claimed guarantee about billing.
    """
    def __init__(self,services,warehouse_id):self.services=services;self.warehouse_id=warehouse_id
    def execute_statement(self,**kwargs):
        try:w=obj(self.services.warehouses.get(self.warehouse_id))
        except Exception:raise ValueError('WAREHOUSE_OBSERVATION_UNAVAILABLE') from None
        require(w.get('id')==self.warehouse_id and w.get('state')=='RUNNING','WAREHOUSE_NOT_RUNNING')
        return self.services.statement_execution.execute_statement(**kwargs)
    def __getattr__(self,name):return getattr(self.services.statement_execution,name)


class PublicationWriter:
    """Construct with generated SDK services or explicitly labelled fixtures.

    SDK must use SingleAttemptApi (factory below). Journal is trusted server-local,
    append-only, locked; callers cannot supply plan/config/journal through HTTP.
    Fresh publication requires all eight table names absent before first mutation.
    """
    def __init__(self,plan,config,services,journal,*,clock=now_ms,identity_profile=STRICT_IDENTITY_PROFILE):
        identity_profile_check(identity_profile);self.identity_profile=identity_profile
        preflight(plan,config);self.plan=plan;self.p=plan.as_dict();self.cfg=replace(config,policy=json.loads(canonical(config.policy)));self.s=services;self.clock=clock
        # Rebuild every SQL/parameter from validated rows, not caller SQL.
        require(set(self.p)=={'version','publication_id','snapshot','config_hash','mapping_sha256','schema_name','tables'} and type(self.p['version']) is int and self.p['version']==1 and all(hash64(self.p[k]) for k in ('snapshot','config_hash','mapping_sha256')),'WRITE_PLAN_INVALID')
        require(isinstance(self.p['tables'],list),'WRITE_TABLE_CLOSURE')
        for t in self.p['tables']:require(isinstance(t,dict) and set(t)=={'logical_name','full_name','row_count','expected_sha256','create_sql','insert_sql','parameters','rows'},'WRITE_TABLE_INVALID')
        tables={t['logical_name']:t['rows'] for t in self.p['tables']}
        require(list(tables)==list(TABLES) and len(self.p['tables'])==8,'WRITE_TABLE_CLOSURE')
        for t in self.p['tables']:
            _rows(t['rows']);require(t['rows'] and t['rows']==sorted(t['rows'],key=lambda r:r['id']) and type(t['row_count']) is int and digest(t['rows'])==t['expected_sha256'] and len(t['rows'])==t['row_count'],'WRITE_ROWS_INVALID')
        # Canonical plan is a pinned trusted artifact; executable SQL must also
        # match the compiler exactly even when a server misconfigures its pin.
        # Snapshot includes source/config metadata not present here; compiler
        # validation below reconstructs expressions independently.
        for t in self.p['tables']:self._validate_sql(t)
        self.fd=_directory(journal,True);self.closed=False
        self.statements=_RunningStatements(services,config.warehouse_id)
        self.reader=PublicationReader(self.statements,warehouse_id=config.warehouse_id,metadata_get=self._metadata,governance_probe=self._governance,evidence_mode=config.evidence_mode,max_statements=96,max_polls=3,max_chunks=64,max_rows=1000,max_bytes=2_000_000,identity_profile=identity_profile)

    def _validate_sql(self,t):
        name=t['full_name'];require(name==self.p['schema_name']+'.'+t['logical_name'],'WRITE_TABLE_NAME_INVALID')
        q=quote(name);pid=self.p['publication_id'];snap=self.p['snapshot']
        require(re.fullmatch('[a-zA-Z0-9_-]{8,64}',pid) and hash64(snap),'WRITE_PLAN_INVALID')
        create='CREATE TABLE '+q+' ('+', '.join('`'+c+'` '+('BOOLEAN' if c in ('synthetic','human_approved') else 'STRING') for c in COLUMNS)+") USING DELTA TBLPROPERTIES ('sbs.publication_id' = '"+pid+"', 'sbs.snapshot' = '"+snap+"')"
        ps=[];vs=[]
        for i,row in enumerate(t['rows']):
            cells=[]
            for c in COLUMNS:
                v=row[c]
                if v is None:cells.append('NULL')
                elif type(v) is bool:cells.append('TRUE' if v else 'FALSE')
                else:
                    k=f'p{i}_{c}';cells.append(':'+k);ps.append(dict(name=k,type='STRING',value=v))
            vs.append('('+', '.join(cells)+')')
        insert='INSERT INTO '+q+' ('+', '.join('`'+c+'`' for c in COLUMNS)+') VALUES '+', '.join(vs)
        require(t['create_sql']==create and t['insert_sql']==insert and t['parameters']==ps,'WRITE_SQL_INVALID')
        require(len(canonical(dict(statement=insert,parameters=ps)).encode())<=2_000_000,'INSERT_PAYLOAD_CAP')

    def close(self):
        if not self.closed:
            import os
            os.close(self.fd);self.closed=True
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
    def _get(self,name):
        try:return json.loads(_read(self.fd,name+'.json'))
        except FileNotFoundError:return None
    def _put(self,name,value):_append(self.fd,name+'.json',canonical(value).encode())

    def _observe(self):
        require(self.cfg.policy['issued_at_ms']<=self.clock()<self.cfg.policy['expires_at_ms'],'WRITER_POLICY_EXPIRED')
        try:
            me=obj(self.s.current_user.me());schema=obj(self.s.schemas.get(self.cfg.schema_name));w=obj(self.s.warehouses.get(self.cfg.warehouse_id))
            catalog=obj(self.s.catalogs.get(self.cfg.schema_name.split('.')[0]));acl=obj(self.s.permissions.get('warehouses',self.cfg.warehouse_id))
        except Exception:raise ValueError('WRITER_OBSERVATION_UNAVAILABLE') from None
        require(str(me.get('id'))==str(self.cfg.executor_id) and type(me.get('id')) in (str,int) and me.get('userName',me.get('user_name'))==self.cfg.owner,'WRITER_IDENTITY_MISMATCH')
        require(schema.get('full_name')==self.cfg.schema_name and schema.get('schema_id')==self.cfg.schema_id and schema.get('owner')==self.cfg.owner,'SCHEMA_OWNER_PIN_MISMATCH')
        require(catalog.get('name')==self.cfg.schema_name.split('.')[0] and catalog.get('owner')==self.cfg.owner,'CATALOG_OWNER_REQUIRED')
        require(acl.get('object_id')=='/sql/warehouses/'+self.cfg.warehouse_id and any(a.get('user_name')==self.cfg.owner and any(p.get('permission_level') in ('CAN_USE','CAN_MANAGE','IS_OWNER') for p in a.get('all_permissions',[])) for a in acl.get('access_control_list',[])),'DIRECT_WAREHOUSE_PERMISSION_REQUIRED')
        require(w.get('id')==self.cfg.warehouse_id and w.get('state')=='RUNNING','WAREHOUSE_NOT_RUNNING')
        return dict(executor_id=self.cfg.executor_id,owner=self.cfg.owner,schema_id=schema['schema_id'],warehouse_id=w['id'],warehouse_state=w['state'])

    def _metadata(self,name):return obj(self.s.tables.get(name))
    def _maybe(self,name):
        try:return self._metadata(name)
        except Exception as e:
            if getattr(e,'error_code',None) in ('TABLE_DOES_NOT_EXIST','RESOURCE_DOES_NOT_EXIST'):return None
            raise ValueError('TABLE_OBSERVATION_UNAVAILABLE') from None
    def _owned(self,t):
        m=self._maybe(t['full_name']);require(isinstance(m,dict),'MUTATION_UNCONFIRMED')
        require(m.get('full_name')==t['full_name'] and m.get('owner')==self.cfg.owner and m.get('data_source_format')=='DELTA' and m.get('table_type')=='MANAGED','TABLE_NOT_OWNED_PUBLICATION')
        require(m.get('browse_only') is not True and isinstance(m.get('columns'),list) and [c.get('name') for c in m['columns']]==list(COLUMNS) and [c.get('type_name') for c in m['columns']]==['BOOLEAN' if c in ('synthetic','human_approved') else 'STRING' for c in COLUMNS],'TABLE_SCHEMA_UNAVAILABLE_OR_CHANGED')
        props=m.get('properties',{})
        require(props.get('sbs.publication_id')==self.p['publication_id'] and props.get('sbs.snapshot')==self.p['snapshot'],'TABLE_NOT_OWNED_PUBLICATION')
        self.reader._identity(t['full_name'])
        return m

    def _mutation(self,key,sql,parameters=()):
        from databricks.sdk.service.sql import StatementParameterListItem,Disposition,Format
        intent=dict(plan_sha256=self.plan.sha256,sql_sha256=sha(sql.encode()),parameters_sha256=digest(parameters))
        prior=self._get(key+'-intent')
        if prior is not None:
            require(prior==intent,'JOURNAL_INTENT_MISMATCH');return # reconcile only
        self._observe() # RUNNING immediately before every mutation; no auto-start
        self._put(key+'-intent',intent)
        try:
            r=obj(self.statements.execute_statement(statement=sql,warehouse_id=self.cfg.warehouse_id,parameters=[StatementParameterListItem(**p) for p in parameters],disposition=Disposition.INLINE,format=Format.JSON_ARRAY,wait_timeout='10s',row_limit=1000,byte_limit=2_000_000))
            sid=r.get('statement_id');require(text(sid),'MUTATION_ID_MISSING')
            self._put(key+'-receipt',dict(statement_id=sid))
            for _ in range(3):
                if r.get('status',{}).get('state') not in ('PENDING','RUNNING'):break
                r=obj(self.statements.get_statement(sid));require(r.get('statement_id')==sid,'MUTATION_ID_CHANGED')
            self._put(key+'-response',dict(statement_id=sid,state=r.get('status',{}).get('state')))
        except Exception:
            # Do not leak SDK errors/credentials and never retry POST. Effect
            # verification below may resolve even a lost response after commit.
            return

    def _read_rows(self,t):
        self._observe();m=self._owned(t)
        cols,data,_=self.reader._execute('DESCRIBE HISTORY '+quote(t['full_name']))
        names=[c['name'] for c in cols];require('version' in names and 'userId' in names,'HISTORY_ACTOR_REQUIRED')
        pos=names.index('version');require(cols[pos]['type_name'] in ('LONG','BIGINT') and data,'HISTORY_VERSION_INVALID')
        require(all(isinstance(r[pos],str) and re.fullmatch('[0-9]+',r[pos]) for r in data),'HISTORY_VERSION_INVALID')
        last=max(data,key=lambda r:int(r[pos]));version=int(last[pos])
        require(last[names.index('userId')]==str(self.cfg.executor_id),'HISTORY_WRITER_MISMATCH')
        sql='SELECT '+', '.join('`'+c+'`' for c in COLUMNS)+' FROM '+quote(t['full_name'])+' VERSION AS OF '+str(version)
        cols,data,_=self.reader._execute(sql)
        require([c['name'] for c in cols]==list(COLUMNS) and [c['type_name'] for c in cols]==['BOOLEAN' if c in ('synthetic','human_approved') else 'STRING' for c in COLUMNS],'READBACK_SCHEMA_INVALID')
        rows=[]
        for cells in data:
            row=dict(zip(COLUMNS,cells))
            for c in ('synthetic','human_approved'):
                require(row[c] in ('true','false'),'BOOLEAN_WIRE_INVALID');row[c]=row[c]=='true'
            rows.append(row)
        _rows(rows);rows.sort(key=lambda r:r['id'])
        require(self._owned(t)==m,'TABLE_METADATA_CHANGED')
        return version,rows,m['table_id']

    def _governance(self,names):
        observed=self._observe();require(names==[t['full_name'] for t in self.p['tables']],'GOVERNANCE_SCOPE_INVALID')
        identities=[self._owned(t) for t in self.p['tables']]
        evidence=dict(profile='trusted_admin_publisher_observed_v1',observations=observed,table_metadata_sha256=digest(identities),administrative_declarations=self.cfg.policy,identity_continuity='not_proven',aba_prevented=False)
        return dict(mode=self.cfg.evidence_mode,source_tables=names,evidence_id=digest(evidence),ddl_identity_controlled=True,retention_controlled=True,select_authorized=True,policies_absent=True,**evidence)

    def publish(self,*,certificate_directory,registry_directory,ttl_ms=300000):
        require(not self.closed,'WRITER_CLOSED');fcntl.flock(self.fd,fcntl.LOCK_EX)
        try:return self._publish(certificate_directory,registry_directory,ttl_ms)
        finally:fcntl.flock(self.fd,fcntl.LOCK_UN)

    def _publish(self,certificate_directory,registry_directory,ttl_ms):
        from .publication_renewal import effective_binding,CumulativeStatements
        bound=dict(plan_sha256=self.plan.sha256,config_sha256=digest(asdict(self.cfg)))
        prior,renewal=effective_binding(self.fd)
        if prior is not None:require(prior==bound,'JOURNAL_BINDING_MISMATCH')
        if renewal is not None and not isinstance(self.statements,CumulativeStatements):
            self.statements=CumulativeStatements(self.statements,self.fd);self.reader.sdk=self.statements
        initial=self._observe()
        if prior is None:
            require(all(self._maybe(t['full_name']) is None for t in self.p['tables']),'EXISTING_TABLE_REFUSED')
            self._put('binding',bound)
        else:require(prior==bound,'JOURNAL_BINDING_MISMATCH')
        versions={}
        for t in self.p['tables']:
            key=t['logical_name'];self._mutation(key+'-create',t['create_sql'])
            m=self._owned(t);identity=self._get(key+'-identity')
            if identity is None:self._put(key+'-identity',dict(table_id=m['table_id']))
            else:require(identity==dict(table_id=m['table_id']),'TABLE_IDENTITY_CHANGED')
            if self._get(key+'-insert-intent') is None:
                _,rows,_=self._read_rows(t);require(not rows,'NEW_TABLE_NOT_EMPTY')
            self._mutation(key+'-insert',t['insert_sql'],t['parameters'])
            version,rows,tid=self._read_rows(t)
            require(rows==t['rows'],'MUTATION_UNCONFIRMED' if not rows else 'PUBLICATION_CONTENT_CONFLICT')
            require(tid==self._get(key+'-identity')['table_id'],'TABLE_IDENTITY_CHANGED');versions[key]=version
        # Build only from actual observed versions, retaining original snapshot.
        from .publication import PublicationPlan,_sqls
        pts=[]
        for t in self.p['tables']:
            item={k:t[k] for k in ('logical_name','full_name','expected_sha256','row_count')};item['delta_version']=versions[t['logical_name']]
            item.update(dict(zip(('detail_sql','history_sql','readback_sql'),_sqls(item))));pts.append(item)
        rp=PublicationPlan(canonical(dict(snapshot=self.p['snapshot'],config_hash=self.p['config_hash'],tables=pts)).encode())
        certificate=self.reader.read(rp)
        require(self._observe()==initial,'WRITER_OBSERVATION_CHANGED')
        for t in self.p['tables']:require(self._owned(t)['table_id']==self._get(t['logical_name']+'-identity')['table_id'],'TABLE_IDENTITY_CHANGED')
        policy=PublisherPolicy(certificate.sha256,self.p['mapping_sha256'],self.p['snapshot'],self.p['config_hash'],self.cfg.owner,self.cfg.warehouse_id,self.cfg.executor_id,ttl_ms,300000,self.cfg.evidence_mode)
        # Durable readback checkpoint survives later independent history failure.
        # This is not registry activation or proof of verified Query History.
        CertificateStore(certificate_directory,identity_profile=self.identity_profile).put(certificate)
        entry=HistoryRegistryBuilder(self.s.query_history,policy,clock=self.clock,identity_profile=self.identity_profile).build(certificate)
        require(entry.as_dict()['registry']['valid_until_ms']<=self.cfg.policy['expires_at_ms'],'REGISTRY_EXCEEDS_ADMIN_POLICY')
        RegistryAdmin(registry_directory,administrator=self.cfg.owner,clock=self.clock,identity_profile=self.identity_profile).publish(entry)
        return dict(status='published',evidence_mode=self.cfg.evidence_mode,certificate_sha256=certificate.sha256,registry_sha256=entry.sha256,versions=versions,snapshot=self.p['snapshot'],mapping_sha256=self.p['mapping_sha256'],genie_space_ready=False,reader_governance_verified=False,**({'identity_profile':self.identity_profile} if self.identity_profile!=STRICT_IDENTITY_PROFILE else {}))


def sdk_writer(plan,config,journal,*,sdk_config,identity_profile=STRICT_IDENTITY_PROFILE):
    """Concrete lazy factory. sdk_config is normal SDK Config from server profile
    or OAuth M2M, never browser payload. Does not GET until publish(). No retries
    for workspace POSTs; auth-provider traffic is outside workspace HTTP quota.
    """
    from types import SimpleNamespace
    from databricks.sdk.service import sql,catalog,iam
    from sbs.operations.cloud_driver import SingleAttemptApi,SafeHttpError
    preflight(plan,config)
    require(config.evidence_mode=='real' and sdk_config.host.rstrip('/')==config.host.rstrip('/'),'SDK_HOST_OR_MODE_MISMATCH')
    allowed_table_paths={"/api/2.1/unity-catalog/tables/"+t["full_name"] for t in plan.as_dict()["tables"]}
    class PublicationApi(SingleAttemptApi):
        def do(self,method,path=None,**kwargs):
            require(method=='GET' or method=='POST' and path=='/api/2.0/sql/statements','PUBLICATION_API_READ_OR_SQL_ONLY')
            if method=='GET' and path=='/api/2.0/sql/history/queries':
                query=dict(kwargs.get('query') or {});filters=query.pop('filter_by',None)
                require(isinstance(filters,dict) and set(filters)=={'statement_ids','warehouse_ids'} and all(isinstance(v,list) and len(v)==1 and text(v[0]) for v in filters.values()),'HISTORY_EXACT_FILTER_REQUIRED')
                # Match official SDK URL dot notation; requests cannot encode
                # the nested dictionary produced by generated service methods.
                kwargs['query']={**query,**{'filter_by.'+k:v for k,v in filters.items()}}
            if method=='GET' and path in allowed_table_paths:
                # Generic Files transport deliberately suppresses error bodies.
                # Initial publication additionally needs bounded, explicit UC
                # TABLE_DOES_NOT_EXIST evidence; 403/HTML/other 404 fail closed.
                require(set(kwargs)<= {'query','headers'},'TABLE_GET_ARGUMENTS_INVALID')
                require(self.calls<self.max_calls,'SDK_QUOTA_EXCEEDED');self.calls+=1
                try:r=self.session.request('GET',self._cfg.host.rstrip('/')+path,params=kwargs.get('query'),headers={**kwargs.get('headers',{}),**self._cfg.authenticate()},timeout=(10,60),allow_redirects=False,stream=True)
                except Exception:raise ValueError('SDK_TRANSPORT_UNCONFIRMED') from None
                import sys
                try:
                    try:raw=r.raw.read(self.max_bytes+1,decode_content=True)
                    except Exception:raise ValueError('SDK_RESPONSE_READ_UNCONFIRMED') from None
                    require(len(raw)<=self.max_bytes,'SDK_RESPONSE_CAP_EXCEEDED')
                    try:body=json.loads(raw)
                    except Exception:raise ValueError('SDK_JSON_INVALID') from None
                    if r.status_code==404 and isinstance(body,dict) and body.get('error_code')=='TABLE_DOES_NOT_EXIST':raise SafeHttpError('TABLE_DOES_NOT_EXIST')
                    require(200<=r.status_code<300 and isinstance(body,dict),'TABLE_GET_UNCONFIRMED')
                    return body
                finally:
                    failed=sys.exc_info()[0] is not None
                    try:r.close()
                    except Exception:
                        if not failed:raise ValueError('SDK_RESPONSE_CLOSE_UNCONFIRMED') from None
            return super().do(method,path,**kwargs)
    api=PublicationApi(sdk_config,max_calls=config.max_http_calls,max_response_bytes=4_000_000)
    services=SimpleNamespace(statement_execution=sql.StatementExecutionAPI(api),query_history=sql.QueryHistoryAPI(api),tables=catalog.TablesAPI(api),schemas=catalog.SchemasAPI(api),warehouses=sql.WarehousesAPI(api),current_user=iam.CurrentUserAPI(api),catalogs=catalog.CatalogsAPI(api),permissions=iam.PermissionsAPI(api))
    return PublicationWriter(plan,config,services,journal,identity_profile=identity_profile)


# Explicit migration API; never called automatically by publish or SDK factory.
from .publication_renewal import renew_policy_window
