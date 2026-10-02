import copy,importlib.util,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('continue204test',ROOT/'deployment/experimental_continue_204.py');p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
class Continue204(unittest.TestCase):
 def test_preflight_adopts_exact_observed_app_same_source_deadline_no_reset(self):
  _,m,b,allowed,old=p.preflight();self.assertEqual((m['source_sha256'],b['expires_at_unix']),(p.SOURCE,p.END));self.assertEqual(list(allowed),['01f1bc4ca1041e21be0f4795d63d7ebf']);self.assertEqual(p.PRIOR_COUNTS['http'],905);self.assertEqual(p.LIMITS['http']+1,1600);self.assertEqual(p.LIMITS['start'],0)
 def test_foreign_owner_source_time_sp_identity_rejected(self):
  original=p.read(ROOT/p.OBSERVATION)
  for key,value in [('creator','foreign'),('source_code_path','/other'),('create_time','2020-01-01T00:00:00Z')]:
   app=copy.deepcopy(original);app['active_deployment'][key]=value
   with self.subTest(key=key),self.assertRaises(ValueError):p.adopted(app,ROOT)
  app=copy.deepcopy(original);app['service_principal_id']=1
  with self.assertRaises(ValueError):p.adopted(app,ROOT)
 def test_zero_start_transport_cap_and_no_second_deploy(self):
  class Delegate:
   calls=0
   def do(self,*a,**kw):self.calls+=1;return {}
  with tempfile.TemporaryDirectory() as t:
   d=Delegate();api=p.prior.prior.LedgerAPI(d,Path(t).resolve(),p.LIMITS)
   with self.assertRaisesRegex(ValueError,'API_CAP'):api.do('POST',p.control.APP_PATH+'/start')
   self.assertEqual(d.calls,0)
  with tempfile.TemporaryDirectory() as t:
   d=Delegate();api=p.prior.prior.LedgerAPI(d,Path(t).resolve(),p.LIMITS);api.do('POST',p.control.APP_PATH+'/deployments')
   with self.assertRaisesRegex(ValueError,'API_CAP'):api.do('POST',p.control.APP_PATH+'/deployments')
   self.assertEqual(d.calls,1)
 def test_execute_no_start_waits_terminal_handoff_same199ledger(self):
  package,m,b,allowed,old=p.preflight()
  with tempfile.TemporaryDirectory() as t:
   root=Path(t).resolve()
   for name in (p.FREEZE,p.prior.REVIEW,p.REVIEW,p.OBSERVATION):
    path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('{}')
   class Apps:
    fresh=0;deploys=0
    def get(self,name):
     app=p.read(ROOT/p.OBSERVATION);app['active_deployment']['status']['state']='SUCCEEDED' if self.fresh>=2 else 'IN_PROGRESS'
     if self.deploys:app['active_deployment']={'deployment_id':'new204','source_code_path':b['source_code_path']}
     return app
    def get_deployment(self,name,ident):
     if ident=='new204':return {'deployment_id':ident,'status':{'state':'SUCCEEDED'}}
     self.fresh+=1;value=copy.deepcopy(old);value['status']['state']='SUCCEEDED';return value
    def start(self,*args):raise AssertionError('START forbidden')
    def deploy(self,name,body):self.deploys+=1;assert self.fresh>=3;return SimpleNamespace(response={'deployment_id':'new204','source_code_path':b['source_code_path']})
   cfg=SimpleNamespace(host=p.base.HOST,authenticate=lambda:{'Authorization':'synthetic'});apps=Apps();server=SimpleNamespace(apps=apps,api=SimpleNamespace(counts=dict.fromkeys(p.LIMITS,0),session=SimpleNamespace(close=lambda:None)))
   with patch.object(p,'preflight',return_value=(package,m,b,allowed,old)),patch.object(p,'review'),patch.object(p.prior.prior.shipping,'upload') as upload,patch.object(p.prior,'materialize',side_effect=AssertionError('renew forbidden')),patch.object(p.prior,'migrate_ledger') as migrate:
    result=p.execute(root,cfg=cfg,services_factory=lambda *a,**kw:server,identity_fn=lambda *a:None,sleep=lambda _:None)
   self.assertEqual(result['status'],'experimental_ui_evaluation_pending',result);upload.assert_called_once();self.assertEqual(apps.deploys,1);self.assertEqual(migrate.call_args.args[1],root/p.prior.STATE);self.assertFalse((root/p.STATE/'start-intent.json').exists());self.assertEqual(p.read(root/p.STATE/'adoption-intent.json')['executor_starts'],0)
 def test_cleanup_reconciles_candidate_from_adoption_without_fake_start(self):
  app0=p.read(ROOT/p.OBSERVATION);old=app0['active_deployment']
  with tempfile.TemporaryDirectory() as t:
   state=Path(t).resolve();(state/'cleanup').mkdir();now=time.time();p.durable(state/'adoption-intent.json',{'at_unix':now-10});p.durable(state/'app-before.json',app0);p.durable(state/'deploy-intent.json',{'source_code_path':'/candidate204','at_unix':now-2})
   from datetime import datetime,timezone
   d={'deployment_id':'candidate204','source_code_path':'/candidate204','creator':p.prior.prior.OWNER,'create_time':datetime.fromtimestamp(now,timezone.utc).isoformat()};app=copy.deepcopy(app0);app['active_deployment']=d
   allowed={old['deployment_id']:old['source_code_path']};p.reconcile_cleanup(app,state,allowed,{'app_deployments':[d]});self.assertEqual(allowed['candidate204'],'/candidate204');self.assertFalse((state/'start-intent.json').exists())
 def test_expiry_before_auth_and_same_cfg_supervisor_cleanup(self):
  with patch.object(p,'review'),patch.object(p,'config') as config:
   with self.assertRaisesRegex(ValueError,'WINDOW'):p.execute(clock=lambda:p.END,config_factory=config)
   config.assert_not_called()
  with tempfile.TemporaryDirectory() as t:
   root=Path(t).resolve();cfg=object()
   def execute(*args,config_factory):self.assertIs(config_factory(),cfg);return {'status':'experimental_ui_evaluation_pending','cleanup_required_before_or_at_unix':0}
   with patch.object(p,'execute',side_effect=execute),patch.object(p,'stop',return_value={'status':'stopped_observed'}) as stop:p.supervised_execute(root,cfg=cfg);stop.assert_called_once_with(root,cfg=cfg)
