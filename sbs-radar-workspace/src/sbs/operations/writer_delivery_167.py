"""Noncircular delivery: template + separately pinned module/config/archive data."""
import base64,hashlib
from pathlib import Path
from .writer_authority_167 import parse_source,canonical,require,digest,sha
TEMPLATE='''# Databricks notebook source
import base64,hashlib,json,pathlib,tarfile,tempfile,sys,types
DELIVERY167 = None
ATTESTATION167 = None
def checked(value,code):
    if not value: raise ValueError(code)
D=DELIVERY167
module_raw=base64.b64decode(D['module_base64'])
checked(hashlib.sha256(module_raw).hexdigest()==D['module_sha256'],'MODULE167_PIN')
module=types.ModuleType('sbs_writer_authority167');sys.modules[module.__name__]=module
exec(compile(module_raw,'writer-authority167','exec'),module.__dict__)
widgets={name:dbutils.widgets.get(name) for name in ('job_id','run_id','request_id','release_id','snapshot_backend_id')}
archive=pathlib.Path(D['archive_path'])
checked(hashlib.sha256(archive.read_bytes()).hexdigest()==D['archive_sha256'],'ARCHIVE167_PIN')
with tempfile.TemporaryDirectory(prefix='sbs-writer167-') as tmp:
    root=pathlib.Path(tmp)/'sbs-radar'
    with tarfile.open(archive) as tar:
        members=tar.getmembers();names=[m.name for m in members]
        checked(len(names)==len(set(names)) and len(names)<=2000 and sum(m.size for m in members)<=134217728,'ARCHIVE167_CAP')
        checked(all(m.isfile() and m.name.startswith('sbs-radar/') and '..' not in pathlib.PurePosixPath(m.name).parts for m in members),'ARCHIVE167_PATH')
        tar.extractall(tmp,filter='data')
    manifest_raw=(root/D['manifest_path']).read_bytes()
    checked(hashlib.sha256(manifest_raw).hexdigest()==D['release_id'],'MANIFEST167_PIN')
    for name,pin in json.loads(manifest_raw)['files'].items():
        checked(not pathlib.PurePosixPath(name).is_absolute() and '..' not in pathlib.PurePosixPath(name).parts and hashlib.sha256((root/name).read_bytes()).hexdigest()==pin,'MANIFEST167_CLOSURE')
    sys.path.insert(0,str(root/'src'))
    from sbs.operations.cloud_driver import load_config
    config=load_config(D['config_path'],D['config_sha256'])
    checked(config.writer.release_id==D['release_id'],'CONFIG167_RELEASE')
    result=module.execute_from_config167(config,root,delivery=D,widgets=widgets)
    dbutils.notebook.exit(json.dumps({k:result[k] for k in ('status','evidence_mode','cloud_acceptance','cost','observations','writer_transport') if k in result},sort_keys=True))
'''
def build_delivery(*,archive_path,archive_sha,manifest_path,release_id,config_path,config_sha,job_id,request_id):
 raw=Path(__file__).with_name('writer_authority_167.py').read_bytes();_,template_sha=parse_source(TEMPLATE.encode())
 return {'version':'delivery167','module_base64':base64.b64encode(raw).decode(),'module_sha256':sha(raw),'template_sha256':template_sha,'archive_path':archive_path,'archive_sha256':archive_sha,'manifest_path':manifest_path,'release_id':release_id,'config_path':config_path,'config_sha256':config_sha,'job_id':job_id,'request_id':request_id,'request_token':digest({'job_id':job_id,'request_id':request_id})}
def render(delivery,attestation=None):
 source=TEMPLATE.replace('DELIVERY167 = None','DELIVERY167 = '+repr(delivery),1).replace('ATTESTATION167 = None','ATTESTATION167 = '+repr(attestation),1)
 parts,pin=parse_source(source.encode());require(pin==delivery['template_sha256'] and parts=={'DELIVERY167':delivery,'ATTESTATION167':attestation},'DELIVERY167_GRAPH');compile(source,'writer167','exec');return source
