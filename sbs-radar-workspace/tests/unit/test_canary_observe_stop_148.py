from pathlib import Path
from types import SimpleNamespace
import importlib.util,json,io
import pytest,requests
from urllib3.response import HTTPResponse
ROOT=Path(__file__).resolve().parents[2]
def module():
 s=importlib.util.spec_from_file_location('test148',ROOT/'deployment/canary_observe_stop_148.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def app(m,phase='RUNNING',active=True):return {'name':m.base.APP,'service_principal_id':77041447522099,'service_principal_client_id':'a947eccf-5f94-4369-a3d4-8f83b4ea98a1','url':m.ORIGIN,'compute_status':{'state':phase},'active_deployment':{'deployment_id':'owned','source_code_path':'/own'} if active else None}
def expected():return {'deployment_id':'owned','source_code_path':'/own','source_sha256':'fixture'}

def test_owned_rejects_foreign_and_url():
 m=module();a=app(m);assert m.owned(a,expected())=='RUNNING'
 a['active_deployment']['source_code_path']='/foreign'
 with pytest.raises(ValueError,match='NOT_OWNED'):m.owned(a,expected())
 a=app(m);a['url']+='?redirect=other'
 with pytest.raises(ValueError,match='URL'):m.owned(a,expected())

def test_latest_failed_own_is_stoppable_but_replacement_rejected():
 m=module();e=expected();entry={'deployment_id':'owned','source_code_path':'/own','create_time':'2026-09-29T18:00:00Z','status':{'state':'FAILED'}}
 m.latest_owned({'app_deployments':[entry]},e)
 with pytest.raises(ValueError,match='NOT_OWNED'):m.latest_owned({'app_deployments':[entry,dict(entry,deployment_id='foreign',source_code_path='/foreign',create_time='2026-09-29T19:00:00Z')]},e)
 with pytest.raises(ValueError,match='INCOMPLETE'):m.latest_owned({'app_deployments':[entry],'next_page_token':'next'},e)
 m.latest_owned({'app_deployments':[]},dict(e,deployment_id=None))

def test_transport_captures_403_before_parse_no_redirects(tmp_path):
 m=module();session=requests.Session();response=requests.Response();response.status_code=403;response.raw=HTTPResponse(body=io.BytesIO(b'forbidden'),preload_content=False)
 def request(*a,**k):assert k['allow_redirects'] is False and k['timeout']==(15,30);return response
 session.request=request;cfg=SimpleNamespace(host=m.base.HOST,authenticate=lambda:{'Authorization':'secret fixture'})
 t=m.Transport(cfg,tmp_path,session)
 with pytest.raises(ValueError,match='HTTP_FAILED'):t.request('app_get','/health')
 saved=m.read(tmp_path/'http-response-01.json');assert saved['status']==403 and 'secret' not in json.dumps(saved)
 with pytest.raises(ValueError,match='PATH_FORBIDDEN'):t.request('app_get','/chat')

def execute_fixture(tmp_path,monkeypatch,action,failed=False):
 m=module();monkeypatch.setattr(m,'preflight',lambda r:{});monkeypatch.setattr(m,'check_review',lambda r:None);monkeypatch.setattr(m,'binding',lambda r:expected())
 (tmp_path/m.FREEZE).parent.mkdir(parents=True);(tmp_path/m.FREEZE).write_text('{}');(tmp_path/m.REVIEW).write_text('{}')
 seen=[];posts=[];gets=[0];session=requests.Session()
 def request(method,url,**kw):
  seen.append((method,url));v={};code=200
  if url.endswith('/stop'):posts.append(url);raise requests.Timeout('ambiguous POST')
  if url.endswith('/deployments'):v={'app_deployments':[dict(expected(),create_time='2026-09-29T18:00:00Z',status={'state':'FAILED' if failed else 'SUCCEEDED'})]}
  elif url==m.base.HOST+m.APP_PATH:
   gets[0]+=1;v=app(m,'STOPPED' if posts else 'RUNNING',active=not failed)
  elif url.endswith('/health'):v={'status':'healthy'}
  elif url.endswith('/evidence'):v={'status':'fixture_runtime_only'}
  response=requests.Response();response.status_code=code;response.raw=HTTPResponse(body=io.BytesIO(json.dumps(v).encode()),preload_content=False);return response
 session.request=request
 cfg=SimpleNamespace(host=m.base.HOST,authenticate=lambda:{'Authorization':'fixture'})
 args=dict(action=action,root=tmp_path,config_factory=lambda **k:cfg,session_factory=lambda:session,sleep=lambda s:None)
 return m,args,seen,posts

def test_stop_failed_own_deployment_ambiguous_post_get_reconcile_no_retry(tmp_path,monkeypatch):
 m,args,seen,posts=execute_fixture(tmp_path,monkeypatch,'stop',failed=True);out=m.execute(**args)
 assert out['status']=='stopped_observed' and len(posts)==1
 with pytest.raises(FileExistsError):m.execute(**args)
 assert len(posts)==1 and not any('.databricksapps.com' in url for _,url in seen)

def test_evidence_no_stop(tmp_path,monkeypatch):
 m,args,seen,posts=execute_fixture(tmp_path,monkeypatch,'evidence');out=m.execute(**args)
 assert out['status']=='evidence_captured_not_validated' and not posts and out['reserved_http_attempts']['app_get']==2
