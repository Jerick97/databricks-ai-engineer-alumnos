"""041: offline plan and explicit, journaled embedding execution. Never promotion.

Authorization is a trusted local operator artifact, not a credential or evidence
of approval merely because a file exists. CLI preflight never constructs an SDK
client. Fixtures exercise execution logic only; they cannot certify real vectors.
"""
from pathlib import Path
import argparse
import fcntl
import hashlib
import json
import os
import math
import time
from urllib.parse import urlsplit

from sbs.models import ModelManifest, validate_embeddings
from sbs.models.databricks import DatabricksEmbeddingAdapter, PinnedQwenTokenizer, SingleShotTransport, ENDPOINT
from sbs.operations.preparers import VerifiedEmbeddingCache
from sbs.paths import resolve_model_manifest

VERSION='embedding-execution-041-v1'
DATASET='data/retrieval/structural-development-026'

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()

def digest(value):
    return hashlib.sha256(value if isinstance(value,bytes) else canonical(value)).hexdigest()

def seal(value):return {'payload':value,'sha256':digest(value)}

def unseal(path):
    d=json.loads(path.read_bytes())
    if set(d)!= {'payload','sha256'} or digest(d['payload'])!=d['sha256']:raise ValueError('RECEIPT_HASH')
    return d['payload']

def local(root,name):
    p=Path(name)
    if p.is_absolute() or '..' in p.parts:raise ValueError('PATH_SCOPE')
    p=root/p
    if not p.resolve().is_relative_to(root) or any(x.is_symlink() for x in [p,*p.parents] if x.is_relative_to(root)):raise ValueError('PATH_SCOPE')
    return p

def syncdir(path):
    fd=os.open(path,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)

def append(path,value):
    raw=canonical(seal(value))
    with path.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    syncdir(path.parent)

def load_local(root):
    root=Path(root).resolve()
    m=json.loads(local(root,'config/pilot-model-bundle.json').read_bytes())
    manifest=ModelManifest.from_bundle(m['bundle'])
    if manifest.bundle_hash!=m['bundle_hash']:raise ValueError('MODEL_HASH')
    pin=json.loads(local(root,'runs/sk05-qwen-tokenizer.json').read_bytes())
    pin=resolve_model_manifest(pin,root=root);f=pin['files']['tokenizer.json']
    tok=PinnedQwenTokenizer(f['path'],revision=pin['revision'],sha256=f['sha256'])
    return manifest,tok

def prepare_plan(root,*,host,output='runs/sk04-embeddings-041-vectors'):
    root=Path(root).resolve();out=local(root,output)
    if out==root or not out.is_relative_to(root/'runs'):raise ValueError('OUTPUT_SCOPE')
    u=urlsplit(host)
    if u.scheme!='https' or not u.hostname or u.path or u.query or u.fragment or u.username or u.password:raise ValueError('HOST')
    closure={}
    def read(name):
        raw=local(root,name).read_bytes();closure[name]=digest(raw);return json.loads(raw)
    artifacts=read(DATASET+'/artifacts.json')
    for name,info in artifacts.items():
        raw=local(root,DATASET+'/'+name).read_bytes()
        if digest(raw)!=info['sha256'] or len(raw)!=info['bytes']:raise ValueError('DATASET_DRIFT')
        closure[DATASET+'/'+name]=digest(raw)
    summary=read(DATASET+'/manifest.json');rows=read(DATASET+'/embedding_inputs.json');passages=read(DATASET+'/passages.json')
    model=read('config/pilot-model-bundle.json');read('runs/sk05-qwen-tokenizer.json')
    manifest,tok=load_local(root);cache=VerifiedEmbeddingCache.from_project(root)
    if cache.identity!=manifest.bundle_hash or summary['model_identity']!=manifest.bundle_hash:raise ValueError('MODEL_IDENTITY')
    adapter=DatabricksEmbeddingAdapter(manifest,tok,transport=lambda _: (_ for _ in ()).throw(AssertionError('OFFLINE')),max_calls=29,max_tokens=108126)
    expected=read('runs/sk05-embedding-smoke-003.json')['model_configuration'];expected={k:v for k,v in expected.items() if k!='observed_at'}
    if summary['candidate_corpus_hash']!=digest(passages) or len(rows)!=len(passages):raise ValueError('CORPUS_HASH')
    pmap={p['passage_id']:p for p in passages};seen=set();items=[]
    for row in rows:
        pid=row['passage_id']
        if pid in seen or pid not in pmap:raise ValueError('INPUT_ID')
        seen.add(pid);p=pmap[pid];raw=local(root,p['rawtext_path']).read_bytes();closure[p['rawtext_path']]=digest(raw)
        if digest(raw)!=p['rawtext_sha256']:raise ValueError('RAW_HASH')
        text=''.join(row['input_parts'])
        if (row['truncated'] is not False or row['model_identity']!=manifest.bundle_hash or
            row['input_parts']!=['',p['quote']] or row['embedding_start']!=p['start'] or
            row['embedding_text']!=p['quote'] or raw.decode()[p['start']:p['end']]!=p['quote'] or
            digest(text.encode())!=row['input_sha256'] or digest([manifest.bundle_hash,row['input_parts']])!=row['model_parts_sha256']):raise ValueError('INPUT_LITERAL_OR_IDENTITY')
        if cache.lookup(row['input_parts'],manifest.bundle_hash) is not None:raise ValueError('EXPECTED_MISS_CHANGED')
        counted=adapter.preflight([text])
        if counted['local_input_tokens']!=row['budget']['input_tokens'] or row['budget']['status']!='ready':raise ValueError('TOKEN_COUNT_DRIFT')
        items.append({'passage_id':pid,'text':text,'input_parts':row['input_parts'],'input_sha256':row['input_sha256'],'tokens':counted['local_input_tokens']})
    batches=[]
    for start in range(0,len(items),8):
        chunk=items[start:start+8];pf=adapter.preflight([r['text'] for r in chunk]);batches.append({'index':len(batches),'items':chunk,'reserved_tokens':pf['reserved_tokens']})
    if len(items)!=231 or sum(x['tokens'] for x in items)!=106278:raise ValueError('FROZEN_026_COUNTS')
    return {'version':VERSION,'dataset':DATASET,'closure':closure,'candidate_corpus_hash':summary['candidate_corpus_hash'],
            'model_identity':manifest.bundle_hash,'dimension':manifest.bundle['dimension'],'expected_response_model':manifest.bundle['parameters']['expected_response_model'],
            'host':host,'profile':'databricks-ai-engineer-aws','output':output,'requests':len(batches),'inputs':len(items),
            'local_input_tokens':106278,'reserved_tokens':sum(b['reserved_tokens'] for b in batches),'max_batch':8,'batches':batches,
            'endpoint':ENDPOINT,'endpoint_observation_expected':expected,'endpoint_gets_max_per_execution':1,'endpoint_gets_max_per_run':3,
            'cost':None,'remote_weights_hash':None,'strategy':summary['candidate_strategy'],
            'limitations':['Execution bundle identity reused; structural corpus hash is separate, no index/promotion','Reservation is local estimate, not billing cap; stop after observed excess','Batch8 reused from real001, not universal server maximum','No query or generation inference','Authority artifact must be supplied by trusted operator after explicit approval']}

def check_authority(plan,auth,clock):
    if not isinstance(auth,dict) or auth.get('approved') is not True or auth.get('plan_sha256')!=digest(plan):raise ValueError('AUTHORITY_REQUIRED')
    for key in ('requests','inputs','reserved_tokens'):
        if type(auth.get(key)) is not int or auth[key]!=plan[key]:raise ValueError('AUTHORITY_CAP')
    if type(auth.get('expires_at')) not in (int,float) or not math.isfinite(auth['expires_at']) or not 0<clock()<auth['expires_at']:raise ValueError('AUTHORITY_EXPIRED')

def batch_items(batch):
    # The production plan uses item lists; tests may construct singleton batches.
    return batch.get('items',[batch])

def validate_plan(plan):
    if any(type(plan[k]) is not int or plan[k]<=0 for k in ('requests','inputs','local_input_tokens','reserved_tokens','dimension')):raise ValueError('PLAN_QUOTA')
    bs=plan['batches'];rows=[r for b in bs for r in batch_items(b)]
    if plan['version']!=VERSION or not bs or [b['index'] for b in bs]!=list(range(len(bs))):raise ValueError('PLAN_SCHEMA')
    if any(len(batch_items(b))>8 or not batch_items(b) or b['reserved_tokens']!=sum(r['tokens']+8 for r in batch_items(b)) for b in bs):raise ValueError('PLAN_BATCH')
    if len({r['passage_id'] for r in rows})!=len(rows) or any(type(r['tokens']) is not int or r['tokens']<0 or r['tokens']+8>32768 or digest(r['text'].encode())!=r['input_sha256'] for r in rows):raise ValueError('PLAN_INPUT')
    if (plan['requests'],plan['inputs'],plan['local_input_tokens'],plan['reserved_tokens'])!=(len(bs),len(rows),sum(r['tokens'] for r in rows),sum(b['reserved_tokens'] for b in bs)):raise ValueError('PLAN_TOTALS')

def execute(root,plan,authorization,*,adapter_factory,clock=time.time,execution_mode="fixture"):
    """Factory is trusted server capability. Production CLI uses real_factory.

    Persistent attempts, not adapter counters, are authoritative across resumes.
    All historical receipts are checked before any new remote factory call.
    """
    if execution_mode not in ("fixture","real"):raise ValueError("EXECUTION_MODE")
    root=Path(root).resolve();validate_plan(plan);check_authority(plan,authorization,clock)
    for path,expected in plan.get('closure',{}).items():
        if digest(local(root,path).read_bytes())!=expected:raise ValueError('INPUT_DRIFT')
    out=local(root,plan['output']);out.mkdir(parents=True,exist_ok=True);syncdir(out.parent)
    if any(p.is_symlink() for p in out.rglob('*')):raise ValueError('OUTPUT_SYMLINK')
    with (out/'lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        meta={'plan_sha256':digest(plan),'mode':execution_mode}
        run=out/'run.json'
        if run.exists():
            if unseal(run)!=meta:raise ValueError('RUN_PLAN_MISMATCH')
        else:append(run,meta)
        pending=[];vectors=[]
        for b in plan['batches']:
            intent=out/f"intent-{b['index']:04}.json";result=out/f"result-{b['index']:04}.json"
            expectation={'plan_sha256':digest(plan),'batch_sha256':digest(b),'reserved_tokens':b['reserved_tokens']}
            if intent.exists():
                if pending:raise ValueError('JOURNAL_NONPREFIX')
                if unseal(intent)!=expectation:raise ValueError('INTENT_MISMATCH')
                if not result.exists():raise ValueError('UNRESOLVED_ATTEMPT')
                payload=unseal(result)
                if payload['intent']!=expectation or payload['status']!='validated':raise ValueError('UNRESOLVED_ATTEMPT')
                r=payload['result'];_validate_result(plan,b,r)
                if r.get('server_usage_exceeds_reserve') is not False:raise ValueError('SERVER_USAGE_EXCEEDED')
                vectors.extend(r['embeddings'])
            elif result.exists():raise ValueError('RESULT_WITHOUT_INTENT')
            else:pending.append(b)
        adapter=None
        for b in pending:
            check_authority(plan,authorization,clock)
            if adapter is None:adapter=adapter_factory()
            if adapter.identity!=plan['model_identity'] or adapter.dimension!=plan['dimension']:raise ValueError('ADAPTER_IDENTITY')
            check_authority(plan,authorization,clock)
            intention={'plan_sha256':digest(plan),'batch_sha256':digest(b),'reserved_tokens':b['reserved_tokens']}
            append(out/f"intent-{b['index']:04}.json",intention)
            result_path=out/f"result-{b['index']:04}.json"
            try:
                check_authority(plan,authorization,clock)
                r=adapter.embed([r['text'] for r in batch_items(b)],role='document');_validate_result(plan,b,r)
            except Exception:
                append(result_path,{'intent':intention,'status':'failed_or_ambiguous','error':'ATTEMPT_FAILED','diagnostics':safe_diagnostics(adapter,plan)})
                raise ValueError('ATTEMPT_FAILED') from None
            append(result_path,{'intent':intention,'status':'validated','result':r})
            if r.get('server_usage_exceeds_reserve') is not False:raise ValueError('SERVER_USAGE_EXCEEDED')
            vectors.extend(r['embeddings'])
        complete={'mode':execution_mode,'plan_sha256':digest(plan),'model_identity':plan['model_identity'],'candidate_corpus_hash':plan.get('candidate_corpus_hash'),'passage_ids':[r['passage_id'] for b in plan['batches'] for r in batch_items(b)],'vectors':vectors,'dimension':plan['dimension'],'index_promoted':False}
        path=out/'vectors.json'
        if path.exists():
            if unseal(path)!=complete:raise ValueError('FINAL_DRIFT')
        else:append(path,complete)
        return {'status':'completed','vectors':len(vectors),'path':str(path.relative_to(root)),'sha256':digest(path.read_bytes()),'cost':None}

def safe_diagnostics(adapter,plan):
    """Closed typed subset; never persist exceptions, headers or unknown strings."""
    from sbs.models.databricks import EmbeddingServiceError
    try:d=adapter.last_attempt
    except Exception:return {}
    if type(d) is not dict:return {}
    out={}
    stages={'transport','response_envelope','response_model','response_count',
            'response_indices','response_vectors','validated'}
    if type(d.get('stage')) is str and d['stage'] in stages:out['stage']=d['stage']
    status=d.get('http_status')
    if type(status) is int and 100<=status<=599:out['http_status']=status
    code=d.get('error_code')
    if type(code) is str:
        normalized=EmbeddingServiceError(code,out.get('http_status')).error_code
        # Constructor normalizes unknown strings; never save the unknown value.
        out['error_code']=normalized
    for key in ('calls_attempted','reserved_tokens','response_count'):
        value=d.get(key)
        if type(value) is int and 0<=value<=2**63-1:out[key]=value
    for key in ('expected_response_model','response_model'):
        if type(d.get(key)) is str and d[key]==plan['expected_response_model']:out[key]=d[key]
        elif key in d:out[key]=None  # Unknown response names are not copied.
    if d.get('endpoint')==ENDPOINT:out['endpoint']=ENDPOINT
    if type(d.get('usage')) is dict:
        out['usage']={k:v for k,v in d['usage'].items() if k in ('prompt_tokens','total_tokens') and type(v) is int and 0<=v<=2**63-1}
    value=d.get('latency_seconds')
    if type(value) in (int,float) and math.isfinite(value) and 0<=value<=86400:out['latency_seconds']=value
    for key in ('response_dimensions','response_indices'):
        value=d.get(key)
        if type(value) is list and len(value)<=8 and all(v is None or type(v) is int and 0<=v<=2**31-1 for v in value):out[key]=value
    return out

def _validate_result(plan,batch,result):
    if result.get('model')!=plan['expected_response_model']:raise ValueError('RESPONSE_MODEL')
    validate_embeddings(result['embeddings'],expected_count=len(batch_items(batch)),dimension=plan['dimension'],expected_identity=plan['model_identity'],actual_identity=result['bundle_hash'])

def production_factory(root,plan,auth,*,clock=time.time):
    """Lazy factory; no SDK/config/auth work until called by execute after gates."""
    def real_factory():
        check_authority(plan,auth,clock)
        from databricks.sdk import WorkspaceClient
        from types import SimpleNamespace
        import requests
        client=WorkspaceClient(profile=plan['profile'])
        if client.config.host.rstrip('/')!=plan['host']:raise ValueError('WORKSPACE_HOST_MISMATCH')
        class GatedConfig:
            host=plan['host']
            def authenticate(self):
                check_authority(plan,auth,clock)
                headers=client.config.authenticate()
                # Called by SingleShotTransport immediately before session.post.
                check_authority(plan,auth,clock)
                return headers
        config=GatedConfig()
        # One bounded GET, no SDK retry policy; observe comparable fields, not
        # unrelated historical config hash encodings or remote weight hashes.
        out=local(Path(root).resolve(),plan['output'])
        n=len(list(out.glob('metadata-intent-*.json')))
        if n>=plan['endpoint_gets_max_per_run']:raise ValueError('METADATA_GET_CAP')
        append(out/f'metadata-intent-{n:04}.json',{'plan_sha256':digest(plan),'attempt':n})
        with requests.Session() as session:
            headers=config.authenticate()
            with session.get(plan['host']+'/api/2.0/serving-endpoints/'+ENDPOINT,headers=headers,timeout=45,allow_redirects=False,stream=True) as response:
                if response.status_code!=200:raise ValueError('ENDPOINT_METADATA_UNAVAILABLE')
                raw=bytearray()
                for chunk in response.iter_content(65536):
                    raw.extend(chunk)
                    if len(raw)>1048576:raise ValueError('ENDPOINT_METADATA_CAP')
                ep=json.loads(raw)
        observed={'endpoint':ENDPOINT,'task':ep.get('task'),'config_version':ep.get('config',{}).get('config_version'),'models':[{'foundation_model_name':x.get('foundation_model',{}).get('name'),'entity_name':x.get('entity_name'),'entity_version':x.get('entity_version')} for x in ep.get('config',{}).get('served_entities',[])]}
        out=local(Path(root).resolve(),plan['output'])
        append(out/f'endpoint-{n:04}.json',{'observed':observed,'matches_prior_fields':observed==plan['endpoint_observation_expected'],'remote_weights_hash':None})
        if observed!=plan['endpoint_observation_expected']:raise ValueError('ENDPOINT_FIELDS_CHANGED')
        manifest,tok=load_local(root)
        return DatabricksEmbeddingAdapter(manifest,tok,transport=SingleShotTransport(SimpleNamespace(config=config)),max_calls=plan['requests'],max_tokens=plan['reserved_tokens'])
    return real_factory

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['preflight','execute'])
    parser.add_argument('--root',type=Path,default=Path.cwd())
    parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--host',default='https://dbc-0410b264-20c7.cloud.databricks.com')
    parser.add_argument('--output',default='runs/sk04-embeddings-041-vectors')
    parser.add_argument('--authorization',type=Path)
    args=parser.parse_args();root=args.root.resolve()
    if args.action=='preflight':
        plan=prepare_plan(root,host=args.host,output=args.output)
        append(args.plan,plan)
        print(json.dumps({'status':'offline_preflight','plan_sha256':digest(plan),'requests':plan['requests'],'inputs':plan['inputs'],'local_input_tokens':plan['local_input_tokens'],'reserved_tokens':plan['reserved_tokens'],'cost':None}))
    else:
        plan=unseal(args.plan)
        if not args.authorization:raise ValueError('AUTHORITY_REQUIRED')
        auth=json.loads(args.authorization.read_bytes());check_authority(plan,auth,time.time)
        if prepare_plan(root,host=plan['host'],output=plan['output'])!=plan:raise ValueError('PLAN_DRIFT')
        print(json.dumps(execute(root,plan,auth,adapter_factory=production_factory(root,plan,auth),execution_mode='real')))

if __name__=='__main__':
    try:main()
    except Exception as exc:
        # No SDK/HTTP exception messages, headers or arbitrary bodies in logs.
        print(json.dumps({'status':'stopped','error_class':type(exc).__name__,'detail':'Inspect local journal; no automatic retry'}))
        raise SystemExit(1) from None
