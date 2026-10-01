"""Opt-in base135→Genie164 server wiring, preserving frozen runtime defaults.

No request payload, credentials, publisher or SQL capability enters this module.
The historical certificate is only a bootstrap identity anchor. Every query
selects and verifies a fresh protected remote generation through loader078.
"""
from copy import deepcopy
from pathlib import Path
import json
from sbs.models.app_selection import create_server_service
from .publication import require
from .server import pinned
from .runtime import load_runtime_binding
from .server_rotation import load_rotating_server_binding

SELECTOR='config/genie-bootstrap-098.json'

class TraceBinding:
    """Retain each tool-call proof through Conversation's existing trace contract.

    The underlying078 reader owns selection/revalidation. This adapter neither
    changes evidence nor claims an HTTP-wide generation transaction.
    """
    def __init__(self,delegate):self.delegate=delegate
    def __getattr__(self,name):return getattr(self.delegate,name)
    def ask_scoped(self,question,*,context):
        result=deepcopy(self.delegate.ask_scoped(question,context=context))
        require(isinstance(result,dict) and isinstance(result.get('trace',{}),dict),'BOOTSTRAP_TRACE_INVALID')
        trace=result.setdefault('trace',{})
        trace['rotation_snapshot_binding_sha256']=self.delegate.reader.binding
        trace['rotation_consistency_scope']='one_genie_tool_call; cross_family_calls_share_snapshot_binding_not_necessarily_generation'
        proof=result.get('execution_provenance')
        if proof is not None:
            require(isinstance(proof,dict),'BOOTSTRAP_PROVENANCE_INVALID')
            trace['execution_provenance']=deepcopy(proof)
        return result


def preflight(root):
    root=Path(root).resolve()
    path=root/SELECTOR
    require(not path.is_symlink() and path.is_file() and path.stat().st_size<=65536,'BOOTSTRAP_CONFIG_INVALID')
    c=json.loads(path.read_bytes())
    fields={'version','enabled','rotation_config_path','rotation_config_sha256','rag_snapshot','genie_snapshot','mapping_sha256','reader_client_id','reader_executor_id'}
    require(isinstance(c,dict) and set(c)==fields and type(c['version']) is int and c['version']==1 and c['enabled'] is True,'BOOTSTRAP_CONFIG_INVALID')
    require(c['rotation_config_path']=='config/genie-rotation-098.json','BOOTSTRAP_ROTATION_PATH_INVALID')
    rotation=json.loads(pinned(root,c['rotation_config_path'],c['rotation_config_sha256']))
    server=json.loads(pinned(root,rotation['server_template_path'],rotation['server_template_sha256']))
    require(server['certificate_path']=='config/genie-bootstrap-certificate-098.json','BOOTSTRAP_CERTIFICATE_PATH_INVALID')
    pinned(root,server['certificate_path'],server['certificate_sha256'])
    pinned(root,server['policy_path'],server['policy_sha256'])
    require(type(c['reader_executor_id']) is int and c['reader_executor_id']>0 and server['executor_id']==c['reader_executor_id'] and server['client_id']==c['reader_client_id'],'BOOTSTRAP_READER_IDENTITY_MISMATCH')
    require(c['reader_executor_id']!=rotation['publisher_executor_id'],'BOOTSTRAP_PUBLISHER_IS_NOT_READER')
    # Exact existing export/mapping/source verification, no SDK construction.
    base=load_runtime_binding(root,server['runtime_config_path'],expected_config_sha256=server['runtime_config_sha256'])
    require((base.rag_snapshot,base.genie_snapshot,base.mapping_sha256)==(c['rag_snapshot'],c['genie_snapshot'],c['mapping_sha256']) and c['rag_snapshot']!=c['genie_snapshot'],'BOOTSTRAP_SNAPSHOT_MAPPING_MISMATCH')
    return c


def create_rotating_service(environ,*,root,mode='local',service_factory=None,binding_loader=None,client_factory=None,**kwargs):
    """environ and dependency factories are trusted server bootstrap inputs only."""
    if 'SBS_GENIE_ROTATION_CONFIG' not in environ:
        return create_server_service(environ,service_factory=service_factory,mode=mode,**kwargs)
    require(environ['SBS_GENIE_ROTATION_CONFIG']==SELECTOR and mode=='cloud','BOOTSTRAP_SELECTOR_INVALID')
    c=preflight(root)
    require(kwargs.get('structural_config_path') is None,'BOOTSTRAP_STRUCTURAL_UNPUBLISHED')
    service=create_server_service(environ,service_factory=service_factory,mode=mode,**kwargs)
    require(service.mode=='cloud' and not hasattr(service,'structural_metadata') and not hasattr(service,'release_metadata'),'BOOTSTRAP_RUNTIME_UNPUBLISHED')
    require(getattr(service,'cloud_refresh',None) is None,'BOOTSTRAP_RUNTIME_PROMOTION_UNSUPPORTED')
    require(service.snapshot==c['rag_snapshot'] and service.genie_binding is None,'BOOTSTRAP_SERVICE_SNAPSHOT_MISMATCH')
    loader=binding_loader or load_rotating_server_binding
    binding=loader(root,mode='cloud',config_path=c['rotation_config_path'],client_factory=client_factory)
    require((binding.rag_snapshot,binding.genie_snapshot,binding.mapping_sha256)==(c['rag_snapshot'],c['genie_snapshot'],c['mapping_sha256']),'BOOTSTRAP_BINDING_MISMATCH')
    binding=TraceBinding(binding)
    service.genie_binding=binding
    service.provenance['genie_rotation_bootstrap']=dict(config=SELECTOR,rag_snapshot=c['rag_snapshot'],genie_snapshot=c['genie_snapshot'],mapping_sha256=c['mapping_sha256'],reader_client_id=c['reader_client_id'],reader_executor_id=c['reader_executor_id'],remote_verified=False,publication_verified=False)
    # Preserve the runtime's own guards; no monkeypatch or fallback loader.
    require(service.initialize_genie() is binding,'BOOTSTRAP_RUNTIME_BINDING_REJECTED')
    return service
