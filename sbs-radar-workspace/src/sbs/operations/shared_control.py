"""Shared singleton Delta control row; SDK injected, no construction I/O or DDL.

Provision and verify the singleton separately. Trusted administrators control
insert/delete/schema/identity and set Serializable; this is not admin resistance.
No UPDATE retries. A persisted operation receipt reconciles an ambiguous outcome.
App readers receive read-only capability; dispatcher and writer APIs belong only
to trusted backend identities. Delta MODIFY cannot enforce JSON-field-level roles.
"""
from copy import deepcopy
import json
import re
from .cloud_dispatch import canonical,digest,require,obj

class Conflict(ValueError):pass
class UnknownCommit(ValueError):
    def __init__(self,code,operation_id=None):
        super().__init__(code);self.operation_id=operation_id

def initial_state():return {'requests':{},'releases':{},'current':None,'fence':0,'owner':None,'receipts':{}}

def _capture_receipt(p):
    keys={'job_id','run_id','base_publication','manifest_path','manifest_sha256','artifacts_sha256','plan_fingerprint','status','revision','checkpoint_id'}
    require(isinstance(p,dict) and set(p)==keys,'CAPTURE_RECEIPT_INVALID')
    require(all(type(p[k]) is int and p[k]>0 for k in ('job_id','run_id','revision')),'CAPTURE_RECEIPT_ID_INVALID')
    require(all(isinstance(p[k],str) and re.fullmatch('[0-9a-f]{64}',p[k]) for k in ('manifest_sha256','artifacts_sha256','plan_fingerprint','checkpoint_id')),'CAPTURE_RECEIPT_HASH_INVALID')
    require(p['base_publication'] is None or isinstance(p['base_publication'],str) and re.fullmatch('[0-9a-f]{64}',p['base_publication']),'CAPTURE_RECEIPT_BASE_INVALID')
    require(p['status']=='pending_validation' and isinstance(p['manifest_path'],str) and len(p['manifest_path'].encode())<=1024 and re.fullmatch(r'/Volumes/[A-Za-z0-9_-]+/sbs_radar/[A-Za-z0-9_-]+/sbs-refresh/runs/capture-'+str(p['run_id'])+r'/[0-9a-f]{64}/manifest.json',p['manifest_path']),'CAPTURE_RECEIPT_LOCATOR_INVALID')
    require(p['checkpoint_id']==digest({k:v for k,v in p.items() if k!='checkpoint_id'}),'CAPTURE_RECEIPT_HASH_INVALID')
    return p


def _state(s,revision=None):
    require(isinstance(s,dict) and set(s)==set(initial_state()),'CONTROL_STATE_INVALID')
    require(all(isinstance(s[k],dict) for k in ('requests','releases','receipts')) and type(s['fence']) is int and s['fence']>=0,'CONTROL_STATE_INVALID')
    owner=s['owner']
    require((owner is None and s['fence']==0) or (isinstance(owner,dict) and set(owner)=={'job_id','run_id','fence'} and all(type(owner[k]) is int and owner[k]>0 for k in owner) and owner['fence']==s['fence']),'CONTROL_OWNER_INVALID')
    for request in s['requests'].values():
        require(isinstance(request,dict),'CONTROL_REQUEST_INVALID')
        if 'capture_checkpoint' in request:
            p=_capture_receipt(request['capture_checkpoint'])
            require(type(request.get('job_id')) is int and type(request.get('run_id')) is int and p['job_id']==request['job_id'] and p['run_id']==request['run_id'] and (revision is None or p['revision']<=revision),'CAPTURE_REQUEST_SCOPE_INVALID')
        for key in ('job_id','run_id'):
            if key in request and request[key] is not None:
                require(type(request[key]) is int and request[key]>0,'CONTROL_REQUEST_ID_INVALID')
    publication_keys={'job_id','run_id','release_id','manifest_path','manifest_sha256','artifacts_sha256','previous','fence','status','publication_id'}
    for key,p in s['releases'].items():
        require(isinstance(p,dict) and set(p)==publication_keys,'CONTROL_PUBLICATION_INVALID')
        require(all(type(p[k]) is int and p[k]>0 for k in ('job_id','run_id','fence')) and p['fence']<=s['fence'],'CONTROL_PUBLICATION_ID_INVALID')
        require(all(isinstance(p[k],str) and re.fullmatch('[0-9a-f]{64}',p[k]) for k in ('release_id','manifest_sha256','artifacts_sha256','publication_id')) and key==p['publication_id'] and p['release_id']==p['manifest_sha256'],'CONTROL_PUBLICATION_HASH_INVALID')
        require(p['previous'] is None or (isinstance(p['previous'],str) and re.fullmatch('[0-9a-f]{64}',p['previous'])),'CONTROL_PUBLICATION_PREVIOUS_INVALID')
        require(p['status']=='published' and isinstance(p['manifest_path'],str) and len(p['manifest_path'].encode())<=1024 and re.fullmatch(r'/Volumes/[A-Za-z0-9_-]+/sbs_radar/[A-Za-z0-9_-]+/sbs-refresh/runs/'+str(p['run_id'])+r'/[0-9a-f]{64}/manifest.json',p['manifest_path']),'CONTROL_PUBLICATION_LOCATOR_INVALID')
        require(key==digest({k:v for k,v in p.items() if k!='publication_id'}),'CONTROL_PUBLICATION_HASH_INVALID')
    current=s['current']
    if current is not None:
        # Validate types before Python equality; bool/float can equal stored ints.
        require(isinstance(current,dict) and set(current)==publication_keys and all(type(current[k]) is int and current[k]>0 for k in ('job_id','run_id','fence')),'CONTROL_CURRENT_INVALID')
        require(isinstance(current.get('publication_id'),str) and current==s['releases'].get(current['publication_id']),'CONTROL_CURRENT_INVALID')
    for key,r in s['receipts'].items():
        require(isinstance(key,str) and re.fullmatch('[0-9a-f]{64}',key) and isinstance(r,dict) and set(r)=={'revision','state_sha256'},'RECEIPT_INVALID')
        require(type(r['revision']) is int and r['revision']>0 and (revision is None or r['revision']<=revision) and isinstance(r['state_sha256'],str) and re.fullmatch('[0-9a-f]{64}',r['state_sha256']),'RECEIPT_INVALID')
    return s


class DeltaControl:
    """Single UPDATE transaction guarded by revision, then receipt readback.

    SDK must have bounded timeout and automatic POST retries disabled. Identity
    probe must be backed by observed UC/Delta metadata/governance, not expectations.
    SELECT reads the whole dedicated table to reject extra rows, including rows
    with other control IDs. No enforced-UNIQUE assumption or MERGE insertion.
    """
    def __init__(self,statement_execution,*,table,warehouse_id,identity_probe,expected_table_id,max_state_bytes=1000000,max_receipts=1000,max_statements=100,max_polls=2):
        require(isinstance(table,str) and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*',table),'TABLE_ID_INVALID')
        require(all(type(v) is int and v>0 for v in (max_state_bytes,max_receipts,max_statements,max_polls)),'CAPS_INVALID')
        require(callable(identity_probe) and isinstance(expected_table_id,str) and expected_table_id and isinstance(warehouse_id,str) and warehouse_id,'SERVER_CAPABILITIES_REQUIRED')
        self.sdk=statement_execution;self.table='.'.join('`'+p+'`' for p in table.split('.'));self.warehouse=warehouse_id;self.probe=identity_probe;self.table_id=expected_table_id
        self.max_bytes=max_state_bytes;self.max_receipts=max_receipts;self.max_statements=max_statements;self.max_polls=max_polls;self.calls=0
    def _identity(self):
        try:p=obj(self.probe())
        except Exception:raise ValueError('CONTROL_IDENTITY_UNAVAILABLE') from None
        require(isinstance(p,dict) and p.get('table_id')==self.table_id and p.get('format')=='delta' and p.get('isolation')=='Serializable' and p.get('singleton_admin_controlled') is True,'CONTROL_IDENTITY_UNVERIFIED')
    def _execute(self,sql,parameters=()):
        from databricks.sdk.service.sql import Disposition,Format
        require(self.calls<self.max_statements,'SQL_QUOTA_EXCEEDED');self.calls+=1
        r=obj(self.sdk.execute_statement(statement=sql,warehouse_id=self.warehouse,parameters=list(parameters),disposition=Disposition.INLINE,format=Format.JSON_ARRAY,wait_timeout='10s',row_limit=2,byte_limit=self.max_bytes+10000))
        require(isinstance(r,dict) and isinstance(r.get('statement_id'),str) and r['statement_id'],'STATEMENT_ID_REQUIRED');sid=r['statement_id']
        for _ in range(self.max_polls):
            status=r.get('status',{}).get('state')
            if status=='SUCCEEDED':break
            require(status in ('PENDING','RUNNING'),'STATEMENT_FAILED')
            r=obj(self.sdk.get_statement(sid));require(r.get('statement_id')==sid,'STATEMENT_ID_MISMATCH')
        require(r.get('status',{}).get('state')=='SUCCEEDED' and not r.get('status',{}).get('error'),'STATEMENT_NOT_CONFIRMED')
        return r
    def read(self):
        self._identity()
        try:r=self._execute('SELECT control_id, revision, state_json FROM '+self.table)
        except Exception:raise ValueError('CONTROL_READ_UNAVAILABLE') from None
        m=r.get('manifest',{});result=r.get('result',{});columns=m.get('schema',{}).get('columns',[])
        require(m.get('truncated') is False and m.get('format')=='JSON_ARRAY' and m.get('total_row_count')==1 and m.get('total_chunk_count')==1,'SINGLETON_READ_REQUIRED')
        require([(c.get('name'),'LONG' if c.get('type_name')=='BIGINT' else c.get('type_name')) for c in columns]==[('control_id','STRING'),('revision','LONG'),('state_json','STRING')],'CONTROL_SCHEMA_INVALID')
        require(all(result.get(k) is None for k in ('next_chunk_index','next_chunk_internal_link')) and not result.get('external_links'),'CONTROL_CONTINUATION_INVALID')
        if 'chunks' in m:
            require(m['chunks']==[{'chunk_index':0,'row_count':1,'row_offset':0}],'CONTROL_CHUNKS_INVALID')
        rows=result.get('data_array');require(isinstance(rows,list) and len(rows)==1 and len(rows[0])==3 and result.get('row_count')==1 and result.get('row_offset')==0 and result.get('chunk_index')==0,'CONTROL_RESULT_INVALID')
        control,revision,body=rows[0];require(control=='control' and isinstance(revision,str) and re.fullmatch(r'0|[1-9][0-9]*',revision) and isinstance(body,str),'CONTROL_ROW_INVALID')
        require(len(body.encode())<=self.max_bytes,'CONTROL_BYTES_EXCEEDED')
        try:state=_state(json.loads(body),int(revision))
        except Exception:raise ValueError('CONTROL_STATE_INVALID') from None
        require(len(state['receipts'])<=self.max_receipts,'RECEIPT_CAP_EXCEEDED');return int(revision),state
    def cas(self,revision,state):
        from databricks.sdk.service.sql import StatementParameterListItem as P
        require(type(revision) is int and 0<=revision<9223372036854775807,'REVISION_INVALID');state=deepcopy(_state(state,revision));self._identity()
        require(len(state['receipts'])<self.max_receipts,'RECEIPT_CAP_EXCEEDED')
        operation=digest({'expected_revision':revision,'next_state':state})
        receipt={'revision':revision+1,'state_sha256':digest(state)};state['receipts'][operation]=receipt
        body=canonical(state);require(len(body.encode())<=self.max_bytes,'CONTROL_BYTES_EXCEEDED')
        sql='UPDATE '+self.table+' SET revision = revision + 1, state_json = :state WHERE control_id = :control AND revision = :revision'
        params=[P(name='state',value=body,type='STRING'),P(name='control',value='control',type='STRING'),P(name='revision',value=str(revision),type='BIGINT')]
        ambiguous=False
        try:self._execute(sql,params)
        except Exception:ambiguous=True
        # Never infer commit from HTTP200, DML manifest, or num_affected_rows.
        try:observed,current=self.read()
        except Exception:raise UnknownCommit('COMMIT_OUTCOME_UNKNOWN',operation) from None
        if current['receipts'].get(operation)==receipt and observed>=revision+1:return revision+1
        if ambiguous:raise UnknownCommit('COMMIT_OUTCOME_UNKNOWN',operation)
        raise Conflict('CAS_CONFLICT')

    def reconcile(self,operation_id):
        """Read-only recovery by safe operation hash; absence remains unknown."""
        require(isinstance(operation_id,str) and re.fullmatch('[0-9a-f]{64}',operation_id),'OPERATION_ID_INVALID')
        revision,state=self.read();receipt=state['receipts'].get(operation_id)
        return {'status':'confirmed' if receipt and revision>=receipt['revision'] else 'unknown',
                'operation_id':operation_id,'receipt':deepcopy(receipt)}


class SharedLedger:
    """cloud_dispatch ledger contract over the same control row as publication."""
    def __init__(self,backend,*,max_requests=100):
        require(type(max_requests) is int and max_requests>0,'REQUEST_CAP_INVALID');self.backend=backend;self.max_requests=max_requests
    def get(self,key):return deepcopy(self.backend.read()[1]['requests'].get(key))
    def reserve(self,key,record):
        require(isinstance(key,str) and re.fullmatch('[0-9a-f]{64}',key) and isinstance(record,dict) and isinstance(record.get('request_hash'),str),'REQUEST_INVALID')
        v,s=self.backend.read();old=s['requests'].get(key)
        if old is not None:require(old['request_hash']==record['request_hash'],'REQUEST_CONFLICT');return deepcopy(old),False
        require(len(s['requests'])<self.max_requests,'REQUEST_CAP_EXCEEDED');s['requests'][key]=deepcopy(record);self.backend.cas(v,s);return deepcopy(record),True
    def update(self,key,changes):
        require(isinstance(changes,dict) and set(changes)<= {'status','run_id','life_cycle_state','result_state','publication_id','error_code','execution_verified'},'LEDGER_FIELDS_INVALID')
        if 'run_id' in changes:require(type(changes['run_id']) is int and changes['run_id']>0,'RUN_ID_INVALID')
        v,s=self.backend.read();require(key in s['requests'],'REQUEST_NOT_FOUND');record=s['requests'][key]
        if record.get('run_id') is not None and 'run_id' in changes:require(record['run_id']==changes['run_id'],'RUN_ID_CONFLICT')
        record.update(deepcopy(changes));self.backend.cas(v,s);return deepcopy(record)


class SnapshotWriter:
    """Writer-only capability. Guards/validators must inspect actual server evidence.

    Artifacts are uploaded immutably elsewhere; validator checks complete closure,
    hashes and availability BEFORE pointer CAS. This module does not upload files.
    Claims are issued only for an independently verified current authorized run.
    """
    def __init__(self,backend,*,job_id,writer_guard,artifact_validator,artifact_prefix):
        require(type(job_id) is int and job_id>0 and callable(writer_guard) and callable(artifact_validator),'WRITER_CAPABILITIES_REQUIRED')
        require(isinstance(artifact_prefix,str) and re.fullmatch(r'/Volumes/[A-Za-z0-9_-]+/sbs_radar/[A-Za-z0-9_-]+/sbs-refresh',artifact_prefix),'ARTIFACT_PREFIX_INVALID')
        self.backend=backend;self.job_id=job_id;self.guard=writer_guard;self.validate=artifact_validator;self.artifact_prefix=artifact_prefix
    def current(self):return deepcopy(_state(self.backend.read()[1])['current'])
    def claim(self,run_id):
        require(type(run_id) is int and run_id>0 and self.guard(self.job_id,run_id) is True,'WRITER_RUN_UNVERIFIED')
        v,s=self.backend.read();s=_state(s);require(any(type(r.get('job_id')) is int and type(r.get('run_id')) is int and r.get('job_id')==self.job_id and r.get('run_id')==run_id for r in s['requests'].values()),'RUN_NOT_REGISTERED')
        s['fence']+=1;s['owner']={'job_id':self.job_id,'run_id':run_id,'fence':s['fence']};self.backend.cas(v,s);return s['fence']
    def publish(self,run_id,fence,*,previous,release_id,artifacts):
        require(type(run_id) is int and run_id>0 and type(fence) is int and fence>0,'WRITER_ID_INVALID')
        require(isinstance(release_id,str) and re.fullmatch('[0-9a-f]{64}',release_id) and isinstance(artifacts,dict) and artifacts,'RELEASE_INVALID')
        require(all(isinstance(k,str) and k and isinstance(h,str) and re.fullmatch('[0-9a-f]{64}',h) for k,h in artifacts.items()),'ARTIFACT_MANIFEST_INVALID')
        manifests=[p for p in artifacts if p.endswith('/manifest.json')]
        require(len(manifests)==1,'MANIFEST_LOCATOR_REQUIRED');manifest=manifests[0]
        require(re.fullmatch(re.escape(self.artifact_prefix)+'/runs/'+str(run_id)+r'/[0-9a-f]{64}/manifest.json',manifest) and len(manifest.encode())<=1024 and artifacts[manifest]==release_id,'MANIFEST_LOCATOR_INVALID')
        require(self.guard(self.job_id,run_id) is True,'WRITER_RUN_UNVERIFIED')
        publication={'job_id':self.job_id,'run_id':run_id,'release_id':release_id,'manifest_path':manifest,'manifest_sha256':release_id,'artifacts_sha256':digest(artifacts),'previous':previous,'fence':fence,'status':'published'}
        publication_id=digest(publication);v,s=self.backend.read();s=_state(s)
        if publication_id in s['releases']:
            require(self.validate(deepcopy(artifacts)) is True,'ARTIFACT_CLOSURE_UNVERIFIED');return deepcopy(s['releases'][publication_id])
        require(s['owner']=={'job_id':self.job_id,'run_id':run_id,'fence':fence},'STALE_WRITER_FENCE')
        current=s['current']['release_id'] if s['current'] else None;require(current==previous,'PREVIOUS_RELEASE_MISMATCH')
        require(self.validate(deepcopy(artifacts)) is True,'ARTIFACT_CLOSURE_UNVERIFIED')
        publication['publication_id']=publication_id;s['releases'][publication_id]=publication;s['current']=publication
        self.backend.cas(v,s);return deepcopy(publication)
    def confirm_current(self,run_id,artifacts):
        """Confirm persisted same-run receipt and live artifact closure after restart."""
        require(type(run_id) is int and run_id>0 and self.guard(self.job_id,run_id) is True,'WRITER_RUN_UNVERIFIED')
        _,s=self.backend.read();s=_state(s);p=s['current']
        require(isinstance(p,dict) and type(p.get('run_id')) is int and p['run_id']==run_id and type(p.get('job_id')) is int and p['job_id']==self.job_id,'PUBLICATION_IDENTITY_INVALID')
        require(type(p.get('fence')) is int and p['fence']>0,'PUBLICATION_FENCE_INVALID')
        require(isinstance(p.get('manifest_path'),str) and len(p['manifest_path'].encode())<=1024 and re.fullmatch(re.escape(self.artifact_prefix)+'/runs/'+str(run_id)+r'/[0-9a-f]{64}/manifest.json',p['manifest_path']),'MANIFEST_LOCATOR_INVALID')
        require(p.get('status')=='published' and p.get('manifest_sha256')==p.get('release_id') and artifacts.get(p.get('manifest_path'))==p.get('release_id') and digest(artifacts)==p.get('artifacts_sha256'),'PUBLICATION_LOCATOR_INVALID')
        require(p.get('publication_id')==digest({k:v for k,v in p.items() if k!='publication_id'}) and s['releases'].get(p['publication_id'])==p,'PUBLICATION_RECEIPT_INVALID')
        require(self.validate(deepcopy(artifacts)) is True,'ARTIFACT_CLOSURE_UNVERIFIED');return deepcopy(p)

    def latest_capture_checkpoint(self,base_publication):
        _,s=self.backend.read();s=_state(s)
        candidates=[r['capture_checkpoint'] for r in s['requests'].values() if r.get('job_id')==self.job_id and 'capture_checkpoint' in r and r['capture_checkpoint']['base_publication']==base_publication]
        return deepcopy(max(candidates,key=lambda p:p['revision'])) if candidates else None

    def save_capture_checkpoint(self,run_id,*,base_publication,plan_fingerprint,staged):
        require(type(run_id) is int and run_id>0 and self.guard(self.job_id,run_id) is True,'WRITER_RUN_UNVERIFIED')
        require(self.validate(deepcopy(staged['artifacts'])) is True,'ARTIFACT_CLOSURE_UNVERIFIED')
        v,s=self.backend.read();s=_state(s)
        current=s['current']['publication_id'] if s['current'] else None
        require(current==base_publication,'CAPTURE_BASE_CHANGED')
        records=[r for r in s['requests'].values() if r.get('job_id')==self.job_id and r.get('run_id')==run_id]
        require(len(records)==1,'RUN_NOT_REGISTERED')
        p={'job_id':self.job_id,'run_id':run_id,'base_publication':base_publication,'manifest_path':staged['manifest_path'],'manifest_sha256':staged['release_id'],'artifacts_sha256':digest(staged['artifacts']),'plan_fingerprint':plan_fingerprint,'status':'pending_validation','revision':v+1}
        old=records[0].get('capture_checkpoint')
        if old is not None:
            require(all(old[k]==value for k,value in p.items() if k!='revision'),'CAPTURE_CHECKPOINT_CONFLICT');return deepcopy(old)
        p['checkpoint_id']=digest(p);_capture_receipt(p)
        require(p['manifest_path'].startswith(self.artifact_prefix+'/runs/'),'MANIFEST_LOCATOR_INVALID')
        records[0]['capture_checkpoint']=p;self.backend.cas(v,s);return deepcopy(p)
