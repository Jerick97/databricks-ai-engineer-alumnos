"""Lossless exact citation deduplication. Memory/question never rewritten."""
from copy import deepcopy
import hashlib,json

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def compact_input(data):
    out=deepcopy(data);pack=data['evidence'];citations={}
    for c in pack['citations']:
        key=c['citation_id']
        if key in citations and citations[key]!=c:raise ValueError('conflicting_citation_id')
        citations[key]=c
    refs=[]
    def replace(value,path):
        kind=cid=None
        if isinstance(value,dict) and value==pack:kind='evidence';cid=pack['evidence_id']
        else:
            for key,c in citations.items():
                if isinstance(value,dict) and value==c:kind='citation';cid=key;break
                if isinstance(value,str) and len(value)>=80 and value==c.get('text'):kind='citation_text';cid=key;break
        if kind:
            marker={'reference_kind':kind,'reference_id':cid,'sha256':digest(value)}
            refs.append({'path':path,'marker':marker});return marker
        if isinstance(value,dict):return {k:replace(v,path+[k]) for k,v in value.items()}
        if isinstance(value,list):return [replace(v,path+[n]) for n,v in enumerate(value)]
        return value
    out['tool_results']=replace(data['tool_results'],[])
    out['compaction']={'version':'exact-citation-refs-v1','original_tool_results_sha256':digest(data['tool_results']),'references':refs,'replacement_count':len(refs),'policy':'References resolve only to unchanged current evidence/citation text. No span, substring, whitespace or ranking alteration.'}
    if expand_input(out)!=data:raise ValueError('compaction_roundtrip_failed')
    return out

def expand_input(data):
    out=deepcopy(data);meta=out.pop('compaction');pack=out['evidence'];citations={c['citation_id']:c for c in pack['citations']}
    for ref in meta['references']:
        marker=ref['marker'];kind=marker['reference_kind'];cid=marker['reference_id']
        if kind=='evidence':
            if cid!=pack['evidence_id']:raise ValueError('reference_id_changed')
            value=pack
        elif kind=='citation':value=citations[cid]
        elif kind=='citation_text':value=citations[cid]['text']
        else:raise ValueError('unknown_reference')
        if digest(value)!=marker['sha256']:raise ValueError('reference_content_changed')
        parent=out['tool_results'];path=ref['path']
        if not path:
            if parent!=marker:raise ValueError('reference_marker_changed')
            out['tool_results']=deepcopy(value)
        else:
            for part in path[:-1]:parent=parent[part]
            if parent[path[-1]]!=marker:raise ValueError('reference_marker_changed')
            parent[path[-1]]=deepcopy(value)
    if digest(out['tool_results'])!=meta['original_tool_results_sha256']:raise ValueError('expanded_hash_mismatch')
    return out
