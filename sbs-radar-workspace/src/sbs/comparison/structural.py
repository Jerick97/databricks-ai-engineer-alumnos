"""Structural literal comparison plus reversible, non-citable derived views.

No materiality inference, legal completeness or replacement of source citations.
"""
from copy import deepcopy
import hashlib
import json
import re
from sbs.foundation.structure import structuralize, structural_alignments
from sbs.foundation.structure_notes import extract_note_links
from sbs.comparison import compare

VERSION='structural-comparison-v3'


def _hash(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def _context(raw,structured,notes):
    provisions=structured['provisions'];excluded=structured['structure'].get('excluded_ranges',[])
    unit_context=[]
    for p in provisions:
        related=[e for e in excluded if e['start']<=p['end'] and e['end']>=p['start']]
        # Adjacency is context only; never assign excluded quoted law to this act.
        start=min([p['start']]+[e['start'] for e in related]);end=max([p['end']]+[e['end'] for e in related])
        unit_context.append(dict(provision_id=p['provision_id'],pages=structured['structure']['spans'][p['provision_id']]['pages'],
                                 unit_completeness='partial',related_exclusions=deepcopy(related),
                                 exclusion_relationship='contextual_not_legal_ownership',
                                 expanded_raw_context=dict(citation_id=_hash([raw,p['document_id'],'expanded_context',start,end]),document_id=p['document_id'],version_id=p['version_id'],citable=True,start=start,end=end,text=raw['rawtext'][start:end],
                                   pages=[x['page'] for x in raw['pages'] if x['start']<end and x['end']>start])))
    return dict(provisions=deepcopy(provisions),unit_context=unit_context,notes=notes,
                excluded_ranges=deepcopy(excluded),structure=deepcopy(structured['structure']),coverage='partial')


def _view(raw,p,context):
    text=raw['rawtext'];notes=context['notes'];intervals=[];uncertainty=[]
    linked={l['note_id']:l for l in notes['links']}
    if any(c['owner_provision_id']==p['provision_id'] for u in notes['unresolved'] for c in u['candidate_owners']):
        uncertainty.append('unresolved_note_owner_candidate')
    for n in notes['notes']:
        c=n['citation']
        if n['note_id'] in linked and n['boundary_status']=='bounded':
            if p['start']<=c['start'] and c['end']<=p['end']:
                intervals.append((c['start'],c['end'],'linked_editorial_note',c['citation_id']))
        elif c['start']<p['end'] and c['end']>p['start']:
            uncertainty.append('unresolved_note_retained')
        cont=n.get('continuation_candidate')
        if cont and cont['start']<p['end'] and cont['end']>p['start']:uncertainty.append('ambiguous_note_continuation_retained')
    for l in notes['links']:
        c=l['marker_span']
        if l['owner_provision_id']==p['provision_id']:
            intervals.append((c['start'],c['end'],'linked_note_marker',c['citation_id']))
    unit=next(u for u in context['unit_context'] if u['provision_id']==p['provision_id'])
    if unit['related_exclusions']:uncertainty.append('adjacent_or_interior_excluded_evidence')
    # Raw text/page offsets provide no visual header/footer classification.
    # Content match alone never authorizes deletion of a prescribed address.
    for m in re.finditer(r'(?m)^[ \t]*Los Laureles Nº 214 - Lima 27 - Perú[ \t]+Telf\.: \(511\) 6309000[ \t]*$',text):
        if p['start']<=m.start() and m.end()<=p['end']:
            uncertainty.append('unverified_page_furniture_retained')
    intervals.sort();clean=[]
    for item in intervals:
        if clean and item[0]<clean[-1][1]:
            uncertainty.append('overlapping_removal_candidates_retained');continue
        clean.append(item)
    mappings=[];omitted=[];derived=[];position=0
    def segment(start,end,value,operation,reason):
        nonlocal position
        mappings.append(dict(raw_start=start,raw_end=end,derived_start=position,derived_end=position+len(value),derived_text=value,operation=operation,reason=reason))
        derived.append(value);position+=len(value)
    def retain(start,end):
        cursor=start
        for m in re.finditer(r'\s+',text[start:end]):
            a,b=start+m.start(),start+m.end()
            if cursor<a:segment(cursor,a,text[cursor:a],'retain','literal_text')
            segment(a,b,' ','replace','whitespace_collapsed');cursor=b
        if cursor<end:segment(cursor,end,text[cursor:end],'retain','literal_text')
    cursor=p['start']
    for a,b,reason,cid in clean:
        retain(cursor,a);segment(a,b,'','omit',reason)
        omitted.append(dict(start=a,end=b,text=text[a:b],reason=reason,citation_id=cid,
                            pages=[x['page'] for x in raw['pages'] if x['start']<b and x['end']>a]));cursor=b
    retain(cursor,p['end'])
    # Collapse whitespace across omission boundaries without concealing mappings.
    normalized=[];last_space=True;position=0
    for m in mappings:
        value=m['derived_text']
        if value==' ' and last_space:value=''
        if value:last_space=value.endswith(' ')
        m.update(derived_start=position,derived_end=position+len(value),derived_text=value);position+=len(value);normalized.append(value)
    # End whitespace is a mapped replacement, never a deleted source interval.
    for m in reversed(mappings):
        if m['derived_text']:
            if m['derived_text']==' ':m.update(derived_text='',derived_end=m['derived_start'])
            break
    position=0
    for m in mappings:m.update(derived_start=position,derived_end=position+len(m['derived_text']));position=m['derived_end']
    # Representation-only compaction after every normalization decision. Exact
    # whitespace is literal; genuine replacements and omissions retain boundaries.
    compact=[]
    for m in mappings:
        if m['operation']!='omit' and text[m['raw_start']:m['raw_end']]==m['derived_text']:
            m.update(operation='retain',reason='literal_text')
        previous=compact[-1] if compact else None
        if (previous and previous['operation']==m['operation']=='retain'
            and previous['raw_end']==m['raw_start'] and previous['derived_end']==m['derived_start']
            and previous['raw_end']-previous['raw_start']==len(previous['derived_text'])
            and m['raw_end']-m['raw_start']==len(m['derived_text'])):
            previous.update(raw_end=m['raw_end'],derived_end=m['derived_end'],derived_text=previous['derived_text']+m['derived_text'])
        else:compact.append(m)
    mappings=compact
    result=''.join(m['derived_text'] for m in mappings)
    assert ''.join(text[m['raw_start']:m['raw_end']] for m in mappings)==p['text']
    return dict(text=result,citable=False,representation='derived_view_not_verbatim_quote',mapping=mappings,
                omitted_ranges=omitted,uncertainty=sorted(set(uncertainty)),source_citation_id=p['citation_id'])


def compare_structural(pair,before,after):
    """Consume pinned RAW bundles; preserve original comparison and exact evidence."""
    # Validate the raw endpoints even when no supported structural unit is found.
    compare(pair,before,after,alignments=[],coverage='partial')
    structured=[structuralize(b) for b in (before,after)]
    alignments=structural_alignments(*structured) if all(s['provisions'] for s in structured) else []
    original=compare(pair,*structured,alignments=alignments,coverage='partial')
    contexts={side:_context(raw,s,extract_note_links(raw,s)) for side,raw,s in zip(('before','after'),(before,after),structured)}
    byid=[{p['provision_id']:p for p in s['provisions']} for s in structured]
    def editorial(side,pid):
        n=contexts[side]['notes'];linked=[l for l in n['links'] if l['owner_provision_id']==pid]
        noteids={l['note_id'] for l in linked}
        return dict(notes=[x for x in n['notes'] if x['note_id'] in noteids],links=linked)
    derived=[]
    for a in alignments:
        l,r=byid[0][a['before'][0]],byid[1][a['after'][0]]
        lv,rv=_view(before,l,contexts['before']),_view(after,r,contexts['after'])
        equal=lv['text']==rv['text'];uncertain=bool(lv['uncertainty'] or rv['uncertainty'])
        category=('unresolved' if uncertain else 'editorial_only_candidate' if l['text']!=r['text'] else 'no_supported_body_difference') if equal else 'body_text_candidate'
        le,re=editorial('before',l['provision_id']),editorial('after',r['provision_id'])
        editorial_delta=[n['citation']['text'] for n in le['notes']]!=[n['citation']['text'] for n in re['notes']]
        derived.append(dict(editorial_comparison={'before':le,'after':re,'text_difference':editorial_delta,'basis':'unique_textual_links_only'},before_provision_id=l['provision_id'],after_provision_id=r['provision_id'],before=lv,after=rv,
                            derived_equal=equal,category=category,comparison_status='inconclusive' if uncertain else 'textual_candidate',materiality='not_assessed'))
    return dict(version=VERSION,original_comparison=original,
                alignment_provenance=dict(method='heuristic_textual_correspondence',algorithm=structured[0]['structure']['version'],legal_alignment_verified=False,correspondences=alignments),
                evidence_context=contexts,derived_comparison=derived,
                provenance=dict(raw_before_sha256=_hash(before),raw_after_sha256=_hash(after),notes_versions=[contexts[x]['notes']['version'] for x in ('before','after')]),
                coverage='partial',materiality='not_assessed')
