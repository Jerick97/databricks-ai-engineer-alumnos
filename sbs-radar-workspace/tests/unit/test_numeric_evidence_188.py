import unittest,json,hashlib,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
class PairedEvidence188(unittest.TestCase):
 def test_exact_input_model_and_unchanged_remote_evidence(self):
  paired=json.loads((ROOT/'runs/sk05-sk09-numeric-188-paired-result.json').read_bytes());path=ROOT/'deployment/state/linux-canary-continue-185/capture178/linux-report.json';raw=json.loads(path.read_bytes())
  self.assertEqual(paired['remote_report_sha256'],hashlib.sha256(path.read_bytes()).hexdigest())
  self.assertEqual(paired['full_rows_sha256'],raw['smoke_input_sha256']);self.assertTrue(paired['same_full_input'])
  self.assertEqual(paired['identity']['weights_sha256'],raw['cpu_execution']['weights_sha256']);self.assertEqual(paired['source133_sha256'],raw['source133_sha256'])
  self.assertEqual(raw['numeric_comparison']['status'],'not_evaluated');self.assertFalse(raw['numeric_comparison']['same_input'])
 def test_exact_paired_deltas_fail_original_threshold(self):
  p=json.loads((ROOT/'runs/sk05-sk09-numeric-188-paired-result.json').read_bytes());r=json.loads((ROOT/'deployment/state/linux-canary-continue-185/capture178/linux-report.json').read_bytes())
  self.assertEqual(len(p['scores']),len(r['scores']));self.assertEqual(len(p['scores']),2)
  self.assertTrue(all(math.isfinite(v) for v in p['scores']+r['scores']))
  self.assertEqual(p['absolute_deltas'],[abs(a-b) for a,b in zip(p['scores'],r['scores'])]);self.assertEqual(p['tolerance'],.001)
  self.assertTrue(all(d>.001 for d in p['absolute_deltas']));self.assertFalse(p['numeric_pass']);self.assertEqual(p['status'],'FAIL_PAIRED_NUMERIC_SMOKE')
  self.assertEqual(p['cloud_calls'],0);self.assertEqual(p['provider_inference_calls'],0)
