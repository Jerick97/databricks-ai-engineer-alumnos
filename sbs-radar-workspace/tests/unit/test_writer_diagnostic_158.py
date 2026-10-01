import unittest,tempfile,time,json,base64
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from sbs.operations import writer_diagnostic_158 as p
class Diagnostic158(unittest.TestCase):
 def test_diagnostic_notebook_exact_five_get_raw_no_headers(self):
  calls=[];outputs=[]
  class Http:
   adapters={}
   def close(self):pass
   def request(self,m,url,**kw):
    assert m=='GET';calls.append(url);raw=json.dumps({'raw_stage':url.split('/api/')[1]}).encode()
    return SimpleNamespace(status_code=403 if len(calls)==3 else 200,headers={'Authorization':'SECRET','x-request-id':'fixture'},raw=SimpleNamespace(read=lambda *a,**k:raw),close=lambda:None)
  cfg=SimpleNamespace(host='https://'+p.HOST,authenticate=lambda:{'Authorization':'SECRET'})
  dbutils=SimpleNamespace(widgets=SimpleNamespace(get=lambda k:str(p.JOB if k=='job_id' else 123)),notebook=SimpleNamespace(exit=outputs.append))
  with patch('databricks.sdk.core.Config',return_value=cfg),patch('requests.Session',return_value=Http()):exec(compile((p.ROOT/p.SOURCE).read_bytes(),'notebook158','exec'),{'dbutils':dbutils})
  report=json.loads(outputs[0]);self.assertEqual(report['cloud_calls'],5);self.assertEqual(report['observations'][2]['http_status'],403);self.assertEqual(len(report['observations']),5);self.assertNotIn('SECRET',outputs[0]);self.assertEqual(report['mutations'],0)
 def test_full_import_run_and_resume_no_second_mutation(self):
  prior=next((p.ROOT/'deployment/state/policy-binding146/notebook146').glob('*.intent.json'));old=p.safe_json(prior)['step']['payload']['content'];job=p.safe_json(p.ROOT/'runs/sk11-job-settings-146.json')
  class Http:
   adapters={}
   def __init__(self):self.source=old;self.imports=0;self.runs=0
   def request(self,m,url,**kw):
    path=url.split(p.HOST)[1]
    if path.endswith('/Me'):v={'id':p.OWNER_ID,'userName':p.OWNER,'active':True}
    elif path.endswith('/jobs/get'):v=job
    elif '/permissions/jobs/' in path:v={'object_id':'/jobs/'+str(p.JOB),'access_control_list':[{'user_name':p.OWNER,'all_permissions':[{'permission_level':'IS_OWNER'}]},{'service_principal_name':job['run_as_user_name'],'all_permissions':[{'permission_level':'CAN_MANAGE_RUN'}]}]}
    elif path.endswith('/workspace/get-status'):v={'path':p.NOTEBOOK,'object_id':p.NBID}
    elif '/permissions/notebooks/' in path:v={'object_id':'/notebooks/'+str(p.NBID),'access_control_list':[{'user_name':p.OWNER,'all_permissions':[{'permission_level':'CAN_MANAGE'}]},{'service_principal_name':job['run_as_user_name'],'all_permissions':[{'permission_level':'CAN_READ'}]}]}
    elif path.endswith('/workspace/export'):v={'content':self.source}
    elif path.endswith('/workspace/import'):self.source=kw['json']['content'];self.imports+=1;v={}
    elif path.endswith('/jobs/run-now'):self.runs+=1;v={'run_id':999}
    else:raise AssertionError(path)
    raw=json.dumps(v).encode();return SimpleNamespace(status_code=200,headers={},raw=SimpleNamespace(read=lambda *a,**k:raw),close=lambda:None)
  with tempfile.TemporaryDirectory() as d:
   now=int(time.time()*1000);review={'approved':True,'scope':'writer_diagnostic158_one_import_one_run','issued_at_ms':now-1000,'expires_at_ms':now+600000,'limits':p.LIMITS,'files':p.inputs()};cfg=SimpleNamespace(host='https://'+p.HOST,authenticate=lambda:{})
   state=Path(d).resolve();http=Http();run=lambda:p.Diagnostic158(p.ROOT,state,review,config_factory=lambda:cfg,session=http).run()
   result=run();self.assertEqual(result['run_id_candidate'],999);self.assertEqual(result['budget'],{'get':7,'import':1,'run':1});run();self.assertEqual((http.imports,http.runs),(1,1));self.assertEqual(p.safe_json(state/'restore146-payload.json')['content'],old)
