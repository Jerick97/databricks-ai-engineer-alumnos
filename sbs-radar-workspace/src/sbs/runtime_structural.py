"""Explicit local development profile049; frozen047 index, no model calls.

The fixed record is an integrity anchor, never quality or deployment approval.
It keeps the existing LocalService conversation/focus contract and changes only
its retrieval artifacts. No current pointer, source file, or default is written.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from sbs.genie import digest
from sbs.retrieval import LocalIndex
from sbs.retrieval.structural_ranking import anchored_read, project_records
from sbs.retrieval.embedding_execution import local

PROFILE = 'structural-development-047-v2'
BASE = 'runs/sk04-structural-ranking-047-v2/'
RECORD_SHA = '2dbac88f42c914042ed2bc241adc07e34973f442a0c3f11a80d3ee1a3d1e21ae'
REVIEW_SHA = '4b1aab5aa826d117279d80d0766144982f1b3ef37583d05a315730349dbd11ab'


def require(condition, code):
    if not condition:raise ValueError(code)


def load_profile(root, config_path):
    root=Path(root).resolve()
    config=json.loads(Path(config_path).read_bytes())
    require(isinstance(config,dict) and set(config)=={'enabled','profile'} and config.get('enabled') is True and config.get('profile')==PROFILE,'STRUCTURAL_CONFIG_INVALID')
    closure={}
    def read(name,sha):
        obj=anchored_read(root,name,sha);closure[name]=sha;return obj
    record=read(BASE+'record.json',RECORD_SHA)
    require(record['status']=='completed_local_development' and record['records']==231,'STRUCTURAL_RECORD_INVALID')
    pins=record['inputs']
    review=read('runs/sk09-query-compatibility-046-review.json',REVIEW_SHA)
    compat=read('runs/sk05-query-compatibility-046.json',review['input_result_sha256'])
    require(compat['status']=='compatible_under_observed_contract_for_local_exposed_development','STRUCTURAL_COMPATIBILITY_REQUIRED')
    data='data/retrieval/structural-development-026/'
    def input_file(name):
        require(pins[name]==compat['inputs_sha256'][name],'STRUCTURAL_PIN_CONFLICT')
        return read(name,pins[name])
    manifest=input_file(data+'manifest.json')
    passages=input_file(data+'passages.json');metadata=input_file(data+'passage_metadata.json')
    inputs=input_file(data+'embedding_inputs.json');questions=input_file(data+'questions.json');pairs=input_file(data+'pairs.json')
    bundles={}
    # Verify original PDFs, raw bytes and extraction metadata BEFORE LocalIndex.
    # Only source closure is consumed here; no qrels/reference/metric input.
    for passage in passages:
        key=(passage['document_id'],passage['version_id'])
        if key in bundles:continue
        rawname=passage['rawtext_path'];name=str(Path(rawname).with_name('result.json'))
        bundle=read(name,manifest['source_files'][name])
        for path in (rawname,'data/foundation-repository/objects/'+bundle['sha256'][:2]+'/'+bundle['sha256']+'.pdf'):
            expected=manifest['source_files'][path]
            raw=local(root,path).read_bytes()
            require(hashlib.sha256(raw).hexdigest()==expected,'STRUCTURAL_SOURCE_CLOSURE')
            if path==rawname:require(raw.decode()==bundle['rawtext'] and expected==bundle['rawtext_sha256'],'STRUCTURAL_RAW_MISMATCH')
            else:require(expected==bundle['sha256'],'STRUCTURAL_PDF_MISMATCH')
            closure[path]=expected
        bundles[key]=bundle
    rows=read(BASE+'records.json',record['records_sha256'])
    require(rows==project_records(passages,metadata,inputs,bundles),'STRUCTURAL_PROJECTION_MISMATCH')
    payload=read(BASE+'index.json',record['index_sha256'])
    vectors=input_file('runs/sk04-embeddings-041-vectors/vectors.json')
    queries=input_file('data/retrieval/sk04-real-001/queries-000.json')
    model_name='config/pilot-model-bundle.json'
    require(compat['inputs_sha256'][model_name]==manifest['source_files'][model_name],'STRUCTURAL_MODEL_PIN_CONFLICT')
    model=read(model_name,compat['inputs_sha256'][model_name])
    for sealed in (vectors,queries):require(digest(sealed['payload'])==sealed['sha256'],'STRUCTURAL_ENVELOPE')
    vectors=vectors['payload'];queries=queries['payload']
    require(digest(model['bundle'])==model['bundle_hash']==payload['model_identity']==vectors['model_identity']==queries['bundle_hash'],'STRUCTURAL_MODEL_MISMATCH')
    require(vectors['mode']=='real' and vectors['passage_ids']==[p['passage_id'] for p in passages] and vectors['candidate_corpus_hash']==digest(passages)==payload['candidate_corpus_hash'] and vectors['vectors']==payload['vectors'],'STRUCTURAL_VECTOR_MISMATCH')
    require(queries['input_sha256']==digest([q['question'] for q in questions]) and len(queries['embeddings'])==len(questions),'STRUCTURAL_QUERY_MISMATCH')
    index=LocalIndex(rows,payload['vectors'],dimension=payload['dimension'],model_identity=payload['model_identity'],actual_identity=vectors['model_identity'])
    require(index.index_hash==record['index_hash']==payload['index_hash'],'STRUCTURAL_INDEX_MISMATCH')
    return dict(index=index,payload=payload,bundles=bundles,questions=questions,pairs=pairs,
                query_cache={q['question']:v for q,v in zip(questions,queries['embeddings'])},closure=closure)


def bind_profile(service, candidate):
    """Bind to a fresh detached LocalService only, preserving its SK03 focus."""
    require(service.mode=='local' and not service.sessions and not hasattr(service,'release_metadata'),'STRUCTURAL_LOCAL_BOOTSTRAP_REQUIRED')
    require(set(candidate['bundles'])==set(service.originals),'STRUCTURAL_SOURCE_SCOPE')
    for key,bundle in candidate['bundles'].items():require(bundle==service.bundles[key],'STRUCTURAL_RUNTIME_SOURCE_MISMATCH')
    rows=candidate['index']._rows;alignment={}
    for pair in candidate['pairs']:
        entries=[e for (pid,_),e in service.entries.items() if pid==pair['pair_id']]
        require(bool(entries),'STRUCTURAL_PAIR_MISMATCH')
        for entry in entries:
            context=entry['context']
            require(context['family']==pair['family'] and all(context['pair'][side]=={k:pair[side][k] for k in ('document_id','version_id')} for side in ('before','after')),'STRUCTURAL_PAIR_MISMATCH')
            cites=service._comparison_item(context)['citations'];matched=[]
            for side in ('before','after'):
                expected=next(c for c in cites if all(c[k]==pair[side][k] for k in ('document_id','version_id')))
                found=[r['citation']['citation_id'] for r in rows if r['origin']=='reused_ai_annotated_subspan' and all(r['citation'][k]==expected[k] for k in ('document_id','version_id','start','end','text'))]
                require(len(found)==1,'STRUCTURAL_COUNTERPART_IDENTITY');matched.append(found[0])
            alignment[matched[0]]=[matched[1]];alignment[matched[1]]=[matched[0]]
    previous=service.snapshot
    service.index=candidate['index'];service.index_payload={**candidate['payload'],'bundle_hash':candidate['index'].model_identity}
    service.query_cache=candidate['query_cache'];service.protocol={**service.protocol,'alignment':alignment}
    service.snapshot=digest({'profile':PROFILE,'baseline_snapshot':previous,'closure':candidate['closure'],'index_hash':service.index.index_hash})
    service.structural_metadata={'profile':PROFILE,'index_hash':service.index.index_hash,'vectors':'real231_cached','query_compatibility':'046_observed_contract_three_exposed_queries','promotion':'not_approved','baseline_snapshot':previous,'snapshot':service.snapshot,'closure':deepcopy(candidate['closure']),'retrieval_strategy':'structural231_plus_verified_focus_expansion','coverage':'partial_exposed_development','quality_acceptance':False}
    service.provenance['structural_profile']=deepcopy(service.structural_metadata)
    service.limitations.append('Índice estructural231 de desarrollo expuesto; compatibilidad046 observada en tres consultas, sin aceptación de calidad ni promoción.')
    return service
