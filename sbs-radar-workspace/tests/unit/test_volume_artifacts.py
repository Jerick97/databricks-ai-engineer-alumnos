from io import BytesIO
from types import SimpleNamespace
import hashlib,json
import pytest
from sbs.operations.volume_artifacts import VolumeArtifacts

class Exists(Exception):error_code='RESOURCE_ALREADY_EXISTS'
class Files:
 def __init__(self):self.data={};self.calls=[]
 def create_directory(self,directory_path):self.calls.append(('mkdir',directory_path))
 def upload(self,file_path,contents,overwrite=None):
  assert overwrite is False;self.calls.append(('upload',file_path))
  if file_path in self.data:raise Exists()
  self.data[file_path]=contents.read()
 def download(self,file_path):return SimpleNamespace(contents=BytesIO(self.data[file_path]))

def store(files,**kwargs):return VolumeArtifacts(files,prefix='/Volumes/catalog/sbs_radar/artifacts/sbs-refresh',**kwargs)
def local(tmp_path):
 p=tmp_path/'file.json';p.write_bytes(b'{}');return {'file.json':hashlib.sha256(b'{}').hexdigest()}

def test_write_once_readback_and_existing_content(tmp_path):
 f=Files();v=store(f);closure=local(tmp_path);a=v.stage('run-1',tmp_path,closure);b=v.stage('run-1',tmp_path,closure)
 assert a==b and v.verify(a['artifacts'])
 assert all(path.startswith('/Volumes/catalog/sbs_radar/artifacts/sbs-refresh/runs/run-1/') for path in f.data)
 nextpath=next(iter(f.data));f.data[nextpath]=b'changed'
 with pytest.raises(ValueError):v.stage('run-1',tmp_path,closure)

def test_caps_and_symlink_before_upload(tmp_path):
 f=Files();closure=local(tmp_path)
 with pytest.raises(ValueError):store(f,max_total_bytes=1).stage('run',tmp_path,closure)
 assert not f.calls
 (tmp_path/'link.json').symlink_to('file.json')
 with pytest.raises(ValueError):store(f).stage('run',tmp_path,{'link.json':closure['file.json']})
 assert not f.calls

@pytest.mark.parametrize('name',['../x','/absolute','x/../y','x%2Fy','x\\y'])
def test_paths_fail_closed(tmp_path,name):
 with pytest.raises(ValueError):store(Files()).stage('run',tmp_path,{name:'a'*64})

def test_wrong_readback_never_validates(tmp_path):
 f=Files();f.download=lambda file_path:SimpleNamespace(contents=BytesIO(b'wrong'))
 with pytest.raises(ValueError):store(f).stage('run',tmp_path,local(tmp_path))

def manifest_fixture(files,version=1):
 from sbs.operations.cloud_dispatch import canonical,digest
 from sbs.operations.volume_artifacts import sha
 entries={name:{'sha256':sha(b'{}'),'bytes':2} for name in files}
 base=store(Files()).prefix+'/runs/run/'+digest(entries)
 raw=canonical({'version':version,'run_id':'run','closure_sha256':digest(entries),'files':entries}).encode()
 f=Files();f.data={base+'/'+name:b'{}' for name in files};f.data[base+'/manifest.json']=raw
 return f,{p:sha(v) for p,v in f.data.items()},base+'/manifest.json'

def test_cw01_manifest_cap_before_entry_downloads():
 f,artifacts,path=manifest_fixture(['a','b']);downloads=[];original=f.download
 def counted(p):downloads.append(p);return original(p)
 f.download=counted
 with pytest.raises(ValueError):store(f,max_files=2).verify({path:artifacts[path]})
 assert downloads==[path]

def test_cw01_incomplete_closure_before_entry_downloads():
 f,artifacts,path=manifest_fixture(['a']);downloads=[];original=f.download
 def counted(p):downloads.append(p);return original(p)
 f.download=counted
 with pytest.raises(ValueError):store(f).verify({path:artifacts[path]})
 assert downloads==[path]

@pytest.mark.parametrize('version',[True,1.0])
def test_cw02_manifest_version_exact_integer(version):
 f,artifacts,_=manifest_fixture(['a'],version)
 with pytest.raises(ValueError):store(f).verify(artifacts)
