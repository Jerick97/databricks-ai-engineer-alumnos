"""Fresh read-only publication through one pinned SQL Connector session.

Transport result normalization is explicit; it is not a captured SEA manifest.
The existing certificate and independent HistoryRegistryBuilder remain unchanged.
No imports initialize credentials, connector sessions, or network clients.
"""
import fcntl
import json
import os
import time
from pathlib import Path
from . import canonical, digest
from .publication import PublicationReader, require, sha, NAMED_IDENTITY_PROFILE
from .publication_registry import _directory, _append, _read, validate_entry
from .publication_rotation import generation, RotationReader

SET_CACHE = 'SET use_cached_result = false'


def require_governance_stable(before, after):
    """Reject observed global table drift; does not assert unobserved continuity."""
    require(isinstance(before,dict) and isinstance(after,dict)
            and isinstance(before.get('table_metadata_sha256'),str)
            and len(before['table_metadata_sha256'])==64
            and before['table_metadata_sha256']==after.get('table_metadata_sha256')
            and before.get('source_tables')==after.get('source_tables'),
            'FRESH_GLOBAL_TABLE_OBSERVATION_CHANGED')


class Journal:
    """A new phase only. Existing reservations require GET-only reconciliation.

    All intents are exclusive and fsynced before outbound execution. Reopening
    never sends SQL, even when the last outcome looks successful: a new session
    would lose SET and readback brackets. Do not delete this journal to retry.
    """
    def __init__(self, directory, *, plan_sha256):
        self.fd = _directory(directory, True)
        try:
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            _append(self.fd, 'binding.json', canonical(dict(phase='081', sql_cap=33, plan_sha256=plan_sha256)).encode())
            require(not any(n.startswith('intent-') for n in os.listdir(self.fd)), 'FRESH_RECONCILIATION_REQUIRED')
        except Exception:
            os.close(self.fd)
            raise
        self.count = 0

    def save(self, name, value):
        require('/' not in name and name.endswith('.json'), 'JOURNAL_NAME_INVALID')
        _append(self.fd, name, canonical(value).encode())

    def reserve(self, sql):
        require(self.count < 33, 'FRESH_SQL_QUOTA_EXCEEDED')
        ordinal = self.count + 1
        self.save(f'intent-{ordinal:02d}.json', dict(ordinal=ordinal, statement=sql, statement_sha256=sha(sql.encode()), reserved_at_ms=int(time.time()*1000), state='reserved_no_resend'))
        self.count = ordinal
        return ordinal

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None


class SessionReader(PublicationReader):
    """Reuse eight-table validation; replace only transport/result decoding."""
    def __init__(self, cursor, journal, *, allowed_sql, **kwargs):
        super().__init__(None, **kwargs)
        self.cursor, self.journal = cursor, journal
        self.allowed_sql = tuple(allowed_sql)
        self.cache_disabled = False
        self.position = 0
        self.ids = set()
        self.poisoned = False

    def _submit(self, sql):
        require(not self.poisoned,'FRESH_RECONCILIATION_REQUIRED')
        ordinal = self.journal.reserve(sql)
        self.poisoned = True
        try:
            self.cursor.execute(sql)
            sid = self.cursor.query_id
            require(isinstance(sid, str) and sid and sid not in self.ids, 'CONNECTOR_QUERY_ID_INVALID')
            self.ids.add(sid)
            self.journal.save(f'submission-{ordinal:02d}.json', dict(statement_id=sid, ordinal=ordinal))
            return ordinal, sid
        except Exception:
            raise ValueError('CONNECTOR_SUBMISSION_UNCONFIRMED_RECONCILIATION_REQUIRED') from None

    def disable_cache(self):
        require(not self.cache_disabled and self.journal.count == 0, 'CACHE_SETUP_ALREADY_ATTEMPTED')
        ordinal, sid = self._submit(SET_CACHE)
        # The server's SET command must finish before any SELECT; no new session.
        self.journal.save(f'result-{ordinal:02d}.json', dict(kind='session_configuration', statement_id=sid, transport='sql_connector_thrift'))
        self.cache_disabled = True
        self.poisoned = False
        return sid

    def _execute(self, sql):
        require(self.cache_disabled, 'FRESH_CACHE_SETUP_REQUIRED')
        require(self.position < len(self.allowed_sql) and sql == self.allowed_sql[self.position], 'FRESH_SQL_PLAN_MISMATCH')
        require(self.statements < self.max_statements, 'STATEMENT_QUOTA_EXCEEDED')
        self.statements += 1
        ordinal, sid = self._submit(sql)
        desc = self.cursor.description
        require(isinstance(desc, (list, tuple)) and desc, 'CONNECTOR_SCHEMA_MISSING')
        columns=[]
        for i,c in enumerate(desc):
            require(len(c)==7 and isinstance(c[0],str) and isinstance(c[1],str), 'CONNECTOR_SCHEMA_INVALID')
            columns.append(dict(name=c[0], type_name=c[1].upper(), position=i))
        require(len({c['name'] for c in columns})==len(columns), 'CONNECTOR_DUPLICATE_COLUMNS')
        rows=[];size=0
        for _ in range(self.max_rows + 1):
            try:batch = self.cursor.fetchmany(min(256, self.max_rows + 1-len(rows)))
            except Exception:raise ValueError('CONNECTOR_FETCH_UNCONFIRMED') from None
            require(isinstance(batch,list), 'CONNECTOR_ROWS_INVALID')
            if not batch:break
            require(len(rows)+len(batch)<=self.max_rows, 'CONNECTOR_ROW_CAP')
            for row in batch:
                require(len(row)==len(columns), 'CONNECTOR_ROW_WIDTH')
                normalized=[]
                for value in row:
                    # Existing validator consumes SQL JSON scalar representations.
                    # Complex DETAIL/HISTORY values are retained as canonical JSON.
                    if value is None or isinstance(value,str):normalized.append(value)
                    elif type(value) is bool:normalized.append('true' if value else 'false')
                    elif type(value) in (int,float):normalized.append(str(value))
                    elif isinstance(value,(dict,list,tuple)):normalized.append(canonical(value))
                    elif hasattr(value,'isoformat'):normalized.append(value.isoformat())
                    else:raise ValueError('CONNECTOR_VALUE_TYPE_UNSUPPORTED')
                size+=len(canonical(normalized).encode())
                require(size<=self.max_bytes,'CONNECTOR_BYTE_CAP')
                rows.append(normalized)
        else:raise ValueError('CONNECTOR_FETCH_CAP')
        require(self.cursor.query_id==sid, 'CONNECTOR_QUERY_ID_CHANGED')
        manifest=dict(transport='databricks_sql_connector_thrift', normalization='sbs-connector-scalars-v1', schema=columns, complete_fetch_eof=True, row_count=len(rows))
        proof=dict(statement_id=sid, sql_sha256=sha(sql.encode()), manifest_sha256=digest(manifest), wire_rows_sha256=digest(rows), row_count=len(rows), evidence_mode=self.mode)
        self.journal.save(f'result-{ordinal:02d}.json',dict(manifest=manifest,normalized_rows=rows,proof=proof))
        self.position += 1
        self.poisoned = False
        return columns, rows, proof


def publish_generation(entry, admin_policy, *, rotation, read, put, journal, clock=lambda:int(time.time()*1000)):
    """Protected Files capabilities; stage/readback before mutable pointer.

    A lost PUT response is reconciled by bytes. Never resend an unknown PUT.
    Snapshot status must already be active via a separate administrative action.
    """
    validate_entry(entry, identity_profile=NAMED_IDENTITY_PROFILE)
    raw=generation(entry,admin_policy,identity_profile=NAMED_IDENTITY_PROFILE)
    pin=sha(raw);name=pin+'.json'
    pointer=canonical(dict(version=1,generation_sha256=pin)).encode()
    candidate={name:raw,'current.json':pointer}
    def candidate_read(key):return candidate[key] if key in candidate else read(key)
    def select(get):
        return RotationReader(get,binding_sha256=rotation['snapshot_binding_sha256'],policy_invariants_sha256=rotation['policy_invariants_sha256'],publisher_identity=rotation['publisher_identity'],publisher_executor_id=rotation['publisher_executor_id'],warehouse_id=rotation['warehouse_id'],clock=clock).select()
    select(candidate_read)
    for key,data,overwrite in ((name,raw,False),('current.json',pointer,True)):
        # Recheck age and revocation immediately before each side effect.
        select(candidate_read)
        journal.save('files-intent-'+('generation' if not overwrite else 'pointer')+'.json',dict(name=key,sha256=sha(data),overwrite=overwrite))
        try:put(key,data,overwrite=overwrite)
        except Exception:
            try:observed=read(key)
            except Exception:raise ValueError('FILES_PUT_UNCONFIRMED_NO_RESEND') from None
            require(observed==data,'FILES_PUT_UNCONFIRMED_NO_RESEND')
        require(read(key)==data,'FILES_READBACK_MISMATCH')
    selected=select(read)
    require(selected.pin==pin,'FILES_POINTER_RACE')
    journal.save('published.json',dict(generation_sha256=pin,certificate_sha256=selected.certificate.sha256))
    return pin


def initialize_snapshot_status(binding, *, read, put, journal):
    """Separate administrative create-only action. A revocation is never replaced."""
    name=binding+'.status.json';data=canonical(dict(binding_sha256=binding,status='active')).encode()
    journal.save('files-intent-status.json',dict(name=name,sha256=sha(data),overwrite=False))
    try:put(name,data,overwrite=False)
    except Exception:pass  # Reconcile only; no second PUT, including conflicts.
    require(read(name)==data,'FRESH_STATUS_REVOKED_OR_UNCONFIRMED')
