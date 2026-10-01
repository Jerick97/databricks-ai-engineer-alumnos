"""Separately cited editorial notes and conservative textual marker links.

Raw evidence is never rewritten. Unique textual match is not legal ownership or
verification. Unsupported layout, missing boundaries and repeated markers remain
unresolved. This module does not import the mutable structural segmenter.
"""
import hashlib
import json
import re
from collections import Counter

VERSION = 'editorial-note-links-v4'
_NOTE = re.compile(r'(?m)^[ \t]*(?P<marker>[1-9][0-9]{0,2})[ \t]+(?:Artículo|Párrafo|Literal|Numeral)[ \t]+(?:modificado|incorporado|sustituido|derogado)\b[^\n]*')
_SECTION = re.compile(r'(?m)^[ \t]*(?:CAP[IÍ]TULO[ \t]+(?:[IVXLCDM]+|[0-9]+)|DISPOSICIONES(?: COMPLEMENTARIAS)?(?: FINALES| TRANSITORIAS| DEROGATORIAS)|RESUELVE:)[ \t]*$')
# Same admitted lexical vocabulary as Task2, no import of mutable segmenter.
_ORDINAL_WORDS = r'Primer[oa]|Segund[oa]|Tercer[oa]|Cuart[oa]|Quint[oa]|Sext[oa]|S[eé]p?tim[oa]|Octav[oa]|Noven[oa]|D[eé]cim[oa]'
_MARKER = re.compile(r'(?P<punct>[.!?])(?P<marker>[1-9][0-9]{0,2})(?=[ \t]*(?:\r?\n|$))')


def _hash(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def _validate(raw, structural):
    text=raw.get('rawtext')
    if not isinstance(text,str) or hashlib.sha256(text.encode()).hexdigest()!=raw.get('rawtext_sha256'):
        raise ValueError('NOTES_RAW_INTEGRITY')
    if raw.get('layer')!='raw_pages' or structural.get('layer')!='structural_provisions':
        raise ValueError('NOTES_LAYER_REQUIRED')
    if any(structural.get(k)!=raw.get(k) for k in ('rawtext','rawtext_sha256','sha256','pages')):
        raise ValueError('NOTES_SOURCE_MISMATCH')
    if structural.get('structure',{}).get('parent_bundle_sha256')!=_hash(raw):
        raise ValueError('NOTES_PARENT_MISMATCH')
    pages=raw.get('pages',[]);previous=-1
    for i,p in enumerate(pages,1):
        if type(p.get('page')) is not int or p['page']!=i or type(p.get('start')) is not int or type(p.get('end')) is not int or not 0<=p['start']<=p['end']<=len(text) or p['start']!=(0 if i==1 else previous+1):
            raise ValueError('NOTES_PAGE_MAP_INVALID')
        previous=p['end']
    if previous!=len(text):raise ValueError('NOTES_PAGE_MAP_INVALID')
    identities=set()
    for bundle in (raw,structural):
        ids=set()
        for p in bundle.get('provisions',[]):
            if type(p.get('start')) is not int or type(p.get('end')) is not int or not 0<=p['start']<p['end']<=len(text) or p.get('text')!=text[p['start']:p['end']]:
                raise ValueError('NOTES_CITATION_INVALID')
            if p.get('citation_id') in ids:raise ValueError('NOTES_DUPLICATE_CITATION')
            ids.add(p.get('citation_id'));identities.add((p.get('document_id'),p.get('version_id'),p.get('source_kind'),p.get('synthetic')))
    if len(identities)!=1:raise ValueError('NOTES_IDENTITY_MISMATCH')
    identity=next(iter(identities))
    if identity[1]!=raw.get('sha256') or identity[2]!='normative':raise ValueError('NOTES_IDENTITY_MISMATCH')
    return text,identity


def extract_note_links(raw_bundle, structural_bundle):
    """Return notes/links/unresolved with exact raw intervals and explicit scope.

    Supported note starts name an editorial operation; punctuation-attached
    terminal digits are marker candidates. Neither ordinary numbers nor body
    containment proves a link. EOF without a following boundary is unresolved.
    """
    text,identity=_validate(raw_bundle,structural_bundle)
    sections=list(_SECTION.finditer(text))
    def scope(offset):
        preceding=[m for m in sections if m.start()<=offset]
        return {'document_id':identity[0],'version_id':identity[1],
                'section_start':preceding[-1].start() if preceding else 0,
                'section_label':preceding[-1][0].strip() if preceding else 'document'}
    def citation(start,end,kind):
        return dict(citation_id=_hash([VERSION,identity,_hash(raw_bundle),raw_bundle['sha256'],raw_bundle['rawtext_sha256'],kind,start,end]),
                    document_id=identity[0],version_id=identity[1],source_kind=identity[2],synthetic=identity[3],
                    start=start,end=end,text=text[start:end],pages=[p['page'] for p in raw_bundle['pages'] if p['start']<end and p['end']>start])
    starts=list(_NOTE.finditer(text));notes=[]
    for m in starts:
        # Exact continuous range, never joining across excluded furniture.
        tail=text[m.end():]
        boundaries=[]
        blank=re.search(r'\n[ \t]*\r?\n',tail)
        if blank:boundaries.append(m.end()+blank.start())
        next_note=next((n.start() for n in starts if n.start()>m.start()),None)
        if next_note is not None:boundaries.append(next_note)
        furniture=re.search(r'(?m)^[ \t]*(?:Los Laureles\b|Artículo [0-9]+[.]|CAP[IÍ]TULO\b|DISPOSICIONES COMPLEMENTARIAS FINALES\b)',tail)
        if furniture:boundaries.append(m.end()+furniture.start())
        end=min(boundaries) if boundaries else len(text)
        ambiguous=re.search(r'(?m)^[ \t]*(?:Artículo[ \t]+(?:'+_ORDINAL_WORDS+r')\b|[0-9]+[.][0-9]+[ \t]+|[a-z][)][ \t]+)',tail)
        continuation=None
        if ambiguous and m.end()+ambiguous.start()<end:
            at=m.end()+ambiguous.start()
            continuation=citation(at,end,'ambiguous_note_continuation')
            end=at
        while end>m.start() and text[end-1].isspace():end-=1
        c=citation(m.start(),end,'note')
        notes.append(dict(note_id=c['citation_id'],marker=m['marker'],citation=c,
                          marker_span=citation(m.start('marker'),m.end('marker'),'note_marker'),
                          scope=scope(m.start()),boundary_status='bounded' if boundaries and continuation is None else 'unresolved',
                          continuation_candidate=continuation,
                          kind='editorial_annotation',legal_status='not_assessed'))
    def inside_note(offset):return any(n['citation']['start']<=offset<n['citation']['end'] for n in notes)
    candidates=[]
    for m in _MARKER.finditer(text):
        if m.start()==0 or text[m.start()-1].isdigit() or inside_note(m.start()):continue
        if re.search(r'(?i)\b(?:art|arts|num|núm|nro|pág|pag|cap|vol|inc|lit|no)$',text[:m.start()]):continue
        owners=[p for p in structural_bundle['provisions'] if p['start']<=m.start('marker') and m.end('marker')<=p['end']]
        for owner in owners:
            # Identify subordinate textual label only from explicit preceding labels
            # inside this owner, excluding detected note text.
            prefix=text[owner['start']:m.start()];subs=[x for x in re.finditer(r'(?m)^[ \t]*(\d+[.]\d+)[ \t]+',prefix) if not inside_note(owner['start']+x.start())]
            label=None
            if subs:
                sub=subs[-1];label=sub[1]
                letters=[x for x in re.finditer(r'(?m)^[ \t]*([a-z])[)][ \t]+',prefix[sub.end():]) if not inside_note(owner['start']+sub.end()+x.start())]
                if letters:label+='('+letters[-1][1]+')'
            candidates.append(dict(marker=m['marker'],marker_span=citation(m.start('marker'),m.end('marker'),'body_marker'),
                                   owner_provision_id=owner['provision_id'],owner_citation_id=owner['citation_id'],owner_label=label,
                                   scope=scope(m.start()),basis='punctuation_attached_terminal_marker_inside_exact_owner'))
    counts=Counter((n['marker'],_hash(n['scope'])) for n in notes)
    links=[];unresolved=[]
    for n in notes:
        matches=[c for c in candidates if c['marker']==n['marker'] and c['scope']==n['scope']]
        reasons=[]
        if n['boundary_status']!='bounded':reasons.append('note_boundary_unresolved')
        if counts[n['marker'],_hash(n['scope'])]!=1:reasons.append('repeated_note_number_in_scope')
        if len(matches)!=1:reasons.append('marker_missing' if not matches else 'multiple_marker_candidates')
        if reasons:
            unresolved.append(dict(note_id=n['note_id'],status='unresolved',reasons=reasons,candidate_owners=matches))
        else:links.append(dict(matches[0],note_id=n['note_id'],status='unique_textual_match',legal_status='not_assessed'))
    return dict(version=VERSION,notes=notes,links=links,unresolved=unresolved,
                provenance={'raw_bundle_sha256':_hash(raw_bundle),'structural_bundle_sha256':_hash(structural_bundle)},
                limitations=['textual_link_not_legal_adjudication','unsupported_note_formats_not_exhaustively_detected','raw_layout_ambiguity_requires_review'],
                coverage='partial')
