"""Write-once Files API objects and complete readback; no rename/delete APIs.

The server supplies FilesAPI and a dedicated pre-authorized Volume prefix.
WRITE VOLUME is not WORM: trusted admins/writer must honor no-overwrite policy.
"""
from io import BytesIO
import hashlib
import json
from pathlib import Path,PurePosixPath
import re
from .cloud_dispatch import canonical,digest,require
from . import verify_closure

def sha(raw):return hashlib.sha256(raw).hexdigest()
def relative(name):
    require(isinstance(name,str) and name and not name.startswith('/') and all(re.fullmatch('[A-Za-z0-9_.-]+',p) and p not in ('.','..') for p in name.split('/')),'ARTIFACT_PATH_INVALID')
    return name


class VolumeArtifacts:
    def __init__(self,files,*,prefix,max_files=500,max_total_bytes=128*1024*1024,max_file_bytes=32*1024*1024,max_calls=3000):
        require(isinstance(prefix,str) and re.fullmatch(r'/Volumes/[A-Za-z0-9_-]+/sbs_radar/[A-Za-z0-9_-]+/sbs-refresh',prefix),'DEDICATED_VOLUME_PREFIX_REQUIRED')
        require(all(type(x) is int and x>0 for x in (max_files,max_total_bytes,max_file_bytes,max_calls)),'ARTIFACT_CAPS_INVALID')
        self.files=files;self.prefix=prefix;self.max_files=max_files;self.max_total=max_total_bytes;self.max_file=max_file_bytes;self.max_calls=max_calls;self.calls=0
    def _call(self,method,*args,**kwargs):
        require(self.calls<self.max_calls,'FILES_QUOTA_EXCEEDED');self.calls+=1
        return getattr(self.files,method)(*args,**kwargs)
    def _path(self,path):
        require(isinstance(path,str) and path.startswith(self.prefix+'/runs/'),'VOLUME_PATH_OUTSIDE_PREFIX')
        relative(path[len(self.prefix)+1:]);return path
    def _read(self,path,expected_size=None):
        self._path(path)
        try:
            response=self._call('download',path);stream=response.contents
            try:raw=stream.read(self.max_file+1)
            finally:stream.close()
        except Exception:raise ValueError('ARTIFACT_READBACK_FAILED') from None
        require(isinstance(raw,bytes) and len(raw)<=self.max_file and (expected_size is None or len(raw)==expected_size),'ARTIFACT_READBACK_SIZE')
        return raw
    def _put(self,path,raw):
        self._path(path)
        try:self._call('upload',path,BytesIO(raw),overwrite=False)
        except Exception as exc:
            # Existing-name conflict is reconciled only by exact byte hash.
            if getattr(exc,'error_code',None) not in ('RESOURCE_ALREADY_EXISTS','ALREADY_EXISTS'):
                raise ValueError('ARTIFACT_UPLOAD_UNCONFIRMED') from None
        require(sha(self._read(path,len(raw)))==sha(raw),'ARTIFACT_READBACK_HASH')
    def stage(self,run_id,local_root,closure):
        require(isinstance(run_id,str) and re.fullmatch('[A-Za-z0-9_-]{1,80}',run_id),'ARTIFACT_RUN_ID_INVALID')
        require(isinstance(closure,dict) and 0<len(closure)<=self.max_files-1,'ARTIFACT_COUNT_CAP')
        for name in closure:relative(name)
        require('manifest.json' not in closure,'RESERVED_MANIFEST_NAME')
        root=Path(local_root).resolve();verify_closure(root,closure)
        contents={};total=0;entries={}
        for name,expected in sorted(closure.items()):
            raw=(root/name).read_bytes();total+=len(raw)
            require(sha(raw)==expected and len(raw)<=self.max_file and total<=self.max_total,'ARTIFACT_BYTES_OR_HASH')
            contents[name]=raw;entries[name]={'sha256':expected,'bytes':len(raw)}
        closure_id=digest(entries);base=self.prefix+'/runs/'+run_id+'/'+closure_id
        manifest={'version':1,'run_id':run_id,'closure_sha256':closure_id,'files':entries};rawmanifest=canonical(manifest).encode()
        require(total+len(rawmanifest)<=self.max_total and len(rawmanifest)<=self.max_file,'ARTIFACT_BYTES_CAP')
        # Upload only after all local bytes pass validation. All remote paths are derived.
        dirs={str(PurePosixPath(base+'/'+name).parent) for name in entries};dirs.add(base)
        for directory in sorted(dirs):
            self._path(directory)
            try:self._call('create_directory',directory)
            except Exception:raise ValueError('ARTIFACT_DIRECTORY_FAILED') from None
        artifacts={}
        for name,raw in contents.items():
            path=base+'/'+name;self._put(path,raw);artifacts[path]=sha(raw)
        path=base+'/manifest.json';require('manifest.json' not in entries,'RESERVED_MANIFEST_NAME')
        self._put(path,rawmanifest);artifacts[path]=sha(rawmanifest)
        require(self.verify(artifacts),'ARTIFACT_CLOSURE_FAILED')
        return {'release_id':sha(rawmanifest),'manifest_path':path,'closure_sha256':closure_id,'artifacts':artifacts}
    def verify(self,artifacts):
        require(isinstance(artifacts,dict) and 0<len(artifacts)<=self.max_files,'ARTIFACT_COUNT_CAP')
        manifests=[p for p in artifacts if p.endswith('/manifest.json')];require(len(manifests)==1,'ONE_MANIFEST_REQUIRED')
        for path,expected in artifacts.items():
            self._path(path);require(isinstance(expected,str) and re.fullmatch('[0-9a-f]{64}',expected),'ARTIFACT_HASH_INVALID')
        manifestpath=manifests[0];raw=self._read(manifestpath);require(sha(raw)==artifacts[manifestpath],'ARTIFACT_MANIFEST_HASH')
        try:m=json.loads(raw)
        except Exception:raise ValueError('ARTIFACT_MANIFEST_INVALID') from None
        require(isinstance(m,dict) and set(m)=={'version','run_id','closure_sha256','files'} and type(m['version']) is int and m['version']==1 and isinstance(m['files'],dict) and isinstance(m['run_id'],str) and re.fullmatch('[A-Za-z0-9_-]{1,80}',m['run_id']) and isinstance(m['closure_sha256'],str) and re.fullmatch('[0-9a-f]{64}',m['closure_sha256']),'ARTIFACT_MANIFEST_INVALID')
        require(0<len(m['files'])<self.max_files,'ARTIFACT_COUNT_CAP')
        require(digest(m['files'])==m['closure_sha256'],'ARTIFACT_CLOSURE_HASH');base=manifestpath.rsplit('/',1)[0]
        require(base==self.prefix+'/runs/'+m['run_id']+'/'+m['closure_sha256'],'ARTIFACT_NAMESPACE_MISMATCH')
        expected={manifestpath:sha(raw)};total=len(raw)
        for name,item in m['files'].items():
            relative(name);require(isinstance(item,dict) and set(item)=={'bytes','sha256'} and type(item['bytes']) is int and 0<=item['bytes']<=self.max_file,'ARTIFACT_ENTRY_INVALID')
            require(isinstance(item['sha256'],str) and re.fullmatch('[0-9a-f]{64}',item['sha256']) and name!='manifest.json','ARTIFACT_ENTRY_INVALID')
            path=base+'/'+name;expected[path]=item['sha256'];total+=item['bytes']
        require(artifacts==expected,'ARTIFACT_CLOSURE_INCOMPLETE')
        require(total<=self.max_total,'ARTIFACT_BYTES_CAP')
        for name,item in m['files'].items():
            data=self._read(base+'/'+name,item['bytes'])
            require(sha(data)==item['sha256'],'ARTIFACT_CLOSURE_HASH')
        return True
    def recover(self,manifest_path,manifest_sha256):
        """Bounded readback of the persisted locator; never uploads or recaptures."""
        self._path(manifest_path)
        require(manifest_path.endswith('/manifest.json') and len(manifest_path.encode())<=1024 and isinstance(manifest_sha256,str) and re.fullmatch('[0-9a-f]{64}',manifest_sha256),'MANIFEST_LOCATOR_INVALID')
        raw=self._read(manifest_path);require(sha(raw)==manifest_sha256,'ARTIFACT_MANIFEST_HASH')
        try:m=json.loads(raw)
        except Exception:raise ValueError('ARTIFACT_MANIFEST_INVALID') from None
        require(isinstance(m,dict) and isinstance(m.get('files'),dict) and 0<len(m['files'])<self.max_files,'ARTIFACT_MANIFEST_INVALID')
        base=manifest_path.rsplit('/',1)[0];artifacts={manifest_path:manifest_sha256}
        for name,item in m['files'].items():
            relative(name);require(isinstance(item,dict) and isinstance(item.get('sha256'),str),'ARTIFACT_ENTRY_INVALID')
            artifacts[base+'/'+name]=item['sha256']
        require(self.verify(artifacts),'ARTIFACT_CLOSURE_UNVERIFIED');return artifacts
