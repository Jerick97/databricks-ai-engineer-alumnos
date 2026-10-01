import unittest,tempfile
from pathlib import Path
from types import SimpleNamespace
from sbs.operations.provision_106 import validate_table,validate_rows,notebook_source,ScopedApi,HOST

class Provision106(unittest.TestCase):
 def test_table_needs_actual_id_and_exact_schema(self):
  with self.assertRaisesRegex(ValueError,'TABLE_METADATA_INVALID'):validate_table({},owner='operator')
 def test_rows_reject_extra_and_wrong_state(self):
  with self.assertRaises(ValueError):validate_rows({'manifest':{},'result':{}},empty=False)
 def test_zero_chunk_empty_select_is_verified_without_seed(self):
  r={'manifest':{'format':'JSON_ARRAY','truncated':False,'total_row_count':0,'total_chunk_count':0,'schema':{'columns':[{'name':n,'type_name':t} for n,t in [('control_id','STRING'),('revision','BIGINT'),('state_json','STRING')]]}}}
  self.assertEqual(validate_rows(r,empty=True)['rows'],0)
  with self.assertRaises(ValueError):validate_rows(r,empty=False)
  r['result']={'external_links':['forbidden']}
  with self.assertRaises(ValueError):validate_rows(r,empty=True)
 def test_transport_rejects_out_of_scope_even_with_permit(self):
  with tempfile.TemporaryDirectory() as tmp:
   session=SimpleNamespace(adapters={},request=lambda *a,**k:self.fail('request sent'))
   api=ScopedApi(SimpleNamespace(host='https://'+HOST),journal=Path(tmp).resolve(),authorize=lambda:None,prefix='/Volumes/fixed',session=session)
   with self.assertRaisesRegex(ValueError,'MUTATION_OUTSIDE_SCOPE'):
    api.with_permit('POST','/api/2.0/sql/statements',{'statement':'DROP TABLE x'},lambda:api.do('POST','/api/2.0/sql/statements',body={'statement':'DROP TABLE x'}))
   self.assertEqual(list(Path(tmp).iterdir()),[])
 def test_wrong_workspace_blocked_before_authentication(self):
  with self.assertRaisesRegex(ValueError,'HOST_INVALID'):
   ScopedApi(SimpleNamespace(host='https://other.example'),journal=Path('/tmp'),authorize=lambda:None,prefix='/Volumes/fixed')
 def test_notebook_pins_bundle_and_configuration_without_env(self):
  code=notebook_source(archive_path='/Volumes/neptuno_manuel_arguelles/sbs_radar/release_artifacts/sbs-refresh/bootstrap106/code.tar.gz',archive_sha='a'*64,manifest_path='deployment/writer-code-manifest-105.json',release_id='b'*64,config_path='/Volumes/neptuno_manuel_arguelles/sbs_radar/release_artifacts/sbs-refresh/bootstrap106/driver.json',config_sha='c'*64,mode='preflight')
  compile(code,'writer106','exec')
  self.assertIn('execute_from_config',code)
  self.assertIn('a'*64,code)
  self.assertNotIn('os.environ',code)
if __name__=='__main__':unittest.main()
