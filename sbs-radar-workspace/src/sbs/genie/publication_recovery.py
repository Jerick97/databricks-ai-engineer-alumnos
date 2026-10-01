"""Explicit GET-artifact reconstruction. No SQL submission or transport API.

Captured artifacts require trusted server provenance. Hash equality authenticates
bytes only. Replay never asserts original UC observations or fresh SELECTs.
"""
from copy import deepcopy
from . import COLUMNS,canonical,digest
from .publication import (PublicationReader,Certificate,require,sha,_detail,
    _detail_identity,_rows,_sqls,validate_certificate,REPLAY_IDENTITY_PROFILE)
from .publication_registry import _observed,PublisherPolicy


def validate_replay_evidence(p):
    e=p['replay_evidence']
    require(isinstance(e,dict) and set(e)=={'origin','select_bracketed_by_detail','original_uc_observations_available','current_metadata_at_ms','current_metadata_sha256','ledger_sha256','cached_reads'},'REPLAY_EVIDENCE_INVALID')
    require(e['origin']=='replay_existing_statements' and e['select_bracketed_by_detail'] is False and e['original_uc_observations_available'] is False,'REPLAY_TEMPORAL_CLAIM_INVALID')
    require(type(e['current_metadata_at_ms']) is int and e['current_metadata_at_ms']>=0,'REPLAY_METADATA_TIME_INVALID')
    require(all(isinstance(e[k],str) and len(e[k])==64 and all(c in '0123456789abcdef' for c in e[k]) for k in ('current_metadata_sha256','ledger_sha256')),'REPLAY_HASH_INVALID')
    require(isinstance(e['cached_reads'],list) and len(e['cached_reads'])==8,'REPLAY_CACHE_CLOSURE_INVALID')
    ids=set()
    for t,link in zip(p['tables'],e['cached_reads']):
        require(set(link)=={'full_name','cached_history','origin_history','cached_proof','origin_proof','cached_response_sha256','origin_response_sha256'},'REPLAY_CACHE_CLOSURE_INVALID')
        require(link['full_name']==t['full_name'] and link['origin_proof']==t['evidence'][2],'REPLAY_CACHE_CLOSURE_INVALID')
        cached,origin=link['cached_history'],link['origin_history'];proof=link['origin_proof'];cp=link['cached_proof']
        require(cached.get('cache_query_id')==origin.get('query_id')==proof['statement_id'] and not origin.get('cache_query_id') and cached.get('query_id')==cp['statement_id'],'REPLAY_ORIGIN_MISMATCH')
        require(cached['query_id'] not in ids and origin['query_id'] not in ids,'REPLAY_DUPLICATE_ID');ids.update((cached['query_id'],origin['query_id']))
        # Validate originals strictly; cached query has identical SQL/actor/warehouse.
        policy=PublisherPolicy('a'*64,'b'*64,p['snapshot'],p['config_hash'],'replay-validation',origin.get('warehouse_id'),origin.get('executed_as_user_id'),1,1,p['evidence_mode'])
        obs=_observed(origin,proof,policy,2)
        require(cached.get('query_text')==origin['query_text'] and cached.get('warehouse_id')==origin['warehouse_id'] and type(cached.get('executed_as_user_id')) is int and cached['executed_as_user_id']==origin['executed_as_user_id'] and cached.get('status')=='FINISHED' and cached.get('is_final') is True and not cached.get('error_message') and cached.get('statement_type')=='SELECT','REPLAY_CACHED_HISTORY_INVALID')
        start,end=cached.get('query_start_time_ms'),cached.get('execution_end_time_ms')
        require(type(start) is int and type(end) is int and obs['ended_at_ms']<=start<=end,'REPLAY_CACHE_TIME_INVALID')
        require(set(cp)==set(proof) and all(cp[k]==proof[k] for k in ('sql_sha256','wire_rows_sha256','row_count','evidence_mode')),'REPLAY_RESULT_MISMATCH')
        require(all(isinstance(link[k],str) and len(link[k])==64 and all(c in '0123456789abcdef' for c in link[k]) for k in ('cached_response_sha256','origin_response_sha256')),'REPLAY_HASH_INVALID')


def reconstruct_certificate(plan,*,history,statements,origins,origin_statements,metadata,metadata_at_ms,journal_identities,ledger,governance,warehouse_id,executor_id,owner):
    """All inputs are observed records from a trusted GET capture, not request data.

    `history` is the exact 48-query continuation. Reuses eight original SELECTs
    and 24 later DETAIL/HISTORY results. No fake execute_statement adapter.
    """
    p=plan.as_dict();rows=sorted(deepcopy(history),key=lambda r:r['query_start_time_ms'])
    require(len(rows)==48 and len({r['query_id'] for r in rows})==48,'REPLAY_HISTORY_CLOSURE_REQUIRED')
    require([sha(r['query_text'].encode()) for r in rows]==[r['statement_sha256'] for r in ledger['submissions'][-48:]],'REPLAY_LEDGER_MISMATCH')
    require(ledger['reserved']==99 and ledger['limit']==112,'REPLAY_LEDGER_SCOPE')
    rows=rows[-32:]
    require(governance.get('mode')=='real' and governance.get('profile')=='trusted_admin_publisher_observed_v1' and governance.get('identity_continuity')=='not_proven' and governance.get('aba_prevented') is False and all(governance.get(k) is True for k in ('ddl_identity_controlled','retention_controlled','select_authorized','policies_absent')),'REPLAY_GOVERNANCE_REQUIRED')
    reader=PublicationReader(None,warehouse_id=warehouse_id,metadata_get=lambda n:metadata[n],governance_probe=lambda names:governance,evidence_mode='real',identity_profile=REPLAY_IDENTITY_PROFILE)
    # Captures must be terminal and self-contained; decoding cannot trigger GET.
    def decode(row,response):
        require(response.get('statement_id')==row['query_id'] and response.get('status',{}).get('state')=='SUCCEEDED' and response.get('manifest',{}).get('total_chunk_count')==1,'REPLAY_COMPLETE_SINGLE_CHUNK_REQUIRED')
        return reader._decode_result(row['query_text'],deepcopy(response))
    tables=[];links=[]
    for i,t in enumerate(p['tables']):
        group=rows[i*4:i*4+4];name=t['full_name'];m=metadata[name];identity=reader._identity(name)
        require(m.get('owner')==owner and m.get('properties',{}).get('sbs.publication_id')==p['publication_id'] and m['properties'].get('sbs.snapshot')==p['snapshot'] and identity['table_id']==journal_identities[t['logical_name']]['table_id'],'REPLAY_CURRENT_UC_IDENTITY_MISMATCH')
        beforecols,beforedata,bp=decode(group[0],statements[group[0]['query_id']]);before=_detail(beforecols,beforedata)
        location=_detail_identity(before,beforecols,identity,REPLAY_IDENTITY_PROFILE)
        hc,hd,hp=decode(group[1],statements[group[1]['query_id']]);vi=[j for j,c in enumerate(hc) if c['name']=='version' and c['type_name'] in ('LONG','BIGINT')];require(len(vi)==1,'HISTORY_SCHEMA_INVALID')
        cached=group[2];origin=origins[cached.get('cache_query_id')]
        oc,od,op=decode(origin,origin_statements[origin['query_id']]);cc,cd,cp=decode(cached,statements[cached['query_id']])
        require(oc==cc and od==cd,'REPLAY_RESULT_MISMATCH')
        types=['BOOLEAN' if c in ('synthetic','human_approved') else 'STRING' for c in COLUMNS]
        require([c['name'] for c in oc]==list(COLUMNS) and [c['type_name'] for c in oc]==types,'READBACK_SCHEMA_INVALID')
        material=[]
        for values in od:
            item=dict(zip(COLUMNS,values))
            for c in ('synthetic','human_approved'):
                require(item[c] in ('true','false'),'BOOLEAN_WIRE_INVALID');item[c]=item[c]=='true'
            material.append(item)
        _rows(material);material.sort(key=lambda r:r['id']);require(material==t['rows'],'READBACK_CONTENT_MISMATCH')
        # Closed SELECT uses one version observed by HISTORY; never parse arbitrary SQL.
        versions=[int(r[vi[0]]) for r in hd if str(r[vi[0]]).isdigit()]
        versions=[v for v in versions if _sqls({**t,'delta_version':v})[2]==origin['query_text']]
        require(len(versions)==1,'REPLAY_VERSION_SQL_MISMATCH');version=versions[0];sqls=_sqls({**t,'delta_version':version})
        require([r['query_text'] for r in group]==[sqls[0],sqls[1],sqls[2],sqls[0]],'REPLAY_SQL_SEQUENCE_MISMATCH')
        ac,ad,ap=decode(group[3],statements[group[3]['query_id']]);after=_detail(ac,ad)
        require(before==after and location==_detail_identity(after,ac,identity,REPLAY_IDENTITY_PROFILE),'REPLAY_DETAIL_IDENTITY_CHANGED')
        # Validate all observed execution attribution; SELECT is the real origin.
        policy=PublisherPolicy('a'*64,p['mapping_sha256'],p['snapshot'],p['config_hash'],owner,warehouse_id,executor_id,1,1,'real')
        for pos,(r,proof) in enumerate(zip([group[0],group[1],origin,group[3]],[bp,hp,op,ap])):_observed(r,proof,policy,pos)
        tables.append(dict(logical_name=t['logical_name'],full_name=name,uc_table_id=identity['table_id'],metastore_id=identity['metastore_id'],delta_table_id=before['id'],location_sha256=sha(identity['storage_location'].encode()),delta_version=version,schema_sha256=digest(list(zip(COLUMNS,types))),content_sha256=digest(material),row_count=len(material),evidence=[bp,hp,op,ap],location_evidence=location))
        links.append(dict(full_name=name,cached_history=cached,origin_history=origin,cached_proof=cp,origin_proof=op,cached_response_sha256=digest(statements[cached['query_id']]),origin_response_sha256=digest(origin_statements[origin['query_id']])))
    out=dict(version=2,mode='delta_version',snapshot=p['snapshot'],config_hash=p['config_hash'],evidence_mode='real',aba_prevented=False,tables=tables,governance_evidence_sha256=digest(governance),governance_evidence_id=governance['evidence_id'],canonicalization='sbs-curated-json-sorted-id-v1',identity_profile=REPLAY_IDENTITY_PROFILE,limitations=['Replayed authenticated GET artifacts; no SQL submitted by recovery.','Original SELECTs precede later DETAIL observations: no temporal bracketing is claimed. Original UC observations were not archived.','Current UC metadata is a separate observation; no identity continuity, ABA prevention, physical-route equivalence or retention availability is proven.','Readback execution times remain original; registry freshness is an explicit server policy, not fresh data execution.'],replay_evidence=dict(origin='replay_existing_statements',select_bracketed_by_detail=False,original_uc_observations_available=False,current_metadata_at_ms=metadata_at_ms,current_metadata_sha256=digest(metadata),ledger_sha256=digest(ledger),cached_reads=links))
    cert=Certificate(canonical(out).encode());validate_certificate(cert,identity_profile=REPLAY_IDENTITY_PROFILE);return cert


def validate_current_observations(observations,metadata,plan,config,*,observed_at_ms):
    """Validate five authenticated GET payloads and eight UC tables, no network.

    Timestamp is the trusted capture clock, not a client argument in any route.
    """
    from .publication_writer import preflight
    preflight(plan,config);p=plan.as_dict()
    require(config.policy['issued_at_ms']<=observed_at_ms<config.policy['expires_at_ms'],'WRITER_POLICY_EXPIRED')
    require(set(observations)=={'me','schema','catalog','warehouse','permissions'},'REPLAY_OBSERVATION_CLOSURE')
    me,s,c,w,a=(observations[k] for k in ('me','schema','catalog','warehouse','permissions'))
    require(str(me.get('id'))==str(config.executor_id) and type(me.get('id')) in (str,int) and me.get('userName',me.get('user_name'))==config.owner,'WRITER_IDENTITY_MISMATCH')
    require(s.get('full_name')==config.schema_name and s.get('schema_id')==config.schema_id and s.get('owner')==config.owner,'SCHEMA_OWNER_PIN_MISMATCH')
    require(c.get('name')==config.schema_name.split('.')[0] and c.get('owner')==config.owner,'CATALOG_OWNER_REQUIRED')
    require(w.get('id')==config.warehouse_id and w.get('state')=='RUNNING','WAREHOUSE_NOT_RUNNING')
    require(a.get('object_id')=='/sql/warehouses/'+config.warehouse_id and any(x.get('user_name')==config.owner and any(z.get('permission_level') in ('CAN_USE','CAN_MANAGE','IS_OWNER') for z in x.get('all_permissions',[])) for x in a.get('access_control_list',[])),'DIRECT_WAREHOUSE_PERMISSION_REQUIRED')
    names=[t['full_name'] for t in p['tables']];require(set(metadata)==set(names),'REPLAY_METADATA_CLOSURE')
    for name in names:
        m=metadata[name];types=['BOOLEAN' if k in ('synthetic','human_approved') else 'STRING' for k in COLUMNS]
        require(m.get('full_name')==name and m.get('owner')==config.owner and m.get('data_source_format')=='DELTA' and m.get('table_type')=='MANAGED' and m.get('browse_only') is not True and [x.get('name') for x in m.get('columns',[])]==list(COLUMNS) and [x.get('type_name') for x in m['columns']]==types,'REPLAY_METADATA_INVALID')
        require(not m.get('row_filter') and all(not x.get('mask') for x in m['columns']),'TABLE_POLICY_UNSUPPORTED')
        require(m.get('properties',{}).get('sbs.publication_id')==p['publication_id'] and m['properties'].get('sbs.snapshot')==p['snapshot'],'TABLE_NOT_OWNED_PUBLICATION')
    e=dict(profile='trusted_admin_publisher_observed_v1',observations=observations,observed_at_ms=observed_at_ms,table_metadata_sha256=digest(metadata),administrative_declarations=config.policy,identity_continuity='not_proven',aba_prevented=False)
    return dict(mode=config.evidence_mode,source_tables=names,evidence_id=digest(e),ddl_identity_controlled=True,retention_controlled=True,select_authorized=True,policies_absent=True,**e)


def finalize_recovery(plan,config,*,history,statements,origins,origin_statements,
                      metadata,metadata_at_ms,journal_identities,ledger,observations,
                      query_history,clock,certificate_directory,registry_directory,
                      max_readback_age_ms,ttl_ms=300000):
    """Current GET checks + replay checkpoint + strict-origin registry.

    Explicit max age is required; this function has no SQL/warehouse-start API.
    Actual admission and transport GET-only restrictions belong to the runner.
    """
    from .publication import CertificateStore
    from .publication_registry import HistoryRegistryBuilder,RegistryAdmin
    require(type(max_readback_age_ms) is int and 0<max_readback_age_ms<=7200000,'REPLAY_READBACK_AGE_LIMIT')
    now=clock();require(config.policy['issued_at_ms']<=metadata_at_ms<=now<config.policy['expires_at_ms'] and now-metadata_at_ms<=60000,'REPLAY_CURRENT_METADATA_EXPIRED')
    require(type(ttl_ms) is int and ttl_ms>0 and now+ttl_ms<=config.policy['expires_at_ms'],'REGISTRY_EXCEEDS_ADMIN_POLICY')
    governance=validate_current_observations(observations,metadata,plan,config,observed_at_ms=metadata_at_ms)
    cert=reconstruct_certificate(plan,history=history,statements=statements,origins=origins,origin_statements=origin_statements,metadata=metadata,metadata_at_ms=metadata_at_ms,journal_identities=journal_identities,ledger=ledger,governance=governance,warehouse_id=config.warehouse_id,executor_id=config.executor_id,owner=config.owner)
    CertificateStore(certificate_directory,identity_profile=REPLAY_IDENTITY_PROFILE).put(cert)
    p=plan.as_dict();policy=PublisherPolicy(cert.sha256,p['mapping_sha256'],p['snapshot'],p['config_hash'],config.owner,config.warehouse_id,config.executor_id,ttl_ms,max_readback_age_ms,config.evidence_mode)
    entry=HistoryRegistryBuilder(query_history,policy,clock=clock,identity_profile=REPLAY_IDENTITY_PROFILE).build(cert)
    require(entry.as_dict()['registry']['valid_until_ms']<=config.policy['expires_at_ms'],'REGISTRY_EXCEEDS_ADMIN_POLICY')
    RegistryAdmin(registry_directory,administrator=config.owner,clock=clock,identity_profile=REPLAY_IDENTITY_PROFILE).publish(entry)
    return dict(status='published',certificate_sha256=cert.sha256,registry_sha256=entry.sha256,identity_profile=REPLAY_IDENTITY_PROFILE,evidence_origin='replay_existing_statements',sql_submissions=0,select_bracketed_by_detail=False,original_uc_observations_available=False,max_readback_age_ms=max_readback_age_ms,aba_prevented=False)
