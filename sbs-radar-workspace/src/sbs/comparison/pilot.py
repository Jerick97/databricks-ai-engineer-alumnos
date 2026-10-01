"""Deterministic pilot subsets from frozen AI reviews 002/003, not legal gold.

build_pilot(root) returns three comparison items with structural bundles and
exact citations. by_provision(root) indexes those items by (family, provision_id).
No retrieval, network, model inference, original mutation or global coverage.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from sbs.comparison import compare
from sbs.paths import project_path

VERSION='0.1.1'


def digest(raw):return hashlib.sha256(raw).hexdigest()


def structural_bundle(bundle, annotation, provision_id):
    """Validate reviewed parent span, then optionally slice 29.1 item 4 exactly.

    Pages checked against the sealed extraction map. The historical visual check
    remains an AI annotation; this function does not redo visual adjudication.
    """
    b=deepcopy(bundle);c=deepcopy(annotation);raw=b['rawtext']
    if digest(raw.encode())!=b['rawtext_sha256']:raise ValueError('raw_hash_mismatch')
    if c['original_sha256']!=b['sha256'] or c['version_id']!=b['sha256']:
        raise ValueError('annotation_version_mismatch')
    if any(p['document_id']!=c['document_id'] or p['version_id']!=c['version_id'] for p in b['provisions']):
        raise ValueError('annotation_identity_mismatch')
    if raw[c['start']:c['end']]!=c['quote_raw']:raise ValueError('annotation_text_mismatch')
    if not any(p['page']==c['page'] and p['start']<=c['start']<c['end']<=p['end'] for p in b['pages']):
        raise ValueError('annotation_page_mismatch')
    start,end=c['start'],c['end']
    if provision_id=='art29.1.4':
        marker='\n4. '
        if c['quote_raw'].count(marker)!=1:raise ValueError('ambiguous_item4_boundary')
        start+=c['quote_raw'].index(marker)+1
    citation_id='structural-'+digest(json.dumps([c['document_id'],c['version_id'],b['rawtext_sha256'],provision_id,start,end],separators=(',',':')).encode())
    p={k:c[k] for k in ('document_id','version_id','page')}
    p.update(citation_id=citation_id,provision_id=provision_id,start=start,end=end,text=raw[start:end],source_kind='normative',synthetic=False)
    b['provisions']=[p];b['layer']='structural_provisions'
    b['quality']={'status':'partial','limitations':sorted(set(b.get('quality',{}).get('limitations',[])+[
        'pilot_ai_annotated_subset_only','not_current_consolidation','materiality_not_assessed']))}
    b['annotation_provenance']={'parent_citation_id':c['citation_id'],'parent_start':c['start'],'parent_end':c['end'],
        'kind':'existing_ai_review_annotation','visual_review_reused':c.get('visual_original_verified') is True,
        'human_gold':False,'institutional_approval':False}
    return b


def build_pilot(root):
    root=Path(root).resolve();inputs={}
    def local(path):
        return project_path(root,path)
    def read(path,expected=None):
        p=local(path);raw=p.read_bytes();h=digest(raw)
        if expected is not None and h!=expected:raise ValueError('sealed_input_hash_mismatch')
        inputs[str(p.relative_to(root))]=h
        return raw
    r3=json.loads(read('runs/astra-normative-review-003.json'))
    r2=json.loads(read('runs/astra-normative-review.json',r3['prior_review']['sha256']))
    if r3['reviewer']['human_gold'] is not False or r2['reviewer']['human_gold'] is not False:
        raise ValueError('ai_provenance_required')
    sealed={str(local(x['path'])):x['sha256'] for x in r3['skill_invocation']['inputs']}
    def sealed_read(path):
        p=local(path)
        if str(p) not in sealed:raise ValueError('input_not_sealed_by_review')
        return read(p,sealed[str(p)])
    sources={}
    for filename in ['runs/sk02-repository-capture.json','runs/sk02-amendments-capture.json']:
        capture=json.loads(sealed_read(filename))
        read(capture['manifest'],capture['manifest_sha256'])
        for entry in capture['sources']:
            source=entry['source'];b=json.loads(sealed_read(entry['result_path']))
            if digest(sealed_read(entry['original_path']))!=source['sha256'] or b['sha256']!=source['sha256']:
                raise ValueError('source_hash_mismatch')
            raw=sealed_read(entry['rawtext_path'])
            if raw.decode()!=b['rawtext'] or digest(raw)!=b['rawtext_sha256']:
                raise ValueError('raw_hash_mismatch')
            sources[(source['document_id'],source['version_id'])]=(b,entry)
    selections=[('cyber-504','cybersecurity','art20.3',r2,'v4-art20-3','v5-art20-3'),
                ('market-3274','market_conduct','art27',r3,'market-v7-art27','market-v8-art27'),
                ('market-3274','market_conduct','art29.1.4',r3,'market-v7-art29-1','market-v8-art29-1')]
    items=[]
    for pair_id,family,provision_id,review,left,right in selections:
        annotations={side:deepcopy(review['citations'][key]) for side,key in [('before',left),('after',right)]}
        bundles={};pair={'pair_id':pair_id,'family':family}
        for side,c in annotations.items():
            b,entry=sources[(c['document_id'],c['version_id'])]
            if local(c['rawtext_path'])!=local(entry['rawtext_path']) or local(c['original_path'])!=local(entry['original_path']):
                raise ValueError('annotation_source_path_mismatch')
            if entry['source']['family']!=family:raise ValueError('annotation_family_mismatch')
            bundles[side]=structural_bundle(b,c,provision_id)
            pair[side]={k:c[k] for k in ('document_id','version_id')}
        result=compare(pair,bundles['before'],bundles['after'],alignments=[{'before':[provision_id],'after':[provision_id]}],coverage='partial')
        item={'pair_id':pair_id,'family':family,'provision_id':provision_id,
              'before':bundles['before']['provisions'][0],'after':bundles['after']['provisions'][0],
              'citations':result['change_set']['evidence']['citations'],'bundles':bundles,
              'annotation':{'kind':'reused_ai_reference','run_id':review['run_id'],'human_gold':False,
                            'institutional_approval':False,'review_citations':annotations,
                            'citation_derivation':'exact_subspan_of_reviewed_29.1_context' if provision_id=='art29.1.4' else 'reviewed_span_unchanged'},**result}
        items.append(item)
    return {'component':'SK03-pilot','version':VERSION,'coverage':'partial','items':items,
            'input_files':[{'path':p,'sha256':h} for p,h in sorted(inputs.items())],
            'limitations':['AI annotations reused; not human gold or institutional approval.',
                           'Only selected copied spans; no exhaustive or current consolidated law claim.',
                           'Literal differences include extraction spacing and footnote markers; materiality not assessed.']}


def by_provision(root):
    return {(item['family'],item['provision_id']):item for item in build_pilot(root)['items']}
