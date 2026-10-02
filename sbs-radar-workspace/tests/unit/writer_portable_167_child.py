"""Isolated -I child: no workspace imports; fixture transport, exact embedded module."""
import sys,json,base64,hashlib,types,copy
from pathlib import Path
from unittest.mock import patch
root=Path(sys.argv[1]).resolve();fixture=json.loads(Path(sys.argv[2]).read_bytes())
assert not any(k=='sbs' or k.startswith('sbs.') for k in sys.modules)
sys.path.insert(0,str(root/'src'))
from sbs.operations.cloud_driver import DriverConfig
D=fixture['delivery'];module_raw=base64.b64decode(D['module_base64'],validate=True)
assert hashlib.sha256(module_raw).hexdigest()==D['module_sha256']
module=types.ModuleType('sbs_writer_authority167');sys.modules[module.__name__]=module
exec(compile(module_raw,'writer-authority167','exec'),module.__dict__)
config=DriverConfig.from_dict(fixture['config'])
class Http:
 adapters={}
 def __init__(self):self.files={};self.control=fixture['control'];self.revision=fixture['revision'];self.calls=[]
 def close(self):pass
 def request(self,m,url,**kw):
  path=url.split('https://dbc-0410b264-20c7.cloud.databricks.com')[1];body=kw.get('json');self.calls.append((m,path));status=200;v={};raw=None
  assert m in ('GET','PUT','POST')
  if path.endswith('/Me'):v=fixture['observed']['Me']
  elif path.endswith('/jobs/get'):v=fixture['observed']['job']
  elif path.endswith('/workspace/get-status'):v={'object_id':3178573112927427,'path':config.writer.notebook_path,'object_type':'NOTEBOOK'}
  elif path.endswith('/workspace/export'):v={'content':fixture['source_base64']}
  elif '/unity-catalog/tables/' in path:v=fixture['observed']['table']
  elif '/sql/warehouses/' in path:v={**fixture['observed']['warehouse'],'state':'RUNNING'}
  elif '/fs/directories/' in path:assert m=='PUT'
  elif '/fs/files/' in path:
   if m=='PUT':self.files[path]=kw['data'].read()
   elif path not in self.files:status=404;v={'error_code':'RESOURCE_DOES_NOT_EXIST'}
   else:raw=self.files[path]
  elif path=='/api/2.0/sql/statements':
   assert m=='POST'
   if body['statement'].startswith('UPDATE'):
    params={v['name']:v['value'] for v in body['parameters']}
    assert params['control']=='control' and int(params['revision'])==self.revision
    self.control=json.loads(params['state']);self.revision+=1;v={'statement_id':'statement1','status':{'state':'SUCCEEDED'}}
   else:v={'statement_id':'statement1','status':{'state':'SUCCEEDED'},'manifest':{'format':'JSON_ARRAY','truncated':False,'total_row_count':1,'total_chunk_count':1,'schema':{'columns':[{'name':'control_id','type_name':'STRING'},{'name':'revision','type_name':'LONG'},{'name':'state_json','type_name':'STRING'}]}},'result':{'data_array':[['control',str(self.revision),json.dumps(self.control)]],'chunk_index':0,'row_offset':0,'row_count':1}}
  elif path.endswith('/jobs/runs/get'):v=fixture['run']
  else:raise AssertionError((m,path))
  raw=raw if raw is not None else json.dumps(v).encode()
  return types.SimpleNamespace(status_code=status,headers={'content-length':str(len(raw))},raw=types.SimpleNamespace(read=lambda *a,**k:raw),close=lambda:None)
http=Http();cfg=types.SimpleNamespace(host='https://dbc-0410b264-20c7.cloud.databricks.com',workspace_id=None,authenticate=lambda:{})
with patch('databricks.sdk.core.Config',return_value=cfg),patch('requests.Session',return_value=http),patch('socket.socket.connect',side_effect=AssertionError('NETWORK_FORBIDDEN')):
 result=module.execute_from_config167(config,root,delivery=D,widgets=fixture['widgets'])
assert result['status']=='published',result
assert result['cloud_acceptance'] is False and http.control['current']['run_id']==123456
imports={}
for name,m in list(sys.modules.items()):
 if name=='sbs' or name.startswith('sbs.'):
  path=Path(m.__file__).resolve();assert path.is_relative_to(root/'src'),(name,path)
  imports[name]={'path':str(path.relative_to(root)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
assert imports and http.files
Path(sys.argv[3]).write_text(json.dumps({'status':result['status'],'cloud':False,'source':'extracted105_only','embedded_module_sha256':D['module_sha256'],'imports':imports,'transport':result['writer_transport'],'counts':result['counts'],'artifact_files':len(http.files)},indent=2)+'\n')
