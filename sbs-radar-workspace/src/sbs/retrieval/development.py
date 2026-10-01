"""Exposed structural development data and exact input inventory; never inference."""
from pathlib import Path
import hashlib,json
from sbs.genie import digest
from sbs.paths import project_path,resolve_model_manifest
from sbs.models import TokenCounter,preflight_budget
from sbs.models.databricks import PinnedQwenTokenizer
from sbs.operations.preparers import VerifiedEmbeddingCache
from sbs.comparison.pilot import build_pilot
from sbs.foundation.structure import structuralize
from sbs.foundation.structure_notes import extract_note_links

VERSION='structural-development-v3'

def compile_inputs(passages,originals,cache,counter):
    rows=[]
    for p in passages:
        raw=originals[(p['document_id'],p['version_id'])]
        if raw[p['start']:p['end']]!=p['quote']:raise ValueError('DEVELOPMENT_LITERAL_MISMATCH')
        start=max(0,p['start']-cache.context_chars);text=raw[start:p['end']];parts=(cache.prefix,text)
        budget=preflight_budget(parts,cache.limit,model_identity=cache.identity,counter=counter)
        hit=cache.lookup(parts,cache.identity)
        rows.append(dict(passage_id=p['passage_id'],model_identity=cache.identity,input_parts=list(parts),
                         embedding_start=start,embedding_text=text,input_sha256=hashlib.sha256(''.join(parts).encode()).hexdigest(),
                         model_parts_sha256=digest([cache.identity,list(parts)]),budget=budget,
                         cache_status='exact_hit' if hit is not None else 'miss',
                         execution_status='not_executed',truncated=False))
    return rows


def build_dataset(root):
    root=Path(root).resolve();inputs={}
    def read(path):
        p=project_path(root,path);raw=p.read_bytes();inputs[str(p.relative_to(root))]=hashlib.sha256(raw).hexdigest();return json.loads(raw)
    pilot=build_pilot(root)
    # Rebase delivery metadata only; frozen reviews and citation identity unchanged.
    for item in pilot['items']:
        for c in item['annotation']['review_citations'].values():
            for key in ('original_path','rawtext_path'):
                c[key]=str(project_path(root,c[key]).relative_to(root))
        item['annotation']['delivery_paths']='project_relative; source review bytes unchanged'
    inputs.update({x['path']:x['sha256'] for x in pilot['input_files']})
    protocol_envelope=read('runs/sk04-real-001-protocol.json');protocol=protocol_envelope['payload']
    if digest(protocol)!=protocol_envelope['sha256']:raise ValueError('PROTOCOL_INTEGRITY')
    schema=read('context/evaluation-018/records.schema.json')
    from jsonschema import Draft202012Validator
    sources={};originals={};auto={};contexts={};passages={};metadata={}
    def passage(p,entry,origin,provenance):
        key=(p['document_id'],p['version_id']);b=sources[key]['bundle'];text=originals[key]
        if text[p['start']:p['end']]!=p['text']:raise ValueError('PASSAGE_LITERAL_MISMATCH')
        q=dict(passage_id=p['citation_id'],document_id=p['document_id'],version_id=p['version_id'],rawtext_path=str(project_path(root,entry['rawtext_path']).relative_to(root)),rawtext_sha256=b['rawtext_sha256'],page=p['page'],start=p['start'],end=p['end'],quote=p['text'],offset_unit='Unicode code points; zero-based; end-exclusive')
        if q['passage_id'] in passages and q!=passages[q['passage_id']]:raise ValueError('PASSAGE_ID_COLLISION')
        passages[q['passage_id']]=q;metadata[q['passage_id']]=dict(origin=origin,provision_id=p['provision_id'],family=entry['source']['family'],pages=[x['page'] for x in b['pages'] if x['start']<p['end'] and x['end']>p['start']],provenance=provenance)
    for name in ('runs/sk02-repository-capture.json','runs/sk02-amendments-capture.json'):
        capture=read(name)
        for entry in capture['sources']:
            b=read(entry['result_path']);source=entry['source'];key=(source['document_id'],source['version_id'])
            raw=project_path(root,entry['rawtext_path']).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=b['rawtext_sha256'] or raw.decode()!=b['rawtext']:raise ValueError('RAW_INTEGRITY')
            sources[key]=dict(bundle=b,entry=entry);originals[key]=b['rawtext'];s=structuralize(b);auto[key]=s
            contexts['|'.join(key)]={'structure':s['structure'],'notes':extract_note_links(b,s),'family':source['family'],'origin':'automatic_partial','embedding_role':'context_only_not_embedded_as_body'}
            for p in s['provisions']:passage(p,entry,'automatic_structural',{'algorithm':s['structure']['version'],'legal_validation':False})
    by_provision={i['provision_id']:i for i in pilot['items']};questions=[];judgments=[];pairs={};gaps=[];references={};counterparts={}
    mapping={'cyber-art20-3':'art20.3','market-art27':'art27','market-art29-1-4':'art29.1.4'}
    for old in protocol['questions']:
        item=by_provision[mapping[old['query_id']]];pair=item['change_set']['pair'];reference_id='reused-reference-'+old['query_id']
        questions.append(dict(query_id=old['query_id'],family=old['family'],pair_id=pair['pair_id'],question=old['question'],task='comparison',provision_ids=[item['provision_id']],expected_answerability='answerable',reference_id=reference_id))
        references[reference_id]={'annotation':item['annotation'],'basis':'Existing reviewed literal spans, not new Astra relevance adjudication','compiler_reviewer_id':'structural-development-024-positive-mapping','human_gold':False}
        pair_record={'pair_id':pair['pair_id'],'family':pair['family'],'dependency_component_id':'six-source-exposed-development','partition':'development','exposure_log':['Astra003/prior review reused','SK04real001 questions exposed','Structural rules adjusted during019-023'],'eligibility_evidence':'Six captured official PDFs; exposed documentary comparison only, no current-law claim'}
        counterpart={}
        for side in ('before','after'):
            p=item[side];key=(p['document_id'],p['version_id']);entry=sources[key]['entry'];b=sources[key]['bundle']
            passage(p,entry,'reused_ai_annotated_subspan',item['annotation'])
            judgments.append(dict(query_id=old['query_id'],passage_id=p['citation_id'],grade=1,side=side,reviewer_id='structural-development-024-positive-mapping',provenance='ai_review',source_locator_verified=True,reason='Compiler positive from exact existing reviewed span for this reused question; not a new Astra judgment, exhaustive qrel or human approval.',disagreement_id=None))
            counterpart[side]=[p['citation_id']]
            number=item['provision_id'][3:].split('.')[0]
            covering=[q['citation_id'] for q in auto[key]['provisions'] if auto[key]['structure']['spans'][q['provision_id']]['number']==number and q['start']<=p['start'] and q['end']>=p['end']]
            gaps.append(dict(query_id=old['query_id'],side=side,automatic_covering_units=covering,status='automatic_article_covering_reference' if covering else 'automatic_target_missing',fallback_passage_id=p['citation_id'],fallback_origin='explicit_reused_ai_annotation_not_auto_mapping'))
            pair_record[side]={**pair[side], 'original_path':str(project_path(root,entry['original_path']).relative_to(root)),'original_sha256':entry['source']['sha256'],'derivative_sha256':inputs[str(project_path(root,entry['result_path']).relative_to(root))],'related_ids':['six-source-exposed-development']}
        pairs[pair['pair_id']]=pair_record;counterparts[old['query_id']]={pair['pair_id']:counterpart}
    from sbs.comparison.structural import compare_structural
    pair_wrappers={pid:compare_structural(next(i['change_set']['pair'] for i in pilot['items'] if i['pair_id']==pid),*[sources[(pair[side]['document_id'],pair[side]['version_id'])]['bundle'] for side in ('before','after')]) for pid,pair in pairs.items()}
    cache=VerifiedEmbeddingCache.from_project(root);manifest=resolve_model_manifest(read('runs/sk05-qwen-tokenizer.json'),root=root)
    f=manifest['files']['tokenizer.json'];tok=PinnedQwenTokenizer(f['path'],revision=manifest['revision'],sha256=f['sha256'])
    if cache.tokenizer!=tok.repo_id or cache.revision!=tok.revision:raise ValueError('TOKENIZER_CACHE_IDENTITY_MISMATCH')
    counter=TokenCounter(cache.tokenizer,cache.revision,cache.identity,lambda parts:tok.count(''.join(parts)))
    rows=compile_inputs(list(passages.values()),originals,cache,counter)
    data={'questions':questions,'passages':list(passages.values()),'judgments':judgments,'pairs':list(pairs.values())}
    for plural,kind in [('questions','question'),('passages','passage'),('judgments','judgment'),('pairs','pair')]:
        validator=Draft202012Validator(schema['$defs'][kind])
        for row in data[plural]:validator.validate(row)
    report=read('runs/sk04-real-001-report.json');model=read('config/pilot-model-bundle.json')
    query_path='data/retrieval/sk04-real-001/queries-000.json';query_envelope=read(query_path);query_payload=query_envelope['payload']
    if inputs[query_path]!=report['artifacts_sha256'][query_path] or digest(query_payload)!=query_envelope['sha256'] or query_payload['input_sha256']!=digest([q['question'] for q in questions]) or query_payload['role']!='query':raise ValueError('QUERY_CACHE_MISMATCH')
    from sbs.models import validate_embeddings
    validate_embeddings(query_payload['embeddings'],expected_count=len(questions),dimension=cache.dimension,expected_identity=cache.identity,actual_identity=query_payload['bundle_hash'])
    query_inputs=[]
    for q in questions:
        rendered='Instruct: '+model['bundle']['parameters']['query_instruction']+'\nQuery:'+q['question']
        query_inputs.append(dict(query_id=q['query_id'],role='query',raw_question=q['question'],rendered_counting_input=rendered,input_sha256=hashlib.sha256(rendered.encode()).hexdigest(),input_tokens=tok.count(rendered),cache_status='exact_hit',model_identity=cache.identity,cache_batch_sha256=inputs[query_path],execution_status='not_executed'))
    qrels={q['query_id']:{j['passage_id']:j['grade'] for j in judgments if j['query_id']==q['query_id']} for q in questions}
    summary=dict(version=VERSION,partition='exposed_development',holdout=[],exhaustive=False,acceptance='not_evaluated',freeze_protocol_called=False,questions=len(questions),pairs=len(pairs),sources=len(sources),passages=len(passages),judgments=len(judgments),negative_judgments=0,input_tokens=sum(r['budget']['input_tokens'] for r in rows),max_input_tokens=max(r['budget']['input_tokens'] for r in rows),over_limit=[r['passage_id'] for r in rows if r['budget']['status']!='ready'],cache_hits=sum(r['cache_status']=='exact_hit' for r in rows),cache_misses=sum(r['cache_status']=='miss' for r in rows),model_identity=cache.identity,tokenizer=cache.tokenizer,tokenizer_revision=cache.revision,tokenizer_sha256=f['sha256'],limit=cache.limit,context_chars=cache.context_chars,cache_provenance=cache.provenance,source_files=inputs,limitations=['Only documented positive reference subspans judged; all others unjudged, not negative','Annotations overlap automatic units but are separate origin; not new automatic coverage','Notes/exclusions/context sidecars are not body embedding inputs','No truncation, inference, vectors generated, index or runtime promotion','No independent holdout or metric acceptance; thresholds018 unchanged','Qrels do not claim new Astra adjudication'])
    summary['query_cache_hits']=len(query_inputs)
    summary['candidate_corpus_hash']=digest(data['passages'])
    summary['candidate_strategy']={'id':'span-limpio-contexto-v1','version':1,'adaptation':'exact_structural_units_plus_explicit_annotated_subspans','new_index_required':True,'indexed':False,'embedding_execution_bundle_reused':cache.identity}
    summary['corpus_views']={origin:[pid for pid,m in metadata.items() if m['origin']==origin] for origin in ('automatic_structural','reused_ai_annotated_subspan')}
    summary['family_inventory']={family:dict(passages=sum(metadata[r['passage_id']]['family']==family for r in rows),input_tokens=sum(r['budget']['input_tokens'] for r in rows if metadata[r['passage_id']]['family']==family),cache_misses=sum(r['cache_status']=='miss' and metadata[r['passage_id']]['family']==family for r in rows)) for family in ('cybersecurity','market_conduct')}
    summary['limitations'].append('Exact automatic spans still contain interleaved notes/furniture; not a cleaned normative corpus')
    return {**data,'query_inputs':query_inputs,'pair_wrappers':pair_wrappers,'passage_metadata':metadata,'context':contexts,'reference_provenance':references,'automatic_gaps':gaps,'embedding_inputs':rows,'qrels_partial':{'qrels':qrels,'counterparts':counterparts,'exhaustive':False},'manifest':summary}


def write_dataset(root,destination):
    destination=Path(destination)
    if destination.exists():raise ValueError('DATASET_DESTINATION_EXISTS')
    result=build_dataset(root);destination.mkdir(parents=True)
    hashes={}
    for name,payload in result.items():
        raw=(json.dumps(payload,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode();(destination/(name+'.json')).write_bytes(raw);hashes[name+'.json']=dict(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
    (destination/'artifacts.json').write_text(json.dumps(hashes,indent=2)+'\n')
    return result['manifest'],hashes


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=Path.cwd());parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();manifest,artifacts=write_dataset(args.root,args.output)
    print(json.dumps({k:v for k,v in manifest.items() if k not in ('source_files','corpus_views')},ensure_ascii=False,indent=2))
