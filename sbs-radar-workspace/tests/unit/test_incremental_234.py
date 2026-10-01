"""Offline deployment and cumulative-allocation contracts; no cloud."""
import importlib.util
from pathlib import Path
import base64,copy,json,shutil,sqlite3
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'deployment'/(name+'.py'))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
m=load('incremental_app234');a=load('activation234')

def test_actual_active232_guard():
    app=m.u.read(ROOT/'deployment/state/incremental-app232/app-active.json')
    m.active_guard(lambda *args,**kwargs:app['active_deployment'],app)
    app['active_deployment']['deployment_id']='foreign'
    import pytest
    with pytest.raises(ValueError):m.active_guard(lambda *a,**k:{},app)

def test_delta_new_and_existing_files_one_deployment_no_start_stop(tmp_path):
    plan=m.u.read(ROOT/m.PACKAGE/'plan.json');shutil.copytree(ROOT/m.PACKAGE,tmp_path/m.PACKAGE)
    m.u.durable(tmp_path/m.PRIOR_RESULT,{'prior_history':'unchanged'})
    original=m.u.read(ROOT/'deployment/state/incremental-app232/app-active.json')
    instances=[]
    class Fake:
        def __init__(self,cfg,state):
            self.count=0;self.calls=[];self.deployed=False;instances.append(self)
            self.files={n:(tmp_path/m.PACKAGE/'originals'/n).read_bytes() for n,d in plan['delta'].items() if d['before'] is not None}
        def __call__(self,method,path,body=None,query=None):
            self.count+=1;self.calls.append((method,path))
            if path.endswith('/Me'):return {'id':'76826984571984','userName':m.u.OWNER,'active':True}
            if path.endswith('/list'):return {'objects':[{'path':m.u.SOURCE+'/'+n} for n in self.files]}
            if path.endswith('/export'):return {'content':base64.b64encode(self.files[query['path'][len(m.u.SOURCE)+1:]]).decode()}
            if path.endswith('/import'):
                n=body['path'][len(m.u.SOURCE)+1:];assert body['overwrite']==(n in self.files)
                self.files[n]=base64.b64decode(body['content']);return {}
            app=copy.deepcopy(original)
            if method=='POST' and path.endswith('/deployments'):self.deployed=True
            if self.deployed:app['active_deployment']['deployment_id']='new234'
            return app['active_deployment'] if '/deployments' in path else app
    with patch.object(m,'review',return_value=plan):result=m.execute(cfg=None,root=tmp_path,api_factory=Fake,sleep=lambda _:None)
    assert result['status']=='deployed_inactive_pending_real_ui'
    posts=[p for method,p in instances[0].calls if method=='POST']
    assert len(posts)==len(plan['delta'])+1 and sum(p.endswith('/deployments') for p in posts)==1
    assert not any(p.endswith(('/start','/stop')) for p in posts)
    assert {n:m.u.digest(raw) for n,raw in instances[0].files.items()}=={n:d['after'] for n,d in plan['delta'].items()}

def test_ninth_allocation_preserves_all_eight(tmp_path):
    mods=[load('activation'+str(n)) for n in (210,214,218,221,223,225,229,232)]
    path=tmp_path/'ledger';pub=mods[0].initialize(path,'a'*64)
    priors=[mods[0].allocate(path,'1'*32,clock=lambda:1000)]
    priors.append(mods[1].append_allocation(path,'2'*32,priors[0],pub,clock=lambda:2000))
    for i,m0 in enumerate(mods[2:],start=3):
        priors.append(m0.append_allocation(path,str(i)*32,list(priors),pub,clock=lambda:i*1000))
    nine=a.append_allocation(path,'9'*32,priors,pub,clock=lambda:9000)
    assert nine['payload']['expires_at_unix']==37800
    assert nine['payload']['caps']=={'generation_posts':6,'embedding_posts':5,'embedding_tokens':50000}
    assert a.append_allocation(path,'9'*32,priors,pub,clock=lambda:10000)==nine
    import pytest
    with pytest.raises(ValueError):a.append_allocation(path,'a'*32,priors,pub)
    with sqlite3.connect(path/'ledger.sqlite') as db:
        rows={e:json.loads(p) for e,p in db.execute('SELECT epoch,payload FROM allocation')}
    assert len(rows)==9
    for prior in priors+[nine]:assert rows[prior['payload']['epoch']]==prior['payload']
