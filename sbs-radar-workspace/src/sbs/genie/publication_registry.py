"""Executable GET-only publisher history adapter and append-only local registry.

All constructors are server capabilities, never request deserializers. Production
must supply authenticated WorkspaceClient.query_history and a protected directory.
Fixtures cannot establish actual origin. No SQL, compute, grants, or governance
proof is generated here. Identity/access remains a separate Delta dependency.
"""
from dataclasses import dataclass,asdict
from pathlib import Path
import hashlib
import json
import os
import fcntl
import time
import uuid
from . import canonical,digest
from .publication import Certificate,validate_certificate,require,STRICT_IDENTITY_PROFILE,REPLAY_IDENTITY_PROFILE,identity_profile_check


def _hash(v):return isinstance(v,str) and len(v)==64 and all(c in '0123456789abcdef' for c in v)
def _int(v):return type(v) is int and v>=0
def _text(v):return isinstance(v,str) and bool(v)
def _sha(v):return hashlib.sha256(v).hexdigest()
def _obj(v):return v.as_dict() if hasattr(v,'as_dict') else v


@dataclass(frozen=True)
class PublisherPolicy:
    certificate_sha256: str
    mapping_sha256: str
    snapshot: str
    config_hash: str
    publisher_identity: str
    warehouse_id: str
    executor_id: int
    ttl_ms: int
    max_readback_age_ms: int
    evidence_mode: str = 'real'

    def __post_init__(self):
        require(all(_hash(v) for v in (self.certificate_sha256,self.mapping_sha256,self.snapshot,self.config_hash)),'REGISTRY_PINS_REQUIRED')
        require(_text(self.publisher_identity) and _text(self.warehouse_id) and _int(self.executor_id),'PUBLISHER_IDENTITY_REQUIRED')
        require(_int(self.ttl_ms) and self.ttl_ms>0 and _int(self.max_readback_age_ms) and self.max_readback_age_ms>0,'REGISTRY_TTL_REQUIRED')
        require(self.evidence_mode in ('fixture','real'),'REGISTRY_MODE_REQUIRED')


def _certificate(cert,policy,identity_profile=STRICT_IDENTITY_PROFILE):
    p=validate_certificate(cert,identity_profile=identity_profile)
    require(cert.payload==canonical(p).encode(),'REGISTRY_CANONICAL_CERTIFICATE_REQUIRED')
    require(cert.sha256==policy.certificate_sha256 and p['snapshot']==policy.snapshot and p['config_hash']==policy.config_hash
            and p['evidence_mode']==policy.evidence_mode,'REGISTRY_CERTIFICATE_PIN_MISMATCH')
    proofs=[e for t in p['tables'] for e in t['evidence']]
    ids=[e['statement_id'] for e in proofs]
    require(len(ids)==32 and len(set(ids))==32 and all(len(i)<=128 for i in ids),'UNIQUE_32_STATEMENTS_REQUIRED')
    return proofs


def _observed(row,proof,policy,position):
    require(isinstance(row,dict),'PUBLISHER_HISTORY_INVALID')
    require(len(canonical(row).encode())<=64000,'PUBLISHER_HISTORY_TOO_LARGE')
    query=row.get('query_text')
    require(_text(query) and len(query)<=16384,'PUBLISHER_SQL_UNAVAILABLE')
    actual_sha=_sha(query.encode())
    require(row.get('query_id')==proof['statement_id'] and actual_sha==proof['sql_sha256']
            and row.get('warehouse_id')==policy.warehouse_id
            and type(row.get('executed_as_user_id')) is int and row['executed_as_user_id']==policy.executor_id
            and row.get('status')=='FINISHED' and row.get('is_final') is True
            and not row.get('cache_query_id') and not row.get('error_message'), 'PUBLISHER_HISTORY_NOT_VERIFIED')
    # The supported history profile accepts DESCRIBE or OTHER for DESCRIBE.
    # Exact observed SQL hash already binds the closed DESCRIBE/SELECT plan.
    require(row.get('statement_type') in (('SELECT',) if position%4==2 else ('DESCRIBE','OTHER')),'PUBLISHER_STATEMENT_TYPE_INVALID')
    start,end=row.get('query_start_time_ms'),row.get('execution_end_time_ms')
    require(_int(start) and _int(end) and start<=end,'PUBLISHER_TIME_INVALID')
    return dict(statement_id=row['query_id'],observed_sql_sha256=actual_sha,warehouse_id=row['warehouse_id'],
        executor_id=row['executed_as_user_id'],status=row['status'],is_final=row['is_final'],started_at_ms=start,ended_at_ms=end,
        history_record_sha256=digest(row))


@dataclass(frozen=True)
class RegistryEntry:
    payload: bytes
    @property
    def sha256(self):return _sha(self.payload)
    def as_dict(self):return json.loads(self.payload)


def _entry(cert,policy,history,issued_at_ms,identity_profile=STRICT_IDENTITY_PROFILE):
    proofs=_certificate(cert,policy,identity_profile)
    require(isinstance(history,list) and len(history)==32 and _int(issued_at_ms),'REGISTRY_HISTORY_CLOSURE_INVALID')
    observed=[_observed(row,p,policy,i) for i,(row,p) in enumerate(zip(history,proofs))]
    if identity_profile==REPLAY_IDENTITY_PROFILE:
        replay=cert.as_dict()['replay_evidence']
        require(0<=issued_at_ms-replay['current_metadata_at_ms']<=60000,'REPLAY_CURRENT_METADATA_EXPIRED')
        require(policy.max_readback_age_ms<=7200000,'REPLAY_READBACK_AGE_LIMIT')
    require(all(issued_at_ms-policy.max_readback_age_ms<=e['started_at_ms']<=e['ended_at_ms']<=issued_at_ms for e in observed), 'REGISTRY_READBACK_TIME_OUTSIDE_POLICY')
    evidence=dict(certificate_sha256=cert.sha256,mapping_sha256=policy.mapping_sha256,status='active',evidence_mode=policy.evidence_mode,
        publisher_identity=policy.publisher_identity,publisher_warehouse_id=policy.warehouse_id,publisher_executor_id=policy.executor_id,
        readback_execution_verified=True,valid_from_ms=issued_at_ms,valid_until_ms=issued_at_ms+policy.ttl_ms,
        readback_executions=observed,policy_sha256=digest(asdict(policy)))
    if identity_profile!=STRICT_IDENTITY_PROFILE:evidence['identity_profile']=identity_profile
    if identity_profile==REPLAY_IDENTITY_PROFILE:evidence.update(publication_evidence_origin='replay_existing_statements',select_bracketed_by_detail=False,current_metadata_at_ms=replay['current_metadata_at_ms'],max_readback_age_ms=policy.max_readback_age_ms)
    evidence['attestation_id']=digest(evidence)
    return dict(version=1,certificate=cert.as_dict(),policy=asdict(policy),issued_at_ms=issued_at_ms,history_records=history,registry=evidence)


def validate_entry(entry,*,identity_profile=STRICT_IDENTITY_PROFILE):
    require(isinstance(entry,RegistryEntry) and type(entry.payload) is bytes,'REGISTRY_ENTRY_INVALID')
    try:
        p=entry.as_dict()
        require(entry.payload==canonical(p).encode(),'REGISTRY_CANONICAL_ENTRY_REQUIRED')
        require(isinstance(p,dict) and set(p)=={'version','certificate','policy','issued_at_ms','history_records','registry'} and type(p['version']) is int and p['version']==1,'REGISTRY_ENTRY_INVALID')
        policy=PublisherPolicy(**p['policy']);cert=Certificate(canonical(p['certificate']).encode())
        expected=_entry(cert,policy,p['history_records'],p['issued_at_ms'],identity_profile)
        require(canonical(p)==canonical(expected),'REGISTRY_ENTRY_EVIDENCE_MISMATCH')
        return p
    except (TypeError,KeyError,json.JSONDecodeError,UnicodeError):raise ValueError('REGISTRY_ENTRY_INVALID') from None


class HistoryRegistryBuilder:
    """Use WorkspaceClient.query_history; list() is GET /sql/history/queries.

    Exactly one complete history record per statement, bounded pagination. Missing
    history/SQL/attribution rejects instead of falling back to submitted SQL.
    clock is a trusted server clock; the caller cannot supply an issuance time.
    """
    def __init__(self,query_history,policy,*,clock=None,max_pages=2,identity_profile=STRICT_IDENTITY_PROFILE):
        identity_profile_check(identity_profile);self.identity_profile=identity_profile
        require(isinstance(policy,PublisherPolicy) and callable(getattr(query_history,'list',None)),'REGISTRY_SERVER_CAPABILITIES_REQUIRED')
        require(type(max_pages) is int and 1<=max_pages<=3,'REGISTRY_PAGINATION_CAP_INVALID')
        self.history=query_history;self.policy=policy;self.clock=clock or (lambda:int(time.time()*1000));self.max_pages=max_pages

    def _get(self,statement_id):
        from databricks.sdk.service.sql import QueryFilter
        rows=[];token=None;seen=set()
        for _ in range(self.max_pages):
            kw=dict(filter_by=QueryFilter(statement_ids=[statement_id],warehouse_ids=[self.policy.warehouse_id]),max_results=2,include_metrics=False)
            if token is not None:kw['page_token']=token
            try:r=_obj(self.history.list(**kw))
            except Exception as e:
                if isinstance(e,PermissionError) or getattr(e,'error_code',None) in ('PERMISSION_DENIED','UNAUTHENTICATED'):raise PermissionError('PUBLISHER_HISTORY_DENIED') from None
                raise ValueError('PUBLISHER_HISTORY_UNAVAILABLE') from None
            require(isinstance(r,dict) and isinstance(r.get('res'),list) and len(r['res'])<=2,'PUBLISHER_HISTORY_INVALID')
            rows.extend(r['res']);require(len(rows)<=1,'EXACT_PUBLISHER_HISTORY_REQUIRED')
            more=r.get('has_next_page',False);require(type(more) is bool,'PUBLISHER_PAGINATION_INVALID')
            if not more:
                require(not r.get('next_page_token'),'PUBLISHER_PAGINATION_INVALID')
                break
            token=r.get('next_page_token');require(_text(token) and token not in seen,'PUBLISHER_PAGINATION_INVALID');seen.add(token)
        else:raise ValueError('PUBLISHER_PAGINATION_LIMIT')
        require(len(rows)==1,'EXACT_PUBLISHER_HISTORY_REQUIRED')
        return rows[0]

    def build(self,certificate):
        proofs=_certificate(certificate,self.policy,self.identity_profile);rows=[]
        for i,p in enumerate(proofs):
            row=self._get(p['statement_id']);_observed(row,p,self.policy,i);rows.append(row)
        payload=_entry(certificate,self.policy,rows,self.clock(),self.identity_profile)
        return RegistryEntry(canonical(payload).encode())


def _directory(path,create):
    """Walk with dir-fds and O_NOFOLLOW, including ancestors; no symlink escapes."""
    path=Path(path).absolute();require('..' not in path.parts,'REGISTRY_PATH_INVALID')
    fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            if create:
                try:os.mkdir(part,mode=0o700,dir_fd=fd)
                except FileExistsError:pass
            new=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=new
        return fd
    except Exception:os.close(fd);raise


def _read(fd,name):
    f=os.open(name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=fd)
    with os.fdopen(f,'rb') as stream:
        data=stream.read(4_000_001)
    require(len(data)<=4_000_000,'REGISTRY_FILE_TOO_LARGE');return data


def _append(fd,name,data):
    temp='.pending-'+uuid.uuid4().hex
    f=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=fd)
    try:
        with os.fdopen(f,'wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
        try:os.link(temp,name,src_dir_fd=fd,dst_dir_fd=fd,follow_symlinks=False)
        except FileExistsError:require(_read(fd,name)==data,'REGISTRY_IMMUTABLE_CONFLICT')
        os.fsync(fd)
    finally:os.unlink(temp,dir_fd=fd)


class RegistryLookup:
    """Read-only capability for DeltaPublication.registry_lookup. No mutator API."""
    def __init__(self,directory,*,identity_profile=STRICT_IDENTITY_PROFILE):
        identity_profile_check(identity_profile);self.identity_profile=identity_profile
        self._path=Path(directory).absolute();fd=_directory(self._path,False)
        try:st=os.fstat(fd);self._identity=(st.st_dev,st.st_ino)
        finally:os.close(fd)

    def _open(self):
        fd=_directory(self._path,False);st=os.fstat(fd)
        if (st.st_dev,st.st_ino)!=self._identity:os.close(fd);raise ValueError('REGISTRY_DIRECTORY_CHANGED')
        return fd

    def __call__(self,*,certificate_sha256):
        require(_hash(certificate_sha256),'REGISTRY_CERTIFICATE_KEY_INVALID');fd=self._open()
        try:
            fcntl.flock(fd,fcntl.LOCK_SH)
            try:raw=_read(fd,certificate_sha256+'.json')
            except FileNotFoundError:return None
            envelope=json.loads(raw)
            require(set(envelope)=={'sha256','entry'} and _hash(envelope['sha256']),'REGISTRY_ENVELOPE_INVALID')
            entry=RegistryEntry(canonical(envelope['entry']).encode());require(entry.sha256==envelope['sha256'],'REGISTRY_HASH_MISMATCH')
            p=validate_entry(entry,identity_profile=self.identity_profile);require(p['registry']['certificate_sha256']==certificate_sha256,'REGISTRY_KEY_MISMATCH')
            out=p['registry']
            try:rev=json.loads(_read(fd,certificate_sha256+'.revoked.json'))
            except FileNotFoundError:return out
            require(set(rev)=={'certificate_sha256','entry_sha256','status','administrator','reason','revoked_at_ms'}
                    and rev['certificate_sha256']==certificate_sha256 and rev['entry_sha256']==entry.sha256 and rev['status']=='revoked'
                    and _text(rev['administrator']) and rev['reason'] in REASONS and _int(rev['revoked_at_ms']),'REGISTRY_REVOCATION_INVALID')
            return {**out,'status':'revoked','revocation':rev}
        finally:os.close(fd)


REASONS=('administrative','identity_change','retention_lost','permission_change')


class RegistryAdmin:
    """Server administrator capability. Do not expose it to client routes.

    Files and revocation tombstones append once; revocation is terminal. Filesystem
    ownership is the trust anchor, not self-authenticating hashes or actor strings.
    """
    def __init__(self,directory,*,administrator,clock=None,identity_profile=STRICT_IDENTITY_PROFILE):
        identity_profile_check(identity_profile);self.identity_profile=identity_profile
        require(_text(administrator),'REGISTRY_ADMINISTRATOR_REQUIRED')
        fd=_directory(directory,True);os.close(fd)
        self.lookup=RegistryLookup(directory,identity_profile=identity_profile);self.administrator=administrator;self.clock=clock or (lambda:int(time.time()*1000))

    def publish(self,entry):
        p=validate_entry(entry,identity_profile=self.identity_profile);key=p['registry']['certificate_sha256'];fd=self.lookup._open()
        try:
            fcntl.flock(fd,fcntl.LOCK_EX)
            # A revoked certificate can never be activated by republishing.
            try:_read(fd,key+'.revoked.json')
            except FileNotFoundError:pass
            else:raise ValueError('REGISTRY_CERTIFICATE_REVOKED')
            _append(fd,key+'.json',canonical(dict(sha256=entry.sha256,entry=p)).encode())
            return key
        finally:os.close(fd)

    def revoke(self,certificate_sha256,*,reason):
        require(_hash(certificate_sha256) and reason in REASONS,'REGISTRY_REVOCATION_REQUEST_INVALID')
        # Read validated current entry before taking exclusive lock (avoid nested flock).
        require(self.lookup(certificate_sha256=certificate_sha256) is not None,'REGISTRY_PUBLICATION_MISSING')
        fd=self.lookup._open()
        try:
            fcntl.flock(fd,fcntl.LOCK_EX)
            envelope=json.loads(_read(fd,certificate_sha256+'.json'));stamp=self.clock();require(_int(stamp),'REGISTRY_CLOCK_INVALID')
            rev=dict(certificate_sha256=certificate_sha256,entry_sha256=envelope['sha256'],status='revoked',administrator=self.administrator,reason=reason,revoked_at_ms=stamp)
            try:existing=json.loads(_read(fd,certificate_sha256+'.revoked.json'))
            except FileNotFoundError:_append(fd,certificate_sha256+'.revoked.json',canonical(rev).encode())
            else:return existing
            return rev
        finally:os.close(fd)
