import tempfile, unittest
from pathlib import Path
from sbs.operations.provision_105 import step_once, creation_settings, control_steps

class Provision105(unittest.TestCase):
    def test_unknown_never_resends(self):
        with tempfile.TemporaryDirectory() as d:
            calls=[]
            def effect(payload):
                calls.append(payload); raise TimeoutError('secret')
            step=control_steps()[0]
            result=step_once(Path(d).resolve(),step,authorize=lambda:None,observe=lambda:None,effect=effect)
            self.assertEqual(result['status'],'outcome_unknown')
            result=step_once(Path(d).resolve(),step,authorize=lambda:None,observe=lambda:None,effect=effect)
            self.assertEqual(len(calls),1)
            self.assertNotIn('secret',repr(result))
    def test_confirmation_requires_readback(self):
        with tempfile.TemporaryDirectory() as d:
            seen=iter([None,{'table_id':'observed'}])
            r=step_once(Path(d).resolve(),control_steps()[0],authorize=lambda:None,observe=lambda:next(seen),effect=lambda _: {'table_id':'response_only'})
            self.assertEqual(r['observation'],{'table_id':'observed'})
    def test_denied_has_no_intent_or_effect(self):
        with tempfile.TemporaryDirectory() as d:
            def deny(): raise ValueError('DENIED')
            with self.assertRaisesRegex(ValueError,'DENIED'):
                step_once(Path(d).resolve(),control_steps()[0],authorize=deny,observe=lambda:None,effect=lambda _:self.fail())
            self.assertEqual(list(Path(d).iterdir()),[])
    def test_changed_payload_cannot_retry_step(self):
        with tempfile.TemporaryDirectory() as d:
            step=control_steps()[0]
            step_once(Path(d).resolve(),step,authorize=lambda:None,observe=lambda:None,effect=lambda _:None)
            step['payload']['statement']='changed'
            with self.assertRaisesRegex(ValueError,'STEP_PLAN_CONFLICT'):
                step_once(Path(d).resolve(),step,authorize=lambda:None,observe=lambda:None,effect=lambda _:self.fail())
    def test_observation_error_blocks_effect(self):
        with tempfile.TemporaryDirectory() as d:
            def fail(): raise ValueError('GET_UNAVAILABLE')
            with self.assertRaisesRegex(ValueError,'GET_UNAVAILABLE'):
                step_once(Path(d).resolve(),control_steps()[0],authorize=lambda:None,observe=fail,effect=lambda _:self.fail())
    def test_window_expiry_after_intent_never_sends(self):
        with tempfile.TemporaryDirectory() as d:
            checks=[]
            def auth():
                checks.append(1)
                if len(checks)==3: raise ValueError('EXPIRED')
            r=step_once(Path(d).resolve(),control_steps()[0],authorize=auth,observe=lambda:None,effect=lambda _:self.fail())
            self.assertEqual(r['status'],'outcome_unknown')
            self.assertEqual(len(list(Path(d).glob('*.intent.json'))),1)
    def test_creation_has_no_fake_job_id(self):
        s=creation_settings(notebook_path='/Shared/sbs-radar/writer',release_id='a'*64,snapshot_backend_id='b'*64,boundary_policy_id='c'*64)
        self.assertNotIn('job_id',s)
        self.assertEqual(s['schedule']['pause_status'],'PAUSED')
        self.assertEqual(s['run_as']['service_principal_name'],'33b6f37c-7e6a-489f-b313-f886418b0319')
        self.assertEqual(s['max_concurrent_runs'],1)
    def test_seed_is_exact_initial_state(self):
        self.assertIn('"fence":0',control_steps()[1]['payload']['statement'])
        self.assertNotIn('IF NOT EXISTS',control_steps()[0]['payload']['statement'])
if __name__=='__main__':unittest.main()
