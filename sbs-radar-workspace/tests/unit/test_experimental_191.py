import unittest,importlib.util,tempfile,json,copy,time,io
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('experiment191tests',ROOT/'deployment/experimental_app_191.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
class Experimental191(unittest.TestCase):
 def test_materialization_preserves_code_chunks_caps_and_failed_gate(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t).resolve();dest=root/p.PACKAGE;m=p.materialize(dest,clock=lambda:2000000000,check_review=False)
   held=root/p.HELD;held.parent.mkdir(parents=True);held.symlink_to(ROOT/p.HELD,target_is_directory=True)
   _,checked,payload=p.ready(root,exact=False)
   self.assertEqual(m,checked);self.assertEqual(m['deadline_unix'],2000001800);self.assertEqual(payload['numeric_equivalence'],'failed');self.assertFalse(payload['final_release_authorized'])
   for n,h in p.read(ROOT/p.HELD/'manifest.json')['files_sha256'].items():
    if n not in ('config/app-integration-133.json','chunks163-manifest.json'):self.assertEqual(m['files_sha256'][n],h)
   changed=dest/'source/app133.py';changed.write_text(changed.read_text()+'\n# tamper\n')
   with self.assertRaisesRegex(ValueError,'SOURCE_DRIFT'):p.ready(root,exact=False)
 def test_restore_exact_source_owner_time_and_other_deployments_rejected(self):
  old=p.read(ROOT/p.OLD);allowed={old['deployment_id']:old['source_code_path']};now=time.time()
  from datetime import datetime,timezone
  d={'deployment_id':'restore191','source_code_path':old['source_code_path'],'creator':p.OWNER,'create_time':datetime.fromtimestamp(now,timezone.utc).isoformat()}
  app={'name':p.base.APP,'url':p.builder.ORIGIN,'service_principal_id':77041447522099,'service_principal_client_id':'a947eccf-5f94-4369-a3d4-8f83b4ea98a1','compute_status':{'state':'ACTIVE'},'last_deployment_id':'restore191','pending_deployment':d}
  self.assertEqual(p.restored(app,old,allowed,now),'ACTIVE');self.assertIn('restore191',allowed)
  for field,value in [('creator','foreign'),('source_code_path','/foreign'),('create_time','2000-01-01T00:00:00Z')]:
   bad=copy.deepcopy(app);bad['pending_deployment'][field]=value
   with self.assertRaises(ValueError):p.restored(bad,old,{old['deployment_id']:old['source_code_path']},now)
 def test_durable_budget_reserves_unknown_without_retry(self):
  class Delegate:
   calls=0
   def do(self,*a,**kw):self.calls+=1;raise TimeoutError()
  with tempfile.TemporaryDirectory() as t:
   d=Delegate();api=p.LedgerAPI(d,Path(t).resolve(),{'http':3,'start':1})
   with self.assertRaises(TimeoutError):api.do('POST',p.control.APP_PATH+'/start')
   self.assertEqual(p.read(Path(t)/'api-0001.json')['reserved']['start'],1)
   with self.assertRaisesRegex(ValueError,'API_CAP'):api.do('POST',p.control.APP_PATH+'/start')
   self.assertEqual(d.calls,1)
 def test_execute_full_upload_start_restore_deploy_handoff(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t).resolve();package=root/p.PACKAGE;m=p.materialize(package,check_review=False);payload=p.read(package/'deployment-payload.json');old=p.read(ROOT/p.OLD)
   (root/p.OLD).parent.mkdir(parents=True);(root/p.OLD).write_text(json.dumps(old))
   for path in (p.FREEZE,p.EXACT):(root/path).parent.mkdir(parents=True,exist_ok=True);(root/path).write_text('{}')
   class Missing(Exception):error_code='RESOURCE_DOES_NOT_EXIST'
   class Workspace:
    def __init__(self):self.entries={}
    def get_status(self,path):
     if path not in self.entries:raise Missing()
     return {'object_type':'DIRECTORY' if self.entries[path] is None else 'FILE'}
    def mkdirs(self,path):self.entries[path]=None
    def upload(self,path,stream,**kwargs):self.entries[path]=stream.read()
    def download(self,path,**kwargs):return io.BytesIO(self.entries[path])
   class Apps:
    def __init__(self):self.started=False;self.deployed=False;self.starts=0;self.deploys=0
    def get(self,name):
     result={'name':name,'url':p.builder.ORIGIN,'service_principal_id':77041447522099,'service_principal_client_id':'a947eccf-5f94-4369-a3d4-8f83b4ea98a1','default_source_code_path':old['source_code_path'],'compute_status':{'state':'ACTIVE' if self.started else 'STOPPED'},'last_deployment_id':old['deployment_id']}
     if self.deployed:result.update(active_deployment={'deployment_id':'new191','source_code_path':payload['source_code_path']},last_deployment_id='new191')
     return result
    def start(self,name):self.starts+=1;self.started=True
    def deploy(self,name,body):self.deploys+=1;self.deployed=True;return SimpleNamespace(response={'deployment_id':'new191','source_code_path':payload['source_code_path']})
    def get_deployment(self,name,ident):return {'deployment_id':ident,'status':{'state':'SUCCEEDED'}}
   ws=Workspace();apps=Apps();server=SimpleNamespace(workspace=ws,apps=apps,api=SimpleNamespace(counts={},session=SimpleNamespace(close=lambda:None)))
   with patch.object(p,'preflight'),patch.object(p,'review'),patch.object(p,'ready',return_value=(package,m,payload)):
    result=p.execute(root,config_factory=lambda:SimpleNamespace(host=p.base.HOST),services_factory=lambda *a,**kw:server,identity_fn=lambda *a:None,sleep=lambda _:None)
   self.assertEqual(result['status'],'experimental_ui_evaluation_pending',result);self.assertEqual((apps.starts,apps.deploys),(1,1));self.assertEqual(sum(v is not None for v in ws.entries.values()),234)
   binding=p.read(root/p.STATE/'demo-ledger/binding.json');self.assertEqual(binding['candidate_kind'],'experimental_linux191');self.assertEqual(binding['caps'],p.CAPS);self.assertIsNone(binding['process_epoch'])
 def test_cleanup_reconciles_start_restore_or_ambiguous_deploy_without_resend(self):
  from datetime import datetime,timezone
  for candidate in (False,True):
   with self.subTest(candidate=candidate),tempfile.TemporaryDirectory() as t:
    state=Path(t).resolve();now=time.time();old=p.read(ROOT/p.OLD);source=p.PREFIX+'a'*64 if candidate else old['source_code_path'];ident='unknown-candidate' if candidate else 'unknown-restore'
    p.durable(state/'start-intent.json',{'app':p.base.APP,'at_unix':now-2});p.durable(state/'app-before.json',{'default_source_code_path':old['source_code_path']})
    if candidate:p.durable(state/'deploy-intent.json',{'source_code_path':source,'mode':'SNAPSHOT','at_unix':now-1})
    deployment={'deployment_id':ident,'source_code_path':source,'creator':p.OWNER,'create_time':datetime.fromtimestamp(now,timezone.utc).isoformat()}
    class Http:
     adapters={}
     def __init__(self):self.stopped=False;self.posts=0
     def close(self):pass
     def request(self,method,url,**kw):
      if method=='POST':self.posts+=1;self.stopped=True;value={}
      elif url.endswith('/deployments'):value={'app_deployments':[deployment]}
      else:value={'name':p.base.APP,'url':p.builder.ORIGIN,'service_principal_id':77041447522099,'service_principal_client_id':'a947eccf-5f94-4369-a3d4-8f83b4ea98a1','compute_status':{'state':'STOPPED' if self.stopped else 'ACTIVE'},'last_deployment_id':ident,'active_deployment':None if self.stopped else deployment}
      raw=json.dumps(value).encode();return SimpleNamespace(status_code=200,raw=SimpleNamespace(read=lambda *a,**kw:raw),close=lambda:None)
    http=Http();cfg=SimpleNamespace(host=p.base.HOST,authenticate=lambda:{})
    result=p.cleanup(cfg,state,{old['deployment_id']:old['source_code_path']},sleep=lambda _:None,session_factory=lambda:http)
    self.assertEqual(result['status'],'stopped_observed',result);self.assertEqual(http.posts,1);self.assertEqual(result['reserved']['stop'],1)
 def test_cleanup_rejects_foreign_and_supervisor_stops_at_deadline(self):
  with tempfile.TemporaryDirectory() as t:
   state=Path(t).resolve();(state/'cleanup').mkdir();p.durable(state/'start-intent.json',{'at_unix':time.time()-3});p.durable(state/'app-before.json',{'default_source_code_path':'/old'})
   app={'last_deployment_id':'foreign'};history={'app_deployments':[{'deployment_id':'foreign','creator':'other','source_code_path':'/old','create_time':'2026-09-29T00:00:00Z'}]}
   with self.assertRaisesRegex(ValueError,'FOREIGN_OWNER'):p.reconcile_cleanup(app,state,{},history)
   with patch.object(p,'ROOT',state),patch.object(p,'execute',return_value={'status':'experimental_ui_evaluation_pending','cleanup_required_before_or_at_unix':0}),patch.object(p,'stop',return_value={'status':'stopped_observed'}) as stop:
    p.supervised_execute();stop.assert_called_once()
