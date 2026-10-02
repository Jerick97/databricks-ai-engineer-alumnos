from pathlib import Path
from types import SimpleNamespace
import importlib.util,io
import pytest,requests
from urllib3.response import HTTPResponse
ROOT=Path(__file__).resolve().parents[2]
def module():
 s=importlib.util.spec_from_file_location('test154',ROOT/'deployment/canary_recovery_154.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def response_session():
 response=requests.Response();response.status_code=404;response.raw=HTTPResponse(body=io.BytesIO(b'{"error_code":"RESOURCE_DOES_NOT_EXIST"}'),preload_content=False)
 session=requests.Session();session.request=lambda *a,**k:response
 return session,response

def test_red151_real_requests_close_masks_404(tmp_path):
 m=module();session,response=response_session();cfg=SimpleNamespace(host=m.base.HOST,authenticate=lambda:{})
 api=m.base.ScopedApi(cfg,'/Workspace/fixture',lambda:None,m.history.ErrorSession(session,tmp_path))
 with pytest.raises(AttributeError,match='close'):api.do('GET','/api/2.0/workspace/get-status',query={'path':'/Workspace/fixture/app098.py'})
 assert (tmp_path/'http-error-0001.json').exists()

def test_green154_real_requests_preserves_404_and_closes(tmp_path):
 from databricks.sdk.errors import DatabricksError
 m=module();session,response=response_session();original=response.raw;cfg=SimpleNamespace(host=m.base.HOST,authenticate=lambda:{})
 api=m.base.ScopedApi(cfg,'/Workspace/fixture',lambda:None,m.ErrorSession(session,tmp_path))
 with pytest.raises(DatabricksError) as e:api.do('GET','/api/2.0/workspace/get-status',query={'path':'/Workspace/fixture/app098.py'})
 assert e.value.error_code=='RESOURCE_DOES_NOT_EXIST' and original.closed
 assert m.read(tmp_path/'http-error-0001.json')['status']==404

def test_preflight_retains_budget_window_and_prior_zero():
 m=module();p=m.preflight();assert p['expires_at_unix']==1790709142 and p['uploads_max']==217 and not any(p['recovery154_prior151_effects'].values())
 assert m.runner.STATE==m.STATE and m.history.STATE=='deployment/state/linux-canary-recovery-151'

def test_no_gate_no_auth(tmp_path):
 m=module()
 with pytest.raises(FileNotFoundError):m.execute(root=tmp_path,config_factory=lambda **k:(_ for _ in ()).throw(AssertionError('auth forbidden')))
 assert not (tmp_path/m.STATE).exists()
