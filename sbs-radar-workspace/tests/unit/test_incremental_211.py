import importlib.util
from pathlib import Path
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[2]
def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'deployment'/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
m=load('incremental_app211');a=load('activation211');old=load('activation210')

class Changes211(unittest.TestCase):
    def test_active_guard_actual_fixture_and_foreign_rejection(self):
        app=m.u.read(ROOT/'deployment/state/incremental-app210/attempt2/app-active.json')
        def api(*args,**kwargs):return app['active_deployment']
        m.active_guard(api,app)
        app['active_deployment']['deployment_id']='foreign'
        with self.assertRaisesRegex(ValueError,'ACTIVE_BINDING'):m.active_guard(api,app)

    def test_live_flow_has_three_imports_one_deploy_no_start_stop(self):
        from unittest.mock import patch
        import copy,base64,shutil
        plan=m.u.read(ROOT/m.PACKAGE/'plan.json')
        original=m.u.read(ROOT/'deployment/state/incremental-app210/attempt2/app-active.json')
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            shutil.copytree(ROOT/m.PACKAGE,root/m.PACKAGE)
            m.u.durable(root/m.u.STATE/'attempt2/result.json',{'historical210':'preserved'})
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
                    if self.deployed:app['active_deployment']['deployment_id']='new211'
                    if '/deployments' in path:return app['active_deployment']
                    return app
            instances=[]
            def factory(cfg,state):
                obj=Fake(cfg,state);instances.append(obj);return obj
            with patch.object(m,'review',return_value=plan):
                result=m.execute(cfg=None,root=root,api_factory=factory,sleep=lambda _:None)
            self.assertEqual(result['status'],'deployed_inactive_pending_real_ui')
            paths=[p for method,p in instances[0].calls if method=='POST']
            self.assertEqual(sum(p.endswith('/import') for p in paths),3)
            self.assertEqual(sum(p.endswith('/deployments') for p in paths),1)
            self.assertFalse(any(p.endswith(('/start','/stop')) for p in paths))
            self.assertFalse(result['activation_started'])

    def test_append_preserves_old_allocation_and_never_resets(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'control';public=old.initialize(path,'a'*64)
            prior=old.allocate(path,'x'*32,clock=lambda:1000)
            new=a.append_allocation(path,'y'*32,prior,public,clock=lambda:2000)
            self.assertEqual(new['payload']['caps'],old.CAPS)
            self.assertEqual(old.allocate(path,'x'*32),prior)
            self.assertEqual(a.append_allocation(path,'y'*32,prior,public,clock=lambda:3000),new)
            with self.assertRaisesRegex(ValueError,'EXHAUSTED'):
                a.append_allocation(path,'z'*32,prior,public)
            with self.assertRaisesRegex(ValueError,'EPOCH'):
                a.append_allocation(path,'x'*32,prior,public)

    def test_new_key_and_changed_prior_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'control';public=old.initialize(path,'a'*64)
            prior=old.allocate(path,'x'*32,clock=lambda:1000)
            with self.assertRaisesRegex(ValueError,'PUBLIC_KEY_CHANGED'):
                a.append_allocation(path,'y'*32,prior,b'wrong')
            changed={**prior,'signature':'wrong'}
            with self.assertRaisesRegex(ValueError,'PRIOR_ALLOCATION'):
                a.append_allocation(path,'y'*32,changed,public)

if __name__=='__main__':unittest.main()
