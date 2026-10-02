"""Opt-in loader078. Server-owned config, protected remote generation per request.

No activation through client payload. Existing server loader/default is unchanged.
"""
import json
import re
from sbs.paths import project_path
from pathlib import Path
from .publication import require, Certificate, REPLAY_IDENTITY_PROFILE
from .publication_rotation import RotationReader,snapshot_binding,invariant_policy
from . import digest
from .server import pinned,RemoteEvidence,BoundScimReaderResolver,ServerPermissionProbe,GenieTransport,workspace_host
from .runtime import load_runtime_binding,ServerDependencies

class RotatingBinding:
    def __init__(self,base,reader,assemble):self.base=base;self.reader=reader;self.assemble=assemble
    def __getattr__(self,name):return getattr(self.base,name)
    def readiness(self):
        return {**self.base.readiness(),'available':True,'status':'configured_pending_remote_verification','remote_verified':False,'publication_verified':False,'rotation_enabled':True}
    def ask_scoped(self,question,*,context):
        # Reject invalid context before store or SDK-backed query capabilities.
        try:self.base._catalog.references(context)
        except Exception:return {'status':'conflict','scope_verified':False,'rows':[],'reason':'CONTEXT_NOT_REGISTERED'}
        try:
            selected=self.reader.select()
            binding=self.assemble(selected)
            return binding.ask_scoped(question,context=context)
        except Exception as exc:
            code=str(exc)
            return {'status':'unavailable','scope_verified':False,'rows':[],'reason':code if code.startswith('ROTATION_') and code.replace('_','').isalnum() else 'ROTATION_VERIFICATION_FAILED'}

def load_rotating_server_binding(root,*,mode,config_path='config/genie-rotation-078.json',client_factory=None):
    root=Path(root).resolve();c=json.loads(project_path(root,config_path).read_bytes())
    fields={'version','enabled','server_template_path','server_template_sha256','snapshot_binding_sha256','policy_invariants_sha256','publisher_identity','publisher_executor_id','warehouse_id'}
    require(isinstance(c,dict) and set(c)==fields and type(c['version']) is int and c['version']==1 and c['enabled'] is True and mode=='cloud','ROTATION_CONFIG_INVALID')
    server=json.loads(pinned(root,c['server_template_path'],c['server_template_sha256']))
    require(type(server.get('version')) is int and server['version']==2 and server.get('identity_profile')==REPLAY_IDENTITY_PROFILE and type(server.get('executor_id')) is int and server['executor_id']>0,'ROTATION_TEMPLATE_INVALID')
    require(isinstance(server.get('genie_acl_object_id'),str) and re.fullmatch(r'/genie/[A-Za-z0-9_-]+',server['genie_acl_object_id']),'ROTATION_TEMPLATE_INVALID')
    workspace_host(server['workspace_host'])
    runtime=json.loads(pinned(root,server['runtime_config_path'],server['runtime_config_sha256']))
    cert=Certificate(pinned(root,server['certificate_path'],server['certificate_sha256']))
    from .publication import validate_certificate
    validate_certificate(cert,identity_profile=REPLAY_IDENTITY_PROFILE)
    policy=json.loads(pinned(root,server['policy_path'],server['policy_sha256']))
    require(snapshot_binding(cert,runtime['mapping_sha256'])==c['snapshot_binding_sha256'] and digest(invariant_policy(policy))==c['policy_invariants_sha256'],'ROTATION_BOOTSTRAP_PIN_MISMATCH')
    require(runtime['warehouse_id']==c['warehouse_id'] and server['evidence_prefix'].startswith('/Volumes/'+runtime['catalog']+'/sbs_radar/'),'ROTATION_RESOURCE_MISMATCH')
    require(policy.get('namespace')==runtime['table_prefix'],'ROTATION_NAMESPACE_MISMATCH')
    require(all(isinstance(runtime.get(k),str) and runtime[k] for k in ('space_id','warehouse_id')),'ROTATION_RESOURCES_PENDING')
    base=load_runtime_binding(root,server['runtime_config_path'],expected_config_sha256=server['runtime_config_sha256'])
    if client_factory is None:
        from databricks.sdk import WorkspaceClient
        from databricks.sdk.core import Config
        client=WorkspaceClient(config=Config(host=server['workspace_host'],auth_type='oauth-m2m',http_timeout_seconds=30,retry_timeout_seconds=0))
    else:client=client_factory()
    require(client.config.host.rstrip('/')==server['workspace_host'].rstrip('/') and client.config.auth_type=='oauth-m2m' and client.config.client_id==server['client_id'],'ROTATION_APP_IDENTITY_MISMATCH')
    remote=RemoteEvidence(client.files,server['evidence_prefix'])
    reader=RotationReader(remote.read,binding_sha256=c['snapshot_binding_sha256'],policy_invariants_sha256=c['policy_invariants_sha256'],publisher_identity=c['publisher_identity'],publisher_executor_id=c['publisher_executor_id'],warehouse_id=c['warehouse_id'])
    def assemble(selected):
        from .governance import UcAccessCollector,TrustedAdminPolicy,TrustedAdminObservedProbe,PROFILE
        from .delta import DeltaPublication
        from databricks.sdk.service.dashboards import GenieAPI
        values=dict(selected.payload['admin_policy']);values['trusted_administrators']=tuple(values['trusted_administrators'])
        policy=TrustedAdminPolicy(**values,status_lookup=selected.policy_status)
        resolver=BoundScimReaderResolver(client.service_principals.get,client.groups.get,executor_id=server['executor_id'],client_id=server['client_id'])
        collector=UcAccessCollector(table_get=client.tables.get,catalog_get=client.catalogs.get,schema_get=client.schemas.get,effective_grants_get=client.grants.get_effective,warehouse_permissions_get=client.warehouses.get_permissions,subject_resolver=resolver)
        cap=DeltaPublication(selected.certificate,selected.certificate.sha256,runtime['mapping_sha256'],selected.registry,TrustedAdminObservedProbe(collector,policy),assurance_profile=PROFILE,certificate_identity_profile=selected.payload['identity_profile'])
        probe=ServerPermissionProbe(client,collector,executor_id=server['executor_id'],warehouse_id=runtime['warehouse_id'],space_id=runtime['space_id'],snapshot=runtime['snapshot'],tables=list(cap.versions),expected_acl_object_id=server['genie_acl_object_id'])
        dependencies=ServerDependencies(GenieAPI(GenieTransport(client.config,space_id=runtime['space_id'])),client.query_history,probe,None,server['executor_id'],cap)
        return load_runtime_binding(root,server['runtime_config_path'],dependencies=dependencies,expected_config_sha256=server['runtime_config_sha256'])
    return RotatingBinding(base,reader,assemble)
