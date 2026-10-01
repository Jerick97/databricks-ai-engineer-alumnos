"""068 server profile integration; real artifact bytes, injected offline clients."""
import json,hashlib,io
from pathlib import Path
from types import SimpleNamespace
import pytest
from sbs.genie.server import load_server_binding,RemoteEvidence
from sbs.genie.publication import REPLAY_IDENTITY_PROFILE
from test_server_genie import enabled_inputs,fake_client
ROOT=Path(__file__).resolve().parents[2]

def replay_inputs(tmp_path):
    c,_=enabled_inputs(tmp_path)
    result=json.loads((ROOT/'runs/sk06-recovery-064-finalization/result.json').read_bytes());key=result['publication']['certificate_sha256']
    raw=(ROOT/f'deployment/state/phase-s-017/certificates/{key}.json').read_bytes()
    # CertificateStore stores canonical raw certificate, not an envelope.
    (tmp_path/c['certificate_path']).write_bytes(raw)
    c.update(version=2,identity_profile=REPLAY_IDENTITY_PROFILE,certificate_sha256=hashlib.sha256(raw).hexdigest())
    (tmp_path/'config/genie-server.json').write_text(json.dumps(c));return c,key

def test_server_v2_propagates_profile_without_remote_calls(tmp_path):
    c,key=replay_inputs(tmp_path);b=load_server_binding(tmp_path,mode='cloud',client_factory=lambda:fake_client(c))
    cap=b._dependencies.delta_publication
    assert cap.certificate_identity_profile==REPLAY_IDENTITY_PROFILE and cap.registry_lookup.__self__.identity_profile==REPLAY_IDENTITY_PROFILE
    assert b.readiness()['remote_verified'] is False

@pytest.mark.parametrize('change',[{'identity_profile':'arbitrary'},{'version':1},{'identity_profile':'strict_location_v1'},{'version':True}])
def test_profile_mismatch_rejects_before_sdk(tmp_path,change):
    c,_=replay_inputs(tmp_path);c.update(change);(tmp_path/'config/genie-server.json').write_text(json.dumps(c))
    calls=[]
    with pytest.raises(ValueError):load_server_binding(tmp_path,mode='cloud',client_factory=lambda:calls.append('sdk'))
    assert calls==[]

def test_remote_registry_explicit_replay_and_default_rejection():
    result=json.loads((ROOT/'runs/sk06-recovery-064-finalization/result.json').read_bytes());key=result['publication']['certificate_sha256']
    raw=(ROOT/f'deployment/state/phase-s-017/registry/{key}.json').read_bytes()
    class Missing(Exception):error_code='NOT_FOUND'
    class Files:
        def download(self,path):
            if '.revoked.' in path:raise Missing()
            return SimpleNamespace(contents=io.BytesIO(raw))
    with pytest.raises(ValueError):RemoteEvidence(Files(),'/Volumes/c/sbs_radar/v/registry').registry(certificate_sha256=key)
    out=RemoteEvidence(Files(),'/Volumes/c/sbs_radar/v/registry',identity_profile=REPLAY_IDENTITY_PROFILE).registry(certificate_sha256=key)
    assert out['publication_evidence_origin']=='replay_existing_statements'


def test_expired_registry_rejects_before_access_probe(tmp_path):
    c,key=replay_inputs(tmp_path);b=load_server_binding(tmp_path,mode='cloud',client_factory=lambda:fake_client(c))
    cap=b._dependencies.delta_publication
    envelope=json.loads((ROOT/f'deployment/state/phase-s-017/registry/{key}.json').read_bytes());registry=envelope['entry']['registry']
    from dataclasses import replace
    cap=replace(cap,registry_lookup=lambda **kw:registry)
    expiry=registry['valid_until_ms'];name=cap.certificate.as_dict()['tables'][0]['full_name']
    with pytest.raises(ValueError,match='REGISTRY_EXPIRED'):
        cap.verify(source_tables=[name],started_at_ms=expiry+1,ended_at_ms=expiry+1,executor_id=1,warehouse_id='warehouse',space_id='space')


def test_concrete_proposal_disabled_resource_pins_and_unverified_grants():
    c=json.loads((ROOT/'config/genie-server-068-proposal.json').read_bytes());r=json.loads((ROOT/c['runtime_config_path']).read_bytes())
    assert c['enabled'] is False and c['identity_profile']==REPLAY_IDENTITY_PROFILE
    assert c['executor_id']==77041447522099 and c['client_id']=='a947eccf-5f94-4369-a3d4-8f83b4ea98a1'
    assert c['genie_acl_object_id']=='/genie/2365958246005085'
    assert r['space_id']=='01f1bb81787b118c9bbc8980e3523a21' and r['warehouse_id']=='828756322bedff37'
    assert r['backend_select_only_grants_verified'] is False
    for path,key in [('runtime_config_path','runtime_config_sha256'),('certificate_path','certificate_sha256'),('policy_path','policy_sha256')]:assert hashlib.sha256((ROOT/c[path]).read_bytes()).hexdigest()==c[key]
