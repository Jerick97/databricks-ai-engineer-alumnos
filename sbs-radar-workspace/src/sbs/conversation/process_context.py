"""Pinned illustrative process context; no normative evidence or approval."""
from pathlib import Path
import json,hashlib

def process_context(root,family,config_path='config/fictitious-processes-075.json'):
    root=Path(root).resolve();config=json.loads((root/config_path).read_bytes());path=(root/config['path']).resolve()
    if not path.is_relative_to(root):raise ValueError('process_path_invalid')
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=config['sha256']:raise ValueError('process_bank_changed')
    selected=[]
    for line in raw.decode().splitlines():
        row=json.loads(line)
        if row['family']!=family:continue
        p=json.loads(row['payload_json'])
        if row.get('synthetic') is not True or row.get('human_approved') is not False or p.get('synthetic') is not True or p.get('family')!=family or p.get('source_kind')!='fictitious_process' or p.get('approval')!='none':raise ValueError('process_not_fictitious')
        selected.append({k:p[k] for k in ('process_id','family','name','synthetic','source_kind','approval')})
    return {'trust':'untrusted_fictitious_context_not_normative_evidence','processes':selected,'source_sha256':config['sha256'],'policy':'Illustration only; no real institutional process or approval. New sub-processes must be explicitly hypothetical examples.'}
