"""Independent178 mission reuses166, capturing logs BEFORE its cleanup."""
from pathlib import Path
import argparse,base64,hashlib,importlib.util,json,os,re,selectors,shutil,subprocess,time
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]
def module(path,name):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
runner=module('deployment/canary_integrated_166.py','recovery178isolated166');gates=module('deployment/app_candidate_153.py','recovery178gates153')
base=runner.base;require=runner.require;read=runner.read;durable=runner.durable;sha=runner.sha
FREEZE='runs/sk12-canary-recovery-178-freeze.json';REVIEW='runs/sk09-canary-recovery-178-review.json';STATE='deployment/state/linux-canary-recovery-178'
MARKER='SBS_CANARY141_RESULT '
original_preflight=runner.preflight

def preflight(root=ROOT):
 root=Path(root);out=original_preflight(root);r=read(root/'runs/sk09-canary-integrated-166-review.json');require(r.get('status')=='PASS_CANARY_INTEGRATED_166' and r.get('freeze_sha256')==sha(root/'runs/sk12-canary-integrated-166-freeze.json'),'CANARY178_PRIOR_REVIEW')
 for p,h in read(root/'runs/sk12-canary-integrated-166-freeze.json')['files_sha256'].items():require(sha(root/p)==h,'CANARY178_PRIOR_INPUT_DRIFT')
 require(shutil.which('databricks') is not None,'CANARY178_CLI_MISSING')
 return {**out,'phase':'178','cli_logs_max':1,'cli_timeout_seconds':60,'cli_output_max_bytes':1048576,'old166_reused_as_admission':False}
def check_review(root):
 r=read(root/REVIEW);require(r.get('status')=='PASS_CANARY_RECOVERY_178' and r.get('freeze_sha256')==sha(root/FREEZE),'CANARY178_REVIEW_REQUIRED')
 for p,h in read(root/FREEZE)['files_sha256'].items():require(sha(root/p)==h,'CANARY178_INPUT_DRIFT')

def run_logs(command,*,timeout=60,cap=1048576):
 """One CLI process, nofollow; cap combined stdout/stderr before parsing."""
 start=time.monotonic();process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
 selector=selectors.DefaultSelector();selector.register(process.stdout,selectors.EVENT_READ);data=bytearray();reason=None
 try:
  while selector.get_map():
   remaining=timeout-(time.monotonic()-start)
   if remaining<=0:reason='timeout';break
   for key,_ in selector.select(min(remaining,.25)):
    block=os.read(key.fileobj.fileno(),min(65536,cap+1-len(data)))
    if not block:selector.unregister(key.fileobj);break
    data.extend(block)
    if len(data)>cap:reason='output_cap';break
   if reason:break
  if reason:
   import signal
   try:os.killpg(process.pid,signal.SIGKILL)
   except ProcessLookupError:pass
  try:code=process.wait(timeout=max(.1,timeout-(time.monotonic()-start)))
  except subprocess.TimeoutExpired:
   import signal
   try:os.killpg(process.pid,signal.SIGKILL)
   except ProcessLookupError:pass
   code=process.wait();reason=reason or 'timeout'
  return {'returncode':code,'termination':reason,'raw':bytes(data[:cap]),'truncated':len(data)>cap,'elapsed_seconds':time.monotonic()-start}
 finally:
  selector.close();process.stdout.close()
  if process.poll() is None:process.kill();process.wait()

def extract_log_report(raw,*,not_before=None):
 """Preserve CLI prefixes externally; accept only one unambiguous currentreport."""
 candidates=[]
 lower=datetime.fromisoformat(not_before.replace('Z','+00:00')) if not_before else None
 if lower:require(lower.tzinfo is not None,'CANARY178_DEPLOY_TIMEZONE')
 for line in raw.decode('utf-8',errors='strict').splitlines():
  if MARKER in line:
   prefix,payload=line.split(MARKER,1)
   if lower:
    match=re.search(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})',prefix)
    require(match is not None,'CANARY178_LOG_TIMESTAMP_UNBOUND')
    stamp=datetime.fromisoformat(match.group().replace('Z','+00:00'))
    if stamp<lower:continue
   report=json.loads(payload);require(isinstance(report,dict),'CANARY178_LOG_OBJECT');candidates.append(report)
 require(len(candidates)==1,'CANARY178_LOG_REPORT_NOT_UNIQUE');return candidates[0]

def capture(cfg,state,expected,*,logs_runner=run_logs,evidence_fn=None,root=ROOT):
 state=Path(state);root=Path(root);directory=state/'capture178';directory.mkdir(exist_ok=False)
 # Keep166 bounded original HTTPcapture; no provider/model execution here.
 http=(evidence_fn or runner.evidence)(cfg,state,expected)
 durable(directory/'http-capture-result.json',http);report=None;origin=None
 path=state/'evidence/evidence-parsed.json'
 if path.is_file():report=read(path);origin='exactAppGET/evidence'
 else:
  # Fresh workspaceidentity prevents reading logs for a replacement deployment.
  import requests
  api=runner.control.Transport(cfg,directory/'identity',requests.Session())
  try:
   app=api.request('workspace_get',runner.control.APP_PATH);runner.control.owned(app,expected)
   require(app.get('compute_status',{}).get('state') in ('ACTIVE','RUNNING'),'CANARY178_LOG_COMPUTE_INACTIVE')
  finally:api.session.close()
  command=['databricks','apps','logs',base.APP,'--profile','databricks-ai-engineer-aws','--tail-lines','100','--search','SBS_CANARY141_RESULT']
  durable(directory/'cli-intent.json',{'command':command,'maximum_invocations':1,'timeout_seconds':60,'byte_cap':1048576,'before_cleanup':True,'deployment_id':expected['deployment_id']})
  observed=logs_runner(command,timeout=60,cap=1048576);raw=observed.pop('raw')
  durable(directory/'cli-raw.json',{**observed,'body_base64':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest()})
  require(observed['returncode']==0 and observed.get('termination') is None and not observed.get('truncated'),'CANARY178_LOG_CAPTURE_FAILED')
  deployment_time=(app.get('active_deployment') or {}).get('create_time')
  if not deployment_time:
   receipt=read(state/'deploy-receipt.json');require(receipt.get('deployment_id')==expected['deployment_id'],'CANARY178_LOG_DEPLOYMENT_CHANGED');deployment_time=receipt.get('create_time')
  require(isinstance(deployment_time,str),'CANARY178_DEPLOYMENT_TIME_MISSING')
  durable(directory/'log-lifetime-binding.json',{'deployment_id':expected['deployment_id'],'source_code_path':expected['source_code_path'],'not_before':deployment_time,'raw_prefix_preserved':True})
  report=extract_log_report(raw,not_before=deployment_time);origin='CLIAppslogs_before_cleanup'
 # The report may be FAIL or numeric-failed. Preserve it before validating gates.
 durable(directory/'linux-report.json',report)
 try:
  verdict=gates.gates(root,directory/'linux-report.json',sha(directory/'linux-report.json'))
  durable(directory/'gate153.json',{'status':'passed','origin':origin,'report_sha256':sha(directory/'linux-report.json'),'gates':verdict})
  return {'status':'captured_linux_report153_pass','origin':origin,'report_sha256':sha(directory/'linux-report.json')}
 except Exception as e:
  durable(directory/'gate153.json',{'status':'failed','origin':origin,'report_sha256':sha(directory/'linux-report.json'),'error_type':type(e).__name__,'error_code':str(e) if str(e).isupper() else 'CANARY178_REPORT_GATE_FAILED'})
  return {'status':'captured_linux_report153_failed','origin':origin,'report_sha256':sha(directory/'linux-report.json')}

# Isolatedmodule configuration only; immutable166 file remainsunchanged.
runner.STATE=STATE;runner.FREEZE=FREEZE;runner.REVIEW=REVIEW;runner.preflight=preflight;runner.check_review=check_review
def execute(root=ROOT,**kwargs):
 root=Path(root)
 def capture_before_cleanup(cfg,state,expected):
  try:return capture(cfg,state,expected,root=root)
  except Exception as e:
   durable(Path(state)/'capture178-failure.json',{'error_type':type(e).__name__,'error_code':str(e) if str(e).startswith('CANARY178_') else 'CANARY178_CAPTURE_FAILED','cleanup_still_required':True})
   return {'status':'capture_failed_cleanup_required'}
 return runner.execute(root=root,evidence_fn=kwargs.pop('evidence_fn',capture_before_cleanup),**kwargs)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');a=p.parse_args();print(json.dumps(execute() if a.execute else preflight(),indent=2))
