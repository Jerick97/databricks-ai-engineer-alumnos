import unittest,json,copy,tempfile,time,base64,tarfile,subprocess,sys
from pathlib import Path
from types import SimpleNamespace
from sbs.operations import writer_operator_167 as p
from sbs.operations import writer_authority_167 as a
from sbs.operations.shared_control import initial_state
class Operator167(unittest.TestCase):
 def test_complete_sdk_two_phase_and_resume_no_second_run(self):
  root=p.ROOT;raw=json.loads((root/'deployment/state/diagnostic-monitor162/result.json').read_bytes())['output_check']['diagnostic_report']['observations'];observed={v['stage']:v['body'] for v in raw}
  acl=json.loads((root/'deployment/state/policy-binding146/driver-config146.json').read_bytes())['expected_acl'];nba=json.loads((root/'deployment/state/writer-diagnostic158/http-05-response.json').read_bytes())
  class Http:
   adapters={}
   def __init__(self):self.files={};self.source=(root/'deployment/writer_diagnostic_158_notebook.py').read_bytes();self.control=initial_state();self.revision=0;self.run_count=0;self.imports=0;self.calls=[];self.writer_mode=False
   def close(self):pass
   def request(self,m,url,**kw):
    path=url.split(p.HOST)[1];body=kw.get('json');self.calls.append((m,path));status=200;v={};raw=None
    if path.endswith('/Me'):v=observed['Me'] if self.writer_mode else {'id':p.OWNER_ID,'userName':p.OWNER,'active':True}
    elif path.endswith('/jobs/get'):v=observed['job']
    elif '/permissions/jobs/' in path:v=acl
    elif '/permissions/notebooks/' in path:v=nba
    elif path.endswith('/workspace/get-status'):v={'object_id':p.NOTEBOOK_ID,'path':p.NOTEBOOK,'object_type':'NOTEBOOK'}
    elif path.endswith('/workspace/export'):v={'content':base64.b64encode(self.source).decode()}
    elif path.endswith('/workspace/import'):self.source=base64.b64decode(body['content']);self.imports+=1
    elif '/unity-catalog/tables/' in path:v=observed['table']
    elif '/sql/warehouses/' in path:v={**observed['warehouse'],'state':'RUNNING'}
    elif '/fs/directories/' in path:v={}
    elif '/fs/files/' in path:
     key=path.split('/api/2.0/fs/files',1)[1]
     if m=='PUT':self.files[key]=kw['data'].read()
     elif key not in self.files:status=404;v={'error_code':'RESOURCE_DOES_NOT_EXIST'}
     else:raw=self.files[key]
    elif path=='/api/2.0/sql/statements':
     if body['statement'].startswith('UPDATE'):
      params={v['name']:v['value'] for v in body['parameters']}
      assert params['control']=='control' and int(params['revision'])==self.revision;self.control=json.loads(params['state']);self.revision+=1;v={'statement_id':'statement1','status':{'state':'SUCCEEDED'}}
     else:v={'statement_id':'statement1','status':{'state':'SUCCEEDED'},'manifest':{'format':'JSON_ARRAY','truncated':False,'total_row_count':1,'total_chunk_count':1,'schema':{'columns':[{'name':'control_id','type_name':'STRING'},{'name':'revision','type_name':'LONG'},{'name':'state_json','type_name':'STRING'}]}},'result':{'data_array':[['control',str(self.revision),json.dumps(self.control)]],'chunk_index':0,'row_offset':0,'row_count':1}}
    elif path.endswith('/jobs/run-now'):self.run_count+=1;v={'run_id':123456}
    elif path.endswith('/jobs/runs/get'):
     v=copy.deepcopy(json.loads((root/'deployment/state/writer-monitor156/result.json').read_bytes())['raw_run']);v['job_id']=p.JOB;v['run_id']=123456;v['state']['life_cycle_state']='RUNNING'
    else:raise AssertionError((m,path,body))
    raw=raw if raw is not None else json.dumps(v).encode();return SimpleNamespace(status_code=status,headers={'content-length':str(len(raw))},raw=SimpleNamespace(read=lambda *a,**k:raw),close=lambda:None)
  with tempfile.TemporaryDirectory() as tmp:
   now=int(time.time()*1000);review={'approved':True,'scope':'writer_operator167_two_phase','issued_at_ms':now-1000,'expires_at_ms':now+600000,'limits':p.LIMITS,'request_id':p.REQUEST,'files':p.review_inputs()};cfg=SimpleNamespace(host='https://'+p.HOST,workspace_id=None,authenticate=lambda:{})
   state=Path(tmp).resolve();http=Http();run=lambda:p.Operator167(root,state,review,config_factory=lambda:cfg,session=http,clock=lambda:now).run()
   result=run();self.assertEqual((http.run_count,http.imports),(1,2));self.assertEqual(result['run_id'],123456)
   config=p.DriverConfig.from_dict(p.safe_json(state/'driver-config167.json'));delivery=p.safe_json(state/'delivery167.json');record=p.safe_json(state/'authority167.json')
   widgets={'job_id':str(p.JOB),'run_id':'123456','request_id':delivery['request_token'],'release_id':config.writer.release_id,'snapshot_backend_id':config.writer.snapshot_backend_id}
   verifier=a.AttestedWriterVerifier167(config,delivery,widgets,clock=lambda:now);self.assertTrue(verifier.accept_source(http.source))
   policy=(state/'policy167.json').read_bytes();run();self.assertEqual((http.run_count,http.imports),(1,2));self.assertEqual(policy,(state/'policy167.json').read_bytes())
   from unittest.mock import patch
   http.writer_mode=True
   archive=root/'runs/sk12-writer-portable-105.tar.gz'
   self.assertEqual(a.sha(archive.read_bytes()),delivery['archive_sha256'])
   with tempfile.TemporaryDirectory() as portable:
    with tarfile.open(archive) as bundle:bundle.extractall(portable,filter='data')
    portable_root=Path(portable)/'sbs-radar'
    captured_run=copy.deepcopy(json.loads((root/'deployment/state/writer-monitor156/result.json').read_bytes())['raw_run']);captured_run['job_id']=p.JOB;captured_run['run_id']=123456;captured_run['state']['life_cycle_state']='RUNNING'
    data={'delivery':delivery,'config':p.safe_json(state/'driver-config167.json'),'widgets':widgets,'source_base64':base64.b64encode(http.source).decode(),'observed':observed,'run':captured_run,'control':http.control,'revision':http.revision}
    fp=Path(portable)/'fixture.json';fp.write_text(json.dumps(data));output=Path(portable)/'result.json'
    child=subprocess.run([sys.executable,'-I',str(root/'tests/unit/writer_portable_167_child.py'),str(portable_root),str(fp),str(output)],cwd=portable,capture_output=True,text=True,timeout=90)
    self.assertEqual(child.returncode,0,child.stdout+child.stderr)
    proof=json.loads(output.read_bytes());self.assertEqual(proof['status'],'published');self.assertFalse(proof['cloud']);self.assertGreater(proof['artifact_files'],0)
    print('portable167_child_proof',json.dumps(proof,sort_keys=True))
   self.assertEqual(http.run_count,1);self.assertEqual(http.imports,2)
   self.assertFalse(any(m in ('PATCH','DELETE') or path.endswith('/start') or path.endswith('/jobs/update') for m,path in http.calls));print('operator167_budget',result['budget'],p.safe_json(state/'budget.json'))
