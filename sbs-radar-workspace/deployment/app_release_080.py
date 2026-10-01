"""Explicit server selection layered on frozen070 source packaging. Local only."""
from pathlib import Path
import argparse, importlib.util, json
ROOT=Path(__file__).resolve().parents[1]
def module(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'deployment'/f'{name}.py')
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result
base=module('app_release_070')
sha=base.sha
jsonbytes=base.jsonbytes
archive_bytes=base.archive_bytes

def snapshot(root=ROOT, *, generation_selection_path='config/generation-selection-073.json'):
    from sbs.models.app_selection import server_selection
    from sbs.models.generation_selection import load_selection
    root=Path(root)
    selected=server_selection({'SBS_GENERATION_SELECTION':generation_selection_path})
    # A fresh module keeps injection local and never changes the original070 module.
    legacy=module('app_release_070');legacy.module=module
    blobs,manifest,config,observed=legacy.snapshot(root)
    selection=load_selection(root,selected)
    for name in (selected,selection['observation_path'],'app080.py','src/sbs/models/app_selection.py'):
        blobs[name]=(root/name).read_bytes()
    config['command']=['python','app080.py']
    config['env']=[e for e in config['env'] if e['name']!='SBS_GENERATION_SELECTION']
    config['env'].append({'name':'SBS_GENERATION_SELECTION','value':selected})
    blobs['app.yaml']=jsonbytes(config)
    hashes={n:sha(raw) for n,raw in sorted(blobs.items())};identity=sha(jsonbytes(hashes))
    manifest.update(release_id='sbs-app-080-'+identity[:16],snapshot_sha256=identity,files_sha256=hashes,generation_selection_path=selected)
    return blobs,manifest,config,observed

def operation_plan(manifest,config,observed):
    plan=base.operation_plan(manifest,config,observed)
    plan['generation_selection_path']=manifest['generation_selection_path']
    plan['status']='held_controlled_sample_and_deployment_review_required'
    plan['steps'][0]='Require exact PASS_CONTROLLED_SAMPLE evidence bound to selection, tested plan/admission and staged behavior before start/deploy.'
    plan['blockers']['generation']='A smoke or local test is not SBS quality acceptance; require the exact reviewed controlled sample for this selection.'
    plan['acceptance']['generation']='Controlled sample quality review required; independent from final E2E acceptance.'
    return plan

def quality_gate(review_path,manifest):
    deploy=module('app_deploy_080')
    if review_path is None or not Path(review_path).is_file():raise ValueError('GENERATION_SBS_QUALITY_REQUIRED')
    review=deploy.read(review_path)
    if review.get('status')!='PASS_CONTROLLED_SAMPLE' or review.get('demo_sample_accepted') is not True:raise ValueError('GENERATION_SBS_QUALITY_REQUIRED')
    needed=deploy.quality_paths(review)
    if not all(p.is_file() for p in needed):raise ValueError('GENERATION_SBS_QUALITY_REQUIRED')
    deploy.tested_implementation(needed,manifest['files_sha256'],manifest['generation_selection_path'])
    from sbs.models.generation_selection import load_selection
    selection=load_selection(ROOT,manifest['generation_selection_path'])
    for path in needed:
        turn=deploy.read(path);answer=turn.get('answer',{});generation=turn.get('generation',{})
        deploy.require(answer.get('status') in ('answered','answered_partial') and isinstance(answer.get('citations'),list) and bool(answer['citations']) and generation.get('http_status')==200 and generation.get('endpoint')==selection['endpoint'] and generation.get('response_model')==selection['expected_response_model'],'SBS_GENERATION_NOT_ANSWERED')
    deploy.require(review['responses_sha256']=={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in needed},'QUALITY_RESPONSE_PINS_MISMATCH')

def build(output,root=ROOT,*,generation_selection_path='config/generation-selection-073.json',quality_review=None):
    # Missing/failed quality cannot cause even a destination directory to appear.
    if quality_review is None:raise ValueError('GENERATION_SBS_QUALITY_REQUIRED')
    blobs,manifest,config,observed=snapshot(root,generation_selection_path=generation_selection_path)
    quality_gate(quality_review,manifest)
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    source=output/'source';source.mkdir()
    for name,raw in blobs.items():
        path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    raw=archive_bytes(blobs);(output/'source.tar.gz').write_bytes(raw)
    manifest.update(archive_sha256=sha(raw),archive_bytes=len(raw))
    (output/'manifest.json').write_bytes(jsonbytes(manifest))
    (output/'operation-plan.json').write_bytes(jsonbytes(operation_plan(manifest,config,observed)))
    return dict(directory=str(output),release_id=manifest['release_id'],files=len(blobs),archive_sha256=manifest['archive_sha256'],deployed=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--build',action='store_true');parser.add_argument('--output',required=True);parser.add_argument('--generation-selection',default='config/generation-selection-073.json');parser.add_argument('--generation-review');args=parser.parse_args()
    if args.build:print(json.dumps(build(args.output,generation_selection_path=args.generation_selection,quality_review=args.generation_review),indent=2))
    else:
        blobs,m,c,o=snapshot(generation_selection_path=args.generation_selection);print(json.dumps({'manifest':m,'operation_plan':operation_plan(m,c,o)},indent=2))
