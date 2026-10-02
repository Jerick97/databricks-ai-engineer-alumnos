"""078 offline fixtures reuse captured064 bytes; no current remote attestation."""
import json
from copy import deepcopy
from pathlib import Path
import pytest
from sbs.genie import canonical,digest
from sbs.genie.publication import Certificate,REPLAY_IDENTITY_PROFILE
from sbs.genie.publication_registry import RegistryEntry,_entry,PublisherPolicy
from sbs.genie.publication_rotation import RotationReader,generation,sha,snapshot_binding,invariant_policy
ROOT=Path(__file__).resolve().parents[2]

def setup():
    c=json.loads((ROOT/'config/genie-server-068-proposal.json').read_bytes())
    envelope=json.loads((ROOT/('deployment/state/phase-s-017/registry/'+c['certificate_sha256']+'.json')).read_bytes())
    entry=RegistryEntry(canonical(envelope['entry']).encode());p=entry.as_dict();cert=Certificate(canonical(p['certificate']).encode())
    now=[p['issued_at_ms']];ap=json.loads((ROOT/c['policy_path']).read_bytes());ap.update(issued_at_ms=now[0]-1,expires_at_ms=now[0]+600000)
    binding=snapshot_binding(cert,p['policy']['mapping_sha256']);data={binding+'.status.json':canonical(dict(binding_sha256=binding,status='active')).encode()}
    def install(e=entry,a=ap):
        raw=generation(e,a,identity_profile=REPLAY_IDENTITY_PROFILE);pin=sha(raw);data[pin+'.json']=raw;data['current.json']=canonical(dict(version=1,generation_sha256=pin)).encode();return pin
    install();pol=p['policy'];reader=RotationReader(data.__getitem__,binding_sha256=binding,policy_invariants_sha256=digest(invariant_policy(ap)),publisher_identity=pol['publisher_identity'],publisher_executor_id=pol['executor_id'],warehouse_id=pol['warehouse_id'],clock=lambda:now[0])
    return reader,data,now,entry,ap,install

def test_select_request_pin_survives_pointer_rotation_but_not_global_revocation():
    r,data,now,entry,ap,install=setup();first=r.select();p=entry.as_dict();p['certificate']['replay_evidence']['current_metadata_at_ms']+=1
    cert=Certificate(canonical(p['certificate']).encode());policy=PublisherPolicy(**{**p['policy'],'certificate_sha256':cert.sha256})
    now[0]+=1;other=RegistryEntry(canonical(_entry(cert,policy,p['history_records'],now[0],REPLAY_IDENTITY_PROFILE)).encode());install(other)
    second=r.select();assert second.pin!=first.pin and second.certificate.sha256!=first.certificate.sha256
    assert first.registry(certificate_sha256=first.certificate.sha256)['certificate_sha256']==first.certificate.sha256
    data[r.binding+'.status.json']=canonical(dict(binding_sha256=r.binding,status='revoked')).encode()
    for selected in (first,second):
        with pytest.raises(ValueError,match='REVOKED'):selected.registry(certificate_sha256=selected.certificate.sha256)
    with pytest.raises(ValueError,match='REVOKED'):r.select()

def test_selected_payload_cannot_change_frozen_registry_or_policy():
    r,data,now,entry,ap,install=setup();s=r.select();s.payload['entry']['registry']['valid_until_ms']=10**16;s.payload['admin_policy']['policy_id']='injected'
    assert s.payload['admin_policy']['policy_id']==ap['policy_id']
    now[0]=entry.as_dict()['registry']['valid_until_ms']
    with pytest.raises(ValueError,match='EXPIRED'):s.registry(certificate_sha256=s.certificate.sha256)

def test_policy_status_checks_its_time_independently():
    r,data,now,entry,ap,install=setup();s=r.select();now[0]=ap['expires_at_ms']
    with pytest.raises(ValueError,match='ADMIN_WINDOW'):s.policy_status(policy_id=ap['policy_id'])

@pytest.mark.parametrize('kind',['hash','pointer','policy','binding','expired','readback','publisher'])
def test_rotation_rejects_incoherent_generation(kind):
    r,data,now,entry,ap,install=setup()
    if kind=='hash':data[json.loads(data['current.json'])['generation_sha256']+'.json']+=b' '
    elif kind=='pointer':data['current.json']=b'{"version":true,"generation_sha256":"bad"}'
    elif kind=='policy':ap['namespace']='other.sbs_radar';install()
    elif kind=='binding':r.binding='f'*64;data[r.binding+'.status.json']=canonical(dict(binding_sha256=r.binding,status='active')).encode()
    elif kind=='expired':now[0]+=300000
    elif kind=='readback':now[0]+=7200001
    else:r.publisher='different'
    with pytest.raises(ValueError):r.select()

def test_context_rejects_before_remote_and_each_valid_request_selects():
    from types import SimpleNamespace
    from sbs.genie.server_rotation import RotatingBinding
    events=[]
    def refs(context):
        if context!='valid':raise ValueError('bad context')
    def select():events.append('select');return object()
    base=SimpleNamespace(_catalog=SimpleNamespace(references=refs),readiness=lambda:{'available':False})
    def assemble(selected):return SimpleNamespace(ask_scoped=lambda *a,**kw:{'status':'completed'})
    b=RotatingBinding(base,SimpleNamespace(select=select),assemble)
    assert b.ask_scoped('x',context='bad')['status']=='conflict' and not events
    for _ in range(2):assert b.ask_scoped('x',context='valid')['status']=='completed'
    assert events==['select','select']

def test_concrete_loader_config_builds_without_remote_io():
    from types import SimpleNamespace
    from sbs.genie.server_rotation import load_rotating_server_binding
    server=json.loads((ROOT/'config/genie-server-068-proposal.json').read_bytes());calls=[]
    class Files:
        def download(self,*a,**kw):calls.append(a);raise AssertionError('remote before request')
    client=SimpleNamespace(config=SimpleNamespace(host=server['workspace_host'],auth_type='oauth-m2m',client_id=server['client_id']),files=Files())
    binding=load_rotating_server_binding(ROOT,mode='cloud',client_factory=lambda:client)
    assert binding.readiness()['rotation_enabled'] is True and binding.readiness()['remote_verified'] is False and calls==[]
    assert binding.rag_snapshot and binding.genie_snapshot and binding.mapping_sha256


def test_fresh_sql_plan_is_exact_32_read_only_and_preserves_old_ledger():
    p=json.loads((ROOT/'deployment/genie-fresh-readback-078-plan.json').read_bytes())
    assert p['sql_cap']==32 and len(p['statements'])==32 and p['new_ledger_created'] is False
    assert len(set(s['table'] for s in p['statements']))==8
    assert p['previous_ledger']['reserved']==99 and p['previous_ledger']['limit']==112 and p['previous_ledger']['submission_records']==96
    assert sha((ROOT/p['previous_ledger']['path']).read_bytes())==p['previous_ledger']['sha256']
    assert not (ROOT/p['new_ledger_path']).exists()
    for i,s in enumerate(p['statements']):
        assert s['ordinal']==i+1 and sha(s['statement'].encode())==s['statement_sha256']
        assert s['statement'].startswith(('SELECT ','DESCRIBE DETAIL ','DESCRIBE HISTORY '))
