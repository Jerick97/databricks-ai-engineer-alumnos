"""SK07 assembly from protected server files and normal Apps OAuth M2M.

No request may select configuration, credentials, policy or publication. Pending
configuration stays offline. Live construction is lazy at the Genie route; no
SQL, grants, deployment, resource creation or model invocation occurs here.
"""
import hashlib
import json
from pathlib import Path
import re
import tempfile
import threading
from urllib.parse import urlsplit
from .publication import Certificate,require,validate_certificate,STRICT_IDENTITY_PROFILE,identity_profile_check
from .runtime import load_runtime_binding,ServerDependencies
from sbs.paths import project_path
from .governance import ScimReaderResolver


def obj(value):return value.as_dict() if hasattr(value,'as_dict') else value

def workspace_host(value):
    require(isinstance(value,str),'SERVER_HOST_INVALID')
    host=value.rstrip('/');u=urlsplit(host)
    require(u.scheme=='https' and u.hostname and u.hostname.endswith('.cloud.databricks.com') and not u.path and not u.query and not u.fragment and not u.username and not u.password and u.port in (None,443),'SERVER_HOST_INVALID')
    return host

class BoundScimReaderResolver(ScimReaderResolver):
    def __init__(self,*args,executor_id,client_id,**kwargs):
        super().__init__(*args,**kwargs);self.executor_id=executor_id;self.client_id=client_id
    def __call__(self,*,executor_id):
        require(type(executor_id) is int and executor_id==self.executor_id,'APP_EXECUTOR_CLIENT_MISMATCH')
        result=super().__call__(executor_id=executor_id)
        # SK06 emits the observed applicationId first, before reported groups.
        require(result['principals'][0]==self.client_id,'APP_EXECUTOR_CLIENT_MISMATCH')
        return result

def pinned(root,path,sha):
    raw=project_path(root,path).read_bytes()
    require(isinstance(sha,str) and hashlib.sha256(raw).hexdigest()==sha,'SERVER_FILE_PIN_MISMATCH')
    return raw


class GenieTransport:
    """Minimal SDK transport: exactly one HTTP attempt, confined Genie endpoints."""
    def __init__(self,config,*,space_id,session_factory=None,max_calls=100):
        host=workspace_host(config.host)
        require(isinstance(space_id,str) and re.fullmatch(r'[A-Za-z0-9_-]+',space_id),'SPACE_ID_INVALID')
        require(type(max_calls) is int and 1<=max_calls<=1000,'GENIE_CALL_CAP_INVALID')
        self._cfg=config;self.host=host;self.space_id=space_id;self.factory=session_factory;self.calls=0;self.max_calls=max_calls;self._lock=threading.Lock()
    def do(self,method,path=None,*,body=None,headers=None,query=None,**other):
        base='/api/2.0/genie/spaces/'+self.space_id
        ident=r'[A-Za-z0-9_-]+'
        allowed=(method=='POST' and (path==base+'/start-conversation' or re.fullmatch(re.escape(base)+r'/conversations/'+ident+r'/messages',path or '')))
        read=(method=='GET' and re.fullmatch(re.escape(base)+r'/conversations/'+ident+r'/messages/'+ident+r'(?:/query-result)?',path or ''))
        require(not other and not query and (allowed or read),'GENIE_REQUEST_OUTSIDE_SCOPE')
        require((allowed and isinstance(body,dict) and set(body)=={'content'} and isinstance(body['content'],str) and 0<len(body['content'])<=20000) or (read and body is None),'GENIE_BODY_INVALID')
        with self._lock:
            require(self.calls<self.max_calls,'GENIE_CALL_CAP_REACHED')
            self.calls+=1
        import requests
        session=(self.factory or requests.Session)();session.mount('https://',requests.adapters.HTTPAdapter(max_retries=0))
        try:
            response=session.request(method,self.host+path,json=body,headers={**(headers or {}),**self._cfg.authenticate()},timeout=30,allow_redirects=False)
            if response.status_code in (401,403):raise PermissionError('GENIE_ACCESS_DENIED')
            require(response.status_code==200,'GENIE_HTTP_FAILED')
            result=response.json();require(isinstance(result,dict),'GENIE_RESPONSE_INVALID');return result
        except PermissionError:raise
        except ValueError as exc:
            if str(exc) in {'GENIE_HTTP_FAILED','GENIE_RESPONSE_INVALID'}:raise
            raise ValueError('GENIE_TRANSPORT_FAILED') from None
        except Exception:raise ValueError('GENIE_TRANSPORT_FAILED') from None
        finally:session.close()


class RemoteEvidence:
    """GET-only UC Files evidence; no assumed local /Volumes mount or cached ACL."""
    def __init__(self,files,prefix,*,max_bytes=2_000_000,identity_profile=STRICT_IDENTITY_PROFILE):
        identity_profile_check(identity_profile);self.identity_profile=identity_profile
        require(isinstance(prefix,str) and re.fullmatch(r'/Volumes/[A-Za-z_][A-Za-z0-9_]*/sbs_radar/[A-Za-z_][A-Za-z0-9_]*/[A-Za-z0-9_/-]+',prefix) and '..' not in prefix and not prefix.endswith('/'),'EVIDENCE_PREFIX_INVALID')
        require(type(max_bytes) is int and max_bytes>0,'EVIDENCE_BYTE_CAP_INVALID')
        self.files=files;self.prefix=prefix;self.max_bytes=max_bytes
    def read(self,name,*,optional=False):
        require(isinstance(name,str) and re.fullmatch(r'[A-Za-z0-9_-]+(?:\.revoked|\.status)?\.json',name),'EVIDENCE_NAME_INVALID')
        try:response=self.files.download(self.prefix+'/'+name)
        except Exception as exc:
            if optional and getattr(exc,'error_code',None) in ('NOT_FOUND','RESOURCE_DOES_NOT_EXIST'):return None
            raise ValueError('REMOTE_EVIDENCE_UNAVAILABLE') from None
        stream=response.contents
        try:raw=stream.read(self.max_bytes+1)
        finally:stream.close()
        require(isinstance(raw,bytes) and len(raw)<=self.max_bytes,'EVIDENCE_BYTES_EXCEEDED');return raw
    def registry(self,*,certificate_sha256):
        require(isinstance(certificate_sha256,str) and re.fullmatch('[0-9a-f]{64}',certificate_sha256),'CERTIFICATE_KEY_INVALID')
        raw=self.read(certificate_sha256+'.json')
        rev=self.read(certificate_sha256+'.revoked.json',optional=True)
        # Reuse the independently reviewed registry parser; temporary copy is
        # per observation, never an enduring authority or revocation cache.
        from .publication_registry import RegistryLookup
        with tempfile.TemporaryDirectory(prefix='sbs-registry-') as directory:
            directory=Path(directory).resolve()
            Path(directory,certificate_sha256+'.json').write_bytes(raw)
            if rev is not None:Path(directory,certificate_sha256+'.revoked.json').write_bytes(rev)
            return RegistryLookup(directory,identity_profile=self.identity_profile)(certificate_sha256=certificate_sha256)
    def policy_status(self,*,policy_id,policy_sha256):
        p=json.loads(self.read(policy_id+'.status.json'))
        require(isinstance(p,dict) and set(p)=={'policy_id','policy_sha256','status'} and p['policy_id']==policy_id and p['policy_sha256']==policy_sha256 and p['status'] in ('active','revoked'),'ADMIN_POLICY_STATUS_INVALID')
        return p['status']


class ServerPermissionProbe:
    def __init__(self,client,collector,*,executor_id,warehouse_id,space_id,snapshot,tables,expected_acl_object_id):
        require(isinstance(expected_acl_object_id,str) and re.fullmatch(r'/genie/[A-Za-z0-9_-]+',expected_acl_object_id),'GENIE_OBSERVED_ACL_ID_REQUIRED')
        self.client=client;self.collector=collector;self.executor=executor_id;self.warehouse=warehouse_id;self.space=space_id;self.snapshot=snapshot;self.tables=tuple(tables);self.acl_object_id=expected_acl_object_id
    def __call__(self):
        observed=self.collector.collect(source_tables=list(self.tables),executor_id=self.executor,warehouse_id=self.warehouse)
        w=obj(self.client.warehouses.get(self.warehouse));space=obj(self.client.genie.get_space(self.space))
        require(w.get('id')==self.warehouse and space.get('space_id')==self.space and space.get('warehouse_id')==self.warehouse,'GENIE_RESOURCE_IDENTITY_CHANGED')
        acl=obj(self.client.permissions.get('genie',self.space));require(isinstance(acl.get('access_control_list'),list),'GENIE_ACL_INCOMPLETE')
        require(acl.get('object_type')=='genie' and acl.get('object_id')==self.acl_object_id,'GENIE_ACL_IDENTITY_CHANGED')
        subjects=set(observed['subject']['principals']);levels=[]
        for entry in acl['access_control_list']:
            principal=next((entry[k] for k in ('user_name','service_principal_name','group_name') if entry.get(k)),None)
            if principal in subjects:
                require(isinstance(entry.get('all_permissions'),list),'GENIE_ACL_INCOMPLETE')
                levels.extend(p.get('permission_level') for p in entry['all_permissions'])
        access='CAN_RUN' in levels and all(p in ('CAN_RUN','CAN_VIEW') for p in levels)
        return dict(warehouse_id=self.warehouse,snapshot=self.snapshot,state=w.get('state'),warehouse_type=w.get('warehouse_type'),can_use=True,tables_read=True,genie_access=access,read_only_backend=True,scope_verified=True)


def load_server_binding(root,*,mode,client_factory=None):
    root=Path(root).resolve();require(mode in ('local','cloud'),'SERVER_MODE_INVALID')
    path=root/'config/genie-server.json'
    if not path.exists():return load_runtime_binding(root)
    c=json.loads(project_path(root,'config/genie-server.json').read_text())
    require(isinstance(c,dict) and type(c.get('enabled')) is bool,'SERVER_CONFIGURATION_INVALID')
    if not c['enabled']:return load_runtime_binding(root)
    require(mode=='cloud','GENIE_CLOUD_BACKEND_REQUIRES_CLOUD_MODE')
    fields={'version','enabled','workspace_host','executor_id','client_id','genie_acl_object_id','runtime_config_path','runtime_config_sha256','certificate_path','certificate_sha256','policy_path','policy_sha256','evidence_prefix'}
    require(type(c.get('version')) is int and c['version'] in (1,2),'SERVER_CONFIGURATION_INVALID')
    if c['version']==2:fields.add('identity_profile')
    require(set(c)==fields and type(c['executor_id']) is int and c['executor_id']>0 and isinstance(c['client_id'],str) and c['client_id'],'SERVER_CONFIGURATION_INVALID')
    identity_profile=c.get('identity_profile',STRICT_IDENTITY_PROFILE)
    identity_profile_check(identity_profile)
    workspace_host(c['workspace_host'])
    require(isinstance(c['genie_acl_object_id'],str) and re.fullmatch(r'/genie/[A-Za-z0-9_-]+',c['genie_acl_object_id']),'GENIE_OBSERVED_ACL_ID_REQUIRED')
    runtime=json.loads(pinned(root,c['runtime_config_path'],c['runtime_config_sha256']))
    require(all(isinstance(runtime.get(k),str) and runtime[k] for k in ('space_id','warehouse_id')),'GENIE_RESOURCES_PENDING')
    certificate=Certificate(pinned(root,c['certificate_path'],c['certificate_sha256']))
    validate_certificate(certificate,identity_profile=identity_profile)
    policy_values=json.loads(pinned(root,c['policy_path'],c['policy_sha256']))
    require(policy_values.get('namespace')==runtime['table_prefix'],'ADMIN_POLICY_NAMESPACE_MISMATCH')
    require(c['evidence_prefix'].startswith('/Volumes/'+runtime['catalog']+'/sbs_radar/'),'EVIDENCE_NAMESPACE_MISMATCH')
    if client_factory is None:
        from databricks.sdk import WorkspaceClient
        from databricks.sdk.core import Config
        client=WorkspaceClient(config=Config(host=c['workspace_host'],auth_type='oauth-m2m',http_timeout_seconds=30,retry_timeout_seconds=0))
    else:client=client_factory()
    require(client.config.host.rstrip('/')==c['workspace_host'].rstrip('/') and client.config.auth_type=='oauth-m2m' and client.config.client_id==c['client_id'],'APP_BACKEND_IDENTITY_MISMATCH')
    from .governance import ScimReaderResolver,UcAccessCollector,TrustedAdminPolicy,TrustedAdminObservedProbe,PROFILE
    from .delta import DeltaPublication
    from databricks.sdk.service.dashboards import GenieAPI
    remote=RemoteEvidence(client.files,c['evidence_prefix'],identity_profile=identity_profile)
    policy_values['trusted_administrators']=tuple(policy_values['trusted_administrators'])
    policy=TrustedAdminPolicy(**policy_values,status_lookup=lambda **kw:remote.policy_status(**kw,policy_sha256=c['policy_sha256']))
    resolver=BoundScimReaderResolver(client.service_principals.get,client.groups.get,executor_id=c['executor_id'],client_id=c['client_id'])
    collector=UcAccessCollector(table_get=client.tables.get,catalog_get=client.catalogs.get,schema_get=client.schemas.get,effective_grants_get=client.grants.get_effective,warehouse_permissions_get=client.warehouses.get_permissions,subject_resolver=resolver)
    cap=DeltaPublication(certificate,c['certificate_sha256'],runtime['mapping_sha256'],remote.registry,TrustedAdminObservedProbe(collector,policy),assurance_profile=PROFILE,certificate_identity_profile=identity_profile)
    probe=ServerPermissionProbe(client,collector,executor_id=c['executor_id'],warehouse_id=runtime['warehouse_id'],space_id=runtime['space_id'],snapshot=runtime['snapshot'],tables=list(cap.versions),expected_acl_object_id=c['genie_acl_object_id'])
    dependencies=ServerDependencies(GenieAPI(GenieTransport(client.config,space_id=runtime['space_id'])),client.query_history,probe,None,c['executor_id'],cap)
    return load_runtime_binding(root,c['runtime_config_path'],dependencies=dependencies,expected_config_sha256=c['runtime_config_sha256'])
