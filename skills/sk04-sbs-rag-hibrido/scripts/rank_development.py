"""One offline lexical/reranker run, no judgment access, vectors or metrics."""
import argparse
from datetime import datetime,timezone
import hashlib,json,time
from pathlib import Path
from sbs.retrieval import _bm25

def scoped_rank(question,family,pair,passages,metadata):
    if pair['family']!=family:raise ValueError('PAIR_FAMILY_MISMATCH')
    endpoints={(pair[s]['document_id'],pair[s]['version_id']) for s in ('before','after')}
    eligible=[p for p in passages if metadata[p['passage_id']]['family']==family and (p['document_id'],p['version_id']) in endpoints]
    rows=[{'citation':{'citation_id':p['passage_id'],'text':p['quote']}} for p in eligible]
    start=time.perf_counter();ranking=_bm25(question,rows);elapsed=time.perf_counter()-start
    return {'eligible_ids':[p['passage_id'] for p in eligible],'ranking':[{'passage_id':pid,'score':score,'rank':i+1} for i,(pid,score) in enumerate(ranking)],'pool_top20':[pid for pid,_ in ranking[:20]],'top5':[pid for pid,_ in ranking[:5]],'lexical_seconds':elapsed,'zero_score_unranked':[p['passage_id'] for p in eligible if p['passage_id'] not in {x[0] for x in ranking}]}

def run(root,prefix,rerank=False):
    root=Path(root).resolve();prefix=Path(prefix)
    if any(prefix.parent.glob(prefix.name+'-rankings*.json')):raise ValueError('RUN_ALREADY_EXISTS')
    dataset=root/'data/retrieval/structural-development-026'
    hashes=json.loads((dataset/'artifacts.json').read_text());inputs={}
    def read(name):
        path=dataset/(name+'.json');raw=path.read_bytes();sha=hashlib.sha256(raw).hexdigest()
        if sha!=hashes[path.name]['sha256']:raise ValueError('INPUT_HASH_MISMATCH')
        inputs[str(path.relative_to(root))]=sha;return json.loads(raw)
    # Deliberately no judgment/reference/provision target fields used for ranking.
    qs=read('questions');passages=read('passages');pairs={p['pair_id']:p for p in read('pairs')};metadata=read('passage_metadata')
    results=[];began=datetime.now(timezone.utc).isoformat()
    for q in qs:
        result=scoped_rank(q['question'],q['family'],pairs[q['pair_id']],passages,metadata)
        result.update(query_id=q['query_id'],question=q['question'],family=q['family'],pair_id=q['pair_id'])
        results.append(result)
    policy={'algorithm':'sbs.retrieval._bm25','k1':1.5,'b':0.75,'terms':'unicode word regex,casefold','idf_scope':'eligible family+pair only','zero_score_policy':'unranked','tie_break':'passage_id ascending','k':[5,20],'pool_size':20,'target_expansion':False,'judgments_read':False,'metrics_computed':False,'vectors':'not_available_not_simulated','partition':'exposed_development'}
    lexical={'started_at':began,'ended_at':datetime.now(timezone.utc).isoformat(),'inputs':inputs,'policy':policy,'results':results}
    lexicalpath=Path(str(prefix)+'-rankings-lexical.json');lexicalpath.write_text(json.dumps(lexical,ensure_ascii=False,indent=2)+'\n')
    if not rerank:return
    from sbs.models.reranker import LocalOnnxReranker
    from sbs.paths import resolve_model_manifest
    mp=root/'context/reranker-manifest.json';model=resolve_model_manifest(json.loads(mp.read_text()),root=root)
    began=time.perf_counter();backend=LocalOnnxReranker.from_manifest(model,cpu_threads=2);load_seconds=time.perf_counter()-began
    pmap={p['passage_id']:p for p in passages};reranked=[]
    for q in results:
        pool=q['pool_top20'];rows=[{'citation':{'citation_id':pid,'text':pmap[pid]['quote']}} for pid in pool]
        began=time.perf_counter();scores=backend(q['question'],rows);elapsed=time.perf_counter()-began
        ranking=sorted(zip(pool,scores),key=lambda x:(-x[1],x[0]))
        reranked.append({'query_id':q['query_id'],'pool_top20':pool,'ranking':[{'passage_id':pid,'score':score,'rank':i+1} for i,(pid,score) in enumerate(ranking)],'seconds':elapsed,'window_trace':backend.last_trace})
    payload={'lexical_sha256':hashlib.sha256(lexicalpath.read_bytes()).hexdigest(),'pool_policy':'exact frozen lexical top20, no expansion','model_manifest_sha256':hashlib.sha256(mp.read_bytes()).hexdigest(),'model_repo':model['repo_id'],'model_revision':model['revision'],'execution_identity':backend.execution_identity,'model_load_seconds':load_seconds,'results':reranked,'metrics_computed':False,'judgments_read':False,'cost':None,'completed_at':datetime.now(timezone.utc).isoformat()}
    Path(str(prefix)+'-rankings-reranker.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path.cwd());p.add_argument('--prefix',type=Path,required=True);p.add_argument('--rerank',action='store_true');a=p.parse_args();run(a.root,a.prefix,a.rerank)
