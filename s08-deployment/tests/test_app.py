"""UI fronteras: reintento y escaping antes de tocar Serving."""
import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('ais08_app',Path(__file__).resolve().parents[1]/'app/app.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class AppTests(unittest.TestCase):
    def test_empty_input_keeps_form(self):
        r=module.app.test_client().post('/',data={'question':''})
        self.assertEqual(r.status_code,400);self.assertIn(b'<form',r.data)
    def test_rejected_html_is_escaped(self):
        r=module.app.test_client().post('/',data={'question':'<script>alert(1)</script>'+'a'*2000})
        self.assertEqual(r.status_code,400);self.assertIn(b'&lt;script&gt;',r.data);self.assertNotIn(b'<script>alert(1)</script>',r.data)
if __name__=='__main__':unittest.main()
