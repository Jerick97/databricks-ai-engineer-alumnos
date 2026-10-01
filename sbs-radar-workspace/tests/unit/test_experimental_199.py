import copy,importlib.util,json,shutil,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('experiment199test',ROOT/'deployment/experimental_app_199.py');p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
class Experiment199(unittest.TestCase):
 def setup_root(self,t):
  root=Path(t).resolve()
  for name in (p.prior.PACKAGE,p.OVERLAY):
   dest=root/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.symlink_to(ROOT/name,target_is_directory=True)
  shutil.copytree(ROOT/p.OLD_LEDGER,root/p.OLD_LEDGER)
  (root/p.OLD).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/p.OLD,root/p.OLD)
  for name in (p.FREEZE,p.REVIEW,p.prior.EXACT):
   target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text('{}')
  return root
 def test_materialize_only_five_files_changed_full_pins_and_unchanged_models(self):
  with tempfile.TemporaryDirectory() as t:
   root=self.setup_root(t);package,m,b=p.materialize(root/p.PACKAGE,root=root,clock=lambda:2000000000)
   prior=p.read(ROOT/p.prior.PACKAGE/'manifest.json')['files_sha256'];changed={n for n in prior if prior[n]!=m['files_sha256'][n]}
   self.assertEqual(changed,{'app.yaml','app133.py','src/sbs/webapp/__init__.py','config/app-integration-133.json','chunks163-manifest.json'});self.assertEqual(len(m['files_sha256']),234);self.assertEqual(m['deadline_unix'],2000001800)
   ch=p.read(package/'source/chunks163-manifest.json')
   for n in changed-{'chunks163-manifest.json'}:self.assertEqual(ch['logical_files_sha256'][n],m['files_sha256'][n])
   cfg=p.read(package/'source/config/app-integration-133.json');old=p.read(ROOT/p.prior.PACKAGE/'source/config/app-integration-133.json');self.assertEqual(cfg,{**old,'deadline_unix':2000001800})
   (package/'source/app133.py').write_text('tampered')
   with self.assertRaisesRegex(ValueError,'SOURCE_DRIFT'):p.ready(root)
 def test_preflight_no_auth_no_state_or_deadline_and_prior_totals(self):
  with patch.object(p,'config',side_effect=AssertionError('auth forbidden')):gate=p.preflight()
  self.assertFalse(gate['deadline_emitted']);self.assertEqual(gate['prior_aggregate'],{'http':904,'upload':234,'mkdir':42,'start':2,'deploy':2});self.assertFalse((ROOT/p.PACKAGE).exists());self.assertFalse((ROOT/p.STATE).exists())
 def test_exact_migration_claim_once_keeps_original_and_reservations(self):
  with tempfile.TemporaryDirectory() as t:
   root=self.setup_root(t);_,m,b=p.materialize(root/p.PACKAGE,root=root,clock=lambda:2000000000);state=root/p.STATE
   binding={'candidate_kind':'experimental_linux199','deployment_id':'new199','source_sha256':m['source_sha256'],'source_code_path':b['source_code_path'],'expires_at_unix':b['expires_at_unix'],'caps':p.CAPS,'scope':'external_coordinator_only_not_server_global','process_epoch':None,'numeric_equivalence':'failed','final_release_authorized':False}
   original={x.name:x.read_bytes() for x in (root/p.OLD_LEDGER).iterdir()};p.migrate_ledger(root,state,binding);p.durable(state/'deploy-receipt.json',{'deployment_id':'new199'})
   observation=root/'observation.json';p.durable(observation,{'deployment_id':'new199','source_sha256':m['source_sha256'],'observed_at_unix':2000000010})
   with patch.object(p,'review'):c=p.Coordinator(root,clock=lambda:2000000010)
   for a in p.TURNS:
    r=c.claim(a,observation);self.assertEqual(r['reserved'],p.read(root/p.OLD_LEDGER/f'turn-{a}-intent.json')['reserved'])
    with self.assertRaisesRegex(ValueError,'NO_RESEND'):c.claim(a,observation)
   self.assertEqual(original,{x.name:x.read_bytes() for x in (root/p.OLD_LEDGER).iterdir()});self.assertEqual(p.read(state/'demo-ledger/migration.json')['reservation_increase'],dict.fromkeys(p.CAPS,0))
   with self.assertRaisesRegex(ValueError,'TURN'):c.claim('turn4',observation)
   c.fail();self.assertTrue((state/'demo-ledger/ui-failed.json').exists())
 def test_auth_failure_precedes_window_materialization(self):
  with patch.object(p,'preflight'),patch.object(p,'review'),patch.object(p,'materialize') as materialize:
   with self.assertRaises(RuntimeError):p.execute(config_factory=lambda:(_ for _ in ()).throw(RuntimeError('auth failed')))
   materialize.assert_not_called()
 def test_supervisor_keeps_same_in_memory_config_for_deadline_and_bad_ui(self):
  for bad_ui in (False,True):
   with self.subTest(bad_ui=bad_ui),tempfile.TemporaryDirectory() as t:
    root=Path(t).resolve();cfg=object();factory=lambda:cfg
    if bad_ui:p.durable(root/p.STATE/'demo-ledger/ui-failed.json',{})
    def execute(*args,config_factory):
     self.assertIs(config_factory(),cfg);return {'status':'experimental_ui_evaluation_pending','cleanup_required_before_or_at_unix':time.time()+100 if bad_ui else 0}
    with patch.object(p,'execute',side_effect=execute),patch.object(p,'stop',return_value={'status':'stopped_observed'}) as stop:
     p.supervised_execute(root,config_factory=factory);stop.assert_called_once_with(root,cfg=cfg)
 def test_execute_terminal_gate_upload_and_failure_cleanup_share_cfg(self):
  with tempfile.TemporaryDirectory() as t:
   root=self.setup_root(t);old=p.read(root/p.OLD);cfg=SimpleNamespace(host=p.base.HOST,authenticate=lambda:{'Authorization':'synthetic'})
   class Apps:
    starts=0;deploys=0;fresh=0
    def get(self,name):
     app={'name':p.base.APP,'url':p.prior.builder.ORIGIN,'service_principal_id':77041447522099,'service_principal_client_id':'a947eccf-5f94-4369-a3d4-8f83b4ea98a1','default_source_code_path':old['source_code_path'],'compute_status':{'state':'ACTIVE' if self.starts else 'STOPPED'},'last_deployment_id':old['deployment_id'],'active_deployment':copy.deepcopy(old)}
     app['active_deployment']['status']['state']='SUCCEEDED' if self.fresh>=2 else 'IN_PROGRESS';return app
    def start(self,name):self.starts+=1
    def get_deployment(self,name,ident):self.fresh+=1;d=copy.deepcopy(old);d['status']['state']='SUCCEEDED';return d
    def deploy(self,name,body):self.deploys+=1;assert self.fresh>=3;raise RuntimeError('deploy failed')
   apps=Apps();server=SimpleNamespace(apps=apps,api=SimpleNamespace(counts=dict.fromkeys(p.LIMITS,0),session=SimpleNamespace(close=lambda:None),do=lambda *a,**kw:{'app_deployments':[]}))
   with patch.object(p,'preflight'),patch.object(p,'review'),patch.object(p.prior.shipping,'upload') as upload,patch.object(p,'cleanup',return_value={'status':'stopped_observed'}) as cleanup:
    result=p.execute(root,cfg=cfg,identity_fn=lambda *a:None,services_factory=lambda *a,**kw:server,sleep=lambda _:None)
   self.assertEqual(result['status'],'incomplete');self.assertEqual((apps.starts,apps.deploys),(1,1));upload.assert_called_once();self.assertIs(cleanup.call_args.args[0],cfg)
