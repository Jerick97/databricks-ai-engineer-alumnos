from pathlib import Path
import importlib.util
import pytest
ROOT=Path(__file__).resolve().parents[2]
def load():
 s=importlib.util.spec_from_file_location('canary141',ROOT/'deployment/linux_canary_141.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def test_reject_nonlinux_before_runtime():
 m=load()
 with pytest.raises(ValueError,match='LINUX'):m.require_platform(system='Darwin',machine='arm64',python=(3,11))
 with pytest.raises(ValueError,match='PYTHON'):m.require_platform(system='Linux',machine='x86_64',python=(3,14))
 assert m.require_platform(system='Linux',machine='x86_64',python=(3,11))=='x86_64'

def test_expiry_and_no_general_routes():
 m=load()
 with pytest.raises(ValueError):m.check_expiry(0,now=1)
 with pytest.raises(ValueError):m.check_expiry(True,now=0)
 with pytest.raises(ValueError):m.check_expiry(1900,now=0)
 assert m.check_expiry(1000,now=0)==1000
 assert m.PUBLIC_PATHS=={'/health','/evidence'}

def test_source_requirements_gap_and_overlay_closure(tmp_path):
 import json,hashlib
 spec=importlib.util.spec_from_file_location('builder141',ROOT/'deployment/prepare_canary_141.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
 source133=ROOT/'runs/sk12-app-133-source-v3/source'
 assert (source133/'requirements.txt').read_text().strip()=='-r deployment/requirements-app.txt'
 assert not (source133/'deployment/requirements-app.txt').exists()
 out=b.prepare(tmp_path/'prepared',expires_at=0)
 source=tmp_path/'prepared/source'
 assert (source/'deployment/requirements-app.txt').read_bytes()==(ROOT/'runs/sk12-linux-installed.txt').read_bytes()
 assert (source/'requirements.txt').read_bytes()==(source133/'requirements.txt').read_bytes()
 assert json.loads((source/'app.yaml').read_bytes())['command']==['python','canary141.py']
 assert not out['linux_verified'] and out['expires_at_unix']==0
 assert load().validate_source(source)['source_sha256']==out['source133_sha256']
 (source/'src/sbs/conversation/hybrid_125.py').write_text('drift')
 with pytest.raises(ValueError,match='SOURCE_DRIFT'):load().validate_source(source)

def test_no_outbound_connection():
 with pytest.raises(RuntimeError,match='OUTBOUND'):load().deny_connect(('some-host',443))

def test_probe_body_real_cpu_with_explicit_fixture_platform_and_metadata(monkeypatch):
 import json,socket,time
 m=load();root=ROOT/'runs/sk12-linux-canary-141-source-v2/source'
 # Linux unavailable: these two gates are deliberate fixtures, not evidence.
 monkeypatch.setattr(m,'require_platform',lambda:'fixture_not_Linux_proof')
 expected=dict(line.split('==') for line in (root/'deployment/requirements-app.txt').read_text().splitlines() if '==' in line)
 monkeypatch.setattr(m.importlib.metadata,'version',lambda name:expected[name])
 old=(socket.socket.connect,socket.socket.connect_ex,socket.create_connection)
 try:
  out=m.probe(root,int(time.time())+120)
  assert out['cpu_execution']['system']=='Darwin'
  assert out['platform']['machine']=='fixture_not_Linux_proof'
  assert out['provider_calls']==0 and out['m2m_verified'] is False
  assert len(out['comparisons'])==3 and len(out['scores'])==2
 finally:socket.socket.connect,socket.socket.connect_ex,socket.create_connection=old
