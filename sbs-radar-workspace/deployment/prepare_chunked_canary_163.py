"""Package141 canary using <=8MiB assets; no changed model identity or cloud."""
from pathlib import Path
import argparse,hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[1];CHUNK=8*1024*1024
s=importlib.util.spec_from_file_location('canary163builder141',ROOT/'deployment/prepare_canary_141.py');prior=importlib.util.module_from_spec(s);s.loader.exec_module(prior)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def prepare(destination,*,root=ROOT,expires_at=0):
 root=Path(root);dest=Path(destination);original=prior.prepare(dest,root=root,expires_at=expires_at);source=dest/'source'
 # Preserve original logical source contract apart from explicit reviewed app command.
 app=json.loads((source/'app.yaml').read_bytes());app['command']=['python','reassemble163.py'];(source/'app.yaml').write_text(json.dumps(app,indent=2)+'\n')
 logical={p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()};artifacts=[]
 for name,pin in sorted(logical.items()):
  target=source/name
  if target.stat().st_size<=CHUNK:continue
  parts=[];length=target.stat().st_size
  with target.open('rb') as stream:
   index=0
   for raw in iter(lambda:stream.read(CHUNK),b''):
    path=f'chunks163/{pin}/{index:05}.part';part=source/path;part.parent.mkdir(parents=True,exist_ok=True)
    with part.open('xb') as output:output.write(raw)
    parts.append({'path':path,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()});index+=1
  artifacts.append({'path':name,'bytes':length,'sha256':pin,'chunks':parts});target.unlink()
 chunks={'version':'lossless-chunks163-v1','chunk_bytes':CHUNK,'logical_files_sha256':logical,'artifacts':artifacts,'source133_sha256':original['source133_sha256']}
 (source/'chunks163-manifest.json').write_text(json.dumps(chunks,indent=2)+'\n');(source/'reassemble163.py').write_bytes((root/'deployment/reassemble_163.py').read_bytes())
 files={p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()}
 if any((source/name).stat().st_size>CHUNK for name in files):raise ValueError('CHUNK163_TRANSPORT_FILE_TOO_LARGE')
 out={'kind':'chunked163_linux_canary_not_release','expires_at_unix':expires_at,'source133_sha256':original['source133_sha256'],'original141_manifest':original,'files_sha256':files,'source_sha256':hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'chunk_bytes':CHUNK,'transport_files':len(files),'artifacts_reassembled':len(artifacts),'logical_files':len(logical),'linux_verified':False,'quality_accepted':False}
 (dest/'manifest.json').write_text(json.dumps(out,indent=2)+'\n');return out
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--destination',required=True);p.add_argument('--expires-at-unix',type=int,default=0);a=p.parse_args();m=prepare(a.destination,expires_at=a.expires_at_unix);print(json.dumps({k:v for k,v in m.items() if k not in ('files_sha256','original141_manifest')},indent=2))
