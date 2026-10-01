import json
from pathlib import Path
from sbs.genie.bootstrap_098 import create_rotating_service,SELECTOR
from .runtime import AppService
CONFIG='config/app-integration-133.json'

def load_config(root):
    path=Path(root)/CONFIG
    if path.is_symlink() or path.stat().st_size>65536:raise ValueError('APP133_CONFIG_INVALID')
    c=json.loads(path.read_bytes())
    if set(c)!={'version','status','deadline_unix','generation_posts_per_process','embedding_posts_per_process','embedding_tokens_per_process','workspace_host','reader_client_id','worker_count'}:raise ValueError('APP133_CONFIG_FIELDS')
    if c['version']!=1 or c['status']!='prepared_quality_and_target_review_required' or c['worker_count']!=1:raise ValueError('APP133_CONFIG_INVALID')
    if c['workspace_host']!='https://dbc-0410b264-20c7.cloud.databricks.com' or c['reader_client_id']!='a947eccf-5f94-4369-a3d4-8f83b4ea98a1':raise ValueError('APP133_CONFIG_IDENTITY')
    for k,upper in [('deadline_unix',2**40),('generation_posts_per_process',100),('embedding_posts_per_process',100),('embedding_tokens_per_process',1000000)]:
        if type(c[k]) is not int or not (0 if k=='deadline_unix' else 1)<=c[k]<=upper:raise ValueError('APP133_CONFIG_LIMIT')
    return c

def create_service133(environ,*,root,clock=None,client_factory=None,binding_loader=None):
    c=load_config(root);mode=environ.get('SBS_MODE','local')
    if 'SBS_GENERATION_SELECTION' in environ:raise ValueError('APP133_ALTERNATE_SELECTION_FORBIDDEN')
    if mode=='cloud' and environ.get('SBS_GENIE_ROTATION_CONFIG')!=SELECTOR:raise ValueError('APP133_ROTATION_REQUIRED')
    def factory(**kwargs):
        service=AppService(**kwargs)
        options={'client_factory':client_factory}
        if clock is not None:options['clock']=clock
        return service.configure133(root,c,**options)
    return create_rotating_service(environ,root=root,mode=mode,service_factory=factory,client_factory=client_factory,binding_loader=binding_loader)
