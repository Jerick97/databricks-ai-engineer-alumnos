"""Read-only SQL history provenance, exact AST matching, and source snapshot maps.

No SQL execution/start/create APIs. Publication lookup is a trusted backend
readback-attestation store, never expected values echoed from a request. A source
mapping verifies local source identity, not remote table publication or grants.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from . import canonical, digest, validate, TABLES

SQLGLOT_VERSION = '30.20.0'


def _parser():
    import sqlglot
    if sqlglot.__version__ != SQLGLOT_VERSION:raise ValueError('PINNED_SQL_PARSER_REQUIRED')
    return sqlglot


def _tree(sql):
    parser=_parser();exp=parser.exp
    # Deliberately narrow literal profile. Backslash interpretation can depend on
    # Spark session settings; reject it instead of assuming unverified semantics.
    if not isinstance(sql,str) or not sql.strip() or len(sql)>8192 or '\\' in sql or any(ord(c)<32 and c not in '\n\t\r' for c in sql):
        raise ValueError('SQL_PROFILE_UNSUPPORTED')
    trees=parser.parse(sql,read='databricks')
    if len(trees)!=1 or not isinstance(trees[0],exp.Select):raise ValueError('SINGLE_SELECT_REQUIRED')
    tree=trees[0]
    if any(n.comments or isinstance(n,exp.Hint) for n in tree.walk()):raise ValueError('SQL_COMMENTS_OR_HINTS_UNSUPPORTED')
    # Exact structural comparison: normalize identifier case/quoting only. No
    # optimizer, predicate removal/reordering, alias substitution or rewriting.
    def normalize(n):
        if isinstance(n,exp.Identifier):
            n.set('this',n.this.lower());n.set('quoted',False)
        return n
    return tree.transform(normalize)


def literalize_reference(sql,parameters):
    exp=_parser().exp;tree=_tree(sql)
    names={p.name for p in tree.find_all(exp.Placeholder)}
    if not isinstance(parameters,dict) or names!=set(parameters):raise ValueError('REFERENCE_BINDINGS_MISMATCH')
    for value in parameters.values():
        if not isinstance(value,str) or any(c in value for c in ("'",'\\','\n','\r','\t','\x00')):
            raise ValueError('REFERENCE_LITERAL_PROFILE_UNSUPPORTED')
    tree=tree.transform(lambda n:exp.Literal.string(parameters[n.name]) if isinstance(n,exp.Placeholder) else n)
    return tree.sql(dialect='databricks')


def matches_literal_reference(statement,reference,parameters):
    try:
        actual=_tree(statement);exp=_parser().exp
        if any(isinstance(n,(exp.Placeholder,exp.Parameter)) for n in actual.walk()):return False
        return actual==_tree(literalize_reference(reference,parameters))
    except (ValueError,TypeError,KeyError,ImportError):return False
    except Exception:
        # SQL parser exceptions may contain the input statement; callers need
        # only a closed rejection, never an untrusted SQL/error string.
        return False


def _source_tables(statement):
    tree=_tree(statement);exp=_parser().exp
    if any(isinstance(n,(exp.Placeholder,exp.Parameter)) for n in tree.walk()):raise ValueError('ACTUAL_BINDINGS_UNAVAILABLE')
    found=[]
    for table in tree.find_all(exp.Table):
        if not all(isinstance(x,exp.Identifier) for x in table.parts) or len(table.parts)!=3:
            raise ValueError('FULL_TABLE_IDENTITY_REQUIRED')
        found.append('.'.join(x.name for x in table.parts))
    if len(found)!=1:raise ValueError('SINGLE_PINNED_TABLE_REQUIRED')
    return found


def executed_delta_bindings(statement):
    """One fully qualified base table with an exact numeric VERSION AS OF."""
    tables=_source_tables(statement);exp=_parser().exp
    table=next(_tree(statement).find_all(exp.Table))
    version=table.args.get('version')
    if not isinstance(version,exp.Version) or version.args.get('this')!='VERSION' or version.args.get('kind')!='AS OF':
        raise ValueError('EXECUTED_DELTA_VERSION_REQUIRED')
    literal=version.args.get('expression')
    if not isinstance(literal,exp.Literal) or literal.is_string or not literal.this.isascii() or not literal.this.isdigit():
        raise ValueError('EXECUTED_DELTA_INTEGER_REQUIRED')
    return {tables[0]:int(literal.this)}


def _dict(value):return value.as_dict() if hasattr(value,'as_dict') else value


class DatabricksHistoryProbe:
    """Callable `probe(statement_id)` compatible with GenieAdapter.execution_probe.

    query_history is WorkspaceClient.query_history. publication_lookup is a
    trusted backend callable accepting source_tables/started_at_ms/ended_at_ms.
    It retrieves an immutable publication certificate based on actual full-table
    readback hashes and an enforced write-free interval covering execution. It
    Optional delta_publication selects the explicit version-pinned server contract
    instead of the v1 no-write interval. Both require independent evidence.
    MUST NOT manufacture a certificate from constructor expectations. Without
    that independent deployed-data evidence the probe refuses to assign snapshot.
    """
    def __init__(self, query_history, *, warehouse_id,space_id,executor_id,snapshot,
                 table_content_sha256,publication_lookup=None,max_pages=2,delta_publication=None):
        if not all(isinstance(v,str) and v for v in (warehouse_id,space_id,snapshot)) or type(executor_id) is not int:
            raise ValueError('PINNED_EXECUTION_IDENTITY_REQUIRED')
        if (delta_publication is None and not callable(publication_lookup)) or not table_content_sha256 or type(max_pages) is not int or not 1<=max_pages<=3:
            raise ValueError('TRUSTED_PUBLICATION_LOOKUP_REQUIRED')
        self.history=query_history;self.warehouse_id=warehouse_id;self.space_id=space_id
        self.executor_id=executor_id;self.snapshot=snapshot;self.hashes=deepcopy(table_content_sha256)
        self.lookup=publication_lookup;self.max_pages=max_pages
        from .delta import DeltaPublication
        if delta_publication is not None and not isinstance(delta_publication,DeltaPublication):raise ValueError('DELTA_CAPABILITY_REQUIRED')
        self.delta=delta_publication
        if self.delta is not None:
            cert=self.delta.certificate.as_dict()
            if cert['snapshot']!=snapshot or {t['full_name']:t['content_sha256'] for t in cert['tables']}!=self.hashes:
                raise ValueError('DELTA_PROBE_PUBLICATION_MISMATCH')

    def __call__(self,query_id):
        from databricks.sdk.service.sql import QueryFilter
        if not isinstance(query_id,str) or not query_id or len(query_id)>128:raise ValueError('INVALID_STATEMENT_ID')
        rows=[];token=None;seen=set()
        for _ in range(self.max_pages):
            kw=dict(filter_by=QueryFilter(statement_ids=[query_id],warehouse_ids=[self.warehouse_id]),max_results=2,include_metrics=False)
            if token:kw['page_token']=token
            try:response=_dict(self.history.list(**kw))
            except Exception as exc:
                if isinstance(exc,PermissionError) or getattr(exc,'error_code',None) in ('PERMISSION_DENIED','UNAUTHENTICATED'):
                    raise PermissionError('HISTORY_ACCESS_DENIED') from None
                raise ValueError('HISTORY_UNAVAILABLE') from None
            if not isinstance(response,dict) or not isinstance(response.get('res'),list):raise ValueError('HISTORY_RESULT_UNAVAILABLE')
            rows.extend(response['res'])
            if not response.get('has_next_page'):break
            token=response.get('next_page_token')
            if not token or token in seen:raise ValueError('HISTORY_PAGINATION_UNPROVEN')
            seen.add(token)
        else:raise ValueError('HISTORY_PAGINATION_LIMIT')
        if len(rows)!=1:raise ValueError('EXACT_HISTORY_RECORD_REQUIRED')
        row=rows[0]
        if not isinstance(row,dict) or not isinstance(row.get('query_source'),dict):
            raise ValueError('HISTORY_SOURCE_ATTRIBUTION_REQUIRED')
        if (row.get('query_id')!=query_id or row.get('warehouse_id')!=self.warehouse_id
                or type(row.get('executed_as_user_id')) is not int or row.get('executed_as_user_id')!=self.executor_id
                or row.get('status')!='FINISHED' or row.get('is_final') is not True
                or row.get('statement_type')!='SELECT' or row.get('cache_query_id') or row.get('error_message')
                or row.get('query_source',{}).get('genie_space_id')!=self.space_id):
            raise ValueError('EXECUTED_IDENTITY_NOT_VERIFIED')
        start,end=row.get('query_start_time_ms'),row.get('execution_end_time_ms')
        if type(start) is not int or type(end) is not int or not 0<=start<=end:raise ValueError('EXECUTION_INTERVAL_REQUIRED')
        tables=_source_tables(row.get('query_text'))
        if any(t not in self.hashes for t in tables):raise ValueError('TABLE_OUTSIDE_DEPLOYMENT')
        if self.delta is not None:
            bindings=executed_delta_bindings(row.get('query_text'))
            if bindings!={t:self.delta.versions[t] for t in tables}:raise ValueError('EXECUTED_DELTA_VERSION_MISMATCH')
            publication_proof=self.delta.verify(source_tables=tables,started_at_ms=start,ended_at_ms=end,
                executor_id=self.executor_id,warehouse_id=self.warehouse_id,space_id=self.space_id)
        else:
            cert=self.lookup(source_tables=deepcopy(tables),started_at_ms=start,ended_at_ms=end)
            if (not isinstance(cert,dict) or cert.get('snapshot')!=self.snapshot or cert.get('source_tables')!=tables
                    or cert.get('table_content_sha256')!={t:self.hashes[t] for t in tables}
                    or not isinstance(cert.get('attestation_id'),str) or not cert['attestation_id']
                    or type(cert.get('valid_from_ms')) is not int or type(cert.get('valid_until_ms')) is not int
                    or not cert['valid_from_ms']<=start<=end<=cert['valid_until_ms']):
                raise ValueError('INDEPENDENT_PUBLICATION_NOT_VERIFIED')
            publication_proof=dict(publication_attestation_id=cert['attestation_id'],publication_certificate_sha256=digest(cert))
        return dict(query_id=query_id,statement=row['query_text'],parameters={},parameter_mode='executed_literals',
                    source_tables=tables,snapshot=self.snapshot,state='SUCCEEDED',
                    execution_provenance=dict(provider='databricks_query_history_get',warehouse_id=self.warehouse_id,
                        genie_space_id=self.space_id,executor_id=self.executor_id,started_at_ms=start,ended_at_ms=end,
                        query_text_sha256=hashlib.sha256(row['query_text'].encode()).hexdigest(),
                        history_record_sha256=digest(row),**publication_proof))


def snapshot_inputs(root):
    """Load only project-owned frozen files, verifying envelopes and byte hashes."""
    root=Path(root).resolve();files={}
    def local(path):
        from sbs.paths import project_path
        return project_path(root,path)
    def read(path):
        p=local(path);content=p.read_bytes();files[str(p.relative_to(root))]=hashlib.sha256(content).hexdigest()
        return json.loads(content)
    def sha(path):
        p=local(path);h=hashlib.sha256(p.read_bytes()).hexdigest();files[str(p.relative_to(root))]=h;return h
    bundle=read('runs/sk06-component-real/manifest.json')
    bundle['tables']={t:[json.loads(line) for line in local('runs/sk06-component-real/'+t+'.jsonl').read_text().splitlines()] for t in TABLES}
    for t in TABLES:sha('runs/sk06-component-real/'+t+'.jsonl')
    if digest({k:v for k,v in bundle.items() if k not in ('snapshot_hash','input_files')})!=bundle['snapshot_hash']:
        raise ValueError('CURATED_SNAPSHOT_INTEGRITY_FAILED')
    report=read('runs/sk04-real-001-report.json')
    target_names=['data/retrieval/sk04-real-001/corpus.json','data/retrieval/sk04-real-001/records.json','data/retrieval/sk04-real-001/index.json']
    for name in target_names:
        if sha(name)!=report['artifacts_sha256'][name]:raise ValueError('RAG_ARTIFACT_HASH_MISMATCH')
    corpus,records,index=[read(name) for name in target_names]
    protocol=read('runs/sk04-real-001-protocol.json')
    for envelope in (index,protocol):
        if digest(envelope['payload'])!=envelope['sha256']:raise ValueError('RAG_ENVELOPE_MISMATCH')
    if index['payload']['records_sha256']!=sha(target_names[1]):raise ValueError('RAG_RECORDS_INDEX_MISMATCH')
    evidence=[]
    for name in ('runs/sk02-repository-capture.json','runs/sk02-amendments-capture.json'):
        capture=read(name)
        if sha(capture['manifest'])!=capture['manifest_sha256']:raise ValueError('SOURCE_MANIFEST_MISMATCH')
        for entry in capture['sources']:
            source=entry['source'];b=read(entry['result_path'])
            original=sha(entry['original_path']);raw=sha(entry['rawtext_path']);result=sha(entry['result_path'])
            if original!=source['sha256'] or original!=b['sha256'] or raw!=b['rawtext_sha256'] or hashlib.sha256(b['rawtext'].encode()).hexdigest()!=raw:
                raise ValueError('SOURCE_BYTES_MISMATCH')
            evidence.append(dict(source=source,extraction=b,result_sha256=result))
    return dict(bundle=bundle,rag_corpus=corpus,rag_records=records,rag_protocol_envelope=protocol,
                rag_index_hash=index['payload']['index_hash'],source_evidence=evidence,
                input_files=files)


def reconcile_snapshots(*,bundle,rag_corpus,rag_records,rag_protocol_envelope,rag_index_hash,source_evidence,input_files):
    try:return _reconcile(bundle,rag_corpus,rag_records,rag_protocol_envelope,rag_index_hash,source_evidence,input_files)
    except (KeyError,TypeError,IndexError) as exc:raise ValueError('MALFORMED_SNAPSHOT_EVIDENCE') from None


def _reconcile(bundle,rag_corpus,rag_records,envelope,index_hash,source_evidence,input_files):
    if digest({k:v for k,v in bundle.items() if k not in ('snapshot_hash','input_files')})!=bundle['snapshot_hash']:raise ValueError('CURATED_SNAPSHOT_MISMATCH')
    if digest(envelope['payload'])!=envelope['sha256']:raise ValueError('RAG_PROTOCOL_MISMATCH')
    protocol=envelope['payload']
    if digest(rag_corpus)!=protocol['corpus_hash']:raise ValueError('RAG_CORPUS_MISMATCH')
    identity=lambda x:(x['document_id'],x['version_id'])
    curated={identity(json.loads(r['payload_json'])):json.loads(r['payload_json']) for r in bundle['tables']['documents']}
    if len(curated)!=len(bundle['tables']['documents']):raise ValueError('DUPLICATE_CURATED_DOCUMENT')
    observed={identity(e['source']):e for e in source_evidence}
    rag={identity(d):d for d in rag_corpus}
    if len(rag)!=len(rag_corpus) or len(observed)!=len(source_evidence) or not set(curated)==set(rag)==set(observed):raise ValueError('SOURCE_SETS_DIFFER')
    matched=[]
    for key in sorted(curated):
        source=curated[key];validate('SourceDocument',source);actual=observed[key];b=actual['extraction'];r=rag[key]
        if source!=actual['source']:raise ValueError('SOURCE_METADATA_DIFFER')
        for field,expected in [('original_sha256',source['sha256']),('config_hash',b['config_hash']),('extractor',b['extractor']),('rawtext_sha256',b['rawtext_sha256']),('result_sha256',actual['result_sha256'])]:
            if r[field]!=expected:raise ValueError('SOURCE_LINEAGE_DIFFER')
        matched.append(dict(document_id=key[0],version_id=key[1],family=source['family'],original_sha256=source['sha256'],
                            rawtext_sha256=b['rawtext_sha256'],extraction_sha256=actual['result_sha256'],extraction_config_hash=b['config_hash']))
    provisions={row['id']:json.loads(row['payload_json']) for row in bundle['tables']['provisions']}
    if len(provisions)!=len(bundle['tables']['provisions']):raise ValueError('DUPLICATE_CURATED_CITATION')
    record_ids=set()
    for row in rag_records:
        c=row['citation'];validate('Provision',c);key=identity(c)
        if c['citation_id'] in record_ids or c!=provisions.get(c['citation_id']):raise ValueError('CITATIONS_DIFFER')
        record_ids.add(c['citation_id'])
        if row['family']!=curated[key]['family']:raise ValueError('CITATION_FAMILY_DIFFER')
        raw=observed[key]['extraction']['rawtext']
        if c['end']>len(raw) or raw[c['start']:c['end']]!=c['text'] or hashlib.sha256(c['text'].encode()).hexdigest()!=row['literal_sha256']:
            raise ValueError('CITATION_BYTES_DIFFER')
        lineage=row['source'];b=observed[key]['extraction']
        if any(lineage[k]!=b[k] for k in ('sha256','config_hash','extractor','rawtext_sha256')):raise ValueError('RAG_CITATION_LINEAGE_DIFFER')
    if record_ids!=set(provisions):raise ValueError('CITATION_COVERAGE_DIFFER')
    pairs=[json.loads(r['payload_json']) for r in bundle['tables']['pairs']];mappings=[]
    for q in protocol['questions']:
        ctx=q['context'];validate('QueryContext',ctx);p=ctx['pair']
        candidates=[x for x in pairs if all(x[k]==p[k] for k in ('family','before','after'))]
        if len(candidates)!=1:raise ValueError('PAIR_COUNTERPARTS_DIFFER')
        mappings.append(dict(query_id=q['query_id'],rag_pair_id=p['pair_id'],sk06_pair_id=candidates[0]['pair_id'],
                             family=p['family'],before=p['before'],after=p['after'],selected_provision_id=ctx['selected_provision_id']))
    result=dict(version='1',status='source_and_raw_page_compatible',sk06_snapshot=bundle['snapshot_hash'],
                sk06_corpus_hash=bundle['corpus_hash'],rag_snapshot=protocol['corpus_hash'],rag_index_hash=index_hash,
                source_set_sha256=digest(matched),sources=matched,matched_citations=len(record_ids),
                citation_set_sha256=digest(sorted(provisions.values(),key=lambda c:c['citation_id'])),pair_mappings=mappings,
                semantic_provision_ids_equivalent=False,input_files=deepcopy(input_files),
                limitations=['Different snapshot algorithms retained; no hash is replaced by another.',
                             'Compatibility covers exact source bytes, extraction and raw-page citations, not legal validity or cloud publication.',
                             'Article-level RAG focus is not a curated raw-page provision ID; no automatic zero-count or semantic ID translation.',
                             'No table deployment/Genie execution is established by this local map.'])
    result['mapping_sha256']=digest(result)
    return result


def build_project_snapshot_mapping(root):return reconcile_snapshots(**snapshot_inputs(root))
