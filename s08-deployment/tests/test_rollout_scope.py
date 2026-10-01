"""Un snapshot docente/alumno ajeno nunca se restaura en otro workspace."""
import ast
from pathlib import Path
import unittest
source=Path(__file__).resolve().parents[1]/'lab/lab_rollout.py'
tree=ast.parse(source.read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='validate_snapshot')
ns={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'snapshot_boundary','exec'),ns)
class SnapshotTests(unittest.TestCase):
    def snapshot(self):return {'endpoint':'ais08-a-rollout','workspace_host':'https://workspace-a','model_name':'catalog.ais08_a.ventas_rollout','served_entities':[{'entity_name':'catalog.ais08_a.ventas_rollout'}]}
    def test_own_snapshot_allowed(self):ns['validate_snapshot'](self.snapshot(),'ais08-a-rollout','https://workspace-a','catalog.ais08_a.ventas_rollout')
    def test_other_workspace_rejected(self):
        with self.assertRaises(ValueError):ns['validate_snapshot'](self.snapshot(),'ais08-a-rollout','https://workspace-b','catalog.ais08_a.ventas_rollout')
    def test_foreign_entity_rejected(self):
        s=self.snapshot();s['served_entities'][0]['entity_name']='other.model'
        with self.assertRaises(ValueError):ns['validate_snapshot'](s,'ais08-a-rollout','https://workspace-a','catalog.ais08_a.ventas_rollout')
if __name__=='__main__':unittest.main()
