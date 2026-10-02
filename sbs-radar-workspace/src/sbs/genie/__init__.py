"""SK06: deterministic local curation and injected Genie SDK boundary.

The permission_probe is trusted server integration, NEVER request-body claims.
Genie executes generated SQL server-side before it can be inspected here. Only
use a dedicated principal with backend SELECT-only grants restricted to curated
mission tables; prompts/regex are not authorization. No remote DDL/start/create.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3
import time
from sbs.contracts import validate_contract

VERSION = '0.1.2'
TABLES = ('documents','versions','provisions','pairs','changes','evidence','reviews','processes')
BENCHMARKS = [
    '¿Cuántas versiones documentales contiene cada familia en este snapshot?',
    'Lista documentos de cybersecurity y sus fechas publicadas conocidas.',
    '¿Qué pares documentales están disponibles para comparar?',
    '¿Qué cambios textuales están registrados y con qué estado de revisión?',
    '¿Qué procesos ficticios están registrados sin considerarlos normas?'
]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',',':'))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def validate(kind, value):
    if not validate_contract(kind,value)['valid']:
        raise ValueError(kind + '_INVALID')


def curate(documents, pairs, comparisons, ai_review, processes, config, *, mode, provisions=()):
    """Preserve source contracts in payload, expose SQL scalar columns and lineage.

    mode=real excludes synthetic normative documents; fictitious processes always
    retain synthetic=True and source_kind=fictitious_process in a separate table.
    Dates unknown in sources remain unknown; no effective/current-law inference.
    """
    if mode not in ('real','fixture') or config.get('namespace') != 'sbs_radar':
        raise ValueError('MODE_OR_NAMESPACE_INVALID')
    documents=sorted(deepcopy(documents),key=lambda d:(d['document_id'],d['version_id']))
    identities={}
    for d in documents:
        validate('SourceDocument',d)
        key=(d['document_id'],d['version_id'])
        if key in identities:raise ValueError('DUPLICATE_SOURCE')
        if mode=='real' and d['synthetic']:raise ValueError('FIXTURE_IN_REAL_CORPUS')
        identities[key]=d
    pair_map={}
    for p in pairs:
        validate('VersionPair',p)
        if p['pair_id'] in pair_map:raise ValueError('DUPLICATE_PAIR')
        for side in ('before','after'):
            d=identities.get((p[side]['document_id'],p[side]['version_id']))
            if not d or d['family']!=p['family']:raise ValueError('PAIR_OUTSIDE_CORPUS')
        pair_map[p['pair_id']]=p
    corpus_hash=digest(documents)
    config_hash=digest(config)
    tables={t:[] for t in TABLES}
    def add(table, identity, payload, *, family=None, synthetic=False, kind='derived', lineage=(), known=None, published=None, effective=None, review='unreviewed'):
        tables[table].append(dict(id=identity,family=family,synthetic=synthetic,source_kind=kind,
            corpus_hash=corpus_hash,config_hash=config_hash,known_at=known,published_on=published,
            effective_on=effective,review_status=review,human_approved=False,
            lineage_json=canonical(list(lineage)),payload_json=canonical(payload)))
    for d in documents:
        args=dict(family=d['family'],synthetic=d['synthetic'],kind=d['source_kind'],lineage=[d['sha256']],known=d['captured_at'],published=d['published_on'],effective=d['effective_on'])
        add('documents',digest([d['document_id'],d['version_id']]),d,**args)
        add('versions',digest([d['document_id'],d['version_id']]),d,**args)
    for p in provisions:
        validate('Provision',p)
        d=identities.get((p['document_id'],p['version_id']))
        if not d or p['synthetic']!=d['synthetic']:raise ValueError('PROVISION_OUTSIDE_CORPUS')
        add('provisions',p['citation_id'],p,family=d['family'],synthetic=d['synthetic'],kind=d['source_kind'],lineage=[d['sha256']],known=d['captured_at'])
    for p in pairs:
        sources=[identities[(p[s]['document_id'],p[s]['version_id'])] for s in ('before','after')]
        add('pairs',p['pair_id'],p,family=p['family'],synthetic=any(d['synthetic'] for d in sources),lineage=[d['sha256'] for d in sources])
    for comparison in comparisons:
        cs=comparison['change_set']; validate('ChangeSet',cs)
        if pair_map.get(cs['pair']['pair_id'])!=cs['pair']:raise ValueError('CHANGESET_PAIR_MISMATCH')
        expected_synthetic=any(identities[(cs['pair'][s]['document_id'],cs['pair'][s]['version_id'])]['synthetic'] for s in ('before','after'))
        if cs['evidence']['synthetic']!=expected_synthetic:raise ValueError('EVIDENCE_SYNTHETIC_MISMATCH')
        args=dict(family=cs['pair']['family'],synthetic=expected_synthetic,lineage=[cs['pair']['pair_id']],review='unreviewed')
        # Incoming approval fields are kept as data only; no authenticated review here.
        add('changes',cs['change_set_id'],comparison,**args)
        add('evidence',cs['evidence']['evidence_id'],cs['evidence'],**args)
    if ai_review:
        add('reviews',ai_review.get('run_id',digest(ai_review)),ai_review,kind='ai_reference',lineage=[digest(ai_review)],known=ai_review.get('generated_at_utc'),review='ai_reference_not_human_approval')
    for p in processes:
        if p.get('synthetic') is not True or p.get('source_kind')!='fictitious_process':raise ValueError('FICTITIOUS_PROCESS_REQUIRED')
        add('processes',p['process_id'],p,family=p.get('family'),synthetic=True,kind='fictitious_process',lineage=[digest(p)])
    for rows in tables.values():
        rows.sort(key=lambda r:r['id'])
        if len({r['id'] for r in rows})!=len(rows):raise ValueError('DUPLICATE_ROW')
    result=dict(version=VERSION,mode=mode,corpus_hash=corpus_hash,config_hash=config_hash,tables=tables,
                limitations=['Coverage partial; repository versions are not legal validity.','AI review is provisional and not human approval.','Local artifacts are not Genie execution.'])
    result['snapshot_hash']=digest(result)
    return result


COLUMNS = ('id','family','synthetic','source_kind','corpus_hash','config_hash','known_at','published_on','effective_on','review_status','human_approved','lineage_json','payload_json')


def example_queries():
    return {
        'versions_by_family':('SELECT family, COUNT(*) AS version_count FROM versions GROUP BY family',()),
        'documents_by_family':('SELECT id, published_on, effective_on, payload_json FROM documents WHERE family = :family',('family',)),
        'comparison_pairs':('SELECT id, family, payload_json FROM pairs ORDER BY id',()),
        'change_sets':('SELECT id, family, review_status, payload_json FROM changes ORDER BY id',()),
        'fictitious_processes':('SELECT id, family, source_kind FROM processes WHERE synthetic = TRUE',())}


def allowed_query(query_id, params):
    """Closed SELECT templates for own SQL execution; caller enforces backend grants."""
    entry=example_queries().get(query_id)
    if not entry or set(params)!=set(entry[1]):raise ValueError('QUERY_NOT_ALLOWED')
    if any(not isinstance(v,str) for v in params.values()):raise ValueError('INVALID_PARAMETER')
    return entry[0],deepcopy(params)


def ddl(*, remote=False):
    prefix='sbs_radar.' if remote else ''
    return '\n'.join('CREATE TABLE '+prefix+t+' ('+', '.join(c+' '+('BOOLEAN' if c in ('synthetic','human_approved') else 'STRING' if remote else 'TEXT') for c in COLUMNS)+');' for t in TABLES)


def verify_examples(bundle):
    db=sqlite3.connect(':memory:')
    try:
        db.executescript(ddl())
        for t,rows in bundle['tables'].items():
            db.executemany('INSERT INTO '+t+' VALUES ('+','.join('?' for _ in COLUMNS)+')',[[r[c] for c in COLUMNS] for r in rows])
        result=[]
        for q in example_queries():
            params={'family':'cybersecurity'} if q=='documents_by_family' else {}
            sql,params=allowed_query(q,params)
            result.append(dict(query_id=q,sql=sql,params=params,rows=[list(r) for r in db.execute(sql,params)],engine='sqlite_local_only',genie_verified=False))
        return result
    finally:db.close()


def export_bundle(bundle, output):
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    for name,rows in bundle['tables'].items():
        (out/(name+'.jsonl')).write_text(''.join(canonical(r)+'\n' for r in rows))
    (out/'manifest.json').write_text(canonical({k:v for k,v in bundle.items() if k!='tables'})+'\n')
    (out/'proposed-ddl.sql').write_text('-- REVIEW ONLY; never executed remotely. Catalog must be explicitly selected.\n'+ddl(remote=True)+'\n')
    (out/'example-queries.json').write_text(canonical(verify_examples(bundle))+'\n')
    (out/'benchmark-questions.json').write_text(canonical(BENCHMARKS)+'\n')


def _dict(value):
    if hasattr(value,'as_dict'):return value.as_dict()
    return value


class GenieAdapter:
    """Inject SDK genie service plus trusted server permission/snapshot probe.

    Network call deadlines must be configured on the injected SDK transport.
    max_polls bounds polling count, not the duration of an individual HTTP call.
    No arbitrary SQL is executed by this client; server-side generated queries
    are not inspectable before execution. Backend grants are mandatory.
    """
    def __init__(self, sdk, config, permission_probe, *, sleep=time.sleep,
                 scope_catalog=None, execution_probe=None):
        self.sdk=sdk;self.config=deepcopy(config);self.probe=permission_probe;self.sleep=sleep
        n=config.get('max_polls',3)
        if not isinstance(n,int) or isinstance(n,bool) or not 1<=n<=100:raise ValueError('INVALID_POLL_BOUND')
        if not 0<=config.get('poll_seconds',0)<=10:raise ValueError('INVALID_POLL_INTERVAL')
        self.conversations={}
        self.scope_catalog=scope_catalog
        self.execution_probe=execution_probe

    def preflight(self):
        c=self.config
        if c.get('namespace')!='sbs_radar' or not all(isinstance(c.get(k),str) and c[k].strip() for k in ('warehouse_id','space_id','snapshot')):
            return 'blocked'
        p=self.probe()
        if p.get('warehouse_id')!=c['warehouse_id']:return 'blocked'
        if p.get('snapshot')!=c['snapshot']:return 'conflict'
        if any(p.get(k) is not True for k in ('can_use','tables_read','genie_access','read_only_backend','scope_verified')):return 'denied'
        if p.get('state')!='RUNNING' or p.get('warehouse_type') not in ('PRO','SERVERLESS'):return 'blocked'
        return None

    def ask(self, question, *, conversation_id=None):
        r=dict(status='blocked',snapshot=self.config.get('snapshot'),conversation_id=conversation_id,
               message_id=None,query_id=None,query=None,rows=[],coverage='unverified',
               execution_boundary='Genie server execution requires backend read-only scope; not inspectable before execution')
        try:
            blocked=self.preflight()
            if blocked:r['status']=blocked;return r
            if not isinstance(question,str) or not question.strip():return r
            if conversation_id is not None and self.conversations.get(conversation_id)!=self.config['snapshot']:
                r['status']='conflict';return r
            kw=dict(space_id=self.config['space_id'],content=question)
            if conversation_id:
                response=self.sdk.create_message(conversation_id=conversation_id,**kw)
            else:response=self.sdk.start_conversation(**kw)
            initial=_dict(getattr(response,'response',response))
            r.update(conversation_id=initial.get('conversation_id'),message_id=initial.get('message_id'))
            if not r['conversation_id'] or not r['message_id']:r['status']='error';return r
            self.conversations[r['conversation_id']]=self.config['snapshot']
            ids=dict(space_id=self.config['space_id'],conversation_id=r['conversation_id'],message_id=r['message_id'])
            for poll in range(self.config.get('max_polls',3)):
                msg=_dict(self.sdk.get_message(**ids)); state=msg.get('status')
                if msg.get('error') or state in ('FAILED','ERROR'):r['status']='error';return r
                if state in ('CANCELLED','CANCELED'):r['status']='cancelled';return r
                if state=='COMPLETED':
                    queries=[a['query'] for a in msg.get('attachments',[]) if a.get('query')]
                    if len(queries)!=1:
                        r['status']='no_query' if not queries else 'unsupported_multiple_queries';return r
                    r['query']=queries[0].get('query')
                    stmt=_dict(self.sdk.get_message_query_result(**ids)).get('statement_response',{})
                    r['query_id']=stmt.get('statement_id')
                    sqlstate=stmt.get('status',{}).get('state')
                    if sqlstate in ('FAILED','CLOSED') or stmt.get('status',{}).get('error'):
                        r['status']='error';return r
                    if sqlstate in ('CANCELED','CANCELLED'):r['status']='cancelled';return r
                    if sqlstate=='SUCCEEDED':
                        data=stmt.get('result',{});manifest=stmt.get('manifest',{})
                        r['rows']=data.get('data_array',[])
                        r['columns']=[c['name'] for c in manifest.get('schema',{}).get('columns',[])]
                        total=manifest.get('total_row_count')
                        if manifest.get('truncated') or data.get('next_chunk_index') is not None or total is None or total!=len(r['rows']):
                            r['status']='partial'
                        else:r['status']='completed' if r['rows'] else 'empty'
                        return r
                if poll+1<self.config.get('max_polls',3):self.sleep(self.config.get('poll_seconds',0))
            r['status']='timeout'
        except Exception as exc:
            # Never emit untrusted exception strings containing credentials/SQL.
            code=getattr(exc,'error_code','')
            r['status']='denied' if isinstance(exc,PermissionError) or code in ('PERMISSION_DENIED','UNAUTHENTICATED') else 'error'
            r['error_type']=type(exc).__name__
        return r

    def ask_scoped(self, question, *, context):
        """Verify an executed reference query against an independently pinned bundle.

        Catalog and execution_probe are trusted backend dependencies, never body
        fields. The probe must retrieve executed SQL/bindings and deployed lineage
        by query ID from independent backend records, NOT Genie prose/attachments.
        Only closed reference SQL is accepted: exact parameterized text with backend bindings, or pinned-parser AST equality for executed safe literals. This is post-execution verification, never regex authorization.
        """
        rejected=dict(status='conflict',scope_verified=False,rows=[],
                      limitations=['structured_scope_not_demonstrated'])
        try:
            if not isinstance(self.scope_catalog,ScopedCatalog) or not callable(self.execution_probe):return rejected
            catalog=self.scope_catalog
            plans=catalog.references(context)
            if catalog.snapshot!=self.config.get('snapshot'):return rejected
            # Context is instruction to Genie, not proof. SQL and rows are checked below.
            prompt=question+'\nResolved documentary scope: '+canonical(context)
            prompt+='\nUse one of these closed reference queries and its exact parameters: '+canonical(
                {key:{k:p[k] for k in ('sql','parameters')} for key,p in plans.items()})
            result=self.ask(prompt)
            if result['status'] not in ('completed','empty'):
                if result['status'] in ('denied','blocked','error','timeout','cancelled'):
                    return {**result,'scope_verified':False,'rows':[]}
                return rejected
            query_id=result.get('query_id')
            if not isinstance(query_id,str) or not query_id:return rejected
            receipt=self.execution_probe(query_id)
            plan=catalog.verify(context,result,receipt)
            return {**result,'kind':'structured_query_result','context':deepcopy(context),
                    'scope_verified':True,'source_tables':deepcopy(plan['source_tables']),
                    'reference_query_id':plan['reference_query_id'],
                    'query':receipt['statement'],'parameters':deepcopy(plan['parameters']),
                    'parameters_origin':plan['parameters_origin'],
                    'execution_provenance':deepcopy(receipt.get('execution_provenance',{})),
                    'lineage':deepcopy(plan['lineage']),
                    'scope_verification':'exact_executed_reference_sql_and_pinned_rows',
                    'limitations':['Documentary result only; no normative EvidencePack or material-change inference.',
                                   'Coverage remains limited to the pinned curated corpus.']}
        except PermissionError:
            return {**rejected,'status':'denied'}
        except Exception:
            return rejected


def prepare_project(root):
    """Read frozen capture artifacts and verify local bytes, without acquisition.

    Pair order follows the explicitly enumerated captures (v7/v8 and v4/v5),
    describes documentary comparison only and never asserts current validity.
    """
    from sbs.comparison import compare
    root=Path(root).resolve()
    def local(path):
        from sbs.paths import project_path
        return project_path(root,path)
    def read(path):return json.loads(local(path).read_text())
    def filehash(path):return hashlib.sha256(local(path).read_bytes()).hexdigest()
    inputs=[];sources=[];bundles={}
    for name in ('runs/sk02-repository-capture.json','runs/sk02-amendments-capture.json'):
        record=read(name)
        if filehash(record['manifest'])!=record['manifest_sha256']:raise ValueError('MANIFEST_HASH_MISMATCH')
        manifest=read(record['manifest'])
        authorized={(s['document_id'],s['url']) for s in manifest['sources']}
        inputs.append(dict(path=name,sha256=filehash(name)))
        inputs.append(dict(path=str(local(record['manifest']).relative_to(root)),sha256=record['manifest_sha256']))
        for entry in record['sources']:
            source=entry['source'];validate('SourceDocument',source)
            if (source['document_id'],source['url']) not in authorized:raise ValueError('SOURCE_NOT_IN_MANIFEST')
            if filehash(entry['original_path'])!=source['sha256']:raise ValueError('PDF_HASH_MISMATCH')
            b=read(entry['result_path'])
            if b['sha256']!=source['sha256'] or hashlib.sha256(b['rawtext'].encode()).hexdigest()!=b['rawtext_sha256'] or filehash(entry['rawtext_path'])!=b['rawtext_sha256']:
                raise ValueError('EXTRACTION_HASH_MISMATCH')
            for p in b['provisions']:
                validate('Provision',p)
                if (p['document_id'],p['version_id'])!=(source['document_id'],source['version_id']) or b['rawtext'][p['start']:p['end']]!=p['text']:
                    raise ValueError('PROVISION_INTEGRITY_MISMATCH')
            sources.append(source);bundles[(source['document_id'],source['version_id'])]=b
            for field in ('original_path','result_path','rawtext_path'):
                inputs.append(dict(path=str(local(entry[field]).relative_to(root)),sha256=filehash(entry[field])))
    review_path='runs/astra-normative-review-003.json';review=read(review_path)
    inputs.append(dict(path=review_path,sha256=filehash(review_path)))
    # This is an IA annotation record, not a ReviewDecision granting approval.
    if review.get('ai_reference',{}).get('human_gold') is not False:raise ValueError('AI_REVIEW_PROVENANCE_REQUIRED')
    source_ids={(d['document_id'],d['version_id']) for d in sources}
    for c in review.get('citations',{}).values():
        key=(c['document_id'],c['version_id'])
        if key not in source_ids or bundles[key]['rawtext'][c['start']:c['end']]!=c['quote_raw']:
            raise ValueError('AI_CITATION_SNAPSHOT_MISMATCH')
    pairs=[];comparisons=[]
    for document_id in ('sbs-3274-2017','sbs-504-2021'):
        versions=[d for d in sources if d['document_id']==document_id]
        if len(versions)!=2:raise ValueError('EXPECTED_TWO_DOCUMENTARY_VERSIONS')
        pair=dict(pair_id='documentary-'+document_id,family=versions[0]['family'],
                  before={k:versions[0][k] for k in ('document_id','version_id')},
                  after={k:versions[1][k] for k in ('document_id','version_id')})
        pairs.append(pair)
        comparisons.append(compare(pair,*(bundles[(d['document_id'],d['version_id'])] for d in versions),coverage='partial'))
    config=dict(config_version=VERSION,namespace='sbs_radar',catalog=None,warehouse_id=None,
                space_id=None,profile='databricks-ai-engineer-aws',snapshot=None,max_polls=8,poll_seconds=1,
                sdk_transport_timeout_seconds=30,permission_probe='trusted_backend_required',
                allowed_tables=list(TABLES),status='pending_authorized_resources',
                expected_backend_grants='Dedicated principal SELECT only on mission tables; CAN USE; Genie access.',
                observed_warehouse=read('runs/sk05-workspace-preflight.json')['warehouses'][0],
                resource_policy='No start, DDL, space creation or course-resource mutation performed.',
                query_execution_boundary='Server-generated Genie SQL cannot be inspected before execution; backend grants required.')
    processes=[dict(process_id='fictitious-'+family,family=family,source_kind='fictitious_process',synthetic=True,
                    name=name,approval='none',purpose='Pilot illustration only; no institutional process claim')
               for family,name in [('market_conduct','Revisión ficticia de información al usuario'),('cybersecurity','Revisión ficticia de controles de autenticación')]]
    bundle=curate(sources,pairs,comparisons,review,processes,config,mode='real',provisions=[p for b in bundles.values() for p in b['provisions']])
    bundle['input_files']=inputs
    config['snapshot']=bundle['snapshot_hash']
    config['curation_config_hash']=bundle['config_hash']
    return bundle,config


class ScopedCatalog:
    """Frozen backend-owned corpus and registered QueryContexts for strict queries.

    Registration is not authentication. The constructor must run behind the
    server boundary on trusted files/contexts, never on user-supplied JSON. Only
    documentary version/provision lists and row counts are supported. Date-based
    legal validity, ChangeSet material counts and arbitrary SQL remain conflicts.
    """
    def __init__(self, bundle, contexts, *, table_prefix, delta_versions=None):
        parts=table_prefix.split('.') if isinstance(table_prefix,str) else []
        if len(parts)!=2 or parts[1]!='sbs_radar' or any(not p.isascii() or not p.isidentifier() for p in parts):
            raise ValueError('AUTHORIZED_CATALOG_AND_MISSION_SCHEMA_REQUIRED')
        snapshot=bundle.get('snapshot_hash')
        content={k:v for k,v in bundle.items() if k not in ('snapshot_hash','input_files')}
        if not isinstance(snapshot,str) or digest(content)!=snapshot:raise ValueError('CURATED_SNAPSHOT_INTEGRITY_FAILED')
        self._bundle=deepcopy(bundle)
        self.snapshot=snapshot
        self.corpus_hash=bundle['corpus_hash']
        self.table_prefix=table_prefix
        self._delta_versions=deepcopy(delta_versions)
        if delta_versions is not None:
            if (not isinstance(delta_versions,dict) or set(delta_versions)!={table_prefix+'.'+t for t in TABLES}
                    or any(type(v) is not int or v<0 for v in delta_versions.values())):
                raise ValueError('DELTA_VERSION_VECTOR_INVALID')
        self._contexts={}
        tables=self._bundle['tables']
        for name in ('documents','provisions','pairs'):
            for row in tables[name]:
                if row['corpus_hash']!=self.corpus_hash or row['config_hash']!=bundle['config_hash']:
                    raise ValueError('ROW_LINEAGE_MISMATCH')
        docs={}
        for row in tables['documents']:
            payload=json.loads(row['payload_json']);validate('SourceDocument',payload)
            if row['family']!=payload['family'] or json.loads(row['lineage_json'])!=[payload['sha256']]:
                raise ValueError('DOCUMENT_LINEAGE_MISMATCH')
            docs[(payload['document_id'],payload['version_id'])]=payload
        for row in tables['provisions']:
            payload=json.loads(row['payload_json']);validate('Provision',payload)
            d=docs.get((payload['document_id'],payload['version_id']))
            if not d or d['family']!=row['family'] or json.loads(row['lineage_json'])!=[d['sha256']]:
                raise ValueError('PROVISION_LINEAGE_MISMATCH')
        pairs={row['id']:json.loads(row['payload_json']) for row in tables['pairs']}
        for context in contexts:
            validate('QueryContext',context)
            if pairs.get(context['pair']['pair_id'])!=context['pair']:raise ValueError('CONTEXT_PAIR_NOT_PINNED')
            for side in ('before','after'):
                ref=context['pair'][side]
                d=docs.get((ref['document_id'],ref['version_id']))
                if not d or d['family']!=context['family']:raise ValueError('CONTEXT_SOURCE_MISMATCH')
            if context['context_id'] in self._contexts:raise ValueError('DUPLICATE_CONTEXT')
            self._contexts[context['context_id']]=deepcopy(context)

    def references(self, context):
        validate('QueryContext',context)
        if self._contexts.get(context['context_id'])!=context:raise ValueError('CONTEXT_NOT_REGISTERED')
        if context['target_date'] is not None:raise ValueError('LEGAL_EFFECT_SCOPE_UNSUPPORTED')
        selected=context['selected_provision_id']
        table='provisions' if selected is not None else 'documents'
        params={'family':context['family'],'corpus_hash':self.corpus_hash}
        for side in ('before','after'):
            for key in ('document_id','version_id'):params[side+'_'+key]=context['pair'][side][key]
        clauses=["family = :family", "corpus_hash = :corpus_hash"]
        sides=[]
        for side in ('before','after'):
            sides.append('('+' AND '.join("get_json_object(payload_json, '$."+key+"') = :"+side+'_'+key for key in ('document_id','version_id'))+')')
        clauses.append('('+' OR '.join(sides)+')')
        if selected is not None:
            clauses.append("get_json_object(payload_json, '$.provision_id') = :provision_id")
            params['provision_id']=selected
        source_table=self.table_prefix+'.'+table
        temporal='' if self._delta_versions is None else ' VERSION AS OF '+str(self._delta_versions[source_table])
        tail=' FROM '+source_table+temporal+' WHERE '+' AND '.join(clauses)
        rows=[];lineage=[]
        identities={(context['pair'][s]['document_id'],context['pair'][s]['version_id']) for s in ('before','after')}
        for row in self._bundle['tables'][table]:
            payload=json.loads(row['payload_json'])
            if row['family']!=context['family'] or (payload['document_id'],payload['version_id']) not in identities:continue
            if selected is not None and payload['provision_id']!=selected:continue
            rows.append([row[k] for k in ('id','family','corpus_hash','payload_json')])
            lineage.append(dict(row_id=row['id'],row_sha256=digest(row),source_sha256=json.loads(row['lineage_json']),
                                document_id=payload['document_id'],version_id=payload['version_id']))
        rows.sort(key=lambda r:r[0]);lineage.sort(key=lambda r:r['row_id'])
        if selected is not None and not rows:
            raise ValueError('SELECTED_PROVISION_NOT_CURATED')
        prefix='provision' if selected is not None else 'document'
        count_column='provision_row_count' if selected is not None else 'document_version_count'
        plans={}
        for kind,projection,columns,expected in [
            ('list','id, family, corpus_hash, payload_json',['id','family','corpus_hash','payload_json'],rows),
            ('count','COUNT(*) AS '+count_column,[count_column],[[str(len(rows))]])]:
            query_id=prefix+'_'+kind
            plans[query_id]=dict(reference_query_id=query_id,sql='SELECT '+projection+tail+(' ORDER BY id' if kind=='list' else ''),
                parameters=deepcopy(params),source_tables=[source_table],columns=columns,rows=deepcopy(expected),
                lineage=dict(corpus_hash=self.corpus_hash,snapshot=self.snapshot,pair=deepcopy(context['pair']),
                             selected_provision_id=selected,rows=deepcopy(lineage)))
        return plans

    def verify(self, context, result, receipt):
        if not isinstance(receipt,dict):raise ValueError('EXECUTION_RECEIPT_REQUIRED')
        if receipt.get('query_id')!=result.get('query_id') or receipt.get('snapshot')!=self.snapshot or receipt.get('state')!='SUCCEEDED':
            raise ValueError('EXECUTION_LINEAGE_MISMATCH')
        if not isinstance(receipt.get('statement'),str) or not isinstance(receipt.get('parameters'),dict):
            raise ValueError('EXECUTED_SQL_REQUIRED')
        mode=receipt.get('parameter_mode','bound_parameters')
        matches=[]
        for p in self.references(context).values():
            if receipt.get('source_tables')!=p['source_tables']:continue
            if mode=='bound_parameters':
                matched=receipt['statement']==p['sql'] and canonical(receipt['parameters'])==canonical(p['parameters'])
            elif mode=='executed_literals' and receipt['parameters']=={}:
                from .provenance import matches_literal_reference
                matched=matches_literal_reference(receipt['statement'],p['sql'],p['parameters'])
            else:matched=False
            if matched:matches.append(p)
        if len(matches)!=1:raise ValueError('EXECUTED_REFERENCE_QUERY_MISMATCH')
        plan=matches[0]
        plan['parameters_origin']='verified_executed_literal_values' if mode=='executed_literals' else 'independent_backend_bound_parameters'
        if result.get('columns')!=plan['columns']:raise ValueError('RESULT_COLUMNS_MISMATCH')
        actual=result.get('rows')
        if not isinstance(actual,list) or any(not isinstance(row,list) or any(type(v) not in (str,int) for v in row) for row in actual):
            raise ValueError('MALFORMED_ROWS')
        normalized=[[str(v) for v in row] for row in actual]
        if normalized!=plan['rows']:raise ValueError('ROWS_DIFFER_FROM_PINNED_CORPUS')
        return plan
