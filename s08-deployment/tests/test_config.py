import importlib.util
from pathlib import Path
import unittest
P=Path(__file__).resolve().parents[1]/'lab/lab_config.py'
class ConfigTests(unittest.TestCase):
 def helper(self):
  self.assertTrue(P.exists(),'Missing shared, isolated configuration helper')
  spec=importlib.util.spec_from_file_location('lab_config',P);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
 def test_students_get_distinct_endpoint_app_and_schema(self):
  m=self.helper();base={'endpoint':'ais08-neptuno','app_name':'ais08-neptuno-ui','schema':'ais08_lab'}
  a=m.build_config(base,'mi_catalogo','warehouse','alice');b=m.build_config(base,'mi_catalogo','warehouse','bob')
  for key in ['endpoint','app_name','schema','model_name']:self.assertNotEqual(a[key],b[key])
  self.assertEqual(base['endpoint'],'ais08-neptuno')
 def test_explicit_teacher_reuse_and_identifiers(self):
  m=self.helper();a=m.build_config({},'neptuno','w','teacher',suffix='neptuno',schema='ais08_lab')
  self.assertEqual(a['endpoint'],'ais08-neptuno');self.assertEqual(a['schema'],'ais08_lab')
  with self.assertRaises(ValueError):m.build_config({},'bad;drop','w','a')
  with self.assertRaises(ValueError):m.build_config({},'ok','w','a',suffix='../bad')
if __name__=='__main__':unittest.main()
