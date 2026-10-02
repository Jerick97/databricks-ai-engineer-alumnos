from pathlib import Path
from types import SimpleNamespace
import importlib.util,json
import pytest
ROOT=Path(__file__).resolve().parents[2]
def module():
 s=importlib.util.spec_from_file_location('test157',ROOT/'deployment/app_deploy_157.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def test_preflight_no_deadline_214():
 p=module().preflight();assert p['uploads_max']==214 and p['start_max']==0 and p['deadline_emitted'] is False

def test_no_linux_no_materialization(tmp_path,monkeypatch):
 m=module();monkeypatch.setattr(m,'preflight',lambda r:{});monkeypatch.setattr(m,'check_review',lambda r:None)
 with pytest.raises(FileNotFoundError):m.materialize(tmp_path/'no-report','missing',root=tmp_path)
 assert not (tmp_path/m.MATERIALIZED).exists()

def test_start_forbidden_and_deploy_reserved_once():
 m=module();a=m.Api(SimpleNamespace(do=lambda *a,**k:None),mkdirs=1)
 with pytest.raises(ValueError,match='CAP'):a.do('POST','/api/2.0/apps/sbs-radar-pilot/start')
 a.do('POST','/api/2.0/apps/sbs-radar-pilot/deployments')
 with pytest.raises(ValueError,match='CAP'):a.do('POST','/api/2.0/apps/sbs-radar-pilot/deployments')

def test_ownership_requires_current_canary_exact():
 m=module();a={'name':m.base.APP,'service_principal_id':77041447522099,'service_principal_client_id':'a947eccf-5f94-4369-a3d4-8f83b4ea98a1','compute_status':{'state':'ACTIVE'},'active_deployment':{'deployment_id':'old','source_code_path':'/own'}}
 m.owned_canary(a,{'source_code_path':'/own'},{'deployment_id':'old'})
 a['active_deployment']['deployment_id']='human'
 with pytest.raises(ValueError,match='NOT_OWNED'):m.owned_canary(a,{'source_code_path':'/own'},{'deployment_id':'old'})

def test_external_ledger_caps_epoch_receipts_no_refund(tmp_path):
 m=module();caps={'generation_posts':4,'embedding_posts':2,'embedding_tokens':20000};m.durable(tmp_path/'binding.json',{'deployment_id':'owned','source_sha256':'sha','expires_at_unix':200,'caps':caps})
 ledger=m.DemoLedger(tmp_path,clock=lambda:100);epoch='process-'+'a'*32;obs=tmp_path/'observation.json';m.durable(obs,{'deployment_id':'owned','source_sha256':'sha','capture_process':epoch,'observed_at_unix':99})
 kwargs=dict(process_epoch=epoch,deployment_id='owned',source_sha256='sha',costs=caps,observation_path=obs,observation_sha256=m.sha(obs))
 ledger.reserve('turn0',**kwargs)
 ledger.record('turn0',actual={'generation_posts':0,'embedding_posts':0,'embedding_tokens':0},unknown=caps,capture_ids=['request-capture'])
 with pytest.raises(ValueError,match='CAP'):ledger.reserve('turn1',**kwargs)
 with pytest.raises(ValueError,match='DUPLICATE'):ledger.reserve('turn0',**kwargs)
 obs2=tmp_path/'observation2.json';epoch2='process-'+'b'*32;m.durable(obs2,{'deployment_id':'owned','source_sha256':'sha','capture_process':epoch2,'observed_at_unix':99})
 with pytest.raises(ValueError,match='RESTART'):ledger.reserve('turn2',**{**kwargs,'process_epoch':epoch2,'observation_path':obs2,'observation_sha256':m.sha(obs2)})
 assert m.read(tmp_path/'turn-turn0-receipt.json')['reservation_retained'] is True

def test_ledger_rejects_unobserved_epoch_and_stale_metadata(tmp_path):
 m=module();caps={'generation_posts':4,'embedding_posts':2,'embedding_tokens':20000};m.durable(tmp_path/'binding.json',{'deployment_id':'owned','source_sha256':'sha','expires_at_unix':200,'caps':caps});obs=tmp_path/'obs.json';m.durable(obs,{'capture_process':'fake'})
 with pytest.raises(ValueError,match='OBSERVATION'):m.DemoLedger(tmp_path,clock=lambda:100).reserve('turn',process_epoch='process-'+'a'*32,deployment_id='owned',source_sha256='sha',costs=caps,observation_path=obs,observation_sha256=m.sha(obs))

def test_full_214_uploads_auto_no_start_single_deploy(tmp_path,monkeypatch):
 import io
 m=module();monkeypatch.setattr(m,'preflight',lambda r:{});monkeypatch.setattr(m,'check_review',lambda r:None)
 package=tmp_path/'package';files={}
 for i in range(214):
  path=package/'source'/f'f{i}.txt';path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(str(i).encode());files[path.name]=m.sha(path)
 manifest={'files_sha256':files,'source_sha256':'fixture'};m.durable(package/'manifest.json',manifest)
 payload={'source_code_path':'/Workspace/own/new','expires_at_unix':200};monkeypatch.setattr(m,'ready',lambda r:(package,manifest,payload))
 for path in [m.FREEZE,m.FINAL_REVIEW]:m.durable(tmp_path/path,{})
 m.durable(tmp_path/m.transport.history.prior.STATE/'source-binding.json',{'source_code_path':'/old'})
 m.durable(tmp_path/'deployment/state/linux-canary-continue-159/deploy-receipt.json',{'deployment_id':'old'})
 m.durable(tmp_path/'deployment/state/linux-canary-continue-159/deploy-intent.json',{'source_code_path':'/old','mode':'SNAPSHOT'})
 stored={};dirs=set();posts={'upload':0,'mkdir':0,'start':0,'deploy':0}
 class Missing(Exception):error_code='RESOURCE_DOES_NOT_EXIST'
 class Workspace:
  def get_status(self,path):
   if path in stored:return {'object_type':'FILE'}
   if path in dirs:return {'object_type':'DIRECTORY'}
   raise Missing()
  def mkdirs(self,path):dirs.add(path);posts['mkdir']+=1
  def upload(self,path,stream,**k):assert k['format'].value=='RAW';stored[path]=stream.read();posts['upload']+=1
  def download(self,path,**k):assert k['format'].value=='AUTO';return io.BytesIO(stored[path])
 class Apps:
  def get(self,name):return {'name':name,'service_principal_id':77041447522099,'service_principal_client_id':'a947eccf-5f94-4369-a3d4-8f83b4ea98a1','compute_status':{'state':'ACTIVE'},'active_deployment':{'deployment_id':'old','source_code_path':'/old'}}
  def deploy(self,name,body):posts['deploy']+=1;return SimpleNamespace(response={'deployment_id':'new'})
  def get_deployment(self,*a):return {'status':{'state':'SUCCEEDED'}}
 server=SimpleNamespace(workspace=Workspace(),apps=Apps(),api=SimpleNamespace(counts=posts,calls=0,session=SimpleNamespace(close=lambda:None)))
 kwargs=dict(root=tmp_path,config_factory=lambda **k:SimpleNamespace(host=m.base.HOST,authenticate=lambda:{'auth':'fixture'}),services_factory=lambda *a:server,clock=lambda:100,sleep=lambda x:None)
 result=m.execute(**kwargs);assert result['status']=='deployed_demo_admission_pending' and posts['upload']==214 and posts['start']==0 and posts['deploy']==1
 assert m.read(tmp_path/m.STATE/'demo-ledger/binding.json')['process_epoch'] is None
 with pytest.raises(FileExistsError):m.execute(**kwargs)
 assert posts['deploy']==1

def test_separate_stop_once_after_deadline(tmp_path,monkeypatch):
 m=module();monkeypatch.setattr(m,'preflight',lambda r:{});monkeypatch.setattr(m,'check_review',lambda r:None);monkeypatch.setattr(m,'ready',lambda r:(tmp_path,{'source_sha256':'sha'},{'source_code_path':'/new','expires_at_unix':1}))
 m.durable(tmp_path/m.FREEZE,{});m.durable(tmp_path/m.STATE/'deploy-intent.json',{'source_code_path':'/new','mode':'SNAPSHOT'});m.durable(tmp_path/m.STATE/'deploy-receipt.json',{'deployment_id':'new'})
 control=m.module('deployment/canary_observe_stop_148.py','fixture157stop148');calls=[]
 class Api:
  def __init__(self,*args):self.counts={};self.session=SimpleNamespace(close=lambda:None)
  def request(self,kind,path):
   calls.append(kind)
   if kind=='stop':raise TimeoutError()
   if path.endswith('/deployments'):return {'app_deployments':[{'deployment_id':'new','source_code_path':'/new','create_time':'2026-09-29T00:00:00Z'}]}
   return {'name':m.base.APP,'service_principal_id':77041447522099,'service_principal_client_id':'a947eccf-5f94-4369-a3d4-8f83b4ea98a1','url':control.ORIGIN,'compute_status':{'state':'STOPPED' if 'stop' in calls else 'ACTIVE'},'active_deployment':{'deployment_id':'new','source_code_path':'/new'}}
 control.Transport=Api;monkeypatch.setattr(m,'module',lambda *a:control)
 args=dict(root=tmp_path,config_factory=lambda **k:SimpleNamespace(host=m.base.HOST,authenticate=lambda:{'fixture':'auth'}),session_factory=lambda:None,sleep=lambda n:None)
 result=m.stop(**args);assert result['status']=='stopped_observed' and calls.count('stop')==1
 with pytest.raises(FileExistsError):m.stop(**args)
 assert calls.count('stop')==1
