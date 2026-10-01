from pathlib import Path
import importlib.util,sys,logging
from types import SimpleNamespace as NS
import pytest
ROOT=Path(__file__).resolve().parents[2];OVERLAY=ROOT/'runs/sk06-genie-diagnostics-220-overlay/source/src/sbs/genie'
def load(name,file):
 spec=importlib.util.spec_from_file_location(name,OVERLAY/file);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
d=load('sbs.genie.diagnostics220','diagnostics220.py');r=load('sbs.genie.rotation220test','server_rotation.py');runtime=load('sbs.genie.runtime220test','runtime.py')
@pytest.mark.parametrize('error',[ValueError('Bearer SECRET'),ValueError('ROTATION_SECRET_TOKEN_ABC'),RuntimeError({'Authorization':'SECRET'}),ValueError('https://host/?token=SECRET')])
def test_secret_exception_text_never_logged(error,caplog):
 with caplog.at_level(logging.WARNING):out=d.log_rejection('rotation_select',error=error)
 assert out['code']=='UNKNOWN';assert 'SECRET' not in caplog.text and 'Authorization' not in caplog.text

def test_fixed_codes_and_unknown_stage_sanitized(caplog):
 assert d.log_rejection('rotation_select',error=ValueError('REMOTE_EVIDENCE_UNAVAILABLE'))['code']=='REMOTE_EVIDENCE_UNAVAILABLE'
 assert d.log_rejection('SECRET',reason='Bearer SECRET')=={'stage':'unknown','code':'UNKNOWN','exception_class':'none'}
 assert 'SECRET' not in caplog.text

@pytest.mark.parametrize('stage',['rotation_select','rotation_assemble','rotation_delegate'])
def test_rotation_failures_preserve_return_and_report_stage(stage,caplog):
 def fail(*a,**kw):raise ValueError('ROTATION_GENERATION_HASH_MISMATCH')
 base=NS(_catalog=NS(references=lambda context:{}));reader=NS(select=fail if stage=='rotation_select' else lambda:object())
 assembly=fail if stage=='rotation_assemble' else lambda _:NS(ask_scoped=fail if stage=='rotation_delegate' else lambda *a,**k:{'status':'ready'})
 obj=r.RotatingBinding(base,reader,assembly);out=obj.ask_scoped('private question',context={})
 assert out=={'status':'unavailable','scope_verified':False,'rows':[],'reason':'ROTATION_GENERATION_HASH_MISMATCH'}
 assert '"stage": "'+stage+'"' in caplog.text and 'private question' not in caplog.text

def test_rotation_return_rejection_logged(caplog):
 expected={'status':'unavailable','reason':'SERVER_EVIDENCE_UNAVAILABLE','rows':[]}
 obj=r.RotatingBinding(NS(_catalog=NS(references=lambda context:{})),NS(select=lambda:object()),lambda _:NS(ask_scoped=lambda *a,**k:expected))
 assert obj.ask_scoped('secret',context={}) is expected
 assert 'SERVER_EVIDENCE_UNAVAILABLE' in caplog.text

def test_logger_failure_never_changes_control_flow(monkeypatch):
 def fail(*a,**kw):raise RuntimeError('secret')
 monkeypatch.setattr(d,'logging',NS(getLogger=fail));assert d.log_rejection('rotation_select',reason='UNKNOWN') is None

def runtime_fixture():
 obj=object.__new__(runtime.RuntimeBinding);obj._genie_snapshot='snapshot';obj._rag_snapshot='rag';obj._mapping={'mapping_sha256':'mapping'};obj._config={'warehouse_id':'warehouse','space_id':'space'};obj._hashes={'table':'hash'};obj._adapter=None
 obj._catalog=NS(references=lambda context:{'ref':{'source_tables':{'table':1}}});obj.readiness=lambda:{'available':True}
 return obj

def test_runtime_readiness_rejection(caplog):
 obj=runtime_fixture();obj.readiness=lambda:{'available':False};out=obj.ask_scoped('private',context={})
 assert out['reason']=='CONFIGURATION_PENDING';assert 'runtime_readiness' in caplog.text

def test_runtime_publication_exception_keeps_unavailable(caplog):
 obj=runtime_fixture()
 def fail(**kw):raise ValueError('DELTA_REGISTRY_IDENTITY_PROFILE_MISMATCH')
 delta=NS(for_request=lambda:NS(verify=fail));obj._dependencies=NS(delta_publication=delta,executor_id=1)
 out=obj.ask_scoped('private',context={});assert out['reason']=='SERVER_EVIDENCE_UNAVAILABLE'
 assert 'runtime_publication' in caplog.text and 'DELTA_REGISTRY_IDENTITY_PROFILE_MISMATCH' in caplog.text

def test_runtime_publication_return_rejection(caplog):
 obj=runtime_fixture();obj._dependencies=NS(delta_publication=None,publication_lookup=lambda **kw:None)
 out=obj.ask_scoped('private',context={});assert out['reason']=='PUBLICATION_NOT_VERIFIED';assert 'PUBLICATION_NOT_VERIFIED' in caplog.text

def test_runtime_delta_request_error_still_propagates(caplog):
 obj=runtime_fixture()
 def fail():raise ValueError('DELTA_REGISTRY_IDENTITY_PROFILE_MISMATCH')
 obj._dependencies=NS(delta_publication=NS(for_request=fail))
 with pytest.raises(ValueError):obj.ask_scoped('private',context={})
 assert 'runtime_delta_request' in caplog.text

def test_runtime_adapter_return_rejection(caplog):
 obj=runtime_fixture()
 def publication(**kw):return {'snapshot':'snapshot','source_tables':{'table':1},'table_content_sha256':{'table':'hash'},'attestation_id':'a','valid_from_ms':0,'valid_until_ms':9999999999999}
 obj._dependencies=NS(delta_publication=None,publication_lookup=publication)
 obj._adapter=NS(ask_scoped=lambda *a,**kw:{'status':'denied','reason':'GENIE_ACCESS_DENIED'})
 out=obj.ask_scoped('private',context={});assert out['status']=='denied';assert 'runtime_result' in caplog.text and 'GENIE_ACCESS_DENIED' in caplog.text

def test_empty_is_valid_adapter_success_not_rejection(caplog):
 expected={'status':'empty','rows':[]}
 obj=r.RotatingBinding(NS(_catalog=NS(references=lambda context:{})),NS(select=lambda:object()),lambda _:NS(ask_scoped=lambda *a,**k:expected))
 assert obj.ask_scoped('private',context={}) is expected
 obj=runtime_fixture()
 obj._dependencies=NS(delta_publication=None,publication_lookup=lambda **kw:{'snapshot':'snapshot','source_tables':{'table':1},'table_content_sha256':{'table':'hash'},'attestation_id':'a','valid_from_ms':0,'valid_until_ms':9999999999999})
 obj._adapter=NS(ask_scoped=lambda *a,**kw:expected)
 assert obj.ask_scoped('private',context={})['status']=='empty'
 assert 'SBS_GENIE_REJECTION' not in caplog.text
