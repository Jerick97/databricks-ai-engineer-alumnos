from pathlib import Path
from types import SimpleNamespace
import importlib.util,json,sys
import pytest
ROOT=Path(__file__).resolve().parents[2]
def module():
 s=importlib.util.spec_from_file_location('test178',ROOT/'deployment/canary_recovery_178.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def test_new_state_original166_unchanged_preflight():
 m=module();p=m.preflight();assert p['phase']=='178' and m.runner.STATE==m.STATE and p['cli_logs_max']==1
 assert 'linux-canary-integrated-166' in (ROOT/'deployment/canary_integrated_166.py').read_text()

def test_one_marker_full_json_only():
 m=module();raw=b'2026-09-29T19:00:00Z SBS_CANARY141_RESULT {"status":"FAIL_LINUX_CANARY"}\n'
 assert m.extract_log_report(raw)['status']=='FAIL_LINUX_CANARY'
 for bad in [raw+raw,b'no report',b'SBS_CANARY141_RESULT {} trailing']:
  with pytest.raises((ValueError,json.JSONDecodeError)):m.extract_log_report(bad)

def test_real_cli_process_cap_and_timeout_without_network():
 m=module();out=m.run_logs([sys.executable,'-c','print("x"*100000)'],cap=1000,timeout=2)
 assert out['truncated'] and out['termination']=='output_cap' and len(out['raw'])==1000
 out=m.run_logs([sys.executable,'-c','import time;time.sleep(3)'],timeout=.05)
 assert out['termination']=='timeout'

def test_failed_http_uses_cli_before_gate_preserves_raw(tmp_path,monkeypatch):
 m=module();order=[];expected={'source_code_path':'/own','source_sha256':'sha','deployment_id':'owned'}
 class API:
  def __init__(self,*a):self.session=SimpleNamespace(close=lambda:None)
  def request(self,*a):return {'name':m.base.APP,'service_principal_id':77041447522099,'service_principal_client_id':'a947eccf-5f94-4369-a3d4-8f83b4ea98a1','url':m.runner.control.ORIGIN,'active_deployment':{'source_code_path':'/own','deployment_id':'owned','create_time':'2026-09-29T19:00:00Z'},'compute_status':{'state':'ACTIVE'}}
 monkeypatch.setattr(m.runner.control,'Transport',API)
 def logs(command,**kwargs):
  assert command[-4:]==['--tail-lines','100','--search','SBS_CANARY141_RESULT'];order.append('logs');return {'returncode':0,'termination':None,'raw':b'2026-09-29T19:00:01Z SBS_CANARY141_RESULT {"status":"fixture_report"}\n','truncated':False}
 def gates(root,path,pin):
  order.append('gate');assert (tmp_path/'capture178/cli-raw.json').exists();return {'fixture_only':True}
 monkeypatch.setattr(m.gates,'gates',gates)
 result=m.capture(None,tmp_path,expected,logs_runner=logs,evidence_fn=lambda *a:{'status':'failed'},root=tmp_path)
 assert order==['logs','gate'] and result['status']=='captured_linux_report153_pass'
 assert m.read(tmp_path/'capture178/linux-report.json')['status']=='fixture_report'

def test_http_report_fail_is_preserved_no_falsepass(tmp_path):
 m=module();m.durable(tmp_path/'evidence/evidence-parsed.json',{'status':'FAIL_LINUX_CANARY','error_code':'CANARY141_PLATFORM'})
 result=m.capture(None,tmp_path,{},logs_runner=lambda *a,**k:(_ for _ in ()).throw(AssertionError('no logs expected')),evidence_fn=lambda *a:{'status':'captured'},root=ROOT)
 assert result['status']=='captured_linux_report153_failed' and m.read(tmp_path/'capture178/gate153.json')['status']=='failed'


def test_current_lifetime_filters_old_marker_and_rejects_undated():
 m=module();raw=b'2026-09-29T18:00:00Z SBS_CANARY141_RESULT {"source":"old"}\n2026-09-29T19:00:01Z SBS_CANARY141_RESULT {"source":"current"}\n'
 assert m.extract_log_report(raw,not_before='2026-09-29T19:00:00Z')['source']=='current'
 with pytest.raises(ValueError,match='TIMESTAMP_UNBOUND'):m.extract_log_report(b'SBS_CANARY141_RESULT {}',not_before='2026-09-29T19:00:00Z')
