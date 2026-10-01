import unittest,tempfile,importlib.util,json
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('app153',ROOT/'deployment/app_candidate_153.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class App153(unittest.TestCase):
 def test_deadline_and_absent_linux_gate_do_not_create(self):
  with tempfile.TemporaryDirectory() as d:
   dest=Path(d)/'out'
   with self.assertRaisesRegex(ValueError,'ABSOLUTE_DEADLINE_REQUIRED'):m.materialize('unused',dest,linux_evidence='absent',linux_sha='x',expires_at=0)
   self.assertFalse(dest.exists())
   with self.assertRaises(FileNotFoundError):m.gates(ROOT,Path(d)/'missing','x')
 def test_non_linux_report_never_accepted(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'fake';p.write_text(json.dumps({'status':'PASS_LINUX_CANARY_RUNTIME_ONLY','source133_sha256':m.BASE_SHA,'platform':{'system':'Darwin','python':'3.11.9','machine':'arm64'}}))
   with self.assertRaisesRegex(ValueError,'LINUX_PLATFORM_REQUIRED'):m.gates(ROOT,p,m.sha(p.read_bytes()))
 def test_candidate_config_closure_and_materialized_diff(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);template=root/'template';candidate=m.prepare(template)
   self.assertEqual(candidate['deadline_unix'],0);self.assertFalse(candidate['linux_verified'])
   source=template/'source';app=m.read(source/'app.yaml');self.assertEqual(app['command'],['python','app133.py']);self.assertEqual({e['name']:e['value'] for e in app['env']}['WEB_CONCURRENCY'],'1')
   self.assertEqual((source/'deployment/requirements-app.txt').read_bytes(),(ROOT/'runs/sk12-linux-installed.txt').read_bytes())
   with patch.object(m,'gates',return_value={'fixture_only':True}):
    out=m.materialize(template,root/'material',linux_evidence='fixture',linux_sha='fixture',expires_at=1900,clock=lambda:1000)
   changed=[p for p,h in candidate['files_sha256'].items() if out['files_sha256'][p]!=h];self.assertEqual(changed,['config/app-integration-133.json'])
   self.assertEqual(m.read(source/'config/app-integration-133.json')['deadline_unix'],0)
   self.assertEqual(m.read(root/'material/source/config/app-integration-133.json')['deadline_unix'],1900)
   self.assertFalse(out['m2m_verified']);self.assertEqual(m.verify(root/'material'),out)
