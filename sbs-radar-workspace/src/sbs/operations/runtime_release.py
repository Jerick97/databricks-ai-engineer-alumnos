"""Read-only promotion of trusted SK11 receipts into a detached runtime candidate.

A digest is integrity, not authorization: pointer/receipt and store are server
capabilities. This module never captures sources, embeds, uploads or publishes.
"""
from copy import deepcopy
import json
from pathlib import Path
import re
import tempfile
from . import verify_closure,sha,canonical
from .volume_artifacts import relative
from sbs.genie import digest,curate
from sbs.contracts import validate_contract
from sbs.retrieval import LocalIndex,ServerScope
from sbs.comparison import compare


def require(condition,message):
    if not condition:raise ValueError(message)



def document_display_name(document_id):
    """Presentation of registered identity; never infer legal dates or validity."""
    match=re.fullmatch(r'sbs-([0-9]+)-([0-9]{4})',document_id)
    return 'Resolución SBS '+match[1]+'-'+match[2] if match else 'Documento normativo'


def structural_display_name(span):
    prefixes={'numbered_article':'Artículo','resolution_article':'Artículo resolutivo',
              'final_provision':'Disposición final','section_provision':'Disposición'}
    prefix=prefixes.get(span.get('unit_kind'),'Disposición')
    number=span.get('number')
    return prefix+(' '+str(number) if number else ' seleccionada')

def load_release(root,*,pointer,model_identity):
    root=Path(root)
    require(not any(p.is_symlink() for p in (root,*root.parents)),'RELEASE_ROOT_SYMLINK')
    root=root.resolve()
    require(isinstance(pointer,dict) and set(pointer)=={'release_id','sha256'} and all(isinstance(v,str) and re.fullmatch('[0-9a-f]{64}',v) for v in pointer.values()),'RELEASE_POINTER_INVALID')
    name='releases/'+pointer['release_id']+'/release.json'
    verify_closure(root,{name:pointer['sha256']});release=json.loads((root/name).read_bytes())
    require(sha(canonical(release))==pointer['release_id'],'RELEASE_IDENTITY')
    require(release.get('release_scope')=='prepared_downstream' and release.get('real_preparation_completed') is True and set(release.get('prepared',{}))=={'SK03','SK04','SK06'},'REAL_PREPARED_RELEASE_REQUIRED')
    closure={name:pointer['sha256']};payloads={}
    for key,item in release['prepared'].items():
        require(item.get('mode')=='real','REAL_PREPARED_RELEASE_REQUIRED')
        for path,expected in {**item['closure'],item['artifact_path']:item['sha256']}.items():
            require(path not in closure or closure[path]==expected,'CLOSURE_CONFLICT');closure[path]=expected
        verify_closure(root,closure)
        envelope=json.loads((root/item['artifact_path']).read_bytes())
        require(digest(envelope['payload'])==envelope['sha256'],'PREPARED_ENVELOPE_INTEGRITY');payloads[key]=envelope['payload']
    c,r,g=(payloads[k] for k in ('SK03','SK04','SK06'))
    for p in payloads.values():
        require(p['source_snapshot']==digest(release['sources']) and p['plan_fingerprint']==release['plan_fingerprint'] and p['plan_id']==release['plan_id'] and p['run_id']==c['run_id'],'RELEASE_COMPONENT_SCOPE')
    require(r['model_identity']==model_identity,'RELEASE_MODEL_INCOMPATIBLE')
    index=LocalIndex(r['records'],r['vectors'],dimension=r['dimension'],model_identity=model_identity,actual_identity=r['model_identity'])
    require(index.index_hash==r['index_hash'],'RELEASE_INDEX_INTEGRITY')
    require(g['curation_config'].get('retrieval_index_hash')==r['index_hash'] and g['curation_config'].get('source_snapshot')==c['source_snapshot'] and g['curation_config'].get('refresh_plan')==release['plan_fingerprint'] and g['curation_config'].get('annotation_sha256')==digest(c['annotation_reuse']),'RELEASE_CURATION_SCOPE')
    bundle=g['bundle'];documents=[json.loads(row['payload_json']) for row in bundle['tables']['documents']]
    require(len(documents)==len(release['sources']),'RELEASE_SOURCE_CLOSURE')
    originals={};bundles={};sources={};families={};docs={}
    for document in documents:
        require(validate_contract('SourceDocument',document)['valid'] and document['synthetic'] is False,'REAL_SOURCE_REQUIRED')
        identity=(document['document_id'],document['version_id']);docs[identity]=document
        matches=[s for s in release['sources'] if s['source_key']==sha(canonical([document['document_id'],document['url']])) and s['sha256']==document['sha256']]
        require(len(matches)==1,'RELEASE_SOURCE_MISMATCH')
        summary=matches[0]
        require(all(summary[k]==document[k] for k in ('document_id','family','sha256')),'RELEASE_SOURCE_MISMATCH')
        original='foundation/objects/'+document['sha256'][:2]+'/'+document['sha256']+'.pdf'
        # Derivation paths are selected by current sealed metadata, not globbing.
        derived='foundation/derived/'+document['sha256']+'/'+sha(summary['extractor'].encode())+'/'+summary['extraction_config_hash']
        paths=[original,derived+'/result.json',derived+'/rawtext.txt']
        require(all(p in closure for p in paths),'RELEASE_SOURCE_CLOSURE')
        b=json.loads((root/paths[1]).read_bytes());raw=(root/paths[2]).read_bytes()
        require(sha((root/original).read_bytes())==document['sha256'] and b['sha256']==document['sha256'] and b['extractor']==summary['extractor'] and b['config_hash']==summary['extraction_config_hash'] and sha(raw)==b['rawtext_sha256']==summary['rawtext_sha256'] and raw.decode()==b['rawtext'],'RELEASE_ORIGINAL_MISMATCH')
        originals[identity]=b['rawtext'];bundles[identity]=b;sources[document['version_id']]=root/original;families[document['version_id']]=document['family']
    def span(p):
        require(validate_contract('Provision',p)['valid'] and p['synthetic'] is False,'RELEASE_SPAN_INVALID')
        identity=(p['document_id'],p['version_id'])
        require(identity in originals and originals[identity][p['start']:p['end']]==p['text'],'RELEASE_LITERAL_MISMATCH')
    for b in bundles.values():
        for p in b['provisions']:span(p)
    for row in r['records']:
        p=row['citation'];span(p);b=bundles[(p['document_id'],p['version_id'])]
        require(row['source']=={k:b[k] for k in ('sha256','extractor','config_hash','rawtext_sha256')},'RELEASE_RECORD_SOURCE_MISMATCH')
        require(row['family']==docs[(p['document_id'],p['version_id'])]['family'] and b['rawtext'][row['embedding_start']:p['end']]==row['embedding_text'],'RELEASE_EMBEDDING_INPUT_MISMATCH')
    wrappers=c.get('structural_wrappers')
    if wrappers is not None:
        from sbs.comparison.structural import compare_structural
        from .structural_evidence import project
        require(type(c.get('structural_evidence_version')) is int and c['structural_evidence_version']==1,'RELEASE_STRUCTURAL_VERSION')
        require(len(wrappers)==len(c['pairs']),'RELEASE_STRUCTURAL_PAIRS')
        require(g['curation_config'].get('structural_evidence_sha256')==digest(wrappers),'RELEASE_STRUCTURAL_HASH')
        for pair,w in zip(c['pairs'],wrappers):
            expected=compare_structural(pair,*[bundles[(pair[side]['document_id'],pair[side]['version_id'])] for side in ('before','after')])
            require(w==expected,'RELEASE_STRUCTURAL_REPLAY_MISMATCH')
            require(w['original_comparison'] in c['comparisons'],'RELEASE_ORIGINAL_COMPARISON_MISSING')
            for p in project(w)[0]:require(p in c['structural_provisions'],'RELEASE_STRUCTURAL_CITATION_MISSING')
    else:require('structural_evidence_version' not in c and 'structural_evidence_sha256' not in g['curation_config'],'RELEASE_STRUCTURAL_VERSION')
    provisions=[p for b in bundles.values() for p in b['provisions']]+c['structural_provisions']
    for p in provisions:span(p)
    review={'run_id':c['run_id']+'-annotations','references':c['annotation_reuse'],'human_gold':False} if c['annotation_reuse'] else None
    require(curate(documents,c['pairs'],c['comparisons'],review,[],g['curation_config'],mode='real',provisions=provisions)==bundle,'RELEASE_CURATION_MISMATCH')
    entries={};pairs=[];comparisons={};alignment={}
    for pair in c['pairs']:
        require(validate_contract('VersionPair',pair)['valid'],'RELEASE_PAIR_INVALID')
        selected=[]
        items=[x for x in c['comparisons'] if x['change_set']['pair']==pair]
        require(bool(items),'RELEASE_COMPARISON_MISSING')
        for item in items:
            require(validate_contract('ChangeSet',item['change_set'])['valid'],'RELEASE_COMPARISON_INVALID')
            citations=item['change_set']['evidence']['citations'];sides={}
            for side in ('before','after'):
                ref=pair[side];sides[side]={p['provision_id']:p for p in citations if all(p[k]==ref[k] for k in ('document_id','version_id'))}
            for p in citations:
                full={**p,'synthetic':False};span(full)
            # Same raw page number is a UI focus, never an asserted semantic alignment.
            for provision in sorted(set(sides['before']) & set(sides['after'])):
                key=(pair['pair_id'],provision);before=deepcopy(sides['before'][provision]);after=deepcopy(sides['after'][provision])
                annotated=any(a['pair_id']==pair['pair_id'] and a['provision_id']==provision for a in c['annotation_reuse'])
                label=provision+(' · anotación IA validada' if annotated else ' · página física, correspondencia semántica pendiente')
                context=dict(context_id=pair['pair_id']+'-'+provision,family=pair['family'],pair=deepcopy(pair),target_date=None,selected_provision_id=provision)
                if annotated:
                    display_label=('Artículo '+provision[3:] if re.fullmatch(r'art[0-9]+(?:[.][0-9]+)*',provision) else 'Disposición anotada · página '+str(before['page']))+' · anotación IA validada'
                else:display_label='Página física '+str(before['page'])+' · correspondencia semántica pendiente'
                entries[key]={'context':context,'label':label,'display_label':display_label,'before':{**before,'quote_raw':before['text']},'after':{**after,'quote_raw':after['text']}}
                left={**bundles[(before['document_id'],before['version_id'])],'provisions':[{**before,'synthetic':False}]}
                right={**bundles[(after['document_id'],after['version_id'])],'provisions':[{**after,'synthetic':False}]}
                if annotated:left['layer']=right['layer']='structural_provisions'
                focused=compare(pair,left,right,alignments=[{'before':[provision],'after':[provision]}] if annotated else None,coverage='partial')
                comparisons[key]={**focused,'citations':[before,after],'focus_origin':'SK03_AI_annotated_subset' if annotated else 'SK03_raw_page_focus'}
                if not any(x['id']==provision for x in selected):selected.append({'id':provision,'label':display_label})
        if wrappers is not None:
            from .structural_evidence import focus
            w=next(w for w in wrappers if w['original_comparison']['change_set']['pair']==pair)
            for a in w['alignment_provenance']['correspondences']:
                if len(a['before'])!=1 or a['before']!=a['after']:continue
                provision=a['before'][0];item,ends=focus(w,provision,bundles);key=(pair['pair_id'],provision)
                label=provision+' · correspondencia estructural heurística, cobertura parcial'
                context=dict(context_id=pair['pair_id']+'-'+provision,family=pair['family'],pair=deepcopy(pair),target_date=None,selected_provision_id=provision)
                display_label=structural_display_name(w['evidence_context']['before']['structure']['spans'][provision])+' · cobertura parcial'
                entries[key]={'context':context,'label':label,'display_label':display_label,**{side:{**{k:v for k,v in p.items() if k!='synthetic'},'quote_raw':p['text']} for side,p in ends.items()}}
                comparisons[key]=item
                selected=[x for x in selected if x['id']!=provision]+[dict(id=provision,label=display_label,evidence_origin='SK03_structural_heuristic')]
        require(bool(selected),'RELEASE_NO_PAIRED_FOCUS')
        title=document_display_name(pair['before']['document_id'])
        if pair['before']['document_id']!=pair['after']['document_id']:title+=' / '+document_display_name(pair['after']['document_id'])
        identity_details={'pair_id':pair['pair_id'],**{side+'_'+field:pair[side][field] for side in ('before','after') for field in ('document_id','version_id')}}
        pairs.append(dict(id=pair['pair_id'],family_id=pair['family'],title=title,before_label='Copia A · '+pair['before']['version_id'][:8],after_label='Copia B · '+pair['after']['version_id'][:8],identity_details=identity_details,status='unreviewed',evidence_status='partial',provisions=selected))
    # Identity includes every prepared artifact and its source closure, not a renamed old index.
    snapshot=digest({'release_id':pointer['release_id'],'closure':closure,'index_hash':index.index_hash})
    verify_closure(root,closure)
    return dict(snapshot=snapshot,index=index,index_payload={**r,'bundle_hash':model_identity},protocol={'alignment':alignment},originals=originals,bundles=bundles,sources=sources,source_families=families,scope=ServerScope(frozenset(families.values()),frozenset(originals)),entries=entries,pairs=pairs,comparisons=comparisons,release_metadata={'pointer':deepcopy(pointer),'root':str(root),'closure':closure,'genie_snapshot':bundle['snapshot_hash'],'coverage':'partial','annotation_count':len(c['annotation_reuse']),'structural_evidence_version':c.get('structural_evidence_version'),'retrieval_strategy':'cached_raw_pages_plus_structural_expansion' if wrappers is not None else 'cached_raw_pages','semantic_vectors':'pending_not_built' if wrappers is not None else 'not_requested'})


def materialize_release(store,receipt,destination):
    """Read a trusted SnapshotWriter current receipt via injected VolumeArtifacts.

    recover/_read are bounded Files download-only methods; no upload is invoked.
    Returns an isolated directory and pointer, retained for the service lifetime.
    The caller owns cleanup only after all users of this snapshot have retired.
    """
    manifest_path=receipt['manifest_path'];expected=receipt['manifest_sha256']
    require(receipt.get('release_id')==expected,'SHARED_RECEIPT_IDENTITY')
    artifacts=store.recover(manifest_path,expected)
    require(digest(artifacts)==receipt['artifacts_sha256'],'SHARED_RECEIPT_CLOSURE')
    raw=store._read(manifest_path);require(sha(raw)==expected,'SHARED_MANIFEST_CHANGED')
    manifest=json.loads(raw);base=manifest_path.rsplit('/',1)[0]
    parent=Path(destination)
    require(not any(p.is_symlink() for p in (parent,*parent.parents)),'MATERIALIZATION_SYMLINK')
    parent.mkdir(parents=True,exist_ok=True)
    root=Path(tempfile.mkdtemp(prefix='runtime-release-',dir=parent))
    try:
        closure={}
        for name,item in manifest['files'].items():
            relative(name);data=store._read(base+'/'+name,item['bytes'])
            require(sha(data)==item['sha256']==artifacts[base+'/'+name],'SHARED_READBACK_CHANGED')
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);p.chmod(0o444);closure[name]=item['sha256']
        verify_closure(root,closure)
        candidates=[n for n in closure if re.fullmatch(r'releases/[0-9a-f]{64}/release.json',n)]
        require(len(candidates)==1,'ONE_PREPARED_RELEASE_REQUIRED')
        name=candidates[0]
        return {'state_root':root,'pointer':{'release_id':name.split('/')[1],'sha256':closure[name]}}
    except Exception:
        import shutil
        shutil.rmtree(root)
        raise
