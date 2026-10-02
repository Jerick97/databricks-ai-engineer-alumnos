from pathlib import Path
import json,sys,types,unittest
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'lab'))
from lab_config import build_config
class Widgets:
 def __init__(self):self.values={}
 def text(self,name,default,label):self.values[name]=default
 def dropdown(self,name,default,choices,label):self.values[name]=default
class TeacherDefaultsTest(unittest.TestCase):
 def test_teacher_opens_without_job_overrides(self):
  source=R/'notebook-docente.py'
  self.assertTrue(source.exists(),'Falta copia docente ejecutable con widgets preconfigurados')
  cells=source.read_text().split('# COMMAND ----------')
  widgets=Widgets();exec(cells[1],{'dbutils':types.SimpleNamespace(widgets=widgets)})
  v=widgets.values;base=json.loads((R/'lab/config.json').read_text())
  actual=build_config(base,v['catalogo'],v['warehouse_id'],'teacher',v['sufijo'],v['esquema'])
  for key in ['catalog','warehouse_id','schema','endpoint','app_name','model_name']:self.assertEqual(actual[key],base[key])
  self.assertEqual(v['modo'],'verificar');self.assertEqual(v['rollout'],'inspeccionar')
  self.assertEqual(v['s07_schema'],base['approved_schema'])
if __name__=='__main__':unittest.main()
