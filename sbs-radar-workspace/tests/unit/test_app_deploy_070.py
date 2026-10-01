"""SDK RAW multipart/endpoint bounds with synthetic HTTP; never cloud."""
from pathlib import Path
from types import SimpleNamespace
import importlib.util,io,json
import pytest
ROOT=Path(__file__).resolve().parents[2]
def load():
    spec=importlib.util.spec_from_file_location('deploy070',ROOT/'deployment/app_deploy_070.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
class Raw(io.BytesIO):
    def read(self,n,**kw):return super().read(n)
class Session:
    adapters={};trust_env=True
    def __init__(self):self.calls=[];self.content=b'{}'
    def request(self,*a,**kw):self.calls.append((a,kw));return SimpleNamespace(status_code=200,raw=Raw(self.content),close=lambda:None)

def test_sdk_workspace_large_upload_is_raw_multipart_not_base64():
    from databricks.sdk.mixins.workspace import WorkspaceExt
    from databricks.sdk.service.workspace import ImportFormat,ExportFormat
    m=load();s=Session();cfg=SimpleNamespace(host=m.HOST,authenticate=lambda:{'Authorization':'test'},workspace_id=None)
    api=m.ScopedApi(cfg,'/Workspace/Users/u/sbs-radar/releases/fixed',lambda:None,s);w=WorkspaceExt(api)
    raw=b'x'*(10*1024*1024+1);stream=io.BytesIO(raw)
    w.upload(api.prefix+'/model.onnx',stream,format=ImportFormat.RAW,overwrite=False)
    args,kw=s.calls[0];assert args[0]=='POST' and kw['files']['content'] is stream and kw['data']['format']=='RAW' and kw['json'] is None
    s.content=raw
    with w.download(api.prefix+'/model.onnx',format=ExportFormat.RAW) as result:assert result.read()==raw
    assert s.calls[-1][1]['params']['direct_download']=='true'

@pytest.mark.parametrize('method,path,kw',[
 ('POST','/api/2.0/sql/statements',{'body':{'statement':'SELECT 1'}}),
 ('POST','/api/2.0/apps/other/start',{}),
 ('POST','/api/2.0/workspace/import',{'data':{'path':'/Workspace/Users/u/sbs-radar/releases/fixed/a','format':'RAW','content':'base64'}}),
 ('POST','/api/2.0/workspace/mkdirs',{'body':{'path':'/Workspace/Users/other'}}),
 ('DELETE','/api/2.0/apps/sbs-radar-pilot',{}),
 ('PATCH','/api/2.0/apps/sbs-radar-pilot',{}),
 ('POST','/api/2.0/apps/sbs-radar-pilot/deployments',{'body':{'source_code_path':'/Workspace/other','mode':'SNAPSHOT'}})])
def test_scoped_transport_rejects_outside_before_auth(method,path,kw):
    m=load();s=Session();calls=[];cfg=SimpleNamespace(host=m.HOST,authenticate=lambda:calls.append(1));api=m.ScopedApi(cfg,'/Workspace/Users/u/sbs-radar/releases/fixed',lambda:None,s)
    with pytest.raises(ValueError):api.do(method,path,**kw)
    assert s.calls==calls==[]

def test_missing_review_never_constructs_services():
    m=load()
    with pytest.raises(ValueError,match='DEPLOY_REVIEW_REQUIRED'):m.execute('/missing','/missing',None)


def test_durable_resume_never_repeats_upload_start_deploy_and_retains_rollback(tmp_path,monkeypatch):
    m=load();monkeypatch.setattr(m,'ROOT',tmp_path);pkg=tmp_path/'pkg';(pkg/'source').mkdir(parents=True)
    (pkg/'source/a.bin').write_bytes(b'a');manifest={'release_id':'fixed','files_sha256':{'a.bin':m.sha(b'a')}};(pkg/'manifest.json').write_text(json.dumps(manifest))
    prefix='/Workspace/Users/u/sbs-radar/releases/fixed';contract={'status':'PENDING','manifest_sha256':'a'*64,'source_code_path':prefix}
    monkeypatch.setattr(m,'preflight',lambda *a:{'status':'ready_for_review','review_contract':contract})
    review=tmp_path/'review.json';review.write_text(json.dumps({**contract,'status':'PASS'}))
    class Missing(Exception):error_code='RESOURCE_DOES_NOT_EXIST'
    objects={};calls=[]
    class Workspace:
        def get_status(self,p):
            if p not in objects:raise Missing()
            return {'object_type':'DIRECTORY' if objects[p] is None else 'FILE'}
        def mkdirs(self,p):calls.append('mkdir');objects[p]=None
        def upload(self,p,s,**kw):calls.append('upload');objects[p]=s.read();raise ValueError('ambiguous after effect')
        def download(self,p,**kw):return io.BytesIO(objects[p])
    app={'service_principal_id':77041447522099,'service_principal_client_id':'a947eccf-5f94-4369-a3d4-8f83b4ea98a1','effective_user_api_scopes':['iam.current-user:read'],'compute_status':{'state':'STOPPED'},'active_deployment':{'deployment_id':'old-deployment','source_code_path':'old-source'}}
    class Apps:
        def get(self,name):return json.loads(json.dumps(app))
        def start(self,name):calls.append('start');app['compute_status']['state']='ACTIVE';raise ValueError('ambiguous after effect')
        def deploy(self,name,request):calls.append('deploy');return SimpleNamespace(response={'deployment_id':'new-deployment'})
        def get_deployment(self,*a):return {'deployment_id':'new-deployment','status':{'state':'SUCCEEDED'}}
    server=SimpleNamespace(workspace=Workspace(),apps=Apps(),api=SimpleNamespace(calls=0,session=SimpleNamespace(close=lambda:None)))
    for _ in range(2):
        out=m.execute(pkg,'quality',review,clock=lambda:1000,sleep=lambda _:None,services_factory=lambda *a:server,config_factory=lambda **kw:SimpleNamespace())
        assert out['status']=='deployed_runtime_verification_pending'
    assert calls.count('upload')==calls.count('start')==calls.count('deploy')==1
    original=m.read(tmp_path/'deployment/state/fixed/app-before.json');assert original['active_deployment']['deployment_id']=='old-deployment'


def test_quality_gate_selects_exact_four_reviewed_case_paths_not_mixed_or_escaped():
    m=load();pins={f'deployment/state/generation-rag-075/turn-{i}-result.json':'a'*64 for i in range(4)}
    assert all('generation-rag-075' in str(p) for p in m.quality_paths({'responses_sha256':pins}))
    for extra in ['../outside','deployment/state/generation-rag-073/turn-0-result.json']:
        bad=dict(pins);bad.pop('deployment/state/generation-rag-075/turn-0-result.json');bad[extra]='b'*64
        with pytest.raises(ValueError):m.quality_paths({'responses_sha256':bad})


def test_tested_implementation_chain_rejects_drift_and_preserves_doc_freedom(tmp_path,monkeypatch):
    m=load();monkeypatch.setattr(m,'ROOT',tmp_path)
    names=set(m.TESTED_REQUIRED)
    inputs={n:m.sha(n.encode()) for n in names}
    inputs['skills/sbs-conversacion-orquestacion/SKILL.md']='0'*64
    plan=tmp_path/'deployment/generation-rag-075-plan.json';plan.parent.mkdir(parents=True)
    plan.write_text(json.dumps({'inputs':inputs}))
    admission=tmp_path/'deployment/state/generation-rag-075/admission.json';admission.parent.mkdir(parents=True)
    admission.write_text(json.dumps({'plan_sha256':m.sha(plan.read_bytes())}))
    needed=[admission.parent/f'turn-{i}-result.json' for i in range(4)]
    pins=m.tested_implementation(needed,dict(inputs))
    assert str(admission.relative_to(tmp_path)) in pins
    changed=dict(inputs);changed['src/sbs/conversation/__init__.py']='f'*64
    with pytest.raises(ValueError,match='TESTED_IMPLEMENTATION_MISMATCH'):m.tested_implementation(needed,changed)
    changed=dict(inputs);changed['skills/sbs-conversacion-orquestacion/SKILL.md']='e'*64
    m.tested_implementation(needed,changed)
    admission.write_text(json.dumps({'plan_sha256':'f'*64}))
    with pytest.raises(ValueError,match='TESTED_PLAN_ADMISSION_MISMATCH'):m.tested_implementation(needed,inputs)
