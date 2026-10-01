from pathlib import Path
from types import SimpleNamespace
import importlib.util,io,json,shutil
import pytest
ROOT=Path(__file__).resolve().parents[2]
def module():
 s=importlib.util.spec_from_file_location('recovery151test',ROOT/'deployment/canary_recovery_151.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def test_preflight_same_window_no_network():
 p=module().preflight();assert p['expires_at_unix']==1790709142 and p['uploads_max']==217 and p['aggregate_uploads_max']==218 and p['new_window'] is False

def fixture(tmp_path,monkeypatch,*,bad_existing=False):
 m=module();p=m.preflight();monkeypatch.setattr(m,'preflight',lambda root:p);monkeypatch.setattr(m,'check_review',lambda root:None)
 old=tmp_path/m.prior.STATE;old.mkdir(parents=True);(old/'package').symlink_to(ROOT/m.prior.STATE/'package',target_is_directory=True)
 for f in (ROOT/m.prior.STATE).glob('mkdir-*.json'):shutil.copyfile(f,old/f.name)
 shutil.copyfile(ROOT/m.prior.STATE/'admission.json',old/'admission.json')
 (tmp_path/m.FREEZE).parent.mkdir(parents=True);(tmp_path/m.FREEZE).write_text('{}');(tmp_path/m.REVIEW).write_text('{}')
 prefix=p['source_code_path'];files=m.read(old/'package/manifest.json')['files_sha256'];stored={prefix+'/app.yaml':b'wrong' if bad_existing else (old/'package/source/app.yaml').read_bytes()};posts=dict(upload=0,mkdir=0,start=0,deploy=0);phase=['STOPPED'];downloads=[]
 dirs={m.read(f)['path'] for f in old.glob('mkdir-*.json')}
 class Missing(Exception):error_code='RESOURCE_DOES_NOT_EXIST'
 class Workspace:
  def get_status(self,path):
   if path in dirs:return {'object_type':'DIRECTORY'}
   if path in stored:return {'object_type':'FILE'}
   raise Missing()
  def upload(self,path,stream,**kw):
   assert path!=prefix+'/app.yaml' and kw['format'].value=='RAW' and kw['overwrite'] is False
   posts['upload']+=1;stored[path]=stream.read();raise RuntimeError('response lost after successful upload')
  def download(self,path,**kw):
   assert kw['format'].value=='AUTO';downloads.append(path);return io.BytesIO(stored[path])
 class Apps:
  def get(self,name):return {'name':name,'service_principal_id':77041447522099,'service_principal_client_id':'a947eccf-5f94-4369-a3d4-8f83b4ea98a1','compute_status':{'state':phase[0]}}
  def start(self,name):posts['start']+=1;phase[0]='RUNNING'
  def deploy(self,name,body):posts['deploy']+=1;assert body.source_code_path==prefix;return SimpleNamespace(response={'deployment_id':'fixture151'})
  def get_deployment(self,*args):return {'deployment_id':'fixture151','status':{'state':'SUCCEEDED'}}
 api=SimpleNamespace(calls=0,counts=posts,session=SimpleNamespace(close=lambda:None));server=SimpleNamespace(workspace=Workspace(),apps=Apps(),api=api)
 cfg=SimpleNamespace(host=m.base.HOST,authenticate=lambda:{'fixture':'not sent'})
 args=dict(root=tmp_path,config_factory=lambda **k:cfg,services_factory=lambda *a,**k:server,clock=lambda:(p['expires_at_unix']-300)*1000,sleep=lambda n:None)
 return m,args,posts,downloads

def test_217_uploads_auto_reconcile_no_resend_and_exclusive_admission(tmp_path,monkeypatch):
 m,args,posts,downloads=fixture(tmp_path,monkeypatch);out=m.execute(**args)
 assert out['status']=='deployed_linux_evidence_pending'
 assert posts==dict(upload=217,mkdir=0,start=1,deploy=1)
 assert out['aggregate_effects_145_151']==dict(upload=218,mkdir=40,start=1,deploy=1)
 assert len(downloads)==218
 assert m.read(tmp_path/m.STATE/('uploaded-'+m.base.sha(b'app.yaml')+'.json'))['reconciles_phase145'] is True
 with pytest.raises(FileExistsError):m.execute(**args)
 assert posts['upload']==217

def test_existing_file_bad_hash_stops_without_posts(tmp_path,monkeypatch):
 m,args,posts,_=fixture(tmp_path,monkeypatch,bad_existing=True);out=m.execute(**args)
 assert out['error_code']=='CANARY151_UPLOAD_READBACK_FAILED' and not any(posts.values())

def test_expiry_and_auth_before_admission(tmp_path,monkeypatch):
 m,args,posts,_=fixture(tmp_path,monkeypatch);args['clock']=lambda:1790709142000
 with pytest.raises(ValueError,match='WINDOW_EXPIRED'):m.execute(**args)
 assert not (tmp_path/m.STATE).exists()
 args['clock']=lambda:1790709000000;args['config_factory']=lambda **kw:(_ for _ in ()).throw(RuntimeError('auth failure'))
 with pytest.raises(RuntimeError):m.execute(**args)
 assert not (tmp_path/m.STATE).exists() and not any(posts.values())

def test_raw_error_archived_before_json_parse(tmp_path):
 import requests,base64
 m=module();session=requests.Session();body=b'{"error_code":"BAD_REQUEST","message":"FILE RAW unsupported"}'
 response=SimpleNamespace(status_code=400,raw=io.BytesIO(body))
 session.request=lambda *a,**k:response
 wrapped=m.ErrorSession(session,tmp_path);r=wrapped.request('GET',m.base.HOST+'/api/2.0/workspace/export',headers={'Authorization':'must not persist'})
 raw=r.raw.read(4000001);record=m.read(tmp_path/'http-error-0001.json')
 assert base64.b64decode(record['body_base64'])==raw==body and record['status']==400
 assert 'Authorization' not in json.dumps(record) and 'must not persist' not in json.dumps(record)

def test_no_additional_mkdir_budget():
 m=module();c=m.prior.CappedApi(SimpleNamespace(do=lambda *a,**k:None),uploads=217,mkdirs=0)
 with pytest.raises(ValueError,match='CAP'):c.do('POST','/api/2.0/workspace/mkdirs')
 for _ in range(217):c.do('POST','/api/2.0/workspace/import')
 with pytest.raises(ValueError,match='CAP'):c.do('POST','/api/2.0/workspace/import')
