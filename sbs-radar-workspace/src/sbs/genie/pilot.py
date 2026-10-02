"""Offline export of frozen raw pages plus SK03 canonical structural provisions.

No network, inference, SQL execution service or cloud resource creation.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from sbs.comparison.pilot import build_pilot
from . import curate, digest, canonical, export_bundle, ScopedCatalog
from .provenance import snapshot_inputs, reconcile_snapshots

VERSION='0.1.0'


def build_pilot_002(root):
    inputs=snapshot_inputs(root);base=reconcile_snapshots(**inputs)
    pilot=build_pilot(root);old=inputs['bundle']
    payloads=lambda table:[json.loads(row['payload_json']) for row in old['tables'][table]]
    raw=payloads('provisions');provisions=deepcopy(raw)
    granularity={p['citation_id']:{'granularity':'raw_page','provision_id':p['provision_id']} for p in raw}
    sources={(e['source']['document_id'],e['source']['version_id']):e for e in inputs['source_evidence']}
    contexts=[];pairs={};comparisons=[];structural=[]
    questions={q['query_id']:q for q in inputs['rag_protocol_envelope']['payload']['questions']}
    query_ids={'art20.3':'cyber-art20-3','art27':'market-art27','art29.1.4':'market-art29-1-4'}
    for item in pilot['items']:
        pair=item['change_set']['pair'];pairs[pair['pair_id']]=pair
        context=deepcopy(questions[query_ids[item['provision_id']]]['context'])
        if any(context['pair'][k]!=pair[k] for k in ('family','before','after')):raise ValueError('PILOT_RAG_PAIR_MISMATCH')
        context.update(context_id=item['pair_id']+'-'+item['provision_id'],pair=deepcopy(pair),selected_provision_id=item['provision_id'])
        contexts.append(context)
        comparisons.append({k:deepcopy(item[k]) for k in ('change_set','changes','alignments','candidates','provenance','no_changes','annotation','provision_id')})
        for side in ('before','after'):
            p=item[side];source=sources[(p['document_id'],p['version_id'])];b=source['extraction']
            if b['rawtext'][p['start']:p['end']]!=p['text']:raise ValueError('STRUCTURAL_SOURCE_MISMATCH')
            if p['citation_id'] in granularity:raise ValueError('STRUCTURAL_CITATION_COLLISION')
            annotation=deepcopy(item['bundles'][side]['annotation_provenance'])
            granularity[p['citation_id']]={'granularity':'structural_provision','provision_id':p['provision_id'],'annotation':annotation}
            provisions.append(deepcopy(p))
            structural.append({'citation_id':p['citation_id'],'document_id':p['document_id'],'version_id':p['version_id'],
                'provision_id':p['provision_id'],'start':p['start'],'end':p['end'],'original_sha256':source['source']['sha256'],
                'rawtext_sha256':b['rawtext_sha256'],'text_sha256':hashlib.sha256(p['text'].encode()).hexdigest(),
                'parent_citation_id':annotation['parent_citation_id'],'annotation_kind':'existing_ai_review_annotation','human_gold':False})
    curation={'namespace':'sbs_radar','bundle_id':'sk06-pilot-002','granularity_sha256':digest(granularity),'sk03_version':pilot['version']}
    # Preserve the complete AI review payload; per-article review003 provenance also lives in changes and granularity.
    bundle=curate(payloads('documents'),list(pairs.values()),comparisons,payloads('reviews')[0],payloads('processes'),curation,mode='real',provisions=provisions)
    mapping={'version':'2','status':'source_raw_pages_and_structural_subspans_verified','sk06_snapshot':bundle['snapshot_hash'],
        'prior_sk06_snapshot':old['snapshot_hash'],'rag_snapshot':base['rag_snapshot'],'rag_index_hash':base['rag_index_hash'],
        'raw_page_count':len(raw),'structural_provision_count':len(structural),'total_provisions':len(provisions),
        'raw_page_mapping_sha256':base['mapping_sha256'],'sources':base['sources'],'structural_subspans':structural,
        'contexts':contexts,'granularity_sha256':digest(granularity),
        'input_files':dict(inputs['input_files'],**{f['path']:f['sha256'] for f in pilot['input_files']}),
        'limitations':['RAG vectors remain raw-page vectors; structural spans are verified source subspans, not reembedded vectors.',
                       'Counts are provision rows across two versions, not material changes.','No cloud publication or Genie execution certified.']}
    mapping['mapping_sha256']=digest(mapping)
    config={'version':VERSION,'bundle_id':'sk06-pilot-002','namespace':'sbs_radar','catalog':'neptuno_manuel_arguelles',
        'table_prefix':'neptuno_manuel_arguelles.sbs_radar','warehouse_id':None,'space_id':None,'snapshot':bundle['snapshot_hash'],
        'status':'local_artifacts_ready_cloud_resources_pending','curation_config':curation,'mapping_sha256':mapping['mapping_sha256'],
        'contexts':contexts,'publication_certificate':None,'backend_select_only_grants_verified':False,
        'limitations':mapping['limitations']}
    catalog=ScopedCatalog(bundle,contexts,table_prefix=config['table_prefix'])
    refs=[dict(context_id=c['context_id'],context=c,**p) for c in contexts for p in catalog.references(c).values()]
    benchmarks=[{'question':'¿Cuántas filas de disposición '+c['selected_provision_id']+' hay entre estas dos versiones?',
                 'context':c,'reference_query_id':'provision_count','expected_rows':[['2']],
                 'meaning':'Dos filas de disposición, una por versión; no cuenta cambios materiales.'} for c in contexts]
    benchmarks += [{'question':'Lista las filas de '+c['selected_provision_id']+' para este par.', 'context':c,
                    'reference_query_id':'provision_list','expected_rows':catalog.references(c)['provision_list']['rows'],
                    'meaning':'Filas estructurales con texto y fuente; no respuesta normativa ni aprobación.'} for c in contexts[:2]]
    return dict(bundle=bundle,config=config,contexts=contexts,granularity=granularity,mapping=mapping,reference_queries=refs,benchmarks=benchmarks)


def export_pilot_002(root, output=None, config_path=None):
    root=Path(root).resolve();out=Path(output) if output is not None else root/'runs/sk06-pilot-002'
    config_path=Path(config_path) if config_path is not None else root/'config/genie-pilot-002.json'
    result=build_pilot_002(root);export_bundle(result['bundle'],out)
    for name,key in [('contexts','contexts'),('granularity','granularity'),('snapshot-map','mapping'),('reference-queries','reference_queries'),('benchmark-questions','benchmarks')]:
        (out/(name+'.json')).write_text(canonical(result[key])+'\n')
    config=deepcopy(result['config'])
    for key,path in [('bundle_path',out),('snapshot_map_path',out/'snapshot-map.json')]:
        config[key]=str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
    config_path.parent.mkdir(parents=True,exist_ok=True);config_path.write_text(canonical(config)+'\n')
    result['config']=config
    artifacts={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir()) if p.is_file() and p.name!='artifacts.json'}
    (out/'artifacts.json').write_text(canonical({'bundle_id':'sk06-pilot-002','sha256':artifacts})+'\n')
    return result
