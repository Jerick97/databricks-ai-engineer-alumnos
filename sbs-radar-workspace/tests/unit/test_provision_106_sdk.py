"""In-memory HTTP fixture exercises the real SDK serializers, never production evidence."""
from pathlib import Path
from types import SimpleNamespace
from io import BytesIO
import base64,json,tempfile,time,unittest
from sbs.operations.provision_106 import Provisioner,LIMITS,TABLE,PRINCIPAL,WAREHOUSE,VOLUME,SELECT,review_inputs,HOST,OWNER,OWNER_ID,notebook_source
from sbs.operations.provision_105 import control_steps
from sbs.operations.shared_control import initial_state
ROOT=Path(__file__).resolve().parents[2]
class MemoryHttp:
 def __init__(self):
  self.adapters={};self.table=False;self.seed=False;self.grant=False;self.directory=False;self.workspace_dir=False;self.notebooks={};self.files={};self.job=None;self.nb_acl=False;self.calls=[]
 def request(self,method,url,*,params,json,data,**kwargs):
  p=url.split(HOST,1)[1];self.calls.append((method,p,json));status=200;body={};raw=None
  if p.endswith('/Me'):body={'userName':OWNER,'id':OWNER_ID,'active':True}
  elif '/ServicePrincipals/' in p:body={'id':'72803555975940','applicationId':PRINCIPAL,'active':True}
  elif '/warehouses/' in p:body={'id':WAREHOUSE,'state':'RUNNING'}
  elif '/volumes/' in p:body={'full_name':VOLUME}
  elif '/tables/' in p:
   if not self.table:status=404;body={'error_code':'TABLE_DOES_NOT_EXIST'}
   else:body={'full_name':TABLE,'table_id':'fixture-observed-table-id','table_type':'MANAGED','data_source_format':'DELTA','owner':OWNER,'properties':{'delta.isolationLevel':'Serializable'},'columns':[{'name':n,'type_name':t,'nullable':False} for n,t in [('control_id','STRING'),('revision','LONG'),('state_json','STRING')]]}
  elif p=='/api/2.0/sql/statements':
   statement=json['statement'];body={'statement_id':'fixture-statement','status':{'state':'SUCCEEDED'}}
   if statement==control_steps()[0]['payload']['statement']:self.table=True
   elif statement==control_steps()[1]['payload']['statement']:self.seed=True
   elif statement==SELECT:
    rows=[['control','0',__import__('json').dumps(initial_state())]] if self.seed else []
    body.update(manifest={'format':'JSON_ARRAY','truncated':False,'total_row_count':len(rows),'total_chunk_count':1,'schema':{'columns':[{'name':n,'type_name':t} for n,t in [('control_id','STRING'),('revision','LONG'),('state_json','STRING')]]}},result={'data_array':rows,'row_count':len(rows),'row_offset':0,'chunk_index':0})
   else:raise AssertionError(statement)
  elif '/permissions/table/' in p:
   if method=='PATCH':self.grant=True
   body={'privilege_assignments':[{'principal':PRINCIPAL,'privileges':['SELECT','MODIFY']}] if self.grant else []}
  elif '/fs/directories' in p:
   if method=='PUT':self.directory=True
   elif not self.directory:status=404;body={'error_code':'RESOURCE_DOES_NOT_EXIST'}
  elif '/fs/files' in p:
   if method=='PUT':self.files[p]=data.read()
   elif p not in self.files:status=404;body={'error_code':'RESOURCE_DOES_NOT_EXIST'}
   else:raw=self.files[p]
  elif p.endswith('/workspace/get-status'):
   path=params['path']
   if path=='/Shared/sbs-radar' and self.workspace_dir:body={'path':path,'object_type':'DIRECTORY','object_id':77}
   elif path in self.notebooks:body={'path':path,'object_type':'NOTEBOOK','object_id':88}
   else:status=404;body={'error_code':'RESOURCE_DOES_NOT_EXIST'}
  elif p.endswith('/workspace/mkdirs'):self.workspace_dir=True
  elif p.endswith('/workspace/import'):self.notebooks[json['path']]=base64.b64decode(json['content'])
  elif p.endswith('/workspace/export'):body={'content':base64.b64encode(self.notebooks[params['path']]).decode()}
  elif '/permissions/notebooks/' in p:
   if method=='PATCH':self.nb_acl=True
   body={'access_control_list':[{'service_principal_name':PRINCIPAL,'all_permissions':[{'permission_level':'CAN_READ'}]}] if self.nb_acl else []}
  elif p.endswith('/jobs/list'):body={'jobs':[{'job_id':99}] if self.job else [],'has_more':False}
  elif p.endswith('/jobs/create'):self.job=dict(json);self.job.pop('access_control_list');body={'job_id':99}
  elif p.endswith('/jobs/get'):body={'job_id':99,'settings':self.job,'run_as_user_name':PRINCIPAL}
  elif '/permissions/jobs/' in p:body={'object_id':'/jobs/99','access_control_list':[{'user_name':OWNER,'all_permissions':[{'permission_level':'IS_OWNER'}]},{'service_principal_name':PRINCIPAL,'all_permissions':[{'permission_level':'CAN_MANAGE_RUN'}]}]}
  else:raise AssertionError((method,p))
  raw=raw if raw is not None else __import__('json').dumps(body).encode()
  return SimpleNamespace(status_code=status,headers={'content-length':str(len(raw)),'content-type':'application/octet-stream'},raw=SimpleNamespace(read=lambda *a,**kw:raw),close=lambda:None)
 def close(self):pass

class SDKProvision106(unittest.TestCase):
 def test_concrete_pipeline_paused_with_real_sdk_serializers(self):
  with tempfile.TemporaryDirectory() as tmp:
   now=int(time.time()*1000);review={'approved':True,'scope':'provision106','issued_at_ms':now-1000,'expires_at_ms':now+300000,'writer_mode':'preflight','limits':LIMITS,'files':review_inputs(ROOT)}
   session=MemoryHttp();cfg=SimpleNamespace(host='https://'+HOST,workspace_id=None,authenticate=lambda:{})
   p=Provisioner(ROOT,Path(tmp).resolve(),review,config_factory=lambda:cfg,session=session)
   result=p.run()
   self.assertEqual(result['status'],'provisioned_paused_not_run');self.assertEqual(result['job_id'],99)
   self.assertEqual(session.job['schedule']['pause_status'],'PAUSED')
   self.assertEqual(sum(path.endswith('/jobs/create') for _,path,_ in session.calls),1)
   self.assertFalse(any('/run-now' in path or '/start' in path for _,path,_ in session.calls))
   self.assertFalse(result['cloud_acceptance'])
   original_job=json.loads(json.dumps(session.job));original_files=dict(session.files);initial_writes=sum(m!='GET' and m!='HEAD' and not (b and b.get('statement')==SELECT) for m,_,b in session.calls)
   revised={**review,'issued_at_ms':now,'expires_at_ms':now+400000}
   resumed=Provisioner(ROOT,Path(tmp).resolve(),revised,config_factory=lambda:cfg,session=session).run()
   self.assertEqual(resumed['config_sha256'],result['config_sha256'])
   self.assertEqual(session.job,original_job);self.assertEqual(session.files,original_files)
   self.assertEqual(sum(m!='GET' and m!='HEAD' and not (b and b.get('statement')==SELECT) for m,_,b in session.calls),initial_writes)
   config_file=Path(tmp)/'fixture-config.json';config_file.write_bytes(session.files['/api/2.0/fs/files'+result['config_path']])
   package=json.loads((ROOT/'runs/sk12-writer-portable-105.json').read_bytes())
   source=notebook_source(archive_path=str(ROOT/package['archive']),archive_sha=package['archive_sha256'],manifest_path=package['release_manifest'],release_id=package['release_id'],config_path=str(config_file),config_sha=result['config_sha256'],mode='preflight')
   exec(compile(source,'fixture-writer106','exec'),{})

   executable=Provisioner(ROOT,Path(tmp).resolve(),{**revised,'writer_mode':'execute'},writer_mode='execute',config_factory=lambda:cfg,session=session).run()
   self.assertEqual(executable['writer_mode'],'execute')
   for code in session.notebooks.values():compile(code,'fixture-execute-writer106','exec')
   self.assertEqual(session.job['schedule']['pause_status'],'PAUSED')
   self.assertEqual(sum(path.endswith('/jobs/create') for _,path,_ in session.calls),1)
   budget=json.loads((Path(tmp)/'budget.json').read_bytes());self.assertLessEqual(budget['mutations'],LIMITS['mutations'])
   print('fixture_only_cumulative_budget',budget)
if __name__=='__main__':unittest.main()
