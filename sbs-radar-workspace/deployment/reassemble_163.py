"""Reassemble exact pinned artifacts locally before unchanged canary141 entrypoint."""
from pathlib import Path
import argparse,hashlib,json,os,stat
CHUNK=8*1024*1024

def require(value,code):
 if not value:raise ValueError(code)
def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as stream:
  for block in iter(lambda:stream.read(CHUNK),b''):h.update(block)
 return h.hexdigest()
def safe(root,name):
 p=Path(name);require(isinstance(name,str) and name and not p.is_absolute() and '..' not in p.parts,'CHUNK163_PATH')
 target=root/p;require(target.resolve().is_relative_to(root.resolve()),'CHUNK163_ESCAPE')
 for parent in (target,*target.parents):
  if parent==root:break
  require(not parent.is_symlink(),'CHUNK163_SYMLINK')
 return target

def reassemble(root):
 root=Path(root).resolve();manifest=json.loads((root/'chunks163-manifest.json').read_bytes())
 require(manifest.get('version')=='lossless-chunks163-v1' and manifest.get('chunk_bytes')==CHUNK,'CHUNK163_MANIFEST')
 outputs=set();chunk_names=set();count=0
 for item in manifest['artifacts']:
  name=item['path'];require(name not in outputs,'CHUNK163_DUPLICATE_OUTPUT');outputs.add(name)
  target=safe(root,name);require(name in manifest['logical_files_sha256'] and item['sha256']==manifest['logical_files_sha256'][name] and type(item['bytes'])is int and item['bytes']>CHUNK,'CHUNK163_IDENTITY')
  chunks=item['chunks'];require(isinstance(chunks,list) and len(chunks)==(item['bytes']+CHUNK-1)//CHUNK,'CHUNK163_COUNT')
  total=0
  for index,part in enumerate(chunks):
   require(part['path']==f'chunks163/{item["sha256"]}/{index:05}.part' and part['path'] not in chunk_names,'CHUNK163_ORDER_OR_DUPLICATE');chunk_names.add(part['path'])
   path=safe(root,part['path']);length=part['bytes'];require(type(length)is int and length==min(CHUNK,item['bytes']-index*CHUNK) and path.stat().st_size==length and digest(path)==part['sha256'],'CHUNK163_PART_HASH');total+=length
  require(total==item['bytes'],'CHUNK163_LENGTH')
  if target.exists():require(target.is_file() and target.stat().st_size==item['bytes'] and digest(target)==item['sha256'],'CHUNK163_EXISTING_MISMATCH');continue
  target.parent.mkdir(parents=True,exist_ok=True);temporary=target.with_name(target.name+'.reassembly163.tmp')
  fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
  try:
   with os.fdopen(fd,'wb') as out:
    for part in chunks:
     with safe(root,part['path']).open('rb') as stream:
      for block in iter(lambda:stream.read(CHUNK),b''):out.write(block)
    out.flush();os.fsync(out.fileno())
   require(temporary.stat().st_size==item['bytes'] and digest(temporary)==item['sha256'],'CHUNK163_REASSEMBLY_HASH')
   os.link(temporary,target);temporary.unlink()
   directory=os.open(target.parent,os.O_RDONLY)
   try:os.fsync(directory)
   finally:os.close(directory)
  except Exception:
   if temporary.exists():temporary.unlink()
   raise
  count+=1
 for name,pin in manifest['logical_files_sha256'].items():require(digest(safe(root,name))==pin,'CHUNK163_LOGICAL_SOURCE_DRIFT')
 return {'status':'exact_bytes_reassembled','artifacts':len(outputs),'newly_reassembled':count,'logical_files':len(manifest['logical_files_sha256']),'network_calls':0,'linux_verified':False}
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--verify-only',action='store_true');args=parser.parse_args();root=Path(__file__).resolve().parent
 out=reassemble(root);print('SBS_CHUNK163_RESULT '+json.dumps(out),flush=True)
 if not args.verify_only:os.execv(__import__('sys').executable,[__import__('sys').executable,str(root/'canary141.py')])
