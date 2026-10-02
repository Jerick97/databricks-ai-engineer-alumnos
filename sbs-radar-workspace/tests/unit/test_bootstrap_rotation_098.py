from pathlib import Path
from types import SimpleNamespace
import json
import pytest
from sbs.genie.bootstrap_098 import create_rotating_service,preflight,SELECTOR
ROOT=Path(__file__).resolve().parents[2]
ENV={'SBS_GENIE_ROTATION_CONFIG':SELECTOR}
def client():
    cfg=json.loads((ROOT/'config/genie-server-template-098.json').read_bytes())
    class Files:
        def download(self,*a,**kw):raise AssertionError('no remote during bootstrap')
    return SimpleNamespace(config=SimpleNamespace(host=cfg['workspace_host'],auth_type='oauth-m2m',client_id=cfg['client_id']),files=Files())
def test_explicit_base135_binding_and_generation_selection():
    service=create_rotating_service(ENV,root=ROOT,mode='cloud',client_factory=client)
    binding=service.initialize_genie()
    assert binding.rag_snapshot==service.snapshot and binding.genie_snapshot!=service.snapshot
    assert binding.mapping_sha256==preflight(ROOT)['mapping_sha256']
    assert binding.readiness()['remote_verified'] is False
    assert service.generation_selection_path=='config/generation-selection-073.json'
    assert service.generator is None and service.embedding is None

def test_default_preserved_no_loader():
    def forbidden(*a,**k):raise AssertionError('loader forbidden')
    service=create_rotating_service({},root=ROOT,mode='local',binding_loader=forbidden)
    assert service.genie_binding is None
@pytest.mark.parametrize('selector',['','../config/genie-rotation-078.json','config/genie-rotation-078.json','injected'])
def test_selector_rejected_before_service(selector):
    def forbidden(**k):raise AssertionError('factory called')
    with pytest.raises(ValueError):create_rotating_service({'SBS_GENIE_ROTATION_CONFIG':selector},root=ROOT,mode='cloud',service_factory=forbidden)
@pytest.mark.parametrize('kind',['local','structural','release','snapshot','refresh'])
def test_incompatible_service_before_loader(kind):
    from sbs.runtime import LocalService
    service=LocalService(mode='cloud')
    if kind=='structural':service.structural_metadata={}
    if kind=='release':service.release_metadata={}
    if kind=='snapshot':service.snapshot='bad'
    if kind=='refresh':service.cloud_refresh=object()
    def forbidden(*a,**k):raise AssertionError('loader called')
    with pytest.raises(ValueError):create_rotating_service(ENV,root=ROOT,mode='local' if kind=='local' else 'cloud',service_factory=lambda **k:service,binding_loader=forbidden)

def test_publisher_identity_not_reader():
    c=client();c.config.auth_type='pat'
    with pytest.raises(ValueError,match='IDENTITY'):create_rotating_service(ENV,root=ROOT,mode='cloud',client_factory=lambda:c)

def test_http_cannot_set_server_selector():
    from sbs.webapp import Question
    with pytest.raises(ValueError):Question(question='count',pair_id='cyber-504',SBS_GENIE_ROTATION_CONFIG=SELECTOR)
def rotation_fixture():
    import importlib.util
    spec=importlib.util.spec_from_file_location('fixture078_for098',ROOT/'tests/unit/test_publication_rotation_078.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.setup()

@pytest.mark.parametrize('event',['rotate','revoke','expire'])
def test_request_retains_generation_and_rechecks_revocation_expiry(event):
    from sbs.genie import canonical
    from sbs.genie.publication import Certificate,REPLAY_IDENTITY_PROFILE
    from sbs.genie.publication_registry import RegistryEntry,PublisherPolicy,_entry
    service=create_rotating_service(ENV,root=ROOT,mode='cloud',client_factory=client)
    binding=service.initialize_genie();reader,data,now,entry,policy,install=rotation_fixture();binding.delegate.reader=reader
    selected_pins=[]
    def assemble(selected):
        selected_pins.append(selected.pin)
        def ask(question,*,context):
            before=selected.registry(certificate_sha256=selected.certificate.sha256)
            if event=='rotate':
                p=entry.as_dict();p['certificate']['replay_evidence']['current_metadata_at_ms']+=1
                cert=Certificate(canonical(p['certificate']).encode());pol=PublisherPolicy(**{**p['policy'],'certificate_sha256':cert.sha256})
                now[0]+=1;install(RegistryEntry(canonical(_entry(cert,pol,p['history_records'],now[0],REPLAY_IDENTITY_PROFILE)).encode()))
            elif event=='revoke':data[reader.binding+'.status.json']=canonical(dict(binding_sha256=reader.binding,status='revoked')).encode()
            else:now[0]=entry.as_dict()['registry']['valid_until_ms']
            after=selected.registry(certificate_sha256=selected.certificate.sha256)
            assert before['certificate_sha256']==after['certificate_sha256']
            return {'status':'completed','generation':selected.pin}
        return SimpleNamespace(ask_scoped=ask)
    binding.delegate.assemble=assemble
    context=service.entry('cyber-504','art20.3')['context']
    result=binding.ask_scoped('fixture',context=context)
    if event=='rotate':
        assert result['status']=='completed'
        # Next request selects new pointer; first request retained its own pin.
        assert binding.ask_scoped('fixture',context=context)['status']=='completed'
        assert selected_pins[0]!=selected_pins[1]
    else:
        assert result['status']=='unavailable' and result['rows']==[]
        assert 'REVOKED' in result['reason'] if event=='revoke' else 'EXPIRED' in result['reason']

def test_unknown_context_rejects_before_store():
    service=create_rotating_service(ENV,root=ROOT,mode='cloud',client_factory=client)
    result=service.initialize_genie().ask_scoped('fixture',context={'bad':'context'})
    assert result['status']=='conflict'

def test_generation_selection080_is_preserved():
    service=create_rotating_service({**ENV,'SBS_GENERATION_SELECTION':'config/generation-selection-077.json'},root=ROOT,mode='cloud',client_factory=client)
    assert service.generation_selection_path=='config/generation-selection-077.json'
    with pytest.raises(ValueError):create_rotating_service({**ENV,'SBS_GENERATION_SELECTION':'config/generation-selection-094.json'},root=ROOT,mode='cloud',client_factory=client)

def test_closed_bootstrap_config(tmp_path):
    cfg=json.loads((ROOT/SELECTOR).read_bytes());cfg['publisher_token']='not-allowed'
    path=tmp_path/SELECTOR;path.parent.mkdir();path.write_text(json.dumps(cfg))
    with pytest.raises(ValueError,match='CONFIG_INVALID'):preflight(tmp_path)
def test_dependency_copy_bootstraps_without_origin_reads(tmp_path):
    import shutil,subprocess,os,sys
    closure=json.loads((ROOT/'runs/sk06-sk07-sk12-bootstrap-098-dependencies.json').read_bytes())
    for name in closure['files_sha256']:
        dest=tmp_path/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
    code='''
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import json,sys
root=Path(sys.argv[1]);origin=Path(sys.argv[2]);original=Path.open
from sbs.genie.bootstrap_098 import create_rotating_service,SELECTOR
c=json.loads((root/'config/genie-server-template-098.json').read_bytes())
def opened(path,*a,**k):
    assert not path.resolve().is_relative_to(origin), 'origin read'
    return original(path,*a,**k)
class Files:
    def download(self,*a,**k):raise AssertionError('network forbidden')
client=SimpleNamespace(config=SimpleNamespace(host=c['workspace_host'],auth_type='oauth-m2m',client_id=c['client_id']),files=Files())
with patch.object(Path,'open',opened):
    service=create_rotating_service({'SBS_GENIE_ROTATION_CONFIG':SELECTOR},root=root,mode='cloud',client_factory=lambda:client)
    assert service.initialize_genie().readiness()['remote_verified'] is False
    assert service.generator is None
print('ISOLATED_BOOTSTRAP_PASS_NO_AUTH_OR_NETWORK')
'''
    out=subprocess.run([sys.executable,'-c',code,str(tmp_path),str(ROOT)],cwd=tmp_path,env={**os.environ,'PYTHONPATH':str(tmp_path/'src')},capture_output=True,text=True,timeout=30)
    assert out.returncode==0,out.stderr
    assert 'ISOLATED_BOOTSTRAP_PASS' in out.stdout
def test_app098_import_local_without_sdk_auth(monkeypatch):
    import databricks.sdk,runpy
    def forbidden(*a,**k):raise AssertionError('SDK initialization forbidden')
    monkeypatch.setattr(databricks.sdk,'WorkspaceClient',forbidden)
    monkeypatch.setenv('SBS_MODE','local');monkeypatch.delenv('SBS_GENIE_ROTATION_CONFIG',raising=False)
    app=runpy.run_path(str(ROOT/'app098.py'))['app']
    assert app is not None
def test_execution_pins_survive_cross_family_conversation(tmp_path,monkeypatch):
    import importlib.util
    import sbs.runtime as runtime
    spec=importlib.util.spec_from_file_location('counts_for098',ROOT/'tests/unit/test_runtime_genie.py')
    fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
    config=preflight(ROOT)
    class Counts(fixture.VerifiedCountFixture):
        rag_snapshot=config['rag_snapshot'];genie_snapshot=config['genie_snapshot'];mapping_sha256=config['mapping_sha256']
        reader=SimpleNamespace(binding='c'*64)
        calls=0
        def ask_scoped(self,question,*,context):
            result=super().ask_scoped(question,context=context);self.calls+=1
            result['execution_provenance']={'publication_certificate_sha256':str(self.calls)*64,'publication_registry_sha256':str(self.calls+2)*64,'provider':'fixture'}
            return result
    counts=Counts()
    service=create_rotating_service(ENV,root=ROOT,mode='cloud',binding_loader=lambda *a,**k:counts)
    (tmp_path/'runs').mkdir();monkeypatch.setattr(runtime,'ROOT',tmp_path)
    service.ask('cross098','¿Cuántos registros hay?','cyber-504','art20.3',True,actor={'authenticated':True,'subject':'fixture-subject','role':'reader','families':['cybersecurity','market_conduct']})
    traces=[answer['trace']['tools']['genie']['trace'] for answer in service.last_result['answers']]
    assert [t['execution_provenance']['publication_certificate_sha256'] for t in traces]==['1'*64,'2'*64]
    assert [t['execution_provenance']['publication_registry_sha256'] for t in traces]==['3'*64,'4'*64]
    assert all(t['rotation_snapshot_binding_sha256']=='c'*64 for t in traces)
