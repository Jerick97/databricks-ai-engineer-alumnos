"""Exactly178 predecessor for unchanged168 finalApp executor and cleanup."""
from pathlib import Path
import argparse,importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('final182isolated168',ROOT/'deployment/final_deploy_168.py');runner=importlib.util.module_from_spec(s);s.loader.exec_module(runner)
require=runner.require;read=runner.read;sha=runner.sha
FREEZE='runs/sk12-final-binding-182-freeze.json';REVIEW='runs/sk09-final-binding-182-review.json'
PREVIOUS='deployment/state/linux-canary-recovery-178';PREVIOUS_FREEZE='runs/sk12-canary-recovery-178-freeze.json';PREVIOUS_REVIEW='runs/sk09-canary-recovery-178-review.json'
BINDING_FILES=('admission.json','source-binding.json','package/manifest.json','source-verified.json','deploy-intent.json','deploy-receipt.json')
original_ready=runner.ready
# This isolatedmodule's cleanup helper takes state explicitly; onlyexecute's
# priorcanary lookup changes. No168/166/178 sourcefile edits or ledger reset.
runner.mission.STATE=PREVIOUS

def check_review(root):
 r=read(root/REVIEW);require(r.get('status')=='PASS_FINAL_BINDING_182' and r.get('freeze_sha256')==sha(root/FREEZE),'FINAL182_REVIEW_REQUIRED')
 for p,h in read(root/FREEZE)['files_sha256'].items():require(sha(root/p)==h,'FINAL182_INPUT_DRIFT')
 runner.review(root)
def predecessor(root):
 root=Path(root);state=root/PREVIOUS;r=read(root/PREVIOUS_REVIEW)
 require(r.get('status')=='PASS_CANARY_RECOVERY_178' and r.get('freeze_sha256')==sha(root/PREVIOUS_FREEZE),'FINAL182_PREVIOUS_REVIEW')
 admission=read(state/'admission.json');require(admission.get('phase')=='178' and admission.get('freeze_sha256')==sha(root/PREVIOUS_FREEZE) and admission.get('review_sha256')==sha(root/PREVIOUS_REVIEW),'FINAL182_PREVIOUS_ADMISSION')
 binding=read(state/'source-binding.json');manifest=read(state/'package/manifest.json')
 require(binding.get('manifest_sha256')==sha(state/'package/manifest.json') and binding.get('source_sha256')==manifest.get('source_sha256') and binding.get('expires_at_unix')==admission.get('expires_at_unix')==manifest.get('expires_at_unix'),'FINAL182_PREVIOUS_SOURCE')
 prefix=runner.prior.transport.history.prior.PREFIX+'canary166-'+manifest['source_sha256'];require(binding.get('source_code_path')==prefix,'FINAL182_PREVIOUS_PREFIX')
 require(read(state/'source-verified.json')=={'files':237,'source_sha256':manifest['source_sha256']},'FINAL182_PREVIOUS_READBACK')
 require(read(state/'deploy-intent.json')=={'source_code_path':prefix,'mode':'SNAPSHOT'},'FINAL182_PREVIOUS_DEPLOY')
 receipt=read(state/'deploy-receipt.json');require(isinstance(receipt.get('deployment_id'),str) and receipt['deployment_id'] and receipt.get('source_code_path')==prefix,'FINAL182_PREVIOUS_RECEIPT')
 return {PREVIOUS+'/'+name:sha(state/name) for name in BINDING_FILES}
def ready(root):
 root=Path(root);out=original_ready(root);review=read(root/runner.EXACT_REVIEW)
 require(review.get('executor182_freeze_sha256')==sha(root/FREEZE) and review.get('previous_canary178_inputs_sha256')==predecessor(root),'FINAL182_EXACT_PREDECESSOR_REVIEW')
 return out
runner.ready=ready

def preflight(root=ROOT):
 root=Path(root);out=runner.preflight(root)
 return {**out,'previous_canary_phase':'178','previous_state':PREVIOUS,'final_state':runner.STATE,'ledger':'samefinal-app168/demo-ledger; no reset','pending_previous_files':[name for name in BINDING_FILES if not (root/PREVIOUS/name).exists()]}
def materialize(report,report_sha,root=ROOT,**kwargs):
 root=Path(root);check_review(root)
 # Original168 materializer still requires actualLinux and139 beforedeadline.
 return runner.materialize(report,report_sha,root=root,**kwargs)
def execute(root=ROOT,**kwargs):
 root=Path(root);check_review(root);return runner.execute(root=root,**kwargs)
def stop(root=ROOT,**kwargs):
 root=Path(root);check_review(root);return runner.stop(root=root,**kwargs)
if __name__=='__main__':
 p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group();g.add_argument('--materialize',type=Path);g.add_argument('--execute',action='store_true');g.add_argument('--stop',action='store_true');p.add_argument('--linux-sha256');a=p.parse_args()
 print(json.dumps(materialize(a.materialize,a.linux_sha256) if a.materialize else execute() if a.execute else stop() if a.stop else preflight(),indent=2))
