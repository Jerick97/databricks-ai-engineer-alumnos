"""Conservative numbered-heading layer over immutable raw text (SK02).

Automatic textual boundaries, not legal segmentation certification. No OCR,
normalization, embeddings or corpus publication. Citations remain contiguous;
running furniture and footnotes inside a span remain visible and partial.
"""
from collections import Counter
from copy import deepcopy
import hashlib
import json
import re
import unicodedata

from sbs.contracts import validate_contract

VERSION = 'numbered-headings-v8'

def _hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()

def _key(text):
    return ' '.join(unicodedata.normalize('NFKC', text).casefold().split())

# Anchored and case sensitive: body references "artículo" are not headings.
_HEADER = re.compile(r'^[ \t]*(?:Artículo|Articulo|ARTÍCULO|ARTICULO)[ \t]+([1-9][0-9]{0,2})[ \t]*[.][ \t]+([^\n]+?)\s*$')
_CHAPTER = re.compile(r'^[ \t]*CAP[IÍ]TULO[ \t]+([IVXLCDM]+|[0-9]+)[ \t]*$', re.I)
_BARRIER = re.compile(r'^[ \t]*(?:DISPOSICIONES\b|ANEXO\b|ÍNDICE\b|INDICE\b|Artículo[ \t]+(?:Primero|Segundo|Tercero|Cuarto|Quinto|Sexto|S[eé]p?timo|Octavo|Noveno|D[eé]cimo)\b)', re.I)
_ANCILLARY = re.compile(r'(?im)^\s*\d+\s+(?:Artículo|Párrafo|Literal|Numeral)\b|Los Laureles|Telf\.')

_ORDINAL_WORDS = r'Primer[oa]|Segund[oa]|Tercer[oa]|Cuart[oa]|Quint[oa]|Sext[oa]|S[eé]p?tim[oa]|Octav[oa]|Noven[oa]|D[eé]cim[oa]'
_ORDINAL_ARTICLE = re.compile(r'^[ \t]*Artículo[ \t]+('+_ORDINAL_WORDS+r')[ \t]*[.][ \t]*[-–—][ \t]*(.*)$')
_ORDINAL_LABEL = re.compile(r'^[ \t]*('+_ORDINAL_WORDS+r')[ \t]*[.]?[ \t]*[-–—][ \t]*(.*)$')
_SECTION = re.compile(r'DISPOSICION(?:ES)?(?: COMPLEMENTARIA(?:S)?)? (FINAL(?:ES)?|TRANSITORIA(?:S)?|DEROGATORIA(?:S)?)(?: Y (?:FINALES|TRANSITORIAS|DEROGATORIAS))?')

def _section(line):
    # Uppercase complete heading, accented singular or plural. Body sentence is not a boundary.
    if line!=line.upper():return None
    plain=''.join(c for c in unicodedata.normalize('NFD',line) if not unicodedata.combining(c))
    return plain if _SECTION.fullmatch(plain) else None


def _validate(bundle):
    b=deepcopy(bundle)
    raw=b.get('rawtext')
    if b.get('layer')!='raw_pages' or not isinstance(raw,str) or hashlib.sha256(raw.encode()).hexdigest()!=b.get('rawtext_sha256'):
        raise ValueError('STRUCTURE_RAW_INTEGRITY')
    for k in ('sha256','config_hash','rawtext_sha256'):
        if not isinstance(b.get(k),str) or not re.fullmatch('[0-9a-f]{64}',b[k]):raise ValueError('STRUCTURE_HASH_INVALID')
    if not b.get('extractor') or not isinstance(b.get('pages'),list) or not b['pages']:raise ValueError('STRUCTURE_PAGE_MAP_REQUIRED')
    previous=-1
    for i,p in enumerate(b['pages'],1):
        if (type(p.get('page')) is not int or p['page']!=i
            or type(p.get('start')) is not int or type(p.get('end')) is not int
            or not 0<=p['start']<=p['end']<=len(raw)
            or (p['start']!=0 if i==1 else p['start']!=previous+1)
            or (i>1 and raw[previous:p['start']]!='\n')):raise ValueError('STRUCTURE_PAGE_MAP_INVALID')
        previous=p['end']
    if previous!=len(raw):raise ValueError('STRUCTURE_PAGE_MAP_INVALID')
    source=None; parent_pages=set(); parent_ids=set()
    for p in b.get('provisions',[]):
        if not validate_contract('Provision',p)['valid']:raise ValueError('STRUCTURE_PROVISION_INVALID')
        identity=(p['document_id'],p['version_id'],p['source_kind'],p['synthetic'])
        if source is None:source=identity
        if identity!=source or p['version_id']!=b['sha256'] or p['text']!=raw[p['start']:p['end']]:raise ValueError('STRUCTURE_SOURCE_MISMATCH')
        if p['page']>len(b['pages']) or p['page'] in parent_pages or p['citation_id'] in parent_ids:raise ValueError('STRUCTURE_PARENT_DUPLICATE_OR_RANGE')
        parent_pages.add(p['page']);parent_ids.add(p['citation_id'])
        page=b['pages'][p['page']-1]
        if p['start']!=page['start'] or p['end']!=page['end']:raise ValueError('STRUCTURE_PARENT_PAGE_MISMATCH')
    if source is None or source[2]!='normative':raise ValueError('STRUCTURE_NORMATIVE_PARENT_REQUIRED')
    required={p['page'] for p in b['pages'] if raw[p['start']:p['end']].strip()}
    if parent_pages!=required:raise ValueError('STRUCTURE_PARENT_CLOSURE_INCOMPLETE')
    return b,source


def structuralize(raw_bundle):
    """Return a new compare-compatible bundle plus structure sidecar.

    `Provision.page` is the first physical page. `structure.spans[id].pages`
    carries every intersecting page; never imply a crossing citation is one page.
    Unhandled headings/sections, duplicate keys, index/annex/quoted contexts are
    boundaries or excluded candidates. Completeness is always partial.
    """
    b,source=_validate(raw_bundle);raw=b['rawtext']
    parent_hash=_hash(b)
    config={'algorithm':VERSION,'parent_bundle_sha256':parent_hash,'normalization':'none',
            'alignment_key':'unique context+number+title; heuristic textual correspondence'}
    config_hash=_hash(config)
    nodes=[];rejected=[];chapter='document';section=None;blocked=False;quoted=False;offset=0
    for line in raw.splitlines(keepends=True):
        stripped=line.strip();m=_HEADER.match(line);chapter_match=_CHAPTER.match(line)
        barrier=_BARRIER.match(line)
        # Exception requires both a syntactically unfinished preceding sentence
        # and a supported reference phrase. Other annex candidates stay bounded.
        if re.match(r'^ANEXO\b',stripped,re.I):
            previous=raw[:offset].rstrip().splitlines()
            continuation=bool(previous and re.search(r'\ben[ \t]+el$',previous[-1],re.I))
            reference=bool(re.fullmatch(r'Anexo[ \t]+(?:N[°ºo.]?[ \t]*)?(?:[0-9]+(?:[-–—][A-Z])?|[A-Z]+)[ \t]+del[ \t]+Reglamento[.,][^\n]*',stripped,re.I))
            barrier=not (continuation and reference)
            if barrier and not quoted:
                rejected.append({'start':offset,'reason':'annex_heading_or_ambiguous_region'})
        section_heading=_section(stripped)
        ordinal=_ORDINAL_ARTICLE.match(line.rstrip('\r\n'))
        label=_ORDINAL_LABEL.match(line.rstrip('\r\n'))
        if stripped.casefold().startswith(('disposiciones','disposición')):barrier=section_heading
        bare=re.match(r'^[ \t]*([1-9][0-9]{0,2})[.] +[A-ZÁÉÍÓÚÑ][^\n]+$',line.rstrip('\r\n'))
        bare_boundary=bool(bare and re.match(r'\s*'+bare[1]+r'[.]1\s',raw[offset+len(line):]))
        if stripped=='RESUELVE:' and not quoted:
            blocked=False;chapter='document';section=None;nodes.append({'start':offset,'kind':'boundary'})
        elif section_heading and not quoted:
            section=section_heading;chapter='section:'+_key(section)
            nodes.append({'start':offset,'kind':'boundary'})
        elif ordinal and quoted:
            rejected.append({'start':offset,'reason':'ordinal_in_unclosed_quote'})
            nodes.append({'start':offset,'kind':'boundary'})
        elif (ordinal or (label and section)) and not quoted and not blocked:
            match=ordinal or label;word=match[1];kind='resolution_article' if ordinal else ('final_provision' if 'FINAL' in section else 'section_provision')
            if ordinal:section=None;chapter='resolution'
            context='resolution' if ordinal else 'section:'+_key(section)
            nodes.append({'start':offset,'kind':'heading','number':word,'title':word,
                          'key':context+'|'+_key(word),'context':context,'unit_kind':kind})
        elif chapter_match and not quoted:
            section=None;chapter='chapter:'+chapter_match[1].upper()
            nodes.append({'start':offset,'kind':'boundary'})
        elif barrier and not quoted:
            # A chapter is also valid inside a TOC/annex; only explicit RESUELVE exits.
            if re.match(r'^(?:ANEXO|ÍNDICE|INDICE)\b',stripped,re.I):blocked=True
            nodes.append({'start':offset,'kind':'boundary'})
        elif bare_boundary and not quoted and not blocked:
            rejected.append({'start':offset,'reason':'numbered_heading_without_article_prefix'})
            nodes.append({'start':offset,'kind':'boundary'})
        elif m:
            title=m[2].strip()
            reason=None
            if blocked:reason='index_or_annex_region'
            elif chapter=='resolution':reason='embedded_numeric_without_explicit_section'
            elif quoted or stripped.startswith(('“','"','«')):reason='quoted_context'
            elif re.search(r'\.{2,}|\t|\||\s\d+\s*$',title):reason='index_or_table_shape'
            elif len(title)>180 or not re.search('[A-Za-zÁÉÍÓÚÑáéíóúñ]',title):reason='unverified_title'
            if reason:
                rejected.append({'start':offset,'reason':reason});nodes.append({'start':offset,'kind':'boundary'})
            else:
                nodes.append({'start':offset,'kind':'heading','number':m[1],'title':title,
                              'key':chapter+'|'+m[1]+'|'+_key(title),'context':chapter,'unit_kind':'numbered_article'})
        # Handle multi-line quotations conservatively; balanced quotes do not leak.
        for char in line:
            if char in '“«':quoted=True
            elif char in '”»':quoted=False
            elif char=='"':quoted=not quoted
        offset+=len(line)
    counts=Counter(n['key'] for n in nodes if n['kind']=='heading')
    spans={};provisions=[];limits=set(b.get('quality',{}).get('limitations',[]))
    limits.update(['automatic_boundaries_unreviewed','structural_coverage_partial','ancillary_text_retained'])
    if any(n>1 for n in counts.values()):limits.add('ambiguous_duplicate_headers')
    for index,node in enumerate(nodes):
        if node['kind']!='heading':continue
        if counts[node['key']]!=1:
            rejected.append({'start':node['start'],'reason':'duplicate_header_key'});continue
        start=node['start'];end=nodes[index+1]['start'] if index+1<len(nodes) else len(raw)
        pages=[p['page'] for p in b['pages'] if p['start']<end and p['end']>start]
        if not pages:continue
        pid=('article-' if node['unit_kind']=='numbered_article' else node['unit_kind']+'-')+node['number']+'-'+_hash(node['key'])[:16]
        cid=_hash([source,parent_hash,VERSION,config_hash,pid,start,end])
        q=dict(citation_id=cid,provision_id=pid,document_id=source[0],version_id=source[1],page=pages[0],start=start,end=end,text=raw[start:end],source_kind=source[2],synthetic=source[3])
        if not validate_contract('Provision',q)['valid']:raise ValueError('STRUCTURE_OUTPUT_INVALID')
        provisions.append(q)
        spans[pid]={k:node[k] for k in ('number','title','key','context','unit_kind')}
        spans[pid].update(pages=pages,ancillary_markers=bool(_ANCILLARY.search(q['text'])),
                          parent_citation_ids=[p['citation_id'] for p in b['provisions'] if p['start']<end and p['end']>start])
    excluded=[];cursor=0
    for start,end in [(p['start'],p['end']) for p in provisions]+[(len(raw),len(raw))]:
        if cursor<start:
            reasons=sorted({r['reason'] for r in rejected if cursor<=r['start']<start})
            excluded.append({'start':cursor,'end':start,'text':raw[cursor:start],
                'pages':[p['page'] for p in b['pages'] if p['start']<start and p['end']>cursor],
                'reason':reasons or ['available_unsegmented_text'],
                'citation_id':_hash([source,parent_hash,VERSION,config_hash,'excluded',cursor,start]),
                'document_id':source[0],'version_id':source[1]})
        cursor=end
    if not provisions:limits.add('no_verified_provisions')
    b.update(layer='structural_provisions',extractor=VERSION,config_hash=config_hash,provisions=provisions,
             quality={'status':'partial','limitations':sorted(limits)},
             structure={'version':VERSION,'parent_bundle_sha256':parent_hash,'config':config,'spans':spans,
                        'rejected_candidates':rejected,'excluded_ranges':excluded,
                        'referenced_annex_availability':'unverified; excluded local text is available, external references are not proof of capture',
                        'covered_characters':sum(p['end']-p['start'] for p in provisions),
                        'raw_characters':len(raw),'coverage_basis':'literal spans, not legal completeness',
                        'embedding_text':None,'response_expansion':None,'strategy':'span-limpio-contexto-v1 adapted; SBS validation pending'})
    return b


def structural_alignments(before,after):
    """Caller-generated heuristic correspondences for compare(alignments=...).

    Same number alone is insufficient. Changed heading/renumbering stays pending.
    Exact key correspondence is not a verified legal alignment or materiality.
    """
    identities=[]
    for b in (before,after):
        ids={p['document_id'] for p in b['provisions']}
        if len(ids)!=1:raise ValueError('STRUCTURE_ALIGNMENT_IDENTITY_REQUIRED')
        identities.append(ids)
    if identities[0]!=identities[1]:raise ValueError('STRUCTURE_ALIGNMENT_IDENTITY_MISMATCH')
    if before['sha256']==after['sha256']:return []
    for b in (before,after):
        if b.get('structure',{}).get('version')!=VERSION:raise ValueError('STRUCTURE_VERSION_MISMATCH')
    def keys(b):
        return {v['key']:k for k,v in b['structure']['spans'].items()}
    left,right=keys(before),keys(after)
    return [{'before':[left[k]],'after':[right[k]]} for k in sorted(left.keys() & right.keys())]
