from pathlib import Path
import importlib.util,json
import pytest
ROOT=Path(__file__).resolve().parents[2]
def module():
 s=importlib.util.spec_from_file_location('deploy145',ROOT/'deployment/canary_deploy_145.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def test_offline_preflight_exact_source():
 m=module();p=m.preflight();assert p['files']==218 and p['provider_calls']==0 and p['start_max']==p['deploy_max']==1

def test_no_auth_without_review(tmp_path):
 m=module()
 with pytest.raises(FileNotFoundError):m.execute(root=tmp_path,config_factory=lambda **k:(_ for _ in ()).throw(AssertionError('auth forbidden')))
 assert not (tmp_path/m.STATE).exists()

def test_effect_caps_reserve_before_single_attempt():
 m=module()
 class Delegate:
  def do(self,*a,**k):raise RuntimeError('ambiguous')
 c=m.CappedApi(Delegate(),uploads=1,mkdirs=1)
 for path,kind in [('/api/2.0/workspace/import','upload'),('/api/2.0/workspace/mkdirs','mkdir'),('/api/2.0/apps/sbs-radar-pilot/start','start'),('/api/2.0/apps/sbs-radar-pilot/deployments','deploy')]:
  with pytest.raises(RuntimeError):c.do('POST',path)
  assert c.counts[kind]==1
  with pytest.raises(ValueError,match='CAP'):c.do('POST',path)


def test_auth_failure_before_durable_admission(tmp_path,monkeypatch):
 from types import SimpleNamespace
 m=module();monkeypatch.setattr(m,'preflight',lambda root:{'base_manifest_sha256':'fixture'});monkeypatch.setattr(m,'check_review',lambda root:None)
 cfg=SimpleNamespace(host=m.base.HOST,authenticate=lambda:(_ for _ in ()).throw(RuntimeError('auth cache failure')))
 with pytest.raises(RuntimeError):m.execute(root=tmp_path,config_factory=lambda **kw:cfg)
 assert not (tmp_path/m.STATE).exists()


def test_scopedapi_rejects_other_app_and_nonraw_upload():
 from types import SimpleNamespace
 import requests
 m=module();session=requests.Session();cfg=SimpleNamespace(host=m.base.HOST,authenticate=lambda:(_ for _ in ()).throw(AssertionError('auth forbidden')))
 api=m.base.ScopedApi(cfg,m.PREFIX+'fixture',lambda:None,session)
 with pytest.raises(ValueError,match='FORBIDDEN'):api.do('POST','/api/2.0/apps/other/start')
 with pytest.raises(ValueError,match='RAW'):api.do('POST','/api/2.0/workspace/import',body={'path':m.PREFIX+'fixture/file','format':'SOURCE'})
 with pytest.raises(ValueError,match='OUTSIDE'):api.do('GET','/api/2.0/workspace/export',query={'path':'/Workspace/other'})
 session.close()


def full_fixture(tmp_path,monkeypatch,*,ambiguous_upload=False,identity_wrong=False):
 from types import SimpleNamespace
 import hashlib,io,time
 m=module();monkeypatch.setattr(m,'preflight',lambda root:{'base_manifest_sha256':'fixture-base'});monkeypatch.setattr(m,'check_review',lambda root:None)
 (tmp_path/m.FREEZE).parent.mkdir(parents=True);(tmp_path/m.FREEZE).write_text('{}');(tmp_path/m.REVIEW).write_text('{}')
 data={f'data/file-{i}.txt':str(i).encode() for i in range(217)}
 data['canary141-config.json']=b'fixture-held'
 original={p:m.base.sha(v) for p,v in data.items()};(tmp_path/m.BASE).mkdir(parents=True);(tmp_path/m.BASE/'manifest.json').write_text(json.dumps({'files_sha256':original}))
 def prepare(dest,root,expires_at):
  content=dict(data);content['canary141-config.json']=json.dumps({'kind':'diagnostic_only_not_release','expires_at_unix':expires_at,'provider_calls':0,'source133_sha256':'fixture-source133'}).encode()
  for p,v in content.items():target=dest/'source'/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(v)
  manifest={'files_sha256':{p:m.base.sha(v) for p,v in content.items()},'source_sha256':'fixture-source145','source133_sha256':'fixture-source133'};(dest/'manifest.json').write_text(json.dumps(manifest));return manifest
 monkeypatch.setattr(m,'module',lambda *args:SimpleNamespace(prepare=prepare))
 stored={};dirs=set();posts={'upload':0,'mkdir':0,'start':0,'deploy':0};phase=['STOPPED'];closed=[]
 class Missing(Exception):error_code='RESOURCE_DOES_NOT_EXIST'
 class Workspace:
  def get_status(self,path):
   if path in dirs:return {'object_type':'DIRECTORY'}
   if path in stored:return {'object_type':'FILE'}
   raise Missing()
  def mkdirs(self,path):posts['mkdir']+=1;dirs.add(path)
  def upload(self,path,stream,**kw):
   posts['upload']+=1;stored[path]=stream.read();assert kw['overwrite'] is False
   if ambiguous_upload:raise RuntimeError('response lost after storage')
  def download(self,path,**kw):return io.BytesIO(stored[path])
 class Apps:
  def get(self,name):return {'name':name,'service_principal_id':0 if identity_wrong else 77041447522099,'service_principal_client_id':'a947eccf-5f94-4369-a3d4-8f83b4ea98a1','compute_status':{'state':phase[0]}}
  def start(self,name):posts['start']+=1;phase[0]='RUNNING'
  def deploy(self,name,body):posts['deploy']+=1;return SimpleNamespace(response={'deployment_id':'fixture145'})
  def get_deployment(self,*args):return {'deployment_id':'fixture145','status':{'state':'SUCCEEDED'}}
 server=SimpleNamespace(workspace=Workspace(),apps=Apps(),api=SimpleNamespace(calls=0,counts=posts,session=SimpleNamespace(close=lambda:closed.append(True))))
 cfg=SimpleNamespace(host=m.base.HOST,authenticate=lambda:{'Authorization':'fixture-never-sent'})
 kwargs=dict(root=tmp_path,config_factory=lambda **kw:cfg,services_factory=lambda *a,**k:server,sleep=lambda n:None)
 return m,kwargs,posts,closed


def test_full_upload_reconciles_ambiguous_once_and_single_admission(tmp_path,monkeypatch):
 m,kwargs,posts,closed=full_fixture(tmp_path,monkeypatch,ambiguous_upload=True)
 out=m.execute(**kwargs)
 assert out['status']=='deployed_linux_evidence_pending' and posts['upload']==218 and posts['start']==posts['deploy']==1 and closed
 assert len(list((tmp_path/m.STATE).glob('uploaded-*.json')))==218
 assert (tmp_path/m.STATE/'start-intent.json').exists() and (tmp_path/m.STATE/'deploy-intent.json').exists()
 with pytest.raises(Exception):m.execute(**kwargs)
 assert posts['upload']==218 and posts['deploy']==1


def test_wrong_app_identity_before_any_mutation(tmp_path,monkeypatch):
 m,kwargs,posts,closed=full_fixture(tmp_path,monkeypatch,identity_wrong=True)
 out=m.execute(**kwargs)
 assert out['error_code']=='CANARY145_APP_IDENTITY_CHANGED'
 assert all(v==0 for v in posts.values()) and closed
