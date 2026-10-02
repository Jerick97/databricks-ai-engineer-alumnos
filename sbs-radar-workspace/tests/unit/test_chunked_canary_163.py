from pathlib import Path
import importlib.util,json,shutil
import pytest
ROOT=Path(__file__).resolve().parents[2]
def load(path,name):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def test_real_package_roundtrip_all_logical_hashes_and_boot_target(tmp_path):
 m=load('deployment/reassemble_163.py','reassemble163test');source=ROOT/'runs/sk12-chunked-canary-163-source-v2/source';target=tmp_path/'source';shutil.copytree(source,target)
 manifest=json.loads((source/'chunks163-manifest.json').read_bytes());assert len(manifest['artifacts'])==3
 assert max(p.stat().st_size for p in source.rglob('*') if p.is_file())<=m.CHUNK
 out=m.reassemble(target);assert out['newly_reassembled']==3 and out['logical_files']==218 and out['network_calls']==0
 for name,pin in manifest['logical_files_sha256'].items():assert m.digest(target/name)==pin
 assert (target/'canary141.py').read_bytes()==(ROOT/'deployment/linux_canary_141.py').read_bytes()
 assert json.loads((target/'app.yaml').read_bytes())['command']==['python','reassemble163.py']
 assert m.reassemble(target)['newly_reassembled']==0
 original=json.loads((target/'canary133-manifest.json').read_bytes())
 for name,pin in original['files_sha256'].items():assert m.digest(target/name)==pin

def fixture(tmp_path):
 import hashlib
 m=load('deployment/reassemble_163.py','reassemble163fixture');raw=b'x'*(m.CHUNK+1);pin=hashlib.sha256(raw).hexdigest();parts=[]
 for i,payload in enumerate([raw[:m.CHUNK],raw[m.CHUNK:]]):
  name=f'chunks163/{pin}/{i:05}.part';path=tmp_path/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(payload);parts.append({'path':name,'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest()})
 data={'version':'lossless-chunks163-v1','chunk_bytes':m.CHUNK,'logical_files_sha256':{'models/test.onnx':pin},'artifacts':[{'path':'models/test.onnx','bytes':len(raw),'sha256':pin,'chunks':parts}]};(tmp_path/'chunks163-manifest.json').write_text(json.dumps(data));return m,data

def test_tampered_chunk_rejected_without_output(tmp_path):
 m,data=fixture(tmp_path);(tmp_path/data['artifacts'][0]['chunks'][0]['path']).write_bytes(b'bad')
 with pytest.raises(ValueError,match='PART_HASH'):m.reassemble(tmp_path)
 assert not (tmp_path/'models/test.onnx').exists()

def test_existing_changed_model_never_overwritten(tmp_path):
 m,_=fixture(tmp_path);target=tmp_path/'models/test.onnx';target.parent.mkdir();target.write_bytes(b'wrong')
 with pytest.raises(ValueError,match='EXISTING_MISMATCH'):m.reassemble(tmp_path)
 assert target.read_bytes()==b'wrong'

def test_reordered_chunk_rejected(tmp_path):
 m,data=fixture(tmp_path);data['artifacts'][0]['chunks'].reverse();(tmp_path/'chunks163-manifest.json').write_text(json.dumps(data))
 with pytest.raises(ValueError,match='ORDER'):m.reassemble(tmp_path)

def test_symlink_escape_rejected(tmp_path):
 m,_=fixture(tmp_path);outside=tmp_path/'outside';outside.mkdir();(tmp_path/'models').symlink_to(outside,target_is_directory=True)
 with pytest.raises(ValueError,match='SYMLINK'):m.reassemble(tmp_path)
 assert not (outside/'test.onnx').exists()

def test_original_backend_limit_regression():
 original=json.loads((ROOT/'runs/sk12-linux-canary-141-source-v2/manifest.json').read_bytes());source=ROOT/'runs/sk12-linux-canary-141-source-v2/source'
 oversized=[name for name in original['files_sha256'] if (source/name).stat().st_size>10485760]
 assert oversized and any('model_qint8_arm64.onnx' in name for name in oversized)
 packaged=ROOT/'runs/sk12-chunked-canary-163-source-v2/source';assert all(p.stat().st_size<=8388608 for p in packaged.rglob('*') if p.is_file())

def test_reassembled_runtime_cpu_with_explicit_platform_dependency_fixtures(tmp_path,monkeypatch):
 import socket,time
 reassembly=load('deployment/reassemble_163.py','reassembly163cpu');source=tmp_path/'source';shutil.copytree(ROOT/'runs/sk12-chunked-canary-163-source-v2/source',source);reassembly.reassemble(source)
 spec=importlib.util.spec_from_file_location('core141from163',source/'canary141.py');core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
 monkeypatch.setattr(core,'require_platform',lambda:'fixture_not_Linux_proof')
 expected=dict(line.split('==') for line in (source/'deployment/requirements-app.txt').read_text().splitlines() if '==' in line);monkeypatch.setattr(core.importlib.metadata,'version',lambda name:expected[name])
 old=(socket.socket.connect,socket.socket.connect_ex,socket.create_connection)
 try:
  result=core.probe(source,int(time.time())+120)
  assert result['cpu_execution']['system']=='Darwin' and result['platform']['machine']=='fixture_not_Linux_proof'
  assert result['provider_calls']==result['sql_calls']==0 and len(result['scores'])==2 and len(result['comparisons'])==3
 finally:socket.socket.connect,socket.socket.connect_ex,socket.create_connection=old
