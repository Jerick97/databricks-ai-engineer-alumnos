"""Regression: an otherwise green closure must reject missing live/teacher proof.

Runs the production CLI in an isolated fixture, never touching real reports/cloud.
Removing either new gate makes its negative acceptance tests fail.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ClosureGatesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for folder in ['scripts', 'reports', 'lab']:
            (self.root / folder).mkdir()
        shutil.copyfile(ROOT / 'scripts/close_validation.py', self.root / 'scripts/close_validation.py')
        for name in ['notebook.py', 'notebook-docente.py', 'lab/agent.py', 'slides.html']:
            (self.root / name).write_text(name)
        self.sha = lambda name: hashlib.sha256((self.root / name).read_bytes()).hexdigest()
        for judge in ['curriculum', 'pedagogy', 'execution']:
            self.write(judge + '-judge.json', {'verdict': 'PASS', 'scope': 'full-session', 'artifact_hashes': {'notebook.py': self.sha('notebook.py')}})
        self.write('coverage-judge.json', {'verdict': 'PASS'})
        for name in ['visual-qa', 'structural-qa', 'material-audit', 'lab-app-http', 'app-visual', 'lab-monitor-verified', 'lab-custom-canary-verified', 'lab-custom-rollback-verified']:
            self.write(name + '.json', {'pass': True, 'artifact_hashes': {'slides.html': self.sha('slides.html')}})
        self.write('notebook-observed.json', {'pass': True, 'notebook_sha256': self.sha('notebook.py')})
        for name, count in [('lab-smoke-local', 6), ('lab-smoke-serving', 6), ('lab-security-smoke', 3)]:
            self.write(name + '.json', [{'pass': True, 'served_model_version': '4'}] * count)
        self.write('lab-unit-tests.json', {'status': 'PASS', 'tests': 14})
        self.write('lab-artifact-check.json', {'source_matches': True, 'sha256': self.sha('lab/agent.py'), 'version': '4'})
        self.write('lab-package.json', {'version': '4'})
        (self.root / 'requirements.json').write_text(json.dumps({'requirements': [{'required': True, 'status': 'satisfied'}]}))
        self.write('class-day-browser.json', {'live_browser_flow_pass': True})
        self.teacher = {'verdict': 'PASS', 'artifact_hashes': {'notebook-docente.py': self.sha('notebook-docente.py')}}
        self.write('teacher-delivery-judge.json', self.teacher)

    def write(self, name, value):
        (self.root / 'reports' / name).write_text(json.dumps(value))

    def run_closure(self):
        result = subprocess.run([sys.executable, str(self.root / 'scripts/close_validation.py')], capture_output=True, text=True)
        self.assertIn(result.returncode, [0, 1], result.stderr)
        return result.returncode, json.loads((self.root / 'reports/closure.json').read_text())

    def assert_rejected(self):
        code, report = self.run_closure()
        self.assertFalse(report['class_ready'])
        self.assertEqual(code, 1)

    def test_accepts_all_required_proof(self):
        code, report = self.run_closure()
        self.assertTrue(report['class_ready'])
        self.assertEqual(code, 0)

    def test_missing_browser_report_rejected(self):
        (self.root / 'reports/class-day-browser.json').unlink()
        self.assert_rejected()

    def test_http_pass_is_not_browser_proof(self):
        self.write('class-day-browser.json', {'http_pass': True})
        self.assert_rejected()

    def test_browser_false_or_truthy_string_rejected(self):
        for value in [False, 'true', 1, None]:
            with self.subTest(value=value):
                self.write('class-day-browser.json', {'live_browser_flow_pass': value})
                self.assert_rejected()

    def test_missing_teacher_judge_rejected(self):
        (self.root / 'reports/teacher-delivery-judge.json').unlink()
        self.assert_rejected()

    def test_teacher_nonpass_rejected(self):
        self.teacher['verdict'] = 'FAIL'
        self.write('teacher-delivery-judge.json', self.teacher)
        self.assert_rejected()

    def test_teacher_missing_hash_rejected(self):
        self.teacher['artifact_hashes'] = {}
        self.write('teacher-delivery-judge.json', self.teacher)
        self.assert_rejected()

    def test_changed_teacher_notebook_rejected(self):
        (self.root / 'notebook-docente.py').write_text('changed after review')
        self.assert_rejected()

    def test_missing_teacher_notebook_rejected(self):
        (self.root / 'notebook-docente.py').unlink()
        self.assert_rejected()


if __name__ == '__main__':
    unittest.main()
