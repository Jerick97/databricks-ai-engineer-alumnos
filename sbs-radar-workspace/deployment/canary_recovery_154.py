"""Recovery154 preserves151; fixes error stream lifecycle, no new window."""
from pathlib import Path
from types import SimpleNamespace
import argparse,base64,importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('recovery154isolated151',ROOT/'deployment/canary_recovery_151.py');runner=importlib.util.module_from_spec(s);s.loader.exec_module(runner)
base=runner.base;require=runner.require;read=runner.read;durable=runner.durable;sha=runner.sha
FREEZE='runs/sk12-canary-recovery-154-freeze.json';REVIEW='runs/sk09-canary-recovery-154-review.json';STATE='deployment/state/linux-canary-recovery-154'
original_preflight=runner.preflight;original_review=runner.check_review
# Keep original151 gate bound to its historical module constants.
s2=importlib.util.spec_from_file_location('recovery154history151',ROOT/'deployment/canary_recovery_151.py');history=importlib.util.module_from_spec(s2);s2.loader.exec_module(history)
def preflight(root=ROOT):
 root=Path(root);p=original_preflight(root);history.check_review(root)
 state=root/history.STATE;result=read(state/'result.json')
 require(result.get('effects')=={'upload':0,'mkdir':0,'start':0,'deploy':0} and result.get('status')=='incomplete','CANARY154_PRIOR_EFFECTS_CHANGED')
 require(not list(state.glob('upload-*.json')) and not (state/'start-intent.json').exists() and not (state/'deploy-intent.json').exists(),'CANARY154_PRIOR_INTENT_CHANGED')
 require(read(state/'admission.json')['expires_at_unix']==p['expires_at_unix'],'CANARY154_WINDOW_CHANGED')
 p['recovery154_prior151_effects']=result['effects'];return p
def check_review(root):
 r=read(root/REVIEW);require(r.get('status')=='PASS_CANARY_RECOVERY_154' and r.get('freeze_sha256')==sha(root/FREEZE),'CANARY154_REVIEW_REQUIRED')
 for p,h in read(root/FREEZE)['files_sha256'].items():require(sha(root/p)==h,'CANARY154_INPUT_DRIFT')
 history.check_review(root)
class ErrorSession(history.ErrorSession):
 def request(self,method,url,**kwargs):
  response=self.session.request(method,url,**kwargs)
  if not 200<=response.status_code<300:
   raw=response.raw;self.sequence+=1;path=self.state/f'http-error-{self.sequence:04}.json'
   class Raw:
    def __getattr__(inner,name):return getattr(raw,name)
    def read(inner,amount,**options):
     content=raw.read(min(amount,1048577),**options)
     durable(path,{'method':method,'url':url,'status':response.status_code,'body_base64':base64.b64encode(content[:1048576]).decode(),'truncated':len(content)>1048576})
     require(len(content)<=1048576,'CANARY154_ERROR_BODY_CAP');return content
   response.raw=Raw()
  return response

def services(cfg,prefix,admit,*,uploads,mkdirs,state):
 import requests
 from databricks.sdk.mixins.workspace import WorkspaceExt
 from databricks.sdk.service.apps import AppsAPI
 api=history.prior.CappedApi(base.ScopedApi(cfg,prefix,admit,ErrorSession(requests.Session(),state)),uploads=uploads,mkdirs=mkdirs)
 return SimpleNamespace(workspace=WorkspaceExt(api),apps=AppsAPI(api),api=api)
runner.STATE=STATE;runner.FREEZE=FREEZE;runner.REVIEW=REVIEW;runner.preflight=preflight;runner.check_review=check_review
# All orchestration and historical effect aggregation remain151;151 contributed0.
def execute(root=ROOT,**kwargs):return runner.execute(root=root,services_factory=kwargs.pop('services_factory',services),**kwargs)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');a=p.parse_args();print(json.dumps(execute() if a.execute else preflight(),indent=2))
