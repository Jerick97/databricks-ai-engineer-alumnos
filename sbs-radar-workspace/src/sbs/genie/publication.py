"""Delta readback certificates, separate from the current interval runtime.

All constructor dependencies/configuration are SERVER capabilities, never request
fields. SDK injection does not authenticate an adapter; evidence_mode is assigned
by trusted integration. Fixture certificates cannot establish remote publication.
No DDL, warehouse start, grants, release-pointer change, or automatic retries.
The SDK itself must be configured without automatic POST retries by integration.
"""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from . import TABLES, COLUMNS, canonical, digest


def require(condition, code):
    if not condition:raise ValueError(code)


def sha(value):return hashlib.sha256(value).hexdigest()

def obj(value):return value.as_dict() if hasattr(value,'as_dict') else value

def integer(value):return type(value) is int and value>=0

STRICT_IDENTITY_PROFILE='strict_location_v1'
NAMED_IDENTITY_PROFILE='uc_managed_named_detail_v1'
REPLAY_IDENTITY_PROFILE='uc_managed_named_replay_v1'


def identity_profile_check(profile):
    require(profile in (STRICT_IDENTITY_PROFILE,NAMED_IDENTITY_PROFILE,REPLAY_IDENTITY_PROFILE),'IDENTITY_PROFILE_INVALID')


def _detail_identity(detail,columns,identity,profile):
    require(detail.get('format')=='delta' and _text(detail.get('id')),'DELTA_IDENTITY_INVALID')
    if profile==STRICT_IDENTITY_PROFILE:
        require(detail.get('location')==identity['storage_location'],'DELTA_IDENTITY_INVALID')
        return None
    types={c['name']:c['type_name'] for c in columns}
    require(types.get('name')=='STRING' and detail.get('name')==identity['full_name'],'DELTA_NAME_IDENTITY_INVALID')
    location=detail.get('location')
    require(type(location) is str and location in ('',identity['storage_location']),'DELTA_LOCATION_CONFLICT')
    return dict(source='uc_metadata',detail_name=detail['name'],detail_location_observation='empty' if location=='' else 'matched',physical_location_relation_observed=location!='')


def _detail(columns,data):
    require(len(data)==1,'DELTA_DETAIL_INVALID')
    types={c['name']:c['type_name'] for c in columns}
    require(all(types.get(k)=='STRING' for k in ('format','id','location')),'DETAIL_SCHEMA_INVALID')
    return dict(zip([c['name'] for c in columns],data[0]))


@dataclass(frozen=True)
class PublicationPlan:
    payload: bytes
    def as_dict(self):return json.loads(self.payload)


@dataclass(frozen=True)
class Certificate:
    payload: bytes
    @property
    def sha256(self):return sha(self.payload)
    def as_dict(self):return json.loads(self.payload)


def _closed(value, keys, code):
    require(isinstance(value,dict) and set(value)==set(keys.split()),code)


def _hash(value):return isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value) is not None


def _text(value):return isinstance(value,str) and bool(value)


def _decode(payload,code):
    require(type(payload) is bytes,code)
    try:value=json.loads(payload)
    except (ValueError,UnicodeError):raise ValueError(code) from None
    require(isinstance(value,dict),code)
    return value


def _table_set(tables,code):
    require(isinstance(tables,list) and len(tables)==len(TABLES),code)
    require(all(isinstance(t,dict) for t in tables),code)
    require([t.get('logical_name') for t in tables]==list(TABLES),code)
    catalogs=set()
    for t in tables:
        name=t.get('full_name');require(isinstance(name,str),code);parts=name.split('.')
        require(len(parts)==3 and all(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',p) for p in parts)
                and parts[1]=='sbs_radar' and parts[2]==t['logical_name'],code)
        catalogs.add(parts[0])
        require(integer(t.get('delta_version')) and integer(t.get('row_count')),code)
    require(len(catalogs)==1,code)


def _sqls(t):
    name='.'.join('`'+p+'`' for p in t['full_name'].split('.'))
    return ['DESCRIBE DETAIL '+name,'DESCRIBE HISTORY '+name,
            'SELECT '+', '.join('`'+c+'`' for c in COLUMNS)+' FROM '+name+' VERSION AS OF '+str(t['delta_version'])]


def validate_plan(plan):
    require(isinstance(plan,PublicationPlan),'SERVER_PLAN_REQUIRED')
    p=_decode(plan.payload,'PLAN_INVALID')
    _closed(p,'snapshot config_hash tables','PLAN_INVALID')
    require(_hash(p['snapshot']) and _hash(p['config_hash']),'PLAN_INVALID')
    _table_set(p['tables'],'PLAN_INVALID')
    for t in p['tables']:
        _closed(t,'logical_name full_name delta_version expected_sha256 row_count detail_sql history_sql readback_sql','PLAN_INVALID')
        require(_hash(t['expected_sha256']),'PLAN_INVALID')
        require(_sqls(t)==[t['detail_sql'],t['history_sql'],t['readback_sql']],'PLAN_SQL_INVALID')
    return p


def validate_certificate(certificate,*,identity_profile=STRICT_IDENTITY_PROFILE):
    require(isinstance(certificate,Certificate),'CERTIFICATE_INVALID')
    p=_decode(certificate.payload,'CERTIFICATE_INVALID')
    identity_profile_check(identity_profile)
    require(p.get('identity_profile',STRICT_IDENTITY_PROFILE)==identity_profile,'CERTIFICATE_IDENTITY_PROFILE_MISMATCH')
    profiled=identity_profile!=STRICT_IDENTITY_PROFILE
    _closed(p,'version mode snapshot config_hash evidence_mode aba_prevented tables governance_evidence_sha256 governance_evidence_id canonicalization limitations'+(' identity_profile' if profiled else '')+(' replay_evidence' if identity_profile==REPLAY_IDENTITY_PROFILE else ''),'CERTIFICATE_INVALID')
    require(type(p['version']) is int and p['version']==2 and p['mode']=='delta_version'
            and p['evidence_mode'] in ('fixture','real') and p['aba_prevented'] is False,'CERTIFICATE_INVALID')
    require(all(_hash(p[k]) for k in ('snapshot','config_hash','governance_evidence_sha256'))
            and _text(p['governance_evidence_id']) and p['canonicalization']=='sbs-curated-json-sorted-id-v1'
            and isinstance(p['limitations'],list) and p['limitations'] and all(_text(v) for v in p['limitations']),'CERTIFICATE_INVALID')
    _table_set(p['tables'],'CERTIFICATE_INVALID')
    expectedtypes=['BOOLEAN' if c in ('synthetic','human_approved') else 'STRING' for c in COLUMNS]
    for t in p['tables']:
        _closed(t,'logical_name full_name uc_table_id metastore_id delta_table_id location_sha256 delta_version schema_sha256 content_sha256 row_count evidence'+(' location_evidence' if profiled else ''),'CERTIFICATE_INVALID')
        require(all(_text(t[k]) for k in ('uc_table_id','metastore_id','delta_table_id'))
                and all(_hash(t[k]) for k in ('location_sha256','schema_sha256','content_sha256'))
                and t['schema_sha256']==digest(list(zip(COLUMNS,expectedtypes))),'CERTIFICATE_INVALID')
        if profiled:
            le=t['location_evidence']
            _closed(le,'source detail_name detail_location_observation physical_location_relation_observed','CERTIFICATE_LOCATION_EVIDENCE_INVALID')
            require(le['source']=='uc_metadata' and le['detail_name']==t['full_name'] and le['detail_location_observation'] in ('empty','matched') and type(le['physical_location_relation_observed']) is bool and le['physical_location_relation_observed']==(le['detail_location_observation']=='matched'),'CERTIFICATE_LOCATION_EVIDENCE_INVALID')
        proofs=t['evidence'];require(isinstance(proofs,list) and len(proofs)==4,'CERTIFICATE_INVALID')
        sqls=_sqls(t)
        for i,e in enumerate(proofs):
            _closed(e,'statement_id sql_sha256 manifest_sha256 wire_rows_sha256 row_count evidence_mode','CERTIFICATE_INVALID')
            require(_text(e['statement_id']) and integer(e['row_count']) and e['evidence_mode']==p['evidence_mode']
                    and all(_hash(e[k]) for k in ('sql_sha256','manifest_sha256','wire_rows_sha256'))
                    and e['sql_sha256']==sha(sqls[i if i<3 else 0].encode()),'CERTIFICATE_INVALID')
        require(proofs[0]['row_count']==proofs[3]['row_count']==1 and proofs[1]['row_count']>0
                and proofs[2]['row_count']==t['row_count'],'CERTIFICATE_INVALID')
    if identity_profile==REPLAY_IDENTITY_PROFILE:
        from .publication_recovery import validate_replay_evidence
        validate_replay_evidence(p)
    return p


def _continuation(chunk,index,n,sid):
    successor=index+1 if index+1<n else None
    nxt=chunk.get('next_chunk_index');link=chunk.get('next_chunk_internal_link')
    require(nxt is None or (integer(nxt) and nxt==successor),'CHUNK_CONTINUATION_INVALID')
    require(link is None or (successor is not None and link==f'/api/2.0/sql/statements/{sid}/result/chunks/{successor}'),'CHUNK_CONTINUATION_INVALID')


def prepare_plan(config, bundle, versions):
    """Caller supplies server-authorized config and independently pinned export.

    Hash integrity is checked here; a self-consistent hostile bundle is not a
    trust anchor. All eight tables must match the same sealed local publication.
    """
    prefix=config.get('table_prefix','');parts=prefix.split('.')
    require(len(parts)==2 and all(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',p) for p in parts)
            and parts==[config.get('catalog'),config.get('namespace')] and parts[1]=='sbs_radar','TABLE_NAMESPACE_INVALID')
    require(set(versions)==set(TABLES) and all(integer(v) for v in versions.values()),'VERSION_VECTOR_INVALID')
    require(set(bundle['tables'])==set(TABLES),'TABLE_SET_INVALID')
    expected=digest({k:v for k,v in bundle.items() if k not in ('snapshot_hash','input_files')})
    require(expected==bundle['snapshot_hash']==config['snapshot'],'EXPORT_SNAPSHOT_INVALID')
    tables=[]
    for name in TABLES:
        rows=bundle['tables'][name];_rows(rows)
        ordered=sorted(rows,key=lambda r:r['id']);require(rows==ordered,'EXPORT_ROW_ORDER_INVALID')
        sqlname='.'.join('`'+p+'`' for p in [*parts,name])
        tables.append(dict(logical_name=name,full_name=prefix+'.'+name,delta_version=versions[name],
            expected_sha256=digest(rows),row_count=len(rows),
            detail_sql='DESCRIBE DETAIL '+sqlname,history_sql='DESCRIBE HISTORY '+sqlname,
            readback_sql='SELECT '+', '.join('`'+c+'`' for c in COLUMNS)+' FROM '+sqlname+' VERSION AS OF '+str(versions[name])))
    return PublicationPlan(canonical(dict(snapshot=expected,config_hash=bundle['config_hash'],tables=tables)).encode())


def _rows(rows):
    require(isinstance(rows,list),'ROWS_INVALID');ids=set()
    for row in rows:
        require(isinstance(row,dict) and set(row)==set(COLUMNS),'ROW_COLUMNS_INVALID')
        require(isinstance(row['id'],str) and row['id'] and row['id'] not in ids,'DUPLICATE_OR_INVALID_ID');ids.add(row['id'])
        for c in COLUMNS:
            require(type(row[c]) is bool if c in ('synthetic','human_approved') else row[c] is None or isinstance(row[c],str),'ROW_TYPE_INVALID')


class CertificateStore:
    """Append-only files under a server-owned directory; no active release pointer.

    OS permissions/ownership and trust of this directory are deployment duties.
    Hash-addressed bytes are immutable through this API, not signed/authenticated
    against an attacker who controls the filesystem. Atomic link avoids partial
    certificates becoming visible; no overwrite or symlink following on reads.
    """
    def __init__(self,directory,*,identity_profile=STRICT_IDENTITY_PROFILE):
        identity_profile_check(identity_profile);self.identity_profile=identity_profile
        self.root=Path(directory).resolve();self.root.mkdir(parents=True,exist_ok=True)
    def put(self,certificate):
        validate_certificate(certificate,identity_profile=self.identity_profile)
        target=self.root/(certificate.sha256+'.json')
        fd,tmp=tempfile.mkstemp(dir=self.root,prefix='.pending-')
        try:
            with os.fdopen(fd,'wb') as f:f.write(certificate.payload);f.flush();os.fsync(f.fileno())
            try:os.link(tmp,target)
            except FileExistsError:require(self.get(certificate.sha256)==certificate,'CERTIFICATE_COLLISION')
        finally:os.unlink(tmp)
        return certificate.sha256
    def get(self,key):
        require(isinstance(key,str) and re.fullmatch('[0-9a-f]{64}',key),'CERTIFICATE_KEY_INVALID')
        fd=os.open(self.root/(key+'.json'),os.O_RDONLY|os.O_NOFOLLOW)
        with os.fdopen(fd,'rb') as f:raw=f.read()
        require(sha(raw)==key,'CERTIFICATE_CORRUPTED')
        certificate=Certificate(raw);validate_certificate(certificate,identity_profile=self.identity_profile);return certificate


class PublicationReader:
    def __init__(self,statement_execution,*,warehouse_id,metadata_get,governance_probe,evidence_mode,max_statements=32,max_chunks=64,max_rows=100000,max_bytes=20000000,max_polls=3,identity_profile=STRICT_IDENTITY_PROFILE):
        identity_profile_check(identity_profile);self.identity_profile=identity_profile
        require(evidence_mode in ('fixture','real'),'EVIDENCE_MODE_REQUIRED')
        require(isinstance(warehouse_id,str) and warehouse_id and callable(metadata_get) and callable(governance_probe),'SERVER_CAPABILITIES_REQUIRED')
        require(all(type(v) is int and v>0 for v in (max_statements,max_chunks,max_rows,max_bytes,max_polls)),'CAPS_INVALID')
        self.sdk=statement_execution;self.warehouse_id=warehouse_id;self.metadata_get=metadata_get;self.governance_probe=governance_probe;self.mode=evidence_mode
        self.max_statements=max_statements;self.max_chunks=max_chunks;self.max_rows=max_rows;self.max_bytes=max_bytes;self.max_polls=max_polls;self.statements=0

    def _execute(self,sql):
        from databricks.sdk.service.sql import Disposition,Format
        require(self.statements<self.max_statements,'STATEMENT_QUOTA_EXCEEDED');self.statements+=1
        try:r=obj(self.sdk.execute_statement(statement=sql,warehouse_id=self.warehouse_id,disposition=Disposition.INLINE,format=Format.JSON_ARRAY,wait_timeout='10s',row_limit=self.max_rows,byte_limit=self.max_bytes))
        except Exception:raise ValueError('STATEMENT_SUBMISSION_FAILED') from None
        return self._decode_result(sql,r)

    def _decode_result(self,sql,r):
        # Shared decoder for submitted results and explicitly labelled GET replay.
        sid=r.get('statement_id') if isinstance(r,dict) else None
        require(isinstance(sid,str) and sid,'STATEMENT_ID_MISSING')
        for _ in range(self.max_polls):
            state=r.get('status',{}).get('state')
            if state=='SUCCEEDED':break
            require(state in ('PENDING','RUNNING'),'STATEMENT_NOT_SUCCEEDED')
            try:r=obj(self.sdk.get_statement(sid))
            except Exception:raise ValueError('STATEMENT_POLL_FAILED') from None
            require(r.get('statement_id')==sid,'STATEMENT_ID_CHANGED')
        require(r.get('status',{}).get('state')=='SUCCEEDED','STATEMENT_TIMEOUT')
        require(not r['status'].get('error'),'STATEMENT_ERROR_PRESENT')
        manifest=r.get('manifest',{});chunks=manifest.get('chunks');columns=manifest.get('schema',{}).get('columns')
        require(manifest.get('format')=='JSON_ARRAY' and manifest.get('truncated') is False,'RESULT_TRUNCATED_OR_FORMAT_INVALID')
        require(isinstance(columns,list) and columns and all(c.get('position')==i and isinstance(c.get('name'),str) and isinstance(c.get('type_name'),str) for i,c in enumerate(columns)),'RESULT_SCHEMA_INVALID')
        require(len({c['name'] for c in columns})==len(columns),'DUPLICATE_COLUMNS')
        count=manifest.get('total_row_count');n=manifest.get('total_chunk_count')
        if 'chunks' not in manifest and integer(count) and count==0 and integer(n) and n==0:
            chunks=[]
        require(integer(count) and count<=self.max_rows and integer(n) and 0<=n<=self.max_chunks and isinstance(chunks,list) and len(chunks)==n,'RESULT_MANIFEST_INVALID')
        rows=[];size=0
        for index,descriptor in enumerate(chunks):
            require(descriptor.get('chunk_index')==index and descriptor.get('row_offset')==len(rows) and integer(descriptor.get('row_count')),'CHUNK_DESCRIPTOR_INVALID')
            try:chunk=r.get('result') if index==0 else obj(self.sdk.get_statement_result_chunk_n(sid,index))
            except Exception:raise ValueError('CHUNK_FETCH_FAILED') from None
            require(isinstance(chunk,dict) and not chunk.get('external_links'),'INLINE_CHUNK_REQUIRED')
            require(all(chunk.get(k)==descriptor[k] for k in ('chunk_index','row_offset','row_count')),'CHUNK_IDENTITY_INVALID')
            _continuation(chunk,index,n,sid)
            data=chunk.get('data_array',[])
            require(isinstance(data,list) and len(data)==descriptor['row_count'] and all(isinstance(row,list) and len(row)==len(columns) for row in data),'CHUNK_ROWS_INVALID')
            size+=len(canonical(data).encode());require(size<=self.max_bytes,'RESULT_BYTES_EXCEEDED');rows.extend(data)
        require(len(rows)==count,'RESULT_INCOMPLETE')
        if n==0:
            empty=r.get('result',{})
            require(count==0 and isinstance(empty,dict),'EMPTY_MANIFEST_INVALID')
            require(isinstance(empty.get('data_array',[]),list) and not empty.get('data_array',[])
                    and not empty.get('external_links')
                    and not any(k in empty for k in ('chunk_index','row_offset','row_count')),'EMPTY_MANIFEST_INVALID')
            _continuation(empty,0,0,sid)
        return columns,rows,dict(statement_id=sid,sql_sha256=sha(sql.encode()),manifest_sha256=digest(manifest),wire_rows_sha256=digest(rows),row_count=count,evidence_mode=self.mode)

    def _identity(self,name):
        try:m=obj(self.metadata_get(name))
        except Exception:raise ValueError('TABLE_METADATA_UNAVAILABLE') from None
        require(isinstance(m,dict) and m.get('full_name')==name and m.get('data_source_format')=='DELTA' and m.get('table_type')=='MANAGED','BASE_MANAGED_DELTA_REQUIRED')
        require(not m.get('row_filter') and all(not c.get('mask') for c in m.get('columns',[])),'TABLE_POLICY_UNSUPPORTED')
        for key in ('table_id','metastore_id','storage_location'):require(isinstance(m.get(key),str) and m[key],'TABLE_IDENTITY_REQUIRED')
        return {k:m[k] for k in ('full_name','table_id','metastore_id','storage_location')}

    def read(self,plan):
        require(self.identity_profile!=REPLAY_IDENTITY_PROFILE,'REPLAY_RECONSTRUCTION_REQUIRED')
        # Reconstruct closed SQL rather than trusting serialized arbitrary SQL.
        p=validate_plan(plan);names=[t['full_name'] for t in p['tables']]
        try:g=obj(self.governance_probe(names))
        except Exception:raise ValueError('GOVERNANCE_UNAVAILABLE') from None
        require(isinstance(g,dict) and g.get('mode')==self.mode and g.get('source_tables')==names and isinstance(g.get('evidence_id'),str) and g['evidence_id'] and all(g.get(k) is True for k in ('ddl_identity_controlled','retention_controlled','select_authorized','policies_absent')),'GOVERNANCE_EVIDENCE_REQUIRED')
        if self.identity_profile==NAMED_IDENTITY_PROFILE:
            require(g.get('profile')=='trusted_admin_publisher_observed_v1' and g.get('identity_continuity')=='not_proven' and g.get('aba_prevented') is False,'NAMED_IDENTITY_GOVERNANCE_REQUIRED')
        tables=[]
        for t in p['tables']:
            parts=t['full_name'].split('.');require(len(parts)==3 and parts[1]=='sbs_radar' and parts[2] in TABLES and all(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',v) for v in parts) and integer(t['delta_version']),'PLAN_INVALID')
            name='.'.join('`'+v+'`' for v in parts)
            sqls=['DESCRIBE DETAIL '+name,'DESCRIBE HISTORY '+name,'SELECT '+', '.join('`'+c+'`' for c in COLUMNS)+' FROM '+name+' VERSION AS OF '+str(t['delta_version'])]
            require(sqls==[t['detail_sql'],t['history_sql'],t['readback_sql']],'PLAN_SQL_INVALID')
            before=self._identity(t['full_name']);cols,data,detailproof=self._execute(sqls[0]);detail=_detail(cols,data)
            location_evidence=_detail_identity(detail,cols,before,self.identity_profile)
            cols,data,histproof=self._execute(sqls[1]);versioncols=[i for i,c in enumerate(cols) if c['name']=='version' and c['type_name'] in ('LONG','BIGINT')];require(len(versioncols)==1,'HISTORY_SCHEMA_INVALID')
            require(str(t['delta_version']) in [r[versioncols[0]] for r in data],'DELTA_VERSION_NOT_OBSERVED')
            cols,data,readproof=self._execute(sqls[2]);expectedtypes=['BOOLEAN' if c in ('synthetic','human_approved') else 'STRING' for c in COLUMNS]
            require([c['name'] for c in cols]==list(COLUMNS) and [c['type_name'] for c in cols]==expectedtypes,'READBACK_SCHEMA_INVALID')
            rows=[]
            for values in data:
                row=dict(zip(COLUMNS,values))
                for c in ('synthetic','human_approved'):
                    require(row[c] in ('true','false'),'BOOLEAN_WIRE_INVALID');row[c]=row[c]=='true'
                rows.append(row)
            _rows(rows);rows.sort(key=lambda r:r['id']);observed=digest(rows)
            require(len(rows)==t['row_count'] and observed==t['expected_sha256'],'READBACK_CONTENT_MISMATCH')
            after=self._identity(t['full_name']);cols,data,postproof=self._execute(sqls[0]);post=_detail(cols,data)
            post_location=_detail_identity(post,cols,after,self.identity_profile)
            require(before==after and location_evidence==post_location and all(post.get(k)==detail[k] for k in ('format','id','location')),'TABLE_IDENTITY_CHANGED')
            tables.append(dict(logical_name=t['logical_name'],full_name=t['full_name'],uc_table_id=before['table_id'],metastore_id=before['metastore_id'],delta_table_id=detail['id'],location_sha256=sha(before['storage_location'].encode()),delta_version=t['delta_version'],schema_sha256=digest(list(zip(COLUMNS,expectedtypes))),content_sha256=observed,row_count=len(rows),evidence=[detailproof,histproof,readproof,postproof],**({'location_evidence':location_evidence} if location_evidence is not None else {})))
        out=dict(version=2,mode='delta_version',snapshot=p['snapshot'],config_hash=p['config_hash'],evidence_mode=self.mode,aba_prevented=False,tables=tables,governance_evidence_sha256=digest(g),governance_evidence_id=g['evidence_id'],canonicalization='sbs-curated-json-sorted-id-v1',limitations=['Pre/post identity checks cannot exclude ABA. Trusted governance remains required.','No current runtime integration, Genie E2E, legal validity or retention availability guarantee.'])
        if self.identity_profile!=STRICT_IDENTITY_PROFILE:
            out['identity_profile']=self.identity_profile
            out['limitations'].append('Storage location hash comes from UC metadata; empty DETAIL location does not observe its physical relation to the Delta ID. Named SQL and stable pre/post identities remain observations, not ABA prevention.')
        certificate=Certificate(canonical(out).encode());validate_certificate(certificate,identity_profile=self.identity_profile);return certificate
