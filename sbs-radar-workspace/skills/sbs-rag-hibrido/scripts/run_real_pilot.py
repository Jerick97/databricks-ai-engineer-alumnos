"""Bounded real SK04/05/09 pilot. Invoke with --execute only in authorized scope.
Success caches are sealed and reused; uncertain/failed attempts block automatic resume.
No generation, remote resources, automatic retries, tuning or human-gold claims.
"""
import argparse, hashlib, json, math, os, sys, time
from datetime import datetime, timezone
from pathlib import Path
from copy import deepcopy
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'src'))
from sbs.foundation.extract import extract
from sbs.models import ModelManifest
from sbs.models.databricks import DatabricksEmbeddingAdapter, PinnedQwenTokenizer, SingleShotTransport, ENDPOINT
from sbs.models.reranker import LocalOnnxReranker, verify_manifest
from sbs.retrieval import chunk_spans, LocalIndex, ServerScope, retrieve
from sbs.evaluation import retrieval_metrics

RUN='sk04-real-001'
D=ROOT/'data/retrieval'/RUN

def now(): return datetime.now(timezone.utc).isoformat()
def canonical(v): return json.dumps(v, ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def sha(v): return hashlib.sha256(canonical(v).encode()).hexdigest()
def file_sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text())
def write(p,v):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    b=canonical(v)+'\n'
    if p.exists():
        if p.read_text()!=b: raise ValueError('immutable_artifact_conflict:'+p.name)
        return
    with p.open('x') as f: f.write(b); f.flush(); os.fsync(f.fileno())
def sealed(p,v): write(p,{'sha256':sha(v),'payload':v})
def unseal(p):
    x=read(p)
    if sha(x['payload'])!=x['sha256']: raise ValueError('cache_integrity_failed')
    return x['payload']

def main(execute=False):
    os.chdir(ROOT); D.mkdir(parents=True,exist_ok=True)
    completed=ROOT/'runs'/f'{RUN}-report.json'
    if completed.exists():
        report=read(completed)
        for path,digest in report['artifacts_sha256'].items():
            if file_sha(ROOT/path)!=digest: raise ValueError('completed_artifact_integrity_failed')
        if unseal(ROOT/'runs'/f'{RUN}-protocol.json') and report['status']=='real_index_and_three_queries_completed':
            print(canonical({'status':'completed_run_verified_no_inference','embedding_calls_original':report['embedding_calls']}),flush=True)
            return
    inputs=['runs/sk02-repository-capture.json','runs/sk02-amendments-capture.json','runs/astra-normative-review-003.json','runs/astra-normative-review.json','runs/sk05-qwen-smoke-bundle-v2.json','runs/sk05-qwen-tokenizer.json','context/reranker-manifest.json']
    invocation={'run_id':RUN,'scope':'authorized existing endpoint integration; no monetary budget inferred','input_sha256':{p:file_sha(p) for p in inputs},'skills':{p:file_sha(p) for p in ['skills/sbs-rag-hibrido/SKILL.md','skills/sbs-modelos-configuracion/SKILL.md','skills/sbs-evaluacion-jueces/SKILL.md']},'strategy':'span-limpio-contexto-v1@1','max_calls':20,'max_reserved_tokens':200000,'max_batch_size':8,'automatic_retries':0,'cost':None}
    write(ROOT/'runs'/f'{RUN}-invocation.json',invocation)
    sources=sum([read(p)['sources'] for p in inputs[:2]],[])
    artifacts=[]
    for s in sources:
        a=extract(s['source'],root=ROOT/'data/foundation-repository')
        if sha(a)!=sha(read(s['result_path'])): raise ValueError('extractstore_result_mismatch')
        artifacts.append((s,a))
    corpus=[{'document_id':s['source']['document_id'],'version_id':s['source']['version_id'],'original_sha256':file_sha(s['original_path']),'rawtext_sha256':a['rawtext_sha256'],'result_sha256':file_sha(s['result_path']),'extractor':a['extractor'],'config_hash':a['config_hash']} for s,a in artifacts]
    bundle=deepcopy(read(inputs[4])['bundle']); rerank_manifest=read(inputs[6]); verify_manifest(rerank_manifest)
    bundle.update(bundle_id='sbs-pilot-real-page-qwen-minilm',revision='1',chunking_version='sbs-preserve-input-units-page-v1',reranker_model=rerank_manifest['repo_id'],reranker_revision=rerank_manifest['revision'])
    bundle['parameters'].update(corpus_hash=sha(corpus),extractor_version=artifacts[0][1]['extractor'],strategy_adaptation_status='partial_raw_page_units_not_semantic_boundaries',chunking_adaptation='preserve_input_units(page)',context_chars=0,reranker_manifest_sha256=file_sha(inputs[6]),reranker_pair_limit=512,reranker_adaptation='sbs-reranker-contiguous-char-windows-v1',reranker_aggregation='max_raw_logit',reranker_cpu_threads=2,other_models_status='generation_unselected')
    manifest=ModelManifest.from_bundle(bundle)
    write(ROOT/'config/pilot-model-bundle.json',{'bundle':manifest.bundle,'bundle_hash':manifest.bundle_hash})
    tok=read(inputs[5]); tokenizer=PinnedQwenTokenizer(tok['files']['tokenizer.json']['path'],revision=tok['revision'],sha256=tok['files']['tokenizer.json']['sha256'])
    # This transport is intentionally unavailable until the sealed full preflight is ready.
    adapter=DatabricksEmbeddingAdapter(manifest,tokenizer,transport=None,max_calls=20,max_tokens=200000)
    records=[]
    for s,a in artifacts:
        records.extend(chunk_spans(a,family=s['source']['family'],counter=adapter.token_counter,model_identity=manifest.bundle_hash,limit=32760,context_chars=0))
    write(D/'records.json',records); write(D/'corpus.json',corpus)
    prior=read(inputs[3]); review=read(inputs[2]); citations={**prior['citations'],**review['citations']}
    specs=[('cyber-art20-3','cybersecurity','¿Cómo cambió la responsabilidad por pérdidas en operaciones digitales sin autenticación reforzada en el artículo 20.3 entre las versiones 4 y 5?',['v4-art20-3','v5-art20-3']),('market-art27','market_conduct','¿Qué cambió en el artículo 27 sobre seguros adicionales, contratación independiente y consentimiento del usuario entre las versiones 7 y 8?',['market-v7-art27','market-v8-art27']),('market-art29-1-4','market_conduct','¿Qué cambió en el artículo 29.1 numeral 4 sobre canales para pagos anticipados y adelantos de cuotas entre las versiones 7 y 8?',['market-v7-art29-1','market-v8-art29-1'])]
    queries=[]; mappings=[]; qrels={}; counterparts={}; alignment={}
    for qid,family,question,keys in specs:
        sides={}; pair={'pair_id':qid,'family':family}
        for side,key in zip(('before','after'),keys):
            c=citations[key]
            a=next(a for s,a in artifacts if s['source']['version_id']==c['version_id'])
            if a['rawtext'][c['start']:c['end']]!=c['quote_raw']: raise ValueError('review_quote_mismatch')
            rows=[r['citation'] for r in records if r['citation']['version_id']==c['version_id'] and r['citation']['start']<c['end'] and r['citation']['end']>c['start']]
            if not rows: raise ValueError('review_mapping_empty')
            sides[side]=[r['citation_id'] for r in rows]
            pair[side]={k:c[k] for k in ('document_id','version_id')}
            mappings.append({'query_id':qid,'review_key':key,'review_path':inputs[2] if key in review['citations'] else inputs[3],'review_span':[c['start'],c['end']],'version_id':c['version_id'],'page_citation_ids':sides[side],'overlaps':[[max(c['start'],r['start']),min(c['end'],r['end'])] for r in rows]})
        for side,other in [('before','after'),('after','before')]:
            for cid in sides[side]: alignment.setdefault(cid,[]).extend(x for x in sides[other] if x not in alignment.get(cid,[]))
        qrels[qid]={cid:1 for ids in sides.values() for cid in ids}; counterparts[qid]={qid:sides}
        queries.append({'query_id':qid,'family':family,'question':question,'context':{'context_id':qid,'family':family,'pair':pair,'target_date':None,'selected_provision_id':None}})
    protocol={'protocol_id':RUN+'-pilot-protocol-v1','corpus_hash':sha(corpus),'bundle_hash':manifest.bundle_hash,'questions_hash':sha(queries),'questions':queries,'qrels':qrels,'counterparts':counterparts,'alignment':alignment,'citation_mappings':mappings,'k':[5],'candidate_k':20,'rrf_k':60,'thresholds':{'recall':.95,'ndcg':.8,'counterparts':1},'variants':['lexical','vector','rrf','rrf_rerank'],'reference_kind':'partial_independent_AI_reference','human_gold':False,'exhaustive':False,'partition':'single_dependency_connected_pilot_group_no_tuning_no_holdout','acceptance':'not_evaluated','freeze_method':'canonical_sha256_write_once_before_any_inference','freeze_protocol_api_not_used':'API requires independent nonempty tune/holdout; this pilot cannot truthfully supply them','counterpart_scope':'sampled reviewed article alignments only; not all pages','scope':'retrieve consolidated before/after pair; amending acts indexed but outside these pair queries; no current global law claim'}
    for q in queries: retrieval_metrics([],qrels[q['query_id']],5,counterparts[q['query_id']])
    sealed(ROOT/'runs'/f'{RUN}-protocol.json',protocol)
    batches=[]
    for i in range(0,len(records),8):
        texts=[''.join(r['input_parts']) for r in records[i:i+8]]
        batches.append({'batch_id':f'doc-{i//8:03d}','role':'document','texts':texts,'citation_ids':[r['citation']['citation_id'] for r in records[i:i+8]],'preflight':adapter.preflight(texts)})
    qt=[q['question'] for q in queries]
    batches.append({'batch_id':'queries-000','role':'query','texts':qt,'query_ids':[q['query_id'] for q in queries],'preflight':adapter.preflight(qt,role='query')})
    reserve=sum(b['preflight']['reserved_tokens'] for b in batches)
    preflight={'corpus_hash':sha(corpus),'record_count':len(records),'batches':[{k:v for k,v in b.items() if k!='texts'} | {'input_sha256':sha(b['texts'])} for b in batches],'calls':len(batches),'reserved_tokens':reserve,'max_calls':20,'max_tokens':200000,'max_batch':8,'bundle_hash':manifest.bundle_hash,'protocol_sha256':sha(protocol),'status':'ready' if len(batches)<=20 and reserve<=200000 else 'quota_exceeded','generation':'unselected','cost':None}
    write(ROOT/'runs'/f'{RUN}-preflight.json',preflight)
    print(canonical({k:v for k,v in preflight.items() if k!='batches'}),flush=True)
    if preflight['status']!='ready' or not execute: return
    if (ROOT/'runs'/f'{RUN}-failure.json').exists(): raise ValueError('failed_run_requires_explicit_new_scope_no_automatic_retry')
    from databricks.sdk import WorkspaceClient
    client=WorkspaceClient(profile='databricks-ai-engineer-aws')
    ep=client.serving_endpoints.get(ENDPOINT).as_dict()
    observed={'endpoint':ENDPOINT,'task':ep.get('task'),'config_version':ep.get('config',{}).get('config_version'),'models':[{'foundation_model_name':x.get('foundation_model',{}).get('name'),'entity_name':x.get('entity_name'),'entity_version':x.get('entity_version')} for x in ep.get('config',{}).get('served_entities',[])]}
    expected={k:v for k,v in read('runs/sk05-embedding-smoke-003.json')['model_configuration'].items() if k!='observed_at'}
    write(D/'endpoint-observation.json',{'configuration':observed,'matches_prior_verified_configuration':observed==expected})
    if observed!=expected: raise ValueError('endpoint_configuration_changed')
    adapter._transport=SingleShotTransport(client)
    vectors=[]; query_vectors=None; usage=[]
    for b in batches:
        p=D/(b['batch_id']+'.json'); marker=D/(b['batch_id']+'-attempt.json')
        if p.exists():
            result=unseal(p)
            if result['input_sha256']!=sha(b['texts']) or result['bundle_hash']!=manifest.bundle_hash: raise ValueError('cached_batch_identity_mismatch')
            adapter.calls_attempted+=1; adapter.tokens_reserved+=b['preflight']['reserved_tokens']
        else:
            if marker.exists(): raise ValueError('uncertain_prior_attempt_no_retry')
            write(marker,{'started_at':now(),'input_sha256':sha(b['texts']),'role':b['role'],'reserved_tokens':b['preflight']['reserved_tokens']})
            try:
                result=adapter.embed(b['texts'],role=b['role'])
                result['input_sha256']=sha(b['texts'])
                sealed(p,result)
            except Exception as e:
                write(ROOT/'runs'/f'{RUN}-failure.json',{'stage':'embedding','batch_id':b['batch_id'],'error_type':type(e).__name__,'diagnostics':adapter.last_attempt,'calls_attempted':adapter.calls_attempted,'reserved_tokens':adapter.tokens_reserved,'cost':None,'stop':'No automatic retry; successful batches preserved'})
                raise
        usage.append({k:v for k,v in result.items() if k!='embeddings'})
        if result.get('server_usage_exceeds_reserve'): raise ValueError('server_usage_exceeds_reserved_stop')
        if b['role']=='document': vectors.extend(result['embeddings'])
        else: query_vectors=result['embeddings']
        print(b['batch_id']+' persisted',flush=True)
    index=LocalIndex(records,vectors,dimension=adapter.dimension,model_identity=adapter.identity,actual_identity=adapter.identity,complete=True)
    sealed(D/'index.json',{'index_hash':index.index_hash,'records_sha256':file_sha(D/'records.json'),'bundle_hash':adapter.identity,'dimension':adapter.dimension,'vectors':vectors,'complete_for_selected_six_PDF_raw_pages':True,'legal_coverage':'partial'})
    reranker=LocalOnnxReranker.from_manifest(ROOT/'context/reranker-manifest.json',cpu_threads=2)
    scope=ServerScope(frozenset(['cybersecurity','market_conduct']),frozenset((s['source']['document_id'],s['source']['version_id']) for s,a in artifacts))
    outputs=[]
    for q,qv in zip(queries,query_vectors):
        query_path=ROOT/'runs'/f"{RUN}-{q['query_id']}.json"
        if query_path.exists():
            item=unseal(query_path)
            if item['query']!=q or item['query_vector_sha256']!=sha(qv) or item['result']['trace']['index_hash']!=index.index_hash:
                raise ValueError('cached_query_identity_mismatch')
            outputs.append(item)
            continue
        started=time.perf_counter()
        result=retrieve(index,q['question'],q['context'],scope,query_vector=qv,query_identity=adapter.identity,top_k=5,candidate_k=20,reranker=reranker,counterparts=alignment)
        elapsed=time.perf_counter()-started
        if result['status']=='technical_error': raise ValueError('retrieval_technical_error')
        metrics={}
        for name,tracekey in [('lexical','lexical'),('vector','vector'),('rrf','fusion'),('rrf_rerank','reranked')]:
            metrics[name]=retrieval_metrics([x[0] for x in result['trace'][tracekey]],qrels[q['query_id']],5,counterparts[q['query_id']])
        expanded=[c['citation_id'] for c in result['evidence']['citations']]
        item={'query':q,'query_vector_sha256':sha(qv),'result':result,'metrics_top5_before_expansion':metrics,'counterpart_expansion_metrics':retrieval_metrics(expanded,qrels[q['query_id']],len(expanded),counterparts[q['query_id']]),'reranker_windows':reranker.last_trace,'retrieval_reranking_seconds':elapsed,'cost':None}
        sealed(ROOT/'runs'/f"{RUN}-{q['query_id']}.json",item); outputs.append(item)
        print(q['query_id']+' measured',flush=True)
    summary={'run_id':RUN,'status':'real_index_and_three_queries_completed','bundle_hash':manifest.bundle_hash,'index_hash':index.index_hash,'protocol_sha256':sha(protocol),'index_records':len(records),'documents':len(sources),'embedding_calls':adapter.calls_attempted,'reserved_tokens':adapter.tokens_reserved,'usage':usage,'cost':None,'metrics':{x['query']['query_id']:x['metrics_top5_before_expansion'] for x in outputs},'latency_seconds':{x['query']['query_id']:x['retrieval_reranking_seconds'] for x in outputs},'acceptance':'not_evaluated','limitations':['Three related reviewed examples; no independent holdout or exhaustive denominator','Physical page spans; semantic segmentation, layout, tables and annexes remain partial','Counterpart expansion uses only reviewed article alignment; no page-number pairing','Remote weights mutable: pinned observed endpoint configuration and exact response model, no weights hash','Generation unselected; no answer grounding metrics','No current global legal coverage; missing 0771-2026 and amendment history','Reranker uses contiguous character windows and max logit; cross-window dependencies not modeled','No monetary authorization inferred from proposed USD100; actual cost unknown'],'artifacts_sha256':{str(p.relative_to(ROOT)):file_sha(p) for p in sorted(D.glob('*.json'))}}
    write(ROOT/'runs'/f'{RUN}-report.json',summary)
    print(canonical({'status':summary['status'],'embedding_calls':summary['embedding_calls'],'reserved_tokens':summary['reserved_tokens']}),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--execute',action='store_true');args=ap.parse_args()
    try: main(args.execute)
    except Exception as e:
        print(canonical({'status':'stopped','error_type':type(e).__name__,'error':str(e) if isinstance(e,ValueError) else 'sanitized_nonvalidation_failure'}),flush=True)
        sys.exit(1)
