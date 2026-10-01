"""Synthetic local gates only: no cloud, inference, package or quality claim."""
from pathlib import Path
import importlib.util,json
import pytest
ROOT=Path(__file__).resolve().parents[2]
def load(name):
    s=importlib.util.spec_from_file_location(name,ROOT/'deployment'/f'{name}.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def test_server_selection_default_explicit_and_rejections():
    from sbs.models.app_selection import server_selection
    assert server_selection({})=='config/generation-selection-073.json'
    assert server_selection({'SBS_GENERATION_SELECTION':'config/generation-selection-077.json'})=='config/generation-selection-077.json'
    for value in ['https://endpoint','../config/generation-selection-077.json','', 'config/generation-selection-075.json']:
        with pytest.raises(ValueError):server_selection({'SBS_GENERATION_SELECTION':value})

def test_quality077_exact_paths_and_mixing_rejected():
    m=load('app_deploy_080');pins={f'deployment/state/generation-rag-077/turn-{i}-result.json':'a'*64 for i in range(4)}
    assert all('077' in str(p) for p in m.quality_paths({'responses_sha256':pins}))
    pins['deployment/state/generation-rag-075/turn-0-result.json']=pins.pop('deployment/state/generation-rag-077/turn-0-result.json')
    with pytest.raises(ValueError):m.quality_paths({'responses_sha256':pins})

def chain(m,tmp_path):
    inputs=json.loads((ROOT/'deployment/generation-rag-077-plan.json').read_text())['inputs']
    plan=tmp_path/'deployment/generation-rag-077-plan.json';plan.parent.mkdir(parents=True)
    plan.write_text(json.dumps({'inputs':inputs,'generation_selection':'config/generation-selection-077.json'}))
    admission=tmp_path/'deployment/state/generation-rag-077/admission.json';admission.parent.mkdir(parents=True)
    admission.write_text(json.dumps({'plan_sha256':m.sha(plan.read_bytes())}))
    return inputs,[admission.parent/f'turn-{i}-result.json' for i in range(4)]

def test077_binds_selection_plan_admission_and_every_behavior(tmp_path,monkeypatch):
    m=load('app_deploy_080');inputs,paths=chain(m,tmp_path);monkeypatch.setattr(m,'ROOT',tmp_path)
    m.tested_implementation(paths,inputs,'config/generation-selection-077.json')
    with pytest.raises(ValueError,match='SELECTION'):m.tested_implementation(paths,inputs,'config/generation-selection-073.json')
    for name in ['src/sbs/runtime.py','config/generation-selection-077.json','skills/sbs-conversacion-orquestacion/assets/generator-instructions.md','runs/sk05-generation-candidates-072-databricks-meta-llama-3-3-70b-instruct.json']:
        changed=dict(inputs);changed[name]='0'*64
        with pytest.raises(ValueError,match='IMPLEMENTATION_MISMATCH'):m.tested_implementation(paths,changed,'config/generation-selection-077.json')

def test_snapshot_explicit077_has_config_observation_server_entrypoint(monkeypatch):
    m=load('app_release_080');original=m.module
    def module(name):
        v=original(name)
        if name=='build_bundle':v.selected_paths=lambda **kw:[]
        return v
    monkeypatch.setattr(m,'module',module)
    b,manifest,c,_=m.snapshot(generation_selection_path='config/generation-selection-077.json')
    assert manifest['generation_selection_path']=='config/generation-selection-077.json'
    assert c['command']==['python','app080.py']
    assert {'name':'SBS_GENERATION_SELECTION','value':'config/generation-selection-077.json'} in c['env']
    assert b['config/generation-selection-077.json']==(ROOT/'config/generation-selection-077.json').read_bytes()
    assert 'runs/sk05-generation-candidates-072-databricks-meta-llama-3-3-70b-instruct.json' in b
    assert 'app080.py' in b and manifest['quality_acceptance'] is False

def test_build077_without_real_quality_never_creates_output(tmp_path):
    m=load('app_release_080');dest=tmp_path/'no-package'
    with pytest.raises(ValueError,match='QUALITY_REQUIRED'):m.build(dest,generation_selection_path='config/generation-selection-077.json')
    assert not dest.exists()

def test_server_service_binds_before_lazy_initialization_without_client_inputs():
    from sbs.models.app_selection import create_server_service
    class Service:
        generator=None
    seen=[]
    service=create_server_service({'SBS_GENERATION_SELECTION':'config/generation-selection-077.json'},service_factory=lambda **kw:seen.append(kw) or Service(),mode='cloud')
    assert service.generation_selection_path=='config/generation-selection-077.json'
    assert service.generator is None and seen==[{'mode':'cloud'}]
    with pytest.raises(ValueError):
        create_server_service({'SBS_GENERATION_SELECTION':'../evil'},service_factory=lambda **kw:pytest.fail('must reject before bootstrap'))


def synthetic_package(m,tmp_path):
    """Isolated synthetic quality-chain contract, never real quality evidence."""
    selected='config/generation-selection-077.json'
    inputs,paths=chain(m,tmp_path)
    names=set(inputs)-{n for n in inputs if n.startswith(('deployment/','runs/sk09','skills/')) and '/assets/' not in n}
    blobs={name:b'synthetic behavior' for name in names}
    for name in [selected,'runs/sk05-generation-candidates-072-databricks-meta-llama-3-3-70b-instruct.json']:
        blobs[name]=(ROOT/name).read_bytes()
    config={'command':['python','app080.py'],'env':[{'name':'SBS_GENERATION_SELECTION','value':selected}]}
    blobs.update({'app080.py':b'synthetic entrypoint','src/sbs/models/app_selection.py':b'synthetic selector','app.yaml':m.rawjson(config)})
    hashes={n:m.sha(raw) for n,raw in sorted(blobs.items())}
    plan_path=tmp_path/'deployment/generation-rag-077-plan.json'
    plan_path.write_bytes(m.rawjson({'inputs':hashes,'generation_selection':selected}))
    (paths[0].parent/'admission.json').write_bytes(m.rawjson({'plan_sha256':m.sha(plan_path.read_bytes())}))
    selection=json.loads(blobs[selected])
    for path in paths:
        path.write_bytes(m.rawjson({'answer':{'status':'answered','citations':['synthetic']},'generation':{'http_status':200,'endpoint':selection['endpoint'],'response_model':selection['expected_response_model']}}))
    review=tmp_path/'quality.json';review.write_bytes(m.rawjson({'status':'PASS_CONTROLLED_SAMPLE','demo_sample_accepted':True,'responses_sha256':{str(p.relative_to(tmp_path)):m.sha(p.read_bytes()) for p in paths}}))
    source=tmp_path/'package/source';source.mkdir(parents=True)
    for name,raw in blobs.items():
        path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    identity=m.sha(m.rawjson(hashes));release='sbs-app-080-'+identity[:16]
    manifest={'release_id':release,'snapshot_sha256':identity,'files_sha256':hashes,'generation_selection_path':selected,'archive_sha256':m.sha(b'synthetic archive')}
    package=source.parent
    (package/'manifest.json').write_bytes(m.rawjson(manifest));(package/'source.tar.gz').write_bytes(b'synthetic archive')
    (package/'operation-plan.json').write_bytes(m.rawjson({'app_name':m.APP,'app_client_id':'a947eccf-5f94-4369-a3d4-8f83b4ea98a1','app_executor_id':77041447522099,'source_code_path':'/Workspace/Users/sociosdosmilveintiseis@gmail.com/sbs-radar/releases/'+release,'app_configuration':config}))
    autonomy=tmp_path/m.AUTONOMY;autonomy.parent.mkdir(exist_ok=True);autonomy.write_bytes((ROOT/m.AUTONOMY).read_bytes())
    for name in ('app_deploy_080.py','app_release_080.py'):(tmp_path/'deployment'/name).write_bytes((ROOT/'deployment'/name).read_bytes())
    return package,review,paths,manifest


def test_preflight_full_synthetic077_chain_and_rejects_response_tamper(tmp_path,monkeypatch):
    m=load('app_deploy_080');package,review,paths,manifest=synthetic_package(m,tmp_path);monkeypatch.setattr(m,'ROOT',tmp_path)
    report=m.preflight(package,review)
    assert report['status']=='ready_for_review' and report['endpoint']=='databricks-meta-llama-3-3-70b-instruct'
    assert 'deployment/generation-rag-077-plan.json' in report['review_contract']['files_sha256']
    paths[0].write_bytes(paths[0].read_bytes()+b' ')
    with pytest.raises(ValueError,match='QUALITY_RESPONSE_PINS_MISMATCH'):m.preflight(package,review)


def test_preflight_unaccepted_review_and_wrong_app_selection_fail_closed(tmp_path,monkeypatch):
    m=load('app_deploy_080');package,review,paths,manifest=synthetic_package(m,tmp_path);monkeypatch.setattr(m,'ROOT',tmp_path)
    data=m.read(review);data['demo_sample_accepted']=False;review.write_bytes(m.rawjson(data))
    assert m.preflight(package,review)['status']=='generation_sbs_quality_pending'
    with pytest.raises(ValueError,match='GENERATION_SBS_QUALITY_REQUIRED'):
        m.execute(package,review,tmp_path/'missing-review',config_factory=lambda **kw:pytest.fail('no authentication'))
    manifest['generation_selection_path']='config/generation-selection-073.json'
    (package/'manifest.json').write_bytes(m.rawjson(manifest))
    with pytest.raises(ValueError,match='APP_SELECTION_MISMATCH'):m.preflight(package,review)


def test_quality_build_gate_accepts_only_exact_synthetic_chain(tmp_path,monkeypatch):
    d=load('app_deploy_080');package,review,paths,manifest=synthetic_package(d,tmp_path)
    m=load('app_release_080');monkeypatch.setattr(m,'ROOT',tmp_path)
    original=m.module
    def module(name):
        result=original(name);result.ROOT=tmp_path;return result
    # Load source modules from real source, while all chain data stays isolated.
    monkeypatch.setattr(m,'module',lambda name: d)
    monkeypatch.setattr(d,'ROOT',tmp_path)
    for name in [manifest['generation_selection_path'],'runs/sk05-generation-candidates-072-databricks-meta-llama-3-3-70b-instruct.json']:
        target=tmp_path/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((package/'source'/name).read_bytes())
    m.quality_gate(review,manifest)
    manifest['files_sha256']['src/sbs/runtime.py']='0'*64
    with pytest.raises(ValueError,match='IMPLEMENTATION_MISMATCH'):m.quality_gate(review,manifest)

def test_real_factory_server_selection_without_inference(monkeypatch):
    from sbs.models.app_selection import create_server_service
    from sbs.runtime import LocalService
    monkeypatch.setattr(LocalService,'initialize_models',lambda self:pytest.fail('no inference/bootstrap models allowed'))
    service=create_server_service({'SBS_GENERATION_SELECTION':'config/generation-selection-077.json'},mode='local')
    assert isinstance(service,LocalService)
    assert service.generation_selection_path=='config/generation-selection-077.json'
    assert len(service.catalog()['families'])==2
