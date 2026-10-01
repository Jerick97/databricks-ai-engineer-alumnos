"""ACTIVE-only handoff185→unchanged168final; no implicit restoration/start."""
from pathlib import Path
import argparse,importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
def module(path,name):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
runner=module('deployment/final_deploy_168.py','handoff186isolated168');previous=module('deployment/canary_continue_185.py','handoff186previous185')
require=runner.require;read=runner.read;sha=runner.sha
FREEZE='runs/sk12-final-handoff-186-freeze.json';REVIEW='runs/sk09-final-handoff-186-review.json'
original_ready=runner.ready;original_current=runner.current;runner.mission.STATE=previous.STATE

def check_review(root):
 r=read(root/REVIEW);require(r.get('status')=='PASS_FINAL_HANDOFF_186' and r.get('freeze_sha256')==sha(root/FREEZE),'FINAL186_REVIEW_REQUIRED')
 for p,h in read(root/FREEZE)['files_sha256'].items():require(sha(root/p)==h,'FINAL186_INPUT_DRIFT')
 runner.review(root)
def predecessor(root):
 root=Path(root);previous.check_review(root);p=previous.preflight(root);state=root/previous.STATE;source=root/previous.prior.STATE/'source-binding.json'
 admission=read(state/'admission.json');require(admission.get('phase')=='185' and admission.get('freeze_sha256')==sha(root/previous.FREEZE) and admission.get('review_sha256')==sha(root/previous.REVIEW) and admission.get('expires_at_unix')==p['expires_at_unix'],'FINAL186_PREVIOUS_ADMISSION')
 require(read(state/'source-binding.json')=={'source_code_path':p['source_code_path'],'source_sha256':p['source_sha256'],'source_binding178_sha256':sha(source)},'FINAL186_SOURCE')
 require(read(state/'deploy-intent.json')=={'source_code_path':p['source_code_path'],'mode':'SNAPSHOT'},'FINAL186_DEPLOY_INTENT')
 receipt=read(state/'deploy-receipt.json');require(receipt.get('source_code_path')==p['source_code_path'] and isinstance(receipt.get('deployment_id'),str),'FINAL186_RECEIPT')
 handoff=read(state/'active-handoff.json');report=state/'capture178/linux-report.json';gate=read(state/'capture178/gate153.json')
 require(handoff.get('deployment_id')==receipt['deployment_id'] and handoff.get('source_code_path')==p['source_code_path'] and handoff.get('source_sha256')==p['source_sha256'] and handoff.get('expires_at_unix')==p['expires_at_unix'] and handoff.get('report_sha256')==sha(report) and gate.get('status')=='passed' and gate.get('report_sha256')==sha(report),'FINAL186_LINUX_HANDOFF')
 # Revalidate original153gates, not merely a boolean in handoff.
 previous.prior.gates.gates(root,report,sha(report))
 names=[previous.STATE+'/'+n for n in ('admission.json','source-binding.json','deploy-intent.json','deploy-receipt.json','active-handoff.json','capture178/linux-report.json','capture178/gate153.json')]+[previous.prior.STATE+'/source-binding.json',previous.FREEZE,previous.REVIEW]
 return {p:sha(root/p) for p in names}
def ready(root):
 root=Path(root);out=original_ready(root);r=read(root/runner.EXACT_REVIEW)
 require(r.get('executor186_freeze_sha256')==sha(root/FREEZE) and r.get('previous185_inputs_sha256')==predecessor(root),'FINAL186_EXACT_PREDECESSOR_REVIEW');return out
runner.ready=ready

def active_only(app,old):
 phase=original_current(app,old);require(phase in ('ACTIVE','RUNNING'),'FINAL186_ACTIVE_HANDOFF_REQUIRED_NO_START');return phase
runner.current=active_only

def preflight(root=ROOT):return {**runner.preflight(Path(root)),'previous_canary':'185receipt/178source','start_max':0,'final_state':runner.STATE,'materialized_state':runner.MATERIALIZED,'linux_materialization_performed':False}
def materialize(report,report_sha,root=ROOT,**kwargs):
 root=Path(root);check_review(root);predecessor(root);require(Path(report).resolve()==(root/previous.STATE/'capture178/linux-report.json').resolve(),'FINAL186_REPORT_SCOPE')
 return runner.materialize(report,report_sha,root=root,**kwargs)
def execute(root=ROOT,**kwargs):
 root=Path(root);check_review(root)
 factory=kwargs.pop('services_factory',runner.prior.transport.services)
 def zero_start(*args,**kw):
  service=factory(*args,**kw);service.api.maximum['start']=0;return service
 return runner.execute(root=root,services_factory=zero_start,**kwargs)
def stop(root=ROOT,**kwargs):
 root=Path(root);check_review(root);predecessor(root)
 receipt=read(root/previous.STATE/'deploy-receipt.json');binding=read(root/previous.STATE/'source-binding.json')
 p={'old_source':binding['source_code_path'],'old_ids':[receipt['deployment_id']]}
 # Exactold185 or ownnewfinal accepted duringfailedreplacementcleanup.
 runner.mission.cleanup=lambda cfg,state,expected,before,**kw:previous.cleanup(cfg,state,p,expected,**kw)
 return runner.stop(root=root,**kwargs)
if __name__=='__main__':
 p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group();g.add_argument('--materialize',type=Path);g.add_argument('--execute',action='store_true');g.add_argument('--stop',action='store_true');p.add_argument('--linux-sha256');a=p.parse_args()
 print(json.dumps(materialize(a.materialize,a.linux_sha256) if a.materialize else execute() if a.execute else stop() if a.stop else preflight(),indent=2))
