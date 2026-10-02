"""047 local structural index/rankings. No qrels, network, adapters or promotion."""
from pathlib import Path
from copy import deepcopy
from datetime import datetime,timezone
import argparse,hashlib,json,time,math
from sbs.genie import digest
from sbs.retrieval import LocalIndex,ServerScope,retrieve,_terms
from sbs.retrieval.embedding_execution import local,unseal

POLICY={'version':'structural-ranking-047-v1','candidate_k':20,'rrf_k':60,'top_k':[5,20],
        'bm25_k1':1.5,'bm25_b':.75,'scope':'server-owned family and pair document_versions before scoring',
        'rrf_pool':'exact top20 RRF of lexical top20 and vector top20','reranker_pool':'same frozen RRF top20',
        'target_expansion':False,'neighbors':False,'partition':'exposed_development','judgments_read':False,
        'zero_lexical_scores':'unranked','tie_break':'passage_id ascending','cpu_threads':2,'lexical_028_comparison':'exact IDs/order;score delta <=2*unique_terms*ulp(max(abs(scores))) to cover unordered-set summation rounding'}

def project_records(passages,metadata,inputs,bundles,*,synthetic=False):
    """Explicit lossless026->LocalIndex projection; never rechunk overlapping units.

    Page/artifact provenance remains literal. Annotation origin is carried beside
    the citation, not elevated to legal approval or substituted for citation text.
    """
    if len(passages)!=len(inputs) or len({p['passage_id'] for p in passages})!=len(passages):raise ValueError('PROJECTION_IDS')
    rows=[]
    for p,item in zip(passages,inputs):
        if item['passage_id']!=p['passage_id']:raise ValueError('PROJECTION_ORDER')
        m=metadata[p['passage_id']];b=bundles[(p['document_id'],p['version_id'])];raw=b['rawtext']
        if hashlib.sha256(raw.encode()).hexdigest()!=b['rawtext_sha256'] or p['rawtext_sha256']!=b['rawtext_sha256']:raise ValueError('PROJECTION_RAW_HASH')
        if type(p['start']) is not int or type(p['end']) is not int or not 0<=p['start']<p['end']<=len(raw) or raw[p['start']:p['end']]!=p['quote']:raise ValueError('PROJECTION_LITERAL')
        touched=[x['page'] for x in b['pages'] if x['start']<p['end'] and x['end']>p['start']]
        initial=[x['page'] for x in b['pages'] if x['start']<=p['start']<x['end']]
        if initial!=[p['page']] or touched!=m['pages']:raise ValueError('PROJECTION_PAGES')
        if item['embedding_start']!=p['start'] or item['embedding_text']!=p['quote'] or item['input_parts']!=['',p['quote']]:raise ValueError('PROJECTION_INPUT')
        citation={k:p[k] for k in ('document_id','version_id','start','end','page')}
        citation.update(citation_id=p['passage_id'],provision_id=m['provision_id'],text=p['quote'],source_kind='normative',synthetic=synthetic)
        rows.append({'family':m['family'],'citation':citation,'pages':touched,'embedding_start':item['embedding_start'],
                     'embedding_text':item['embedding_text'],'input_parts':deepcopy(item['input_parts']),'budget':deepcopy(item['budget']),
                     'limitations':['structural_partial_literal_units','not_legal_adjudication','notes_and_furniture_may_remain','overlapping_annotated_and_automatic_units_preserved'],
                     'source':{k:b[k] for k in ('sha256','rawtext_sha256','extractor','config_hash')},
                     'strategy':{'id':'span-limpio-contexto-v1','version':1,'adaptation':'exact_structural_units_plus_explicit_annotated_subspans','context_chars':0},
                     'literal_sha256':hashlib.sha256(p['quote'].encode()).hexdigest(),'origin':m['origin']})
    return rows

def scoped_variants(index,question,pair,query_vector):
    scope=ServerScope(frozenset({pair['family']}),frozenset((pair[s]['document_id'],pair[s]['version_id']) for s in ('before','after')))
    context={'context_id':'development-'+pair['pair_id'],'family':pair['family'],'pair':pair,'target_date':None,'selected_provision_id':None}
    result=retrieve(index,question,context,scope,query_vector=query_vector,query_identity=index.model_identity,
                    top_k=20,candidate_k=20,rrf_k=60,neighbors=None,counterparts=None)
    if result['status'] not in ('partial','empty'):raise ValueError('RETRIEVAL_NOT_READY')
    ids=[r['citation']['citation_id'] for r in index._rows if scope.permits(r)]
    t=result['trace']
    return {'eligible_ids':ids,'rankings':{'lexical':t['lexical'],'vector':t['vector'],'rrf':t['fusion']},'trace':t}

def lexical_matches(question,current,previous):
    if [pid for pid,_ in current]!=[x['passage_id'] for x in previous]:return False
    n=max(1,len(set(_terms(question))))
    return all(abs(score-old['score'])<=2*n*math.ulp(max(abs(score),abs(old['score']))) for (_,score),old in zip(current,previous))

def save(path,payload):
    raw=json.dumps(payload,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False).encode()+b'\n'
    with Path(path).open('xb') as f:f.write(raw)
    return hashlib.sha256(raw).hexdigest()

def anchored_read(root,name,expected):
    raw=local(Path(root).resolve(),name).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('ANCHORED_INPUT_HASH')
    return json.loads(raw)

def run(root,output):
    root=Path(root).resolve();output=local(root,output)
    if output.exists():raise ValueError('OUTPUT_EXISTS')
    output.mkdir(parents=True)
    observed={}
    def read(name):
        raw=local(root,name).read_bytes();observed[name]=hashlib.sha256(raw).hexdigest();return json.loads(raw)
    def sealed(name):
        v=read(name)
        if digest(v['payload'])!=v['sha256']:raise ValueError('ENVELOPE_HASH')
        return v['payload']
    try:
        compatibility=read('runs/sk05-query-compatibility-046.json')
        review=read('runs/sk09-query-compatibility-046-review.json')
        # The frozen approval is evidence, not a new remote capability.
        if observed['runs/sk09-query-compatibility-046-review.json']!='4b1aab5aa826d117279d80d0766144982f1b3ef37583d05a315730349dbd11ab':raise ValueError('COMPATIBILITY_REVIEW_CHANGED')
        if observed['runs/sk05-query-compatibility-046.json']!=review['input_result_sha256']:raise ValueError('COMPATIBILITY_REPORT_CHANGED')
        if compatibility['status']!='compatible_under_observed_contract_for_local_exposed_development':raise ValueError('COMPATIBILITY_NOT_READY')
        for name,sha in compatibility['inputs_sha256'].items():
            # Only relevant inputs consumed below; never open qrels/metrics.
            if name.endswith(('queries-000.json','vectors.json','endpoint-0000.json','pilot-model-bundle.json','sk04-embeddings-041-plan-v2.json')):
                if hashlib.sha256(local(root,name).read_bytes()).hexdigest()!=sha:raise ValueError('COMPATIBILITY_INPUT_DRIFT')
        base='data/retrieval/structural-development-026/'
        pins=compatibility['inputs_sha256']
        def anchored(name,expected):
            value=anchored_read(root,name,expected);observed[name]=expected;return value
        artifacts=anchored(base+'artifacts.json',pins[base+'artifacts.json'])
        manifest=anchored(base+'manifest.json',pins[base+'manifest.json'])
        def data(name):
            p=base+name+'.json';value=anchored(p,pins[p])
            if observed[p]!=artifacts[name+'.json']['sha256']:raise ValueError('DATASET_HASH')
            return value
        passages=data('passages');inputs=data('embedding_inputs');metadata=data('passage_metadata');qs=data('questions');pairs=data('pairs')
        pairmap={p['pair_id']:{k:p[k] for k in ('pair_id','family','before','after')} for p in pairs}
        # Dataset pair side objects include source metadata, QueryContext does not.
        for pair in pairmap.values():
            for side in ('before','after'):pair[side]={k:pair[side][k] for k in ('document_id','version_id')}
        bundles={}
        for p in passages:
            key=(p['document_id'],p['version_id'])
            if key not in bundles:
                result_path=str(Path(p['rawtext_path']).with_name('result.json'));b=anchored(result_path,manifest['source_files'][result_path])
                if b['rawtext_sha256']!=p['rawtext_sha256']:raise ValueError('RAW_BUNDLE_HASH')
                bundles[key]=b
        rows=project_records(passages,metadata,inputs,bundles)
        envelope=sealed('runs/sk04-embeddings-041-vectors/vectors.json');queries=sealed('data/retrieval/sk04-real-001/queries-000.json')
        if envelope['mode']!='real' or envelope['passage_ids']!=[p['passage_id'] for p in passages] or envelope['candidate_corpus_hash']!=digest(passages):raise ValueError('VECTOR_IDS_OR_CORPUS')
        if queries['bundle_hash']!=envelope['model_identity'] or queries['input_sha256']!=digest([q['question'] for q in qs]) or len(queries['embeddings'])!=len(qs):raise ValueError('QUERY_IDENTITY')
        index=LocalIndex(rows,envelope['vectors'],dimension=envelope['dimension'],model_identity=envelope['model_identity'],actual_identity=envelope['model_identity'])
        recsha=save(output/'records.json',rows)
        idxsha=save(output/'index.json',{'index_hash':index.index_hash,'records_sha256':recsha,'model_identity':index.model_identity,'candidate_corpus_hash':digest(passages),'dimension':index.dimension,'vectors':envelope['vectors'],'complete':True,'coverage':'all231selected_development_passages_not_global_normative_coverage'})
        results={k:[] for k in ('lexical','vector','rrf')};traces=[]
        prior=read('runs/sk04-lexical-development-028-rankings-lexical.json');prior={r['query_id']:r for r in prior['results']}
        for q,vector in zip(qs,queries['embeddings']):
            pair=pairmap[q['pair_id']]
            if pair['family']!=q['family']:raise ValueError('PAIR_FAMILY')
            start=time.perf_counter();r=scoped_variants(index,q['question'],pair,vector);elapsed=time.perf_counter()-start
            if r['eligible_ids']!=prior[q['query_id']]['eligible_ids'] or not lexical_matches(q['question'],r['rankings']['lexical'],prior[q['query_id']]['ranking'][:20]):raise ValueError('LEXICAL_028_MISMATCH')
            for variant,ranking in r['rankings'].items():
                results[variant].append({'query_id':q['query_id'],'family':q['family'],'pair_id':q['pair_id'],'question':q['question'],'eligible_ids':r['eligible_ids'],'ranking':[{'passage_id':pid,'score':score,'rank':n+1} for n,(pid,score) in enumerate(ranking)],'pool_top20':[pid for pid,_ in ranking],'seconds_shared_retrieval':elapsed})
            traces.append({'query_id':q['query_id'],'lexical_028_max_abs_score_delta':max((abs(s-o['score']) for (_,s),o in zip(r['rankings']['lexical'],prior[q['query_id']]['ranking'][:20])),default=0),'lexical_028_exact_ids':True,'trace':r['trace'],'shared_retrieval_seconds':elapsed})
        hashes={}
        for variant,values in results.items():hashes[variant]=save(output/f'rankings-{variant}.json',{'policy':POLICY,'results':values,'inputs':observed.copy(),'index_hash':index.index_hash,'metrics_computed':False})
        save(output/'traces.json',traces)
        from sbs.models.reranker import LocalOnnxReranker
        from sbs.paths import resolve_model_manifest
        model=resolve_model_manifest(read('context/reranker-manifest.json'),root=root)
        start=time.perf_counter();backend=LocalOnnxReranker.from_manifest(model,cpu_threads=2);loaded=time.perf_counter()-start
        rowmap={r['citation']['citation_id']:r for r in rows};reranked=[]
        for q in results['rrf']:
            pool=q['pool_top20'];candidates=[deepcopy(rowmap[pid]) for pid in pool]
            start=time.perf_counter();scores=list(backend(q['question'],candidates));elapsed=time.perf_counter()-start
            if len(scores)!=len(pool) or any(type(s) not in (float,int) or not math.isfinite(s) for s in scores):raise ValueError('RERANKER_SCORES')
            ranked=sorted(zip(pool,scores),key=lambda x:(-x[1],x[0]))
            reranked.append({**q,'pool_top20':pool,'ranking':[{'passage_id':pid,'score':score,'rank':n+1} for n,(pid,score) in enumerate(ranked)],'reranker_seconds':elapsed,'window_trace':backend.last_trace})
        hashes['rrf_reranker']=save(output/'rankings-rrf-reranker.json',{'policy':POLICY,'results':reranked,'inputs':observed.copy(),'rrf_rankings_sha256':hashes['rrf'],'model_load_seconds':loaded,'model_repo':model['repo_id'],'model_revision':model['revision'],'execution_identity':backend.execution_identity,'metrics_computed':False})
        return {'status':'completed_local_development','policy':POLICY,'index_hash':index.index_hash,'index_sha256':idxsha,'records_sha256':recsha,'ranking_hashes':hashes,'inputs':observed,'records':len(rows),'queries':len(qs),'source_drift':[p for p,h in observed.items() if hashlib.sha256(local(root,p).read_bytes()).hexdigest()!=h],'remote_calls':0,'promotion':False,'metrics_computed':False}
    except Exception as exc:
        save(output/'failure.json',{'status':'failed','error_class':type(exc).__name__,'safe_error':str(exc) if type(exc) is ValueError and str(exc).isupper() else None,'at':datetime.now(timezone.utc).isoformat()})
        raise

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path.cwd());p.add_argument('--output',required=True);a=p.parse_args()
    result=run(a.root,a.output);save(Path(a.root)/a.output/'record.json',result);print(json.dumps({k:v for k,v in result.items() if k not in ('inputs','policy')}))
