from pathlib import Path
import importlib.util
import pytest
ROOT=Path(__file__).resolve().parents[2]
def module():
 s=importlib.util.spec_from_file_location('test182',ROOT/'deployment/final_binding_182.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def test_isolated178_seam_preserves168state_and166file():
 m=module();assert m.runner.mission.STATE==m.PREVIOUS
 assert m.runner.STATE=='deployment/state/final-app-168' and m.runner.MATERIALIZED=='deployment/state/final-materialized-168'
 assert "STATE='deployment/state/linux-canary-integrated-166'" in (ROOT/'deployment/canary_integrated_166.py').read_text()
 assert m.preflight()['previous_canary_phase']=='178'

def fixture(tmp_path):
 m=module();write=m.runner.durable;state=tmp_path/m.PREVIOUS
 write(tmp_path/m.PREVIOUS_FREEZE,{});write(tmp_path/m.PREVIOUS_REVIEW,{'status':'PASS_CANARY_RECOVERY_178','freeze_sha256':m.sha(tmp_path/m.PREVIOUS_FREEZE)})
 write(state/'admission.json',{'phase':'178','freeze_sha256':m.sha(tmp_path/m.PREVIOUS_FREEZE),'review_sha256':m.sha(tmp_path/m.PREVIOUS_REVIEW),'expires_at_unix':200})
 write(state/'package/manifest.json',{'source_sha256':'fixture','expires_at_unix':200});prefix=m.runner.prior.transport.history.prior.PREFIX+'canary166-fixture'
 write(state/'source-binding.json',{'source_code_path':prefix,'source_sha256':'fixture','manifest_sha256':m.sha(state/'package/manifest.json'),'expires_at_unix':200})
 write(state/'source-verified.json',{'files':237,'source_sha256':'fixture'});write(state/'deploy-intent.json',{'source_code_path':prefix,'mode':'SNAPSHOT'});write(state/'deploy-receipt.json',{'deployment_id':'real178fixture','source_code_path':prefix})
 return m,state

def test_predecessor_requires_exact178notarbitrary(tmp_path):
 m,state=fixture(tmp_path);assert len(m.predecessor(tmp_path))==6
 receipt=m.read(state/'deploy-receipt.json');receipt['source_code_path']='/another';(state/'deploy-receipt.json').write_text(__import__('json').dumps(receipt))
 with pytest.raises(ValueError,match='RECEIPT'):m.predecessor(tmp_path)

def test_final_review_pins_actual178_binding(tmp_path,monkeypatch):
 m,state=fixture(tmp_path);m.runner.durable(tmp_path/m.FREEZE,{})
 m.runner.durable(tmp_path/m.runner.EXACT_REVIEW,{'executor182_freeze_sha256':m.sha(tmp_path/m.FREEZE),'previous_canary178_inputs_sha256':m.predecessor(tmp_path)})
 monkeypatch.setattr(m,'original_ready',lambda root:('fixture-package','fixture-manifest','fixture-payload'))
 assert m.ready(tmp_path)[0]=='fixture-package'
 (state/'deploy-receipt.json').write_text((state/'deploy-receipt.json').read_text()+' ')
 with pytest.raises(ValueError,match='EXACT_PREDECESSOR'):m.ready(tmp_path)

def test_no_review_no_auth(tmp_path):
 m=module()
 with pytest.raises(FileNotFoundError):m.execute(root=tmp_path,config_factory=lambda **k:(_ for _ in ()).throw(AssertionError('auth forbidden')))
 assert not (tmp_path/m.runner.STATE).exists()
