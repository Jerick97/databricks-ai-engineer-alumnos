"""Closed citation projections and focused metadata from verified structural artifacts."""
from copy import deepcopy
from sbs.genie import digest
from sbs.contracts import validate_contract
from sbs.comparison import compare

FIELDS=('citation_id','document_id','version_id','provision_id','page','start','end','text','source_kind')

def project(wrapper):
    provisions={};metadata={}
    def add(c,pid,kind,pages,synthetic=False):
        if not c['text'].strip():return
        row={k:c[k] for k in ('citation_id','document_id','version_id','start','end','text')}
        row.update(provision_id=pid,page=pages[0],source_kind=c.get('source_kind','normative'),synthetic=synthetic)
        if not validate_contract('Provision',row)['valid']:raise ValueError('STRUCTURAL_EVIDENCE_PROJECTION_INVALID')
        if row['citation_id'] in provisions and provisions[row['citation_id']]!=row:raise ValueError('STRUCTURAL_CITATION_COLLISION')
        provisions[row['citation_id']]=row;metadata[row['citation_id']]={'pages':pages,'kind':kind,'legal_status':'not_assessed'}
    for side,ctx in wrapper['evidence_context'].items():
        for p in ctx['provisions']:add(p,p['provision_id'],'structural_body',ctx['structure']['spans'][p['provision_id']]['pages'],p['synthetic'])
        synthetic=ctx['provisions'][0]['synthetic'] if ctx['provisions'] else False
        for n in ctx['notes']['notes']:
            for key,kind in [('citation','editorial_note'),('marker_span','note_marker'),('continuation_candidate','ambiguous_note_continuation')]:
                c=n.get(key)
                if c:add(c,kind+'-'+c['citation_id'],kind,c['pages'],synthetic)
        for e in ctx['excluded_ranges']:add(e,'excluded-'+e['citation_id'],'excluded_context',e['pages'],synthetic)
        for u in ctx['unit_context']:
            e=u['expanded_raw_context'];add(e,'expanded-'+e['citation_id'],'expanded_context',e['pages'],synthetic)
    return list(provisions.values()),metadata


def focus(wrapper,pid,bundles):
    pair=wrapper['original_comparison']['change_set']['pair'];provisions,metadata=project(wrapper)
    byid={p['citation_id']:p for p in provisions};selected={};raw=[];ids=set();details={}
    limitations=['Correspondencia estructural heurística; cobertura parcial, sin adjudicación jurídica.',
                 'Notas compuestas/no soportadas y exclusiones permanecen en evidencia; no equivalen a texto dispositivo limpio.']
    for side in ('before','after'):
        ctx=wrapper['evidence_context'][side];p=next(p for p in ctx['provisions'] if p['provision_id']==pid);selected[side]=p;ids.add(p['citation_id'])
        unit=next(u for u in ctx['unit_context'] if u['provision_id']==pid)
        ids.add(unit['expanded_raw_context']['citation_id']);ids.update(e['citation_id'] for e in unit['related_exclusions'])
        linked={l['note_id'] for l in ctx['notes']['links'] if l['owner_provision_id']==pid}
        # Global unresolved notes remain visible at every focus; no owner is inferred.
        unresolved={u['note_id'] for u in ctx['notes']['unresolved']}
        if unresolved:limitations.append('Notas no resueltas en '+side+': '+', '.join(sorted(n['marker'] for n in ctx['notes']['notes'] if n['note_id'] in unresolved))+'. Su relación con el foco no está establecida.')
        notes=[n for n in ctx['notes']['notes'] if n['note_id'] in linked|unresolved]
        for n in notes:
            for key in ('citation','marker_span','continuation_candidate'):
                if n.get(key):ids.add(n[key]['citation_id'])
        details[side]={'unit':deepcopy(unit),'notes':deepcopy(notes),'unresolved':deepcopy(ctx['notes']['unresolved']),
                       'note_relationship':'unique_textual_links_or_global_unresolved_not_ownership','links':[deepcopy(l) for l in ctx['notes']['links'] if l['owner_provision_id']==pid]}
        source=bundles[(p['document_id'],p['version_id'])]
        raw.append({**source,'layer':'structural_provisions','provisions':[p]})
    out=compare(pair,*raw,alignments=[{'before':[pid],'after':[pid]}],coverage='partial')
    citations=[{k:byid[c][k] for k in FIELDS} for c in sorted(ids) if c in byid]
    evidence=out['change_set']['evidence'];evidence['citations']=citations
    evidence['limitations']=list(dict.fromkeys(evidence['limitations']+limitations));evidence['evidence_id']='evidence-'+digest(evidence)
    out['change_set']['change_set_id']='changeset-'+digest(out['change_set'])
    if not validate_contract('ChangeSet',out['change_set'])['valid']:raise ValueError('STRUCTURAL_FOCUS_INVALID')
    derived=next((deepcopy(d) for d in wrapper['derived_comparison'] if d['before_provision_id']==pid and d['after_provision_id']==pid),None)
    return {**out,'citations':citations,'focus_origin':'SK03_structural_heuristic',
            'citation_metadata':{cid:metadata[cid] for cid in ids if cid in metadata},
            'alignment_provenance':deepcopy(wrapper['alignment_provenance']),
            'evidence_context':{**details,'global_limitations':limitations,'coverage':'partial'},'derived_comparison':derived},selected
