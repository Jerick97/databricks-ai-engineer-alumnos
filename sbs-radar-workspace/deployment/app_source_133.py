"""Fresh local source staging, independent of070. No SDK/cloud operations."""
from pathlib import Path
import ast,hashlib,importlib.util,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def encoded(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
def read(root,p):return json.loads((root/p).read_bytes())

def closure(root=ROOT):
    root=Path(root)
    names=set(read(root,'runs/sk06-sk07-sk12-bootstrap-098-dependencies.json')['files_sha256'])
    names|={'app133.py','src/sbs/app133/__init__.py','config/app-integration-133.json','config/generation-selection-110.json','runs/sk05-generation-candidates-109-databricks-qwen35-122b-a10b.json','skills/sbs-conversacion-orquestacion/assets/generator-instructions-115.md'}
    queue=['app133.py'];seen=set()
    def module_path(name):
        p=root/'src'/Path(*name.split('.'))
        return p.with_suffix('.py') if p.with_suffix('.py').is_file() else p/'__init__.py' if (p/'__init__.py').is_file() else None
    while queue:
        name=queue.pop()
        if name in seen:continue
        seen.add(name);path=root/name
        parts=path.relative_to(root/'src').with_suffix('').parts if name.startswith('src/') else ()
        module='.'.join(parts[:-1] if parts and parts[-1]=='__init__' else parts);package=module if path.name=='__init__.py' else module.rpartition('.')[0]
        for node in ast.walk(ast.parse(path.read_bytes())):
            imports=[]
            if isinstance(node,ast.Import):imports=[a.name for a in node.names]
            elif isinstance(node,ast.ImportFrom):
                base=importlib.util.resolve_name('.'*node.level+(node.module or ''),package) if node.level else node.module or ''
                imports=[base]+[base+'.'+a.name for a in node.names]
            for imported in imports:
                if not imported.startswith('sbs'):continue
                for i in range(1,len(imported.split('.'))+1):
                    p=module_path('.'.join(imported.split('.')[:i]))
                    if p:queue.append(p.relative_to(root).as_posix())
    names|=seen
    names.update(p.relative_to(root).as_posix() for p in (root/'contracts').glob('*.json'))
    tested=read(root,'runs/sk03-sk07-sk08-hybrid-125-freeze.json')['files_sha256']
    names.update(p for p in tested if p.startswith(('src/','config/','data/')) or '/assets/' in p)
    names.add('runs/sk06-pilot-002/processes.jsonl')
    names.add('config/app-runtime-133-template.json')
    from sbs.paths import resolve_model_manifest,model_relative_path
    for name in ('runs/sk05-qwen-tokenizer.json','context/reranker-manifest.json'):
        names.add(name);manifest=read(root,name);resolve_model_manifest(manifest,root=root)
        names.update(str(model_relative_path(manifest,n)) for n in manifest['files'])
    if any(Path(p).is_absolute() or '..' in Path(p).parts or p.startswith('deployment/state/') for p in names):raise ValueError('APP133_SOURCE_ESCAPE_OR_STATE')
    if any('fresh_publication_081' in p or 'connector_transport_081' in p for p in names):raise ValueError('APP133_PUBLISHER_DEPENDENCY')
    return sorted(names)

def prepare(destination,root=ROOT):
    root=Path(root).resolve();destination=Path(destination)
    names=closure(root);destination.mkdir(parents=True,exist_ok=False)
    source=destination/'source';source.mkdir();files={}
    for name in names:
        original=root/name
        if original.is_symlink():raise ValueError('APP133_SOURCE_SYMLINK')
        raw=original.read_bytes();target=source/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);files[name]=sha(raw)
    (source/'runs').mkdir(exist_ok=True)
    manifest={'kind':'prepared_source_not_release','entrypoint':'app133.py','files_sha256':files,'source_sha256':sha(encoded(files)),'cloud_executed':False,'linux_target_verified':False,'quality_accepted':False,'contains_historical_state':False}
    (destination/'manifest.json').write_bytes(encoded(manifest))
    for p,h in files.items():
        if sha((source/p).read_bytes())!=h:raise ValueError('APP133_COPY_MISMATCH')
    return manifest

def release_gate(stage,quality_review,technical_review,root=ROOT):
    """All reviews are concrete artifacts; no truthy CLI approval flags."""
    root=Path(root);stage=Path(stage);manifest=read(stage,'manifest.json');files=manifest['files_sha256']
    if sha(encoded(files))!=manifest['source_sha256']:raise ValueError('APP133_MANIFEST_CHANGED')
    for p,h in files.items():
        target=stage/'source'/p
        if Path(p).is_absolute() or '..' in Path(p).parts or target.is_symlink() or sha(target.read_bytes())!=h:raise ValueError('APP133_SOURCE_CHANGED')
    quality=json.loads(Path(quality_review).read_bytes())
    if quality.get('status')!='PASS_CONTROLLED_SAMPLE' or quality.get('demo_sample_accepted') is not True:raise ValueError('APP133_REAL125_QUALITY_REQUIRED')
    expected={f'deployment/state/generation-rag-125/turn-{i}-result.json' for i in range(4)}
    if set(quality.get('responses_sha256',{}))!=expected:raise ValueError('APP133_QUALITY_SCOPE')
    reviewer=quality.get('reviewer',{})
    if reviewer.get('model')!='gpt-6-astra' or reviewer.get('reasoning_effort')!='high':raise ValueError('APP133_ASTRA_REQUIRED')
    for p,h in quality['responses_sha256'].items():
        if sha((root/p).read_bytes())!=h:raise ValueError('APP133_RESPONSE_DRIFT')
    plan=read(root,'deployment/generation-rag-125-plan.json');admission=read(root,'deployment/state/generation-rag-125/admission.json')
    freeze=read(root,'runs/sk03-sk07-sk08-hybrid-125-freeze.json')
    if admission.get('plan_sha256')!=sha((root/'deployment/generation-rag-125-plan.json').read_bytes()) or admission.get('freeze_sha256')!=sha((root/'runs/sk03-sk07-sk08-hybrid-125-freeze.json').read_bytes()):raise ValueError('APP133_TESTED_ADMISSION_CHANGED')
    for p,h in freeze['files_sha256'].items():
        if p.startswith(('src/','config/','data/')) or '/assets/' in p:
            if files.get(p)!=h:raise ValueError('APP133_TESTED_CODE_NOT_STAGED:'+p)
    rows=[read(root,f'deployment/state/generation-rag-125/turn-{i}-result.json') for i in range(4)]
    if any(r['answer']['status'] not in ('answered','answered_partial') for r in rows):raise ValueError('APP133_SAMPLE_NOT_ANSWERED')
    if [r.get('model_generation_requests_this_turn') for r in rows]!=[0,0,0,1] or rows[-1].get('generation_requests')!=1:raise ValueError('APP133_SAMPLE_CALL_ACCOUNTING')
    generation=rows[-1]['generation'].get('generation',{})
    if generation.get('response_model')!='qwen35-122b-a10b' or generation.get('http_status')!=200:raise ValueError('APP133_REAL_PROPOSAL_REQUIRED')
    tech=json.loads(Path(technical_review).read_bytes())
    if tech.get('status')!='PASS_APP_INTEGRATION_133' or tech.get('source_sha256')!=manifest['source_sha256'] or tech.get('linux_target_verified') is not True:raise ValueError('APP133_TECHNICAL_TARGET_REVIEW_REQUIRED')
    config=read(stage/'source','config/app-integration-133.json')
    if config['deadline_unix']<=0:raise ValueError('APP133_DEMO_DEADLINE_REQUIRED')
    return {'status':'release_gate_passed_not_deployed','source_sha256':manifest['source_sha256'],'quality_review_sha256':sha(Path(quality_review).read_bytes()),'technical_review_sha256':sha(Path(technical_review).read_bytes())}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--prepare-source',required=True);a=p.parse_args();print(json.dumps(prepare(a.prepare_source),indent=2))
