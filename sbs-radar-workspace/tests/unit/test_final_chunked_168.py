from pathlib import Path
from types import SimpleNamespace
import importlib.util,io,json,shutil
import pytest
ROOT=Path(__file__).resolve().parents[2]
def module(path='deployment/final_deploy_168.py',name='test168'):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def test_exact214logical_roundtrip_with_app133_target(tmp_path):
 source=tmp_path/'source';shutil.copytree(ROOT/'runs/sk12-final-chunked-168-source/source',source)
 reassembly=module('deployment/reassemble_163.py','test168reassembly');result=reassembly.reassemble(source);assert result['logical_files']==214 and result['newly_reassembled']==3
 original=json.loads((ROOT/'runs/sk12-app-candidate-153-source/manifest.json').read_bytes())
 for p,h in original['files_sha256'].items():
  if p!='app.yaml':assert reassembly.digest(source/p)==h
 assert json.loads((source/'app.yaml').read_bytes())['command']==['python','bootstrap168.py']
 assert (source/'reassemble163.py').read_bytes()==(ROOT/'deployment/reassemble_163.py').read_bytes()
 assert "str(root/'app133.py')" in (source/'bootstrap168.py').read_text()
 assert all(p.stat().st_size<=8388608 for p in (ROOT/'runs/sk12-final-chunked-168-source/source').rglob('*') if p.is_file())

def test_missing_linux_does_not_emit_deadline(tmp_path,monkeypatch):
 m=module();monkeypatch.setattr(m,'preflight',lambda r:{});monkeypatch.setattr(m,'review',lambda r:None)
 with pytest.raises(FileNotFoundError):m.materialize(tmp_path/'missing','bad',root=tmp_path)
 assert not (tmp_path/m.MATERIALIZED).exists()

def test_preflight_held():assert module().preflight()['deadline_emitted'] is False

@pytest.mark.parametrize('initial,start_count',[('STOPPED',1),('ACTIVE',0)])
def test_full234upload_conditional_start_singledeploy(tmp_path,monkeypatch,initial,start_count):
 m=module();monkeypatch.setattr(m,'preflight',lambda r:{});monkeypatch.setattr(m,'review',lambda r:None)
 package=tmp_path/'package';files={}
 for i in range(234):
  p=package/'source'/f'f{i}.txt';p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(str(i).encode());files[p.name]=m.sha(p)
 manifest={'files_sha256':files,'source_sha256':'newsha'};m.durable(package/'manifest.json',manifest)
 payload={'source_code_path':'/new168','expires_at_unix':200};monkeypatch.setattr(m,'ready',lambda r:(package,manifest,payload))
 for p in (m.FREEZE,m.EXACT_REVIEW):m.durable(tmp_path/p,{})
 m.durable(tmp_path/m.mission.STATE/'source-binding.json',{'source_code_path':'/old166'});m.durable(tmp_path/m.mission.STATE/'deploy-receipt.json',{'deployment_id':'old166'})
 stored={};dirs=set();posts=dict(upload=0,mkdir=0,start=0,deploy=0);phase=[initial]
 class Missing(Exception):error_code='RESOURCE_DOES_NOT_EXIST'
 class Workspace:
  def get_status(self,path):
   if path in dirs:return {'object_type':'DIRECTORY'}
   if path in stored:return {'object_type':'FILE'}
   raise Missing()
  def mkdirs(self,path):dirs.add(path);posts['mkdir']+=1
  def upload(self,path,stream,**k):assert k['format'].value=='RAW';stored[path]=stream.read();posts['upload']+=1
  def download(self,path,**k):assert k['format'].value=='AUTO';return io.BytesIO(stored[path])
 class Apps:
  def get(self,name):return {'name':name,'service_principal_id':77041447522099,'service_principal_client_id':'a947eccf-5f94-4369-a3d4-8f83b4ea98a1','compute_status':{'state':phase[0]},'last_deployment_id':'old166','active_deployment':{'source_code_path':'/old166','deployment_id':'old166'}}
  def start(self,name):posts['start']+=1;phase[0]='ACTIVE'
  def deploy(self,name,body):posts['deploy']+=1;return SimpleNamespace(response={'deployment_id':'new168'})
  def get_deployment(self,*a):return {'status':{'state':'SUCCEEDED'}}
 server=SimpleNamespace(workspace=Workspace(),apps=Apps(),api=SimpleNamespace(counts=posts,calls=0,session=SimpleNamespace(close=lambda:None)))
 args=dict(root=tmp_path,config_factory=lambda **k:SimpleNamespace(host=m.base.HOST,authenticate=lambda:{'fixture':'auth'}),services_factory=lambda *a,**k:server,clock=lambda:100,sleep=lambda n:None,readiness_fn=lambda *a:{'http_status':200,'accepted':False})
 out=m.execute(**args);assert out['status']=='deployed_demo_admission_pending' and posts['upload']==234 and posts['start']==start_count and posts['deploy']==1 and out['provider_calls']==0
 assert m.read(tmp_path/m.STATE/'demo-ledger/binding.json')['process_epoch'] is None
 with pytest.raises(FileExistsError):m.execute(**args)
 assert posts['deploy']==1

def test_other_active_deployment_rejected():
 m=module();a={'name':m.base.APP,'service_principal_id':77041447522099,'service_principal_client_id':'a947eccf-5f94-4369-a3d4-8f83b4ea98a1','compute_status':{'state':'ACTIVE'},'active_deployment':{'source_code_path':'/foreign','deployment_id':'foreign'}}
 with pytest.raises(ValueError,match='OTHER_ACTIVE'):m.current(a,{'source_code_path':'/old166','deployment_id':'old166'})

def test_externalledger_is_existing157_implementation():
 m=module();assert m.DemoLedger is m.prior.DemoLedger
