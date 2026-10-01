import importlib.util,io,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('continue207test',ROOT/'deployment/experimental_continue_207.py');p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
class Missing(Exception):error_code='RESOURCE_DOES_NOT_EXIST'
class Workspace:
 def __init__(self,entries):self.entries=entries;self.uploads=[];self.downloads=[];self.statuses=[];self.fail=False
 def get_status(self,path):
  self.statuses.append(path)
  if path not in self.entries:raise Missing()
  return {'object_type':'DIRECTORY' if self.entries[path] is None else 'FILE'}
 def download(self,path,**kw):
  self.downloads.append(path)
  if path not in self.entries:raise Missing()
  return io.BytesIO(self.entries[path])
 def upload(self,path,stream,**kw):
  self.uploads.append(path)
  if self.fail:raise TimeoutError('SECRET must not be persisted')
  assert kw['overwrite'] is False;assert path not in self.entries;self.entries[path]=stream.read()
class Continue207(unittest.TestCase):
 def fixture(self,t,existing_ambiguous=False):
  root=Path(t).resolve();state=root/'state';state.mkdir();package=root/'package';(package/'source').mkdir(parents=True)
  files={n:p.base.sha(n.encode()) for n in ('a','b','c')}
  for n in files:(package/'source'/n).write_bytes(n.encode())
  entries={'/prefix':None,'/prefix/a':b'a'}
  if existing_ambiguous:entries['/prefix/b']=b'b'
  ws=Workspace(entries);return state,package,files,ws
 def test_preflight_preserves_attempts_partial_receipts_window_and_caps(self):
  _,m,b,_,_,verified,ambiguous,dirs=p.preflight();self.assertEqual((len(verified),len(ambiguous),len(dirs)),(8,1,42));self.assertEqual((m['source_sha256'],b['expires_at_unix']),(p.SOURCE,p.END));self.assertEqual(p.LIMITS['upload']+9,235);self.assertEqual(p.PRIOR_COUNTS['http']+p.LIMITS['http'],2504);self.assertEqual(p.LIMITS['mkdir'],0)
 def test_rechecks_verified_skips_existing_ambiguous_uploads_only_unattempted(self):
  with tempfile.TemporaryDirectory() as t:
   state,package,files,ws=self.fixture(t,True);p.resume_upload(SimpleNamespace(workspace=ws),state,package,files,'/prefix',{'a':files['a']},{'b'},{'/prefix'},lambda:None)
   self.assertEqual(ws.uploads,['/prefix/c']);self.assertEqual(ws.downloads,['/prefix/a','/prefix/b','/prefix/c']);self.assertFalse(p.read(state/'failed-import-reconciled.json')['new_import_allowed_only_if_missing'])
 def test_missing_failed_import_reconciled_before_one_new_attempt(self):
  with tempfile.TemporaryDirectory() as t:
   state,package,files,ws=self.fixture(t);p.resume_upload(SimpleNamespace(workspace=ws),state,package,files,'/prefix',{'a':files['a']},{'b'},{'/prefix'},lambda:None)
   self.assertEqual(ws.uploads,['/prefix/b','/prefix/c']);self.assertEqual(ws.statuses,['/prefix','/prefix/b','/prefix/c']);self.assertTrue(p.read(state/'failed-import-reconciled.json')['prior_attempt_retained'])
 def test_verified_drift_unexpected_file_and_missing_directory_block_before_mutation(self):
  for case in ('verified','unexpected','directory'):
   with self.subTest(case=case),tempfile.TemporaryDirectory() as t:
    state,package,files,ws=self.fixture(t,True)
    if case=='verified':ws.entries['/prefix/a']=b'changed'
    elif case=='unexpected':ws.entries['/prefix/c']=b'c'
    else:ws.entries.pop('/prefix')
    with self.assertRaises(ValueError):p.resume_upload(SimpleNamespace(workspace=ws),state,package,files,'/prefix',{'a':files['a']},{'b'},{'/prefix'},lambda:None)
    self.assertEqual(ws.uploads,[])
 def test_import_exception_records_type_only_no_retry_and_exports_once(self):
  with tempfile.TemporaryDirectory() as t:
   state,package,files,ws=self.fixture(t);ws.fail=True
   with self.assertRaises(Missing):p.resume_upload(SimpleNamespace(workspace=ws),state,package,files,'/prefix',{'a':files['a']},{'b'},{'/prefix'},lambda:None)
   self.assertEqual(ws.uploads,['/prefix/b']);self.assertEqual(ws.downloads,['/prefix/a','/prefix/b']);error=next(state.glob('upload-error-*.json'));self.assertEqual(p.read(error)['error_type'],'TimeoutError');self.assertNotIn('SECRET',error.read_text())
 def test_expiry_before_auth_and_same_cfg_cleanup(self):
  with patch.object(p,'review'),patch.object(p,'config') as cfg:
   with self.assertRaisesRegex(ValueError,'WINDOW'):p.execute(clock=lambda:p.END,config_factory=cfg)
   cfg.assert_not_called()
  with tempfile.TemporaryDirectory() as t:
   root=Path(t).resolve();cfg=object()
   def execute(*args,config_factory):self.assertIs(config_factory(),cfg);return {'status':'experimental_ui_evaluation_pending','cleanup_required_before_or_at_unix':0}
   with patch.object(p,'execute',side_effect=execute),patch.object(p,'stop',return_value={'status':'stopped_observed'}) as stop:p.supervised_execute(root,cfg=cfg);stop.assert_called_once_with(root,cfg=cfg)

 def test_execute_resumes_before_single_start_terminal_guard_and_cleanup(self):
  import copy
  values=p.preflight();package,m,b,allowed,old,*_=values
  with tempfile.TemporaryDirectory() as t:
   root=Path(t).resolve()
   for name in (p.FREEZE,p.prior.REVIEW):
    file=root/name;file.parent.mkdir(parents=True,exist_ok=True);file.write_text('{}')
   class Apps:
    started=False;starts=0;fresh=0;deploys=0
    def get(self,name):
     app=p.read(ROOT/'deployment/state/auth-observation207/app.json');app['compute_status']['state']='ACTIVE' if self.started else 'STOPPED'
     if self.started:app['active_deployment']=copy.deepcopy(old);app['active_deployment']['status']['state']='SUCCEEDED' if self.fresh>=2 else 'IN_PROGRESS'
     return app
    def start(self,name):self.starts+=1;self.started=True
    def get_deployment(self,name,ident):self.fresh+=1;d=copy.deepcopy(old);d['status']['state']='SUCCEEDED';return d
    def deploy(self,name,body):self.deploys+=1;assert self.fresh>=3;raise TimeoutError()
   apps=Apps();cfg=SimpleNamespace(host=p.base.HOST,authenticate=lambda:{'Authorization':'synthetic'});server=SimpleNamespace(apps=apps,api=SimpleNamespace(counts=dict.fromkeys(p.LIMITS,0),session=SimpleNamespace(close=lambda:None),do=lambda *a,**kw:{'app_deployments':[]}))
   def resumed(*a):self.assertFalse(apps.started)
   with patch.object(p,'preflight',return_value=values),patch.object(p,'review'),patch.object(p,'resume_upload',side_effect=resumed) as upload,patch.object(p,'cleanup',return_value={'status':'stopped_observed'}) as cleanup:
    result=p.execute(root,cfg=cfg,identity_fn=lambda *a:None,services_factory=lambda *a,**kw:server,sleep=lambda _:None)
   self.assertEqual((apps.starts,apps.deploys),(1,1));upload.assert_called_once();self.assertIs(cleanup.call_args.args[0],cfg);self.assertEqual(result['status'],'incomplete');self.assertTrue((root/p.STATE/'start-intent.json').exists())
