"""Chunked finalApp153 preparation. Requires original Linux+139 gates."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,shutil,time
ROOT=Path(__file__).resolve().parents[1];CHUNK=8388608
def module(path,name):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
base=module('deployment/app_candidate_153.py','final168builder153');require=base.require;read=base.read
TEMPLATE='runs/sk12-app-candidate-153-source'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
BOOTSTRAP="""from pathlib import Path
import os,sys,json
from reassemble163 import reassemble
root=Path(__file__).resolve().parent
print('SBS_CHUNK168_RESULT '+json.dumps(reassemble(root)),flush=True)
os.execv(sys.executable,[sys.executable,str(root/'app133.py')])
"""
def pack(source,*,root=ROOT):
 source=Path(source);root=Path(root);original=base.files(source);require(len(original)==214,'FINAL168_LOGICAL_COUNT')
 app=read(source/'app.yaml');require(app==base.app_config(),'FINAL168_APP_CONFIG');app['command']=['python','bootstrap168.py'];(source/'app.yaml').write_text(json.dumps(app,indent=2)+'\n')
 logical=base.files(source);artifacts=[]
 for name,pin in sorted(logical.items()):
  target=source/name;length=target.stat().st_size
  if length<=CHUNK:continue
  parts=[]
  with target.open('rb') as stream:
   for index,raw in enumerate(iter(lambda:stream.read(CHUNK),b'')):
    namepart=f'chunks163/{pin}/{index:05}.part';part=source/namepart;part.parent.mkdir(parents=True,exist_ok=True)
    with part.open('xb') as out:out.write(raw)
    parts.append({'path':namepart,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
  artifacts.append({'path':name,'bytes':length,'sha256':pin,'chunks':parts});target.unlink()
 manifest={'version':'lossless-chunks163-v1','chunk_bytes':CHUNK,'logical_files_sha256':logical,'artifacts':artifacts,'source133_sha256':base.BASE_SHA}
 (source/'chunks163-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');(source/'reassemble163.py').write_bytes((root/'deployment/reassemble_163.py').read_bytes());(source/'bootstrap168.py').write_text(BOOTSTRAP)
 files=base.files(source);require(all((source/p).stat().st_size<=CHUNK for p in files),'FINAL168_FILE_LIMIT')
 return {'logical_files_sha256':logical,'original153_files_sha256':original,'files_sha256':files,'source_sha256':base.sha(base.encoded(files)),'transport_files':len(files),'artifacts_reassembled':len(artifacts)}
def prepare(destination,*,root=ROOT):
 root=Path(root);source=root/TEMPLATE;m=base.verify(source);require(m['kind']=='candidate153_deadline0_not_deployable' and m['deadline_unix']==0,'FINAL168_TEMPLATE')
 dest=Path(destination);require(not dest.exists(),'FINAL168_DESTINATION_EXISTS');dest.mkdir(parents=True);shutil.copytree(source/'source',dest/'source')
 out={'kind':'held168_deadline0','deadline_unix':0,'base_source133_sha256':base.BASE_SHA,'template153_manifest_sha256':sha(source/'manifest.json'),**pack(dest/'source',root=root),'linux_verified':False,'cloud_executed':False};(dest/'manifest.json').write_text(json.dumps(out,indent=2)+'\n');return out

def materialize(destination,*,linux_evidence,linux_sha,expires_at,root=ROOT,clock=time.time):
 root=Path(root);dest=Path(destination)
 # Exact original153 gates and logical materializer; no weakening or fakeLinux.
 logical=dest/'logical153';out153=base.materialize(root/TEMPLATE,logical,linux_evidence=linux_evidence,linux_sha=linux_sha,expires_at=expires_at,root=root,clock=clock)
 source=dest/'source';shutil.copytree(logical/'source',source);out={'kind':'materialized168_exactreviewrequired','deadline_unix':expires_at,'base_source133_sha256':base.BASE_SHA,'logical153_manifest_sha256':sha(logical/'manifest.json'),'template153_manifest_sha256':sha(root/TEMPLATE/'manifest.json'),'gates':out153['gates'],**pack(source,root=root),'cloud_executed':False,'m2m_verified':False,'ui_verified':False}
 (dest/'manifest.json').write_text(json.dumps(out,indent=2)+'\n');payload={'app_name':base.APP,'host':base.HOST,'observed_public_origin':base.ORIGIN,'source_code_path':'/Workspace/Users/sociosdosmilveintiseis@gmail.com/sbs-radar/releases/app168-'+out['source_sha256'],'mode':'SNAPSHOT','source_sha256':out['source_sha256'],'manifest_sha256':sha(dest/'manifest.json'),'expires_at_unix':expires_at,'limits':{'upload_max':out['transport_files'],'start_max':1,'deploy_max':1,'provider_calls':0}}
 (dest/'deployment-payload.json').write_text(json.dumps(payload,indent=2)+'\n');return out
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--destination',required=True);a=p.parse_args();out=prepare(a.destination);print(json.dumps({k:v for k,v in out.items() if not k.endswith('files_sha256')},indent=2))
