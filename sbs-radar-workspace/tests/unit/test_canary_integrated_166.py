from pathlib import Path
from types import SimpleNamespace
import importlib.util,io,json,time
import pytest,requests
from urllib3.response import HTTPResponse
ROOT=Path(__file__).resolve().parents[2]
def module():
 s=importlib.util.spec_from_file_location('test166',ROOT/'deployment/canary_integrated_166.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def test_offline_preflight_new_window_not_issued():
 p=module().preflight();assert p['upload_max']==237 and p['start_wait_max_seconds']==600 and p['deploy_wait_max_seconds']==300

def fixture(tmp_path,monkeypatch,failed=False):
 m=module();monkeypatch.setattr(m,'preflight',lambda r:{});monkeypatch.setattr(m,'check_review',lambda r:None)
 for name in (m.FREEZE,m.REVIEW):m.durable(tmp_path/name,{})
 original_builder=m.builder.prepare;monkeypatch.setattr(m.builder,'prepare',lambda destination,root,expires_at:original_builder(destination,root=ROOT,expires_at=expires_at))
 original_verify=m.verify_package;monkeypatch.setattr(m,'verify_package',lambda root,p,e:original_verify(ROOT,p,e))
 stored={};dirs=set();posts=dict(upload=0,mkdir=0,start=0,deploy=0);polls=[0];cleanups=[];sleeps=[]
 class Missing(Exception):error_code='RESOURCE_DOES_NOT_EXIST'
 class Workspace:
  def get_status(self,path):
   if path in dirs:return {'object_type':'DIRECTORY'}
   if path in stored:return {'object_type':'FILE'}
   raise Missing()
  def mkdirs(self,path):posts['mkdir']+=1;dirs.add(path)
  def upload(self,path,stream,**kw):assert kw['format'].value=='RAW';raw=stream.read();assert len(raw)<=8388608;stored[path]=raw;posts['upload']+=1
  def download(self,path,**kw):assert kw['format'].value=='AUTO';return io.BytesIO(stored[path])
 class Apps:
  def get(self,name):
   if posts['start']:polls[0]+=1
   phase='STOPPED' if not posts['start'] else 'STARTING' if polls[0]<=30 else 'ACTIVE'
   return {'name':name,'service_principal_id':77041447522099,'service_principal_client_id':'a947eccf-5f94-4369-a3d4-8f83b4ea98a1','compute_status':{'state':phase},'last_deployment_id':'old159'}
  def start(self,name):posts['start']+=1
  def deploy(self,name,body):posts['deploy']+=1;return SimpleNamespace(response={'deployment_id':'owned166'})
  def get_deployment(self,*args):return {'status':{'state':'FAILED' if failed else 'SUCCEEDED'}}
 server=SimpleNamespace(workspace=Workspace(),apps=Apps(),api=SimpleNamespace(counts=posts,calls=0,session=SimpleNamespace(close=lambda:None)))
 def cleanup(cfg,state,expected,before,**kw):cleanups.append(expected);return {'status':'fixture_stopped'}
 kwargs=dict(root=tmp_path,config_factory=lambda **k:SimpleNamespace(host=m.base.HOST,authenticate=lambda:{'fixture':'auth'}),services_factory=lambda *a,**k:server,sleep=lambda n:sleeps.append(n),evidence_fn=lambda *a:{'status':'fixture_captured'},cleanup_fn=cleanup)
 return m,kwargs,posts,cleanups,sleeps

def test_full237_wait300seconds_then_deploy_cleanup_once(tmp_path,monkeypatch):
 m,kwargs,posts,cleanups,sleeps=fixture(tmp_path,monkeypatch);out=m.execute(**kwargs)
 assert out['status']=='deployed_evidence_pending' and posts['upload']==237 and posts['start']==posts['deploy']==1
 assert sum(sleeps)==300 and len(cleanups)==1 and out['cleanup']['status']=='fixture_stopped'
 with pytest.raises(FileExistsError):m.execute(**kwargs)
 assert posts['start']==posts['deploy']==1

def test_failed_deploy_still_cleanup(tmp_path,monkeypatch):
 m,kwargs,posts,cleanups,_=fixture(tmp_path,monkeypatch,failed=True);out=m.execute(**kwargs)
 assert out['error_code']=='CANARY166_DEPLOY_FAILED' and len(cleanups)==1 and posts['deploy']==1

def test_cleanup_pending_own_source_single_stop_then_readback(tmp_path):
 m=module();session=requests.Session();seen=[];expected={'source_code_path':'/own166','source_sha256':'sha','deployment_id':'new166'};before={'last_deployment_id':'old159'}
 def request(method,url,**kw):
  seen.append((method,url));stopped=any(x[0]=='POST' for x in seen)
  if url.endswith('/deployments'):value={'app_deployments':[{'deployment_id':'new166','source_code_path':'/own166','create_time':'2026-09-29T19:00:00Z'}]}
  else:value={'name':m.base.APP,'service_principal_id':77041447522099,'service_principal_client_id':'a947eccf-5f94-4369-a3d4-8f83b4ea98a1','compute_status':{'state':'STOPPED' if stopped else 'ACTIVE'},'pending_deployment':None if stopped else {'deployment_id':'new166','source_code_path':'/own166'},'last_deployment_id':'new166'}
  response=requests.Response();response.status_code=200;response.raw=HTTPResponse(body=io.BytesIO(json.dumps(value).encode()),preload_content=False);return response
 session.request=request;cfg=SimpleNamespace(host=m.base.HOST,authenticate=lambda:{'fixture':'auth'})
 out=m.cleanup(cfg,tmp_path,expected,before,session_factory=lambda:session,sleep=lambda x:None)
 assert out['status']=='stopped_observed' and sum(method=='POST' for method,url in seen)==1
 assert (tmp_path/'cleanup/stop-intent.json').exists()

def test_auth_fail_creates_no_window(tmp_path,monkeypatch):
 m=module();monkeypatch.setattr(m,'preflight',lambda r:{});monkeypatch.setattr(m,'check_review',lambda r:None)
 with pytest.raises(RuntimeError):m.execute(root=tmp_path,config_factory=lambda **k:(_ for _ in ()).throw(RuntimeError('auth failed')))
 assert not (tmp_path/m.STATE).exists()
