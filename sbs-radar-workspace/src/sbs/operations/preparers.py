"""Actual local SK03/SK04/SK06 preparation from the current refresh capture.

Frozen vectors are reused only for exact complete inputs and a verified model
bundle. No provider client is created, no network call is implicit, and no
published corpus/index is changed. Explicit adapters remain trusted capabilities.
"""
from copy import deepcopy
from pathlib import Path
import json
import sqlite3
from sbs.paths import project_path
from sbs.foundation import extract
from sbs.foundation.store import object_path
from sbs.comparison import compare
from sbs.comparison.pilot import structural_bundle
from sbs.models import TokenCounter
from sbs.retrieval import chunk_spans,LocalIndex
from sbs.genie import curate,digest
from . import atomic,canonical,sha,verify_closure


class Pending(Exception):pass


class VerifiedEmbeddingCache:
    def __init__(self,records,vectors,identity,dimension,index_hash):
        index=LocalIndex(records,vectors,dimension=dimension,model_identity=identity,actual_identity=identity)
        if index.index_hash!=index_hash:raise ValueError('CACHE_INDEX_HASH_MISMATCH')
        self.records=deepcopy(records);self.identity=identity;self.dimension=dimension;self.entries={}
        for row,vector in zip(records,vectors):
            key=(identity,tuple(row['input_parts']))
            entry={'vector':deepcopy(vector),'budget':deepcopy(row['budget'])}
            if key in self.entries and self.entries[key]!=entry:raise ValueError('CACHE_INPUT_AMBIGUITY')
            self.entries[key]=entry
        first=records[0];self.prefix=first['input_parts'][0];self.context_chars=first['strategy']['context_chars'];self.limit=first['budget']['limit']
        self.tokenizer=first['budget']['tokenizer'];self.revision=first['budget']['tokenizer_revision']

    @classmethod
    def from_project(cls,root):
        root=Path(root).resolve()
        report=json.loads(project_path(root,'runs/sk04-real-001-report.json').read_bytes())
        def read(name):
            raw=project_path(root,name).read_bytes()
            if sha(raw)!=report['artifacts_sha256'][name]:raise ValueError('CACHE_FILE_HASH_MISMATCH')
            return json.loads(raw)
        records=read('data/retrieval/sk04-real-001/records.json');envelope=read('data/retrieval/sk04-real-001/index.json')
        if digest(envelope['payload'])!=envelope['sha256']:raise ValueError('CACHE_ENVELOPE_MISMATCH')
        p=envelope['payload'];model=json.loads(project_path(root,'config/pilot-model-bundle.json').read_bytes())
        if digest(model['bundle'])!=model['bundle_hash'] or p['bundle_hash']!=model['bundle_hash'] or p['bundle_hash']!=report['bundle_hash']:raise ValueError('CACHE_MODEL_MISMATCH')
        if p['records_sha256']!=report['artifacts_sha256']['data/retrieval/sk04-real-001/records.json']:raise ValueError('CACHE_RECORDS_MISMATCH')
        cache=cls(records,p['vectors'],p['bundle_hash'],p['dimension'],p['index_hash'])
        cache.provenance={'records_sha256':p['records_sha256'],'index_file_sha256':report['artifacts_sha256']['data/retrieval/sk04-real-001/index.json'],'index_hash':p['index_hash'],'model_bundle_hash':model['bundle_hash']}
        return cache

    def lookup(self,parts,identity):return deepcopy(self.entries.get((identity,tuple(parts))))


def _current_inputs(ctx):
    """Recover exact current-run SourceDocuments, then reverify SK02 sealed cache."""
    root=Path(ctx['foundation_root']).resolve();state=Path(ctx['state_root']).resolve()
    if not root.is_relative_to(state):raise ValueError('FOUNDATION_OUTSIDE_STATE')
    with sqlite3.connect(root/'foundation.sqlite3') as db:
        captured=[json.loads(r[0]) for r in db.execute('SELECT c.source FROM captures c JOIN attempts a ON a.id=c.attempt_id WHERE a.run=? AND a.status=?',(canonical(ctx['run_id']).decode(),'captured'))]
    key=lambda s:(sha(canonical([s['document_id'],s['url']])),s['sha256'])
    lookup={key(s):s for s in captured}
    active=[s for s in ctx['sources'] if not s.get('retained')]
    if len(lookup)!=len(captured) or len(captured)!=len(active):raise ValueError('CURRENT_CAPTURE_INCOMPLETE')
    with sqlite3.connect(root/'foundation.sqlite3') as db:
        history=[json.loads(r[0]) for r in db.execute('SELECT source FROM captures ORDER BY attempt_id')]
    historical={key(s):s for s in history}
    documents=[];bundles={};closure={}
    for summary in ctx['sources']:
        s=(historical if summary.get('retained') else lookup).get((summary.get('source_key'),summary['sha256']))
        if not s or any(s[k]!=summary[k] for k in ('document_id','family','sha256')):raise ValueError('CURRENT_CAPTURE_MISMATCH')
        b=extract(s,root=root)
        if (b['rawtext_sha256'],b['config_hash'],b['extractor'])!=(summary['rawtext_sha256'],summary['extraction_config_hash'],summary['extractor']):raise ValueError('CURRENT_EXTRACTION_MISMATCH')
        original=object_path(root,s['sha256']);derived=root/'derived'/s['sha256']/sha(b['extractor'].encode())/b['config_hash']
        for path in (original,derived/'result.json',derived/'rawtext.txt'):closure[str(path.relative_to(state))]=sha(path.read_bytes())
        documents.append(s);bundles[(s['document_id'],s['version_id'])]=b
    verify_closure(state,closure)
    return documents,bundles,closure


def _save(ctx,payload,closure):
    path=Path(ctx['stage'])/(ctx['hook']+'.json')
    value={'payload':payload,'sha256':digest(payload)};atomic(path,value)
    if canonical(json.loads(path.read_bytes()))!=canonical(value):raise ValueError('STAGING_READBACK_FAILED')
    verify_closure(ctx['state_root'],closure)
    return {'status':'validated','mode':'real','artifact_path':path.name,'sha256':sha(path.read_bytes()),'closure':closure}


def _prior(ctx,key):
    path=Path(ctx['stage'])/(key+'.json')
    if not path.exists():raise Pending('UPSTREAM_PENDING')
    value=json.loads(path.read_bytes())
    if digest(value['payload'])!=value['sha256']:raise ValueError('STAGING_DEPENDENCY_MISMATCH')
    return value['payload'],{str(path.relative_to(ctx['state_root'])):sha(path.read_bytes())}


def build_real_hooks(project_root,*,annotations=(),embedding_adapter=None,token_counter=None,
                     allow_inference=False,structural_evidence=True,max_embedding_calls=0,max_embedding_inputs=0,max_embedding_tokens=0):
    """Return SK03/SK04/SK06 hooks; construction verifies existing real vector cache.

    SealedPlan.pairs supplies explicit VersionPairs; no pairs are inferred from
    version sorting. annotations are optional trusted frozen review dictionaries
    {pair_id,provision_id,before,after}; structural_bundle validates exact original
    identity, span and page before reuse. They remain AI reference, never approval.
    For new text, an exact compatible TokenCounter and real server adapter plus
    explicit finite quotas are required. No adapter is invoked by default.
    """
    if any(type(x) is not int or x<0 for x in (max_embedding_calls,max_embedding_inputs,max_embedding_tokens)):raise ValueError('INVALID_INFERENCE_QUOTA')
    cache=VerifiedEmbeddingCache.from_project(project_root);annotations=deepcopy(tuple(annotations))
    used={'calls':0,'inputs':0,'tokens':0}
    if embedding_adapter is not None and (embedding_adapter.identity!=cache.identity or embedding_adapter.dimension!=cache.dimension):raise ValueError('ADAPTER_MODEL_MISMATCH')
    if token_counter is not None and (token_counter.model_identity,token_counter.tokenizer,token_counter.revision)!=(cache.identity,cache.tokenizer,cache.revision):raise ValueError('COUNTER_MODEL_MISMATCH')

    def count(parts):
        hit=cache.lookup(parts,cache.identity)
        if hit:return hit['budget']['input_tokens']
        if token_counter is None:raise Pending('TOKENIZER_PENDING')
        return token_counter.count(parts)
    counter=TokenCounter(cache.tokenizer,cache.revision,cache.identity,count)

    def prepare(ctx):
        try:
            documents,bundles,closure=_current_inputs(ctx);pairs=deepcopy(list(ctx['pairs']))
            if not pairs:raise Pending('PAIRS_PENDING')
            if len({p['pair_id'] for p in pairs})!=len(pairs):raise ValueError('DUPLICATE_PAIR_ID')
            for p in pairs:
                for side in ('before','after'):
                    key=(p[side]['document_id'],p[side]['version_id'])
                    if key not in bundles:raise Pending('PAIR_SOURCE_MISSING')
                    if not any(d['document_id']==key[0] and d['version_id']==key[1] and d['family']==p['family'] for d in documents):raise ValueError('PAIR_FAMILY_MISMATCH')
            common={'run_id':ctx['run_id'],'plan_id':ctx['plan_id'],'plan_fingerprint':ctx['plan_fingerprint'],
                    'source_snapshot':digest(ctx['sources']),'coverage':'partial','human_approved':False}
            if ctx['hook']=='SK03':
                comparisons=[compare(p,bundles[(p['before']['document_id'],p['before']['version_id'])],bundles[(p['after']['document_id'],p['after']['version_id'])],coverage='partial') for p in pairs]
                structural=[];review=[];wrappers=[]
                if structural_evidence:
                    from sbs.comparison.structural import compare_structural
                    from .structural_evidence import project
                    for pair in pairs:
                        w=compare_structural(pair,*[bundles[(pair[side]['document_id'],pair[side]['version_id'])] for side in ('before','after')])
                        wrappers.append(w);structural.extend(project(w)[0])
                    comparisons=[w['original_comparison'] for w in wrappers]
                structural=list({p['citation_id']:p for p in structural}.values())
                for annotation in annotations:
                    p=next((p for p in pairs if p['pair_id']==annotation['pair_id']),None)
                    if p is None:raise Pending('ANNOTATION_SOURCE_CHANGED')
                    selected={}
                    for side in ('before','after'):
                        b=bundles[(p[side]['document_id'],p[side]['version_id'])]
                        a=annotation[side]
                        if (a.get('document_id'),a.get('version_id'))!=(p[side]['document_id'],p[side]['version_id']):raise Pending('ANNOTATION_SOURCE_CHANGED')
                        try:selected[side]=structural_bundle(b,a,annotation['provision_id'])
                        except ValueError:raise Pending('ANNOTATION_SOURCE_CHANGED') from None
                        structural+=selected[side]['provisions']
                    comparisons.append(compare(p,selected['before'],selected['after'],alignments=[{'before':[annotation['provision_id']],'after':[annotation['provision_id']]}],coverage='partial'))
                    review.append({'pair_id':p['pair_id'],'provision_id':annotation['provision_id'],'kind':'reused_ai_annotation','human_gold':False,'annotations':annotation})
                return _save(ctx,{**common,'pairs':pairs,'comparisons':comparisons,'structural_provisions':structural,'annotation_reuse':review,**({'structural_evidence_version':1,'structural_wrappers':wrappers} if structural_evidence else {}),'limitations':['Raw-page alignments are partial literal comparison, not material change judgments.']},closure)
            if ctx['hook']=='SK04':
                records=[]
                for document in documents:
                    b=bundles[(document['document_id'],document['version_id'])]
                    records+=chunk_spans(b,family=document['family'],counter=counter,model_identity=cache.identity,limit=cache.limit,prefix=cache.prefix,context_chars=cache.context_chars)
                hits=[cache.lookup(r['input_parts'],cache.identity) for r in records];missing=[i for i,h in enumerate(hits) if h is None]
                tokens=sum(records[i]['budget']['input_tokens'] for i in missing)
                if missing:
                    if embedding_adapter is None or not allow_inference:raise Pending('EMBEDDINGS_MISSING')
                    if used['calls']+1>max_embedding_calls or used['inputs']+len(missing)>max_embedding_inputs or used['tokens']+tokens>max_embedding_tokens:raise Pending('INFERENCE_QUOTA_EXCEEDED')
                    used['calls']+=1;used['inputs']+=len(missing);used['tokens']+=tokens
                    produced=embedding_adapter.embed_documents([tuple(records[i]['input_parts']) for i in missing])
                    from sbs.models import validate_embeddings
                    produced=validate_embeddings(produced,expected_count=len(missing),dimension=cache.dimension,expected_identity=cache.identity,actual_identity=embedding_adapter.identity)
                    for i,vector in zip(missing,produced):hits[i]={'vector':list(vector)}
                vectors=[h['vector'] for h in hits]
                index=LocalIndex(records,vectors,dimension=cache.dimension,model_identity=cache.identity,actual_identity=cache.identity)
                return _save(ctx,{**common,'records':records,'vectors':vectors,'index_hash':index.index_hash,'dimension':cache.dimension,'model_identity':cache.identity,'cache_provenance':deepcopy(cache.provenance),'embedding_calls':1 if missing else 0,'cached_inputs':len(records)-len(missing),'new_inputs':len(missing),'strategy':{'id':'span-limpio-contexto-v1','version':1,'adaptation':'preserve_input_raw_pages','semantic_validation':'pending'}},closure)
            if ctx['hook']=='SK06':
                comparison,dependencies=_prior(ctx,'SK03');retrieval,dep2=_prior(ctx,'SK04');closure.update(dependencies);closure.update(dep2)
                if any(x['source_snapshot']!=common['source_snapshot'] or x['plan_fingerprint']!=common['plan_fingerprint'] for x in (comparison,retrieval)):raise ValueError('UPSTREAM_SCOPE_MISMATCH')
                provisions=[p for b in bundles.values() for p in b['provisions']]+comparison['structural_provisions']
                config={'namespace':'sbs_radar','refresh_plan':ctx['plan_fingerprint'],'source_snapshot':common['source_snapshot'],'retrieval_index_hash':retrieval['index_hash'],'annotation_sha256':digest(comparison['annotation_reuse'])}
                review={'run_id':ctx['run_id']+'-annotations','references':comparison['annotation_reuse'],'human_gold':False} if comparison['annotation_reuse'] else None
                if 'structural_wrappers' in comparison:config['structural_evidence_sha256']=digest(comparison['structural_wrappers'])
                bundle=curate(documents,pairs,comparison['comparisons'],review,[],config,mode='real',provisions=provisions)
                return _save(ctx,{**common,'bundle':bundle,'curation_config':config,'limitations':['No cloud tables, runtime promotion or publication certificate.','No fictitious processes added implicitly.']},closure)
            raise ValueError('UNKNOWN_HOOK')
        except Pending as p:return {'status':'pending','reason':str(p)}
    return {key:prepare for key in ('SK03','SK04','SK06')}
