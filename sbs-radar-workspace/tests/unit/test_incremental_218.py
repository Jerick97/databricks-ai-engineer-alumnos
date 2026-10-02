import importlib.util
from pathlib import Path
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[2]
def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'deployment'/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
m=load('incremental_app218');a=load('activation218');old=load('activation210')

class Changes218(unittest.TestCase):
    def test_active_guard_actual_fixture_and_foreign_rejection(self):
        app=m.u.read(ROOT/'deployment/state/incremental-app214/app-active.json')
        def api(*args,**kwargs):return app['active_deployment']
        m.active_guard(api,app)
        app['active_deployment']['deployment_id']='foreign'
        with self.assertRaisesRegex(ValueError,'ACTIVE_BINDING'):m.active_guard(api,app)

    def test_live_flow_has_seven_imports_one_deploy_no_start_stop(self):
        from unittest.mock import patch
        import copy,base64,shutil
        plan=m.u.read(ROOT/m.PACKAGE/'plan.json')
        original=m.u.read(ROOT/'deployment/state/incremental-app214/app-active.json')
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            shutil.copytree(ROOT/m.PACKAGE,root/m.PACKAGE)
            m.u.durable(root/m.PRIOR_RESULT,{'historical210':'preserved'})
            class Fake:
                def __init__(self,cfg,state):
                    self.count=0;self.calls=[];self.deployed=False
                    self.files={n:(root/m.PACKAGE/'originals'/n).read_bytes() for n in plan['delta']}
                def __call__(self,method,path,body=None,query=None):
                    self.count+=1;self.calls.append((method,path))
                    if path.endswith('/Me'):return {'id':'76826984571984','userName':m.u.OWNER,'active':True}
                    if path.endswith('/export'):
                        name=query['path'][len(m.u.SOURCE)+1:]
                        return {'content':base64.b64encode(self.files[name]).decode()}
                    if path.endswith('/import'):
                        name=body['path'][len(m.u.SOURCE)+1:];self.files[name]=base64.b64decode(body['content']);return {}
                    app=copy.deepcopy(original)
                    if method=='POST' and path.endswith('/deployments'):self.deployed=True
                    if self.deployed:app['active_deployment']['deployment_id']='new218'
                    if '/deployments' in path:return app['active_deployment']
                    return app
            instances=[]
            def factory(cfg,state):
                obj=Fake(cfg,state);instances.append(obj);return obj
            with patch.object(m,'review',return_value=plan):
                result=m.execute(cfg=None,root=root,api_factory=factory,sleep=lambda _:None)
            self.assertEqual(result['status'],'deployed_inactive_pending_real_ui')
            paths=[p for method,p in instances[0].calls if method=='POST']
            self.assertEqual(sum(p.endswith('/import') for p in paths),7)
            self.assertEqual(sum(p.endswith('/deployments') for p in paths),1)
            self.assertFalse(any(p.endswith(('/start','/stop')) for p in paths))
            self.assertFalse(result['activation_started'])

    def test_third_allocation_retains_two_rows_and_enforces_reduced_runtime_caps(self):
        previous=load('activation214')
        from cryptography.hazmat.primitives.serialization import load_pem_public_key
        spec=importlib.util.spec_from_file_location('sbs.app133.lifecycle218_test',ROOT/'deployment/overlay218/src/sbs/app133/lifecycle210.py')
        runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'control';public=old.initialize(path,'a'*64)
            first=old.allocate(path,'x'*32,clock=lambda:1000)
            second=previous.append_allocation(path,'y'*32,first,public,clock=lambda:2000)
            budget=runtime.EpochBudget210(load_pem_public_key(public),clock=lambda:3000)
            third=a.append_allocation(path,budget.epoch,[first,second],public,clock=lambda:3000)
            self.assertEqual(third['payload']['caps'],{'generation_posts':6,'embedding_posts':5,'embedding_tokens':50000})
            self.assertEqual(old.allocate(path,'x'*32),first)
            budget.activate(third)
            for _ in range(6):budget.reserve()
            with self.assertRaises(ValueError):budget.reserve()
            for _ in range(5):budget.reserve_embedding(10000)
            with self.assertRaises(ValueError):budget.reserve_embedding(1)
            self.assertEqual(a.append_allocation(path,budget.epoch,[first,second],public,clock=lambda:4000),third)
            with self.assertRaisesRegex(ValueError,'EXHAUSTED'):
                a.append_allocation(path,'z'*32,[first,second],public)
            import sqlite3,json
            db=sqlite3.connect(path/'ledger.sqlite')
            rows={r[0]:json.loads(r[1]) for r in db.execute('SELECT epoch,payload FROM allocation')};db.close()
            self.assertEqual(len(rows),3)
            self.assertEqual(rows['x'*32],first['payload']);self.assertEqual(rows['y'*32],second['payload'])

    def test_wrong_prior_count_and_key_fail_closed(self):
        previous=load('activation214')
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'control';public=old.initialize(path,'a'*64)
            first=old.allocate(path,'x'*32,clock=lambda:1000)
            second=previous.append_allocation(path,'y'*32,first,public,clock=lambda:2000)
            with self.assertRaisesRegex(ValueError,'PRIOR_COUNT'):
                a.append_allocation(path,'z'*32,[first],public)
            with self.assertRaisesRegex(ValueError,'PUBLIC_KEY_CHANGED'):
                a.append_allocation(path,'z'*32,[first,second],b'wrong')

if __name__=='__main__':unittest.main()
