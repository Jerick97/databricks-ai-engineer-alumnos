import copy,importlib.util,json,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('continue194test',ROOT/'deployment/experimental_continue_194.py');p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
class Continue194(unittest.TestCase):
 def test_pending_null_active_in_progress_is_not_ready_even_if_fresh_terminal(self):
  old=p.read(ROOT/p.prior.STATE/'start-observation-37.json')['active_deployment'];app=p.read(ROOT/p.prior.STATE/'start-observation-37.json');allowed={old['deployment_id']:old['source_code_path']}
  fresh=copy.deepcopy(old);fresh['status']['state']='SUCCEEDED';apps=SimpleNamespace(get_deployment=lambda *a:fresh)
  with tempfile.TemporaryDirectory() as t:
   self.assertFalse(p.restoration_ready(SimpleNamespace(apps=apps),app,old,allowed,time.time(),Path(t).resolve(),0))
   app['active_deployment']['status']['state']='SUCCEEDED';fresh['status']['state']='IN_PROGRESS'
   self.assertFalse(p.restoration_ready(SimpleNamespace(apps=apps),app,old,allowed,time.time(),Path(t).resolve(),1))
   fresh['status']['state']='SUCCEEDED'
   self.assertTrue(p.restoration_ready(SimpleNamespace(apps=apps),app,old,allowed,time.time(),Path(t).resolve(),2))
   fresh['creator']='foreign'
   with self.assertRaisesRegex(ValueError,'FRESH_RESTORE_BINDING'):p.restoration_ready(SimpleNamespace(apps=apps),app,old,allowed,time.time(),Path(t).resolve(),3)
 def test_preserved_source_window_and_receipts(self):
  _,m,b,_=p.preflight();self.assertEqual((m['source_sha256'],b['expires_at_unix']),(p.SOURCE,p.END))
  original=p.prior.ready
  def altered(root):
   package,m,b=original(root);m['deadline_unix']+=1;return package,m,b
  with patch.object(p.prior,'ready',side_effect=altered):
   with self.assertRaisesRegex(ValueError,'SOURCE_WINDOW'):p.preflight()
 def test_no_upload_mkdir_and_additional_attempt_caps(self):
  class Delegate:
   calls=0
   def do(self,*a,**kw):self.calls+=1;return {}
  for path,kind in [('/api/2.0/workspace/import','upload'),('/api/2.0/workspace/mkdirs','mkdir'),(p.control.APP_PATH+'/start','start'),(p.control.APP_PATH+'/deployments','deploy')]:
   with self.subTest(kind=kind),tempfile.TemporaryDirectory() as t:
    delegate=Delegate();api=p.prior.LedgerAPI(delegate,Path(t).resolve(),p.LIMITS)
    if kind in ('start','deploy'):api.do('POST',path)
    with self.assertRaisesRegex(ValueError,'API_CAP'):api.do('POST',path)
    self.assertEqual(delegate.calls,1 if kind in ('start','deploy') else 0)
  self.assertEqual(p.PRIOR_COUNTS['http']+p.LIMITS['http'],1600)
  self.assertEqual(p.PRIOR_COUNTS['start']+p.LIMITS['start'],2)
  self.assertEqual(p.PRIOR_COUNTS['deploy']+p.LIMITS['deploy'],2)
 def test_execute_waits_and_writes_192_binding_without_uploads(self):
  package,m,b,old=p.preflight()
  with tempfile.TemporaryDirectory() as t:
   root=Path(t).resolve();(root/p.FREEZE).parent.mkdir(parents=True);(root/p.FREEZE).write_text('{}');(root/p.prior.EXACT).write_text('{}')
   (root/p.prior.STATE).mkdir(parents=True);(root/p.prior.STATE/'source-verified.json').write_text('{}')
   class Apps:
    starts=0;deploys=0;gets=0;fresh=0
    def get(self,name):
     self.gets+=1;app=p.read(ROOT/p.prior.STATE/'start-observation-37.json');app['compute_status']['state']='ACTIVE' if self.starts else 'STOPPED'
     if self.starts:app['active_deployment']['status']['state']='SUCCEEDED' if self.fresh>=2 else 'IN_PROGRESS'
     if self.deploys:app.update(active_deployment={'deployment_id':'new194','source_code_path':b['source_code_path']},last_deployment_id='new194')
     return app
    def start(self,name):self.starts+=1
    def get_deployment(self,name,ident):
     if ident=='new194':return {'deployment_id':ident,'status':{'state':'SUCCEEDED'}}
     self.fresh+=1;v=copy.deepcopy(old);v['status']['state']='SUCCEEDED' if self.fresh>=2 else 'IN_PROGRESS';return v
    def deploy(self,name,body):
     assert self.fresh>=3;self.deploys+=1;return SimpleNamespace(response={'deployment_id':'new194','source_code_path':b['source_code_path']})
   apps=Apps();api=SimpleNamespace(counts=dict.fromkeys(p.LIMITS,0),session=SimpleNamespace(close=lambda:None));server=SimpleNamespace(apps=apps,api=api)
   with patch.object(p,'preflight',return_value=(package,m,b,old)),patch.object(p,'review'):
    result=p.execute(root,config_factory=lambda:SimpleNamespace(host=p.base.HOST),services_factory=lambda *a,**kw:server,identity_fn=lambda *a:None,clock=lambda:p.END-600,sleep=lambda _:None)
   self.assertEqual(result['status'],'experimental_ui_evaluation_pending',result);self.assertEqual((apps.starts,apps.deploys),(1,1))
   binding=p.read(root/p.prior.STATE/'demo-ledger/binding.json');self.assertEqual(binding['candidate_kind'],'experimental_linux191');self.assertEqual(binding['caps'],p.CAPS);self.assertEqual(binding['expires_at_unix'],p.END)
 def test_expired_window_precedes_auth_and_supervisor_cleanup(self):
  with patch.object(p,'review'),patch.object(p,'config') as cfg:
   with self.assertRaisesRegex(ValueError,'WINDOW'):p.execute(clock=lambda:p.END,config_factory=cfg)
   cfg.assert_not_called()
  with tempfile.TemporaryDirectory() as t,patch.object(p,'ROOT',Path(t).resolve()),patch.object(p,'execute',return_value={'status':'experimental_ui_evaluation_pending','cleanup_required_before_or_at_unix':0}),patch.object(p,'stop',return_value={'status':'stopped_observed'}) as stop:
   p.supervised_execute();stop.assert_called_once()
