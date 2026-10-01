"""Offline deployment and cumulative-allocation contracts; no cloud."""
import importlib.util
from pathlib import Path
import base64,copy,json,shutil,sqlite3
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'deployment'/(name+'.py'))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
m=load('incremental_app223');a=load('activation223')

def test_actual_active221_guard():
    app=m.u.read(ROOT/'deployment/state/incremental-app221/app-active.json')
    m.active_guard(lambda *args,**kwargs:app['active_deployment'],app)
    app['active_deployment']['deployment_id']='foreign'
    import pytest
    with pytest.raises(ValueError):m.active_guard(lambda *a,**k:{},app)

def test_delta_new_and_existing_files_one_deployment_no_start_stop(tmp_path):
    plan=m.u.read(ROOT/m.PACKAGE/'plan.json');shutil.copytree(ROOT/m.PACKAGE,tmp_path/m.PACKAGE)
    m.u.durable(tmp_path/m.PRIOR_RESULT,{'prior_history':'unchanged'})
    original=m.u.read(ROOT/'deployment/state/incremental-app221/app-active.json')
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
            if self.deployed:app['active_deployment']['deployment_id']='new223'
            return app['active_deployment'] if '/deployments' in path else app
    with patch.object(m,'review',return_value=plan):result=m.execute(cfg=None,root=tmp_path,api_factory=Fake,sleep=lambda _:None)
    assert result['status']=='deployed_inactive_pending_real_ui'
    posts=[p for method,p in instances[0].calls if method=='POST']
    assert len(posts)==len(plan['delta'])+1 and sum(p.endswith('/deployments') for p in posts)==1
    assert not any(p.endswith(('/start','/stop')) for p in posts)
    assert {n:m.u.digest(raw) for n,raw in instances[0].files.items()}=={n:d['after'] for n,d in plan['delta'].items()}

def test_fifth_allocation_keeps_all_four_reservations(tmp_path):
    old=load('activation210');second=load('activation214');third=load('activation218');fourth=load('activation221')
    path=tmp_path/'ledger';pub=old.initialize(path,'a'*64)
    one=old.allocate(path,'1'*32,clock=lambda:1000)
    two=second.append_allocation(path,'2'*32,one,pub,clock=lambda:2000)
    three=third.append_allocation(path,'3'*32,[one,two],pub,clock=lambda:3000)
    four=fourth.append_allocation(path,'4'*32,[one,two,three],pub,clock=lambda:4000)
    five=a.append_allocation(path,'5'*32,[one,two,three,four],pub,clock=lambda:5000)
    assert five['payload']['caps']=={'generation_posts':6,'embedding_posts':5,'embedding_tokens':50000}
    assert five['payload']['expires_at_unix']==33800
    assert a.append_allocation(path,'5'*32,[one,two,three,four],pub,clock=lambda:6000)==five
    import pytest
    with pytest.raises(ValueError):a.append_allocation(path,'6'*32,[one,two,three,four],pub)
    with sqlite3.connect(path/'ledger.sqlite') as db:
        rows={e:json.loads(p) for e,p in db.execute('SELECT epoch,payload FROM allocation')}
    assert len(rows)==5
    for prior in [one,two,three,four,five]:assert rows[prior['payload']['epoch']]==prior['payload']
    assert sum(p['caps']['generation_posts'] for p in rows.values())==34
    assert sum(p['caps']['embedding_posts'] for p in rows.values())==31
    assert sum(p['caps']['embedding_tokens'] for p in rows.values())==310000
