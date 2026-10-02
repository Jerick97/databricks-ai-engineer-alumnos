"""Read-only release verification. No provider SDK, network, inference or mutations."""
from pathlib import Path
import hashlib
import json
import sys


def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path): return json.loads(Path(path).read_text())
def canonical(value): return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def unseal(path):
    data=read(path)
    if hashlib.sha256(canonical(data['payload'])).hexdigest()!=data['sha256']:
        raise ValueError('Sealed artifact changed: '+Path(path).name)
    return data['payload']

def local(root,path):
    """Rebase archived project paths without editing historical signed content."""
    root=Path(root).resolve(); original=Path(path)
    if original.is_absolute():
        parts=original.parts
        if 'sbs-genie-e2e' not in parts: raise ValueError('Unrecognized historical root')
        original=Path(*parts[parts.index('sbs-genie-e2e')+1:])
    result=(root/original).resolve()
    if not result.is_relative_to(root): raise ValueError('Path outside release root')
    return result

def verify(root):
    root=Path(root).resolve()
    sys.path.insert(0,str(root/'src'))
    from sbs.models import ModelManifest
    from sbs.retrieval import LocalIndex
    from sbs.evaluation import retrieval_metrics
    from sbs.contracts import validate_contract
    report=read(root/'runs/sk04-real-001-report.json')
    for path,expected in report['artifacts_sha256'].items():
        if digest(local(root,path))!=expected: raise ValueError('Artifact changed: '+path)
    raw={}; families=set(); pdfs=[]
    for capture in ['sk02-repository-capture','sk02-amendments-capture']:
        for source in read(root/'runs'/f'{capture}.json')['sources']:
            metadata=source['source']; families.add(metadata['family'])
            pdf=local(root,source['original_path'])
            if digest(pdf)!=metadata['version_id']: raise ValueError('PDF hash mismatch')
            if metadata.get('synthetic') is not False: raise ValueError('Non-real corpus')
            raw[metadata['version_id']]=local(root,source['rawtext_path']).read_text()
            pdfs.append(pdf.name)
    if families!={'cybersecurity','market_conduct'}: raise ValueError('Both families required')
    records=read(root/'data/retrieval/sk04-real-001/records.json')
    for r in records:
        c=r['citation']
        if raw[c['version_id']][c['start']:c['end']]!=c['text']: raise ValueError('Citation span mismatch')
    bundle=read(root/'config/pilot-model-bundle.json'); manifest=ModelManifest.from_bundle(bundle['bundle'])
    if manifest.bundle_hash!=bundle['bundle_hash'] or manifest.bundle_hash!=report['bundle_hash']: raise ValueError('ModelBundle identity mismatch')
    index_data=unseal(root/'data/retrieval/sk04-real-001/index.json')
    index=LocalIndex(records,index_data['vectors'],dimension=manifest.bundle['dimension'],model_identity=manifest.bundle_hash,actual_identity=manifest.bundle_hash)
    if index.index_hash!=report['index_hash'] or index.index_hash!=index_data['index_hash']: raise ValueError('Index identity mismatch')
    protocol=unseal(root/'runs/sk04-real-001-protocol.json')
    if hashlib.sha256(canonical(protocol)).hexdigest()!=report['protocol_sha256']: raise ValueError('Protocol identity mismatch')
    queries=[]
    for question in protocol['questions']:
        qid=question['query_id']; item=unseal(root/'runs'/f'sk04-real-001-{qid}.json')
        evidence=item['result']['evidence']
        if not validate_contract('EvidencePack',evidence)['valid']: raise ValueError('Invalid EvidencePack')
        for c in evidence['citations']:
            if raw[c['version_id']][c['start']:c['end']]!=c['text']: raise ValueError('Evidence span mismatch')
        for name,key in [('lexical','lexical'),('vector','vector'),('rrf','fusion'),('rrf_rerank','reranked')]:
            computed=retrieval_metrics([r[0] for r in item['result']['trace'][key]],protocol['qrels'][qid],5,protocol['counterparts'][qid])
            if computed!=item['metrics_top5_before_expansion'][name]: raise ValueError('Metric mismatch')
        queries.append({'id':qid,'family':question['family'],'citations':len(evidence['citations']),'metrics_recomputed':True})
    return {'status':'passed_offline_integrity_and_metrics','families':sorted(families),'pdfs':len(pdfs),'records':len(records),'hashed_artifacts':len(report['artifacts_sha256']),'queries':queries,'inference_calls':0,'network_calls':0,'acceptance':'not_evaluated','limitations':['Stored pilot only; no new inference','Hash verification is not a legal truth or human relevance assessment','Cloud, UI, scheduling and disaster recovery need separate evidence']}

def remote_preflight(root):
    """Declarative assessment only: never instantiate a Databricks client."""
    cfg=read(Path(root)/'config/genie-notebook.json')
    return {'mode':'declarative_only','network_calls':0,'resource_actions':0,'ready_for_remote_execution':False,'warehouse_candidate':cfg.get('observed_warehouse'),'warehouse_assigned':cfg.get('warehouse_id'),'catalog_assigned':cfg.get('catalog'),'space_assigned':cfg.get('space_id'),'gates':[{'gate':'budget_new_resources','status':'not_authorized','action':'Approve specific cost ceiling and resource plan before starting or creating resources.'},{'gate':'warehouse_binding','status':'pending','action':'Confirm dedicated authorized warehouse binding; observed STOPPED resource is a candidate, not permission to start it.'},{'gate':'genie_bindings','status':'pending','action':'Bind dedicated catalog/space, server-side grants and independently verified SQL execution context.'},{'gate':'cloud_auth','status':'pending','action':'Install verified identity/authorization adapter; local app refuses cloud mode.'},{'gate':'schedule','status':'not_enabled','action':'08:00 America/Lima and on demand; verify idempotence and cost limits before enabling.'},{'gate':'e2e_acceptance','status':'pending','action':'Verify real browser flows, both families, response evaluations and isolated recovery.'}]}
