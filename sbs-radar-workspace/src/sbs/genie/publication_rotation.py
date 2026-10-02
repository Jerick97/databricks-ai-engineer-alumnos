"""Protected server generation selection. No SQL, SDK or mutation API.

The read capability must be provisioned by the server against an operator-owned
store; digests detect corruption, not publisher authentication. One generation
is retained for an entire request, while snapshot revocation is re-read.
"""
import json
import hashlib
import time
from copy import deepcopy
from . import canonical, digest
from .publication import Certificate, validate_certificate, require, REPLAY_IDENTITY_PROFILE, NAMED_IDENTITY_PROFILE
from .publication_registry import RegistryEntry, validate_entry

PROFILES=(REPLAY_IDENTITY_PROFILE,NAMED_IDENTITY_PROFILE)
TABLE_BINDINGS=('logical_name','full_name','uc_table_id','metastore_id','delta_table_id','location_sha256','delta_version','schema_sha256','content_sha256','row_count')

def sha(raw):return hashlib.sha256(raw).hexdigest()
def key(value):return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)
def invariant_policy(policy):return {k:v for k,v in policy.items() if k not in ('issued_at_ms','expires_at_ms')}
def snapshot_binding(certificate,mapping_sha256):
    p=certificate.as_dict()
    return digest(dict(snapshot=p['snapshot'],config_hash=p['config_hash'],mapping_sha256=mapping_sha256,tables=[{k:t[k] for k in TABLE_BINDINGS} for t in p['tables']]))

def generation(entry,admin_policy,*,identity_profile):
    """Package an already independently verified registry; never mint evidence."""
    p=validate_entry(entry,identity_profile=identity_profile)
    return canonical(dict(version=1,identity_profile=identity_profile,entry=p,admin_policy=admin_policy)).encode()

class RotationReader:
    def __init__(self,read,*,binding_sha256,policy_invariants_sha256,publisher_identity,publisher_executor_id,warehouse_id,clock=lambda:int(time.time()*1000)):
        require(callable(read) and key(binding_sha256) and key(policy_invariants_sha256),'ROTATION_SERVER_CAPABILITY_REQUIRED')
        require(isinstance(publisher_identity,str) and bool(publisher_identity) and type(publisher_executor_id) is int and publisher_executor_id>0 and isinstance(warehouse_id,str) and bool(warehouse_id),'ROTATION_PUBLISHER_INVALID')
        self.read=read;self.binding=binding_sha256;self.policy_pin=policy_invariants_sha256
        self.publisher=publisher_identity;self.executor=publisher_executor_id;self.warehouse=warehouse_id;self.clock=clock
    def _raw(self,name):
        raw=self.read(name);require(type(raw) is bytes and len(raw)<=2_000_000,'ROTATION_BYTES_INVALID');return raw
    def _active(self):
        p=json.loads(self._raw(self.binding+'.status.json'))
        require(p=={'binding_sha256':self.binding,'status':'active'},'ROTATION_SNAPSHOT_REVOKED')
    def select(self):
        self._active();pointer=json.loads(self._raw('current.json'))
        require(isinstance(pointer,dict) and set(pointer)=={'version','generation_sha256'} and type(pointer['version']) is int and pointer['version']==1 and key(pointer['generation_sha256']),'ROTATION_POINTER_INVALID')
        pin=pointer['generation_sha256'];raw=self._raw(pin+'.json');require(sha(raw)==pin,'ROTATION_GENERATION_HASH_MISMATCH')
        p=json.loads(raw)
        require(isinstance(p,dict) and set(p)=={'version','identity_profile','entry','admin_policy'} and type(p['version']) is int and p['version']==1 and p['identity_profile'] in PROFILES,'ROTATION_GENERATION_INVALID')
        entry=RegistryEntry(canonical(p['entry']).encode());e=validate_entry(entry,identity_profile=p['identity_profile'])
        cert=Certificate(canonical(e['certificate']).encode());validate_certificate(cert,identity_profile=p['identity_profile'])
        r=e['registry'];policy=p['admin_policy'];now=self.clock()
        require(snapshot_binding(cert,r['mapping_sha256'])==self.binding,'ROTATION_SNAPSHOT_CHANGED')
        require(digest(invariant_policy(policy))==self.policy_pin,'ROTATION_ADMIN_POLICY_CHANGED')
        start,end=policy.get('issued_at_ms'),policy.get('expires_at_ms')
        require(type(start) is int and type(end) is int and 0<=start<=now<end and 0<end-start<=1800000,'ROTATION_ADMIN_WINDOW_INVALID')
        require(e['policy']['evidence_mode']=='real' and e['policy']['publisher_identity']==self.publisher and type(e['policy']['executor_id']) is int and e['policy']['executor_id']==self.executor and e['policy']['warehouse_id']==self.warehouse,'ROTATION_PUBLISHER_CHANGED')
        require(0<e['policy']['ttl_ms']<=300000 and start<=r['valid_from_ms']<=now<r['valid_until_ms']<=end,'ROTATION_REGISTRY_EXPIRED')
        max_age=7200000 if p['identity_profile']==REPLAY_IDENTITY_PROFILE else 300000
        require(e['policy']['max_readback_age_ms']<=max_age,'ROTATION_READBACK_POLICY_INVALID')
        require(all(now-v['started_at_ms']<=e['policy']['max_readback_age_ms'] for v in r['readback_executions']),'ROTATION_READBACK_EXPIRED')
        return SelectedGeneration(self,pin,p,cert)

class SelectedGeneration:
    def __init__(self,reader,pin,payload,certificate):self.reader=reader;self.pin=pin;self._payload=deepcopy(payload);self.certificate=certificate
    @property
    def payload(self):return deepcopy(self._payload)
    def registry(self,*,certificate_sha256):
        self.reader._active()
        require(sha(self.reader._raw(self.pin+'.json'))==self.pin,'ROTATION_GENERATION_CHANGED')
        require(certificate_sha256==self.certificate.sha256,'ROTATION_CERTIFICATE_MISMATCH')
        r=self.payload['entry']['registry'];now=self.reader.clock();policy=self.payload['entry']['policy']
        require(r['valid_from_ms']<=now<r['valid_until_ms'],'ROTATION_REGISTRY_EXPIRED')
        require(all(now-v['started_at_ms']<=policy['max_readback_age_ms'] for v in r['readback_executions']),'ROTATION_READBACK_EXPIRED')
        return deepcopy(r)
    def policy_status(self,*,policy_id):
        self.reader._active()
        policy=self._payload['admin_policy'];now=self.reader.clock()
        require(policy['issued_at_ms']<=now<policy['expires_at_ms'],'ROTATION_ADMIN_WINDOW_INVALID')
        require(policy_id==policy['policy_id'],'ROTATION_POLICY_ID_MISMATCH')
        return 'active'
