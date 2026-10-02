"""Build an immutable Apps source snapshot locally; never create/start/deploy.

Reuses existing portable selection and cloud-config renderer. Remote operations
are emitted as a reviewable plan for the existing SBS App only.
"""
from pathlib import Path
import argparse,gzip,hashlib,importlib.util,io,json,tarfile
ROOT=Path(__file__).resolve().parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def jsonbytes(v):return (json.dumps(v,sort_keys=True,indent=2)+'\n').encode()
def module(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'deployment'/f'{name}.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def snapshot(root=ROOT):
    root=Path(root);builder=module('build_bundle');builder.ROOT=root
    paths=builder.selected_paths(include_models=True,include_structural_profile=False)
    blobs={str(p.relative_to(root)):p.read_bytes() for p in sorted(paths)}
    # Explicit073 closure; the genericbuilder intentionally does not include allruns.
    selection=json.loads((root/'config/generation-selection-073.json').read_bytes())
    observation=selection['observation_path']
    if observation!='runs/sk05-generation-candidates-072-databricks-qwen3-next-80b-a3b-instruct.json':raise ValueError('GENERATION_OBSERVATION_OUTSIDE_ALLOWLIST')
    raw=(root/observation).read_bytes()
    if sha(raw)!=selection['observation_sha256']:raise ValueError('GENERATION_OBSERVATION_DRIFT')
    blobs[observation]=raw
    context=json.loads((root/'config/fictitious-processes-075.json').read_bytes())
    if context['path']!='runs/sk06-pilot-002/processes.jsonl':raise ValueError('PROCESS_CONTEXT_OUTSIDE_ALLOWLIST')
    context_raw=(root/context['path']).read_bytes()
    if sha(context_raw)!=context['sha256']:raise ValueError('PROCESS_CONTEXT_DRIFT')
    blobs[context['path']]=context_raw
    observed=json.loads((root/'deployment/state/app-grants-069/after.json').read_bytes());app=observed['app']
    if app['name']!='sbs-radar-pilot' or app['service_principal_id']!=77041447522099 or app['service_principal_client_id']!='a947eccf-5f94-4369-a3d4-8f83b4ea98a1':raise ValueError('APP_IDENTITY_DRIFT')
    if 'iam.current-user:read' not in app.get('effective_user_api_scopes',[]):raise ValueError('DELEGATED_CURRENT_USER_SCOPE_REQUIRED')
    appconfig=module('prepare_app_config').build(app,json.loads((root/'runs/sk08-identity-real-probe.json').read_bytes()))
    appconfig['env'] += [{'name':name,'value':value} for name,value in [('PYTHONUNBUFFERED','1'),('HF_HUB_OFFLINE','1'),('TRANSFORMERS_OFFLINE','1'),('TOKENIZERS_PARALLELISM','false')]]
    # JSON is valid YAML; no new YAML dependency or secrets. Apps reads app.yaml.
    blobs['app.yaml']=jsonbytes(appconfig)
    # Explicitly disable Genie until a separately reviewed fresh remote registry
    # and reader policy are staged. Model-backed routes keep honest failures.
    blobs['config/genie-server.json']=jsonbytes({'version':1,'enabled':False})
    hashes={name:sha(raw) for name,raw in sorted(blobs.items())};identity=sha(jsonbytes(hashes))
    manifest=dict(version=1,release_id='sbs-app-070-'+identity[:16],snapshot_sha256=identity,files_sha256=hashes,models_included=True,structural_049_activated=False,genie_enabled=False,native_linux_current_release_verified=False,quality_acceptance=False)
    return blobs,manifest,appconfig,observed


def archive_bytes(blobs):
    buffer=io.BytesIO()
    with gzip.GzipFile(fileobj=buffer,mode='wb',mtime=0,filename='') as gz:
        with tarfile.open(fileobj=gz,mode='w') as tar:
            for name,raw in sorted(blobs.items()):
                if Path(name).is_absolute() or '..' in Path(name).parts:raise ValueError('RELEASE_PATH_ESCAPE')
                item=tarfile.TarInfo(name);item.size=len(raw);item.mode=0o644;item.mtime=0;item.uid=item.gid=0;item.uname=item.gname='';tar.addfile(item,io.BytesIO(raw))
    return buffer.getvalue()


def operation_plan(manifest,appconfig,observed):
    app=observed['app'];base='/Workspace/Users/sociosdosmilveintiseis@gmail.com/sbs-radar/releases/'+manifest['release_id']
    tables=['documents','versions','provisions','pairs','changes','evidence','reviews','processes']
    resources=[dict(name='sbs-warehouse',sql_warehouse=dict(id='828756322bedff37',permission='CAN_USE')),dict(name='sbs-genie',genie_space=dict(name='SBS Radar',space_id='01f1bb81787b118c9bbc8980e3523a21',permission='CAN_RUN')),dict(name='sbs-evidence-volume',uc_securable=dict(securable_full_name='neptuno_manuel_arguelles.sbs_radar.release_artifacts',securable_type='VOLUME',permission='READ_VOLUME'))]+[dict(name='sbs-'+t,uc_securable=dict(securable_full_name='neptuno_manuel_arguelles.sbs_radar.'+t,securable_type='TABLE',permission='SELECT')) for t in tables]
    return dict(status='held_generation_endpoint_validation_required',app_name='sbs-radar-pilot',app_client_id=app['service_principal_client_id'],app_executor_id=app['service_principal_id'],source_code_path=base,app_configuration=appconfig,resource_bindings_proposed=resources,user_api_scopes_observed=app['effective_user_api_scopes'],user_api_scope_changes=[],deployment_request={'source_code_path':base,'mode':'SNAPSHOT'},authorization_record='runs/sk00-autonomy-053.json',effects={'create_resource':False,'sql':0,'grant_changes_required_by_this_runner':0,'app_start_max':1,'app_deploy_max':1,'endpoint_permission_changes':False,'resource_binding_updates_require_exact_current_grant_reconciliation':True},steps=['User steering: validate generation on SBS with reviewed073 before start/deploy; Sol remains rate0, Qwen/Llama smoke072 passed, SBS validation pending. Sources-only readiness is not a substitute live demo.','Independent SK09 verifies source manifest and this exact plan; no new human consent inferred.','ReGET existing app and identity/scopes/resources. Preserve original metadata/deployment ID for rollback.','Stage source files under unique source_code_path, verify file hashes; no overwrite of other apps/releases.','Reuse069 exact grants; if resource bindings registered, reconcile to same permissions and preserve unrelated bindings; no serving endpoint grants.','If STOPPED, one admitted start of existing app, otherwise reuse RUNNING. Ambiguous response => GET reconcile, never repeat POST.','Deploy exactly one SNAPSHOT from pinned source_code_path; persist deployment ID and reconcile GET status, no blind retry.','Verify real delegated-user identity via catalog,6sources and3comparisons; rejection403/503 is failure for that capability, not E2E pass.'],genie_staging=['Keep disabled in baseline package.','Before enabling: reviewed fresh064/operation13currentGET+32history, immutablecertificate+registry and policy.status in ownvolume, separate hashpins, currentreadergrants; no extraSQL.','RegistryTTL300000 and policyexpiry unchanged; deploy/reload must finish inside validinterval or regenerate evidence, never stretchTTL.','Past originalSELECT2h profile limit: stop and obtain newly authorized readback; no relabeling.'],blockers={'generation':'Sol071 remains Databricks-set rate limit0; Qwen3Next and Llama3.3 smoke072 passed; reviewed073 SBS two-family/followup validation pending; no bypass/retry loop','genie':'disabled pending fresh registry/policy upload and app effectiveSELECTonly verification','linux':'priorLinuxsource/catalog/comparison andCPU load observed; numericdrift preserved; currentnativeApps execution pending','retrieval':'Default135 cached vectors+structural focus expansion;049231 is exposed-development profile and not promoted'},acceptance={'source_identity_comparison':'must be observed on realApp afterdeploy','genie':'separate verifiedSQL/provenance/grants needed','generation':'Sol403 remains; Qwen/Llama smoke072 does not establish073 SBS interpretation; unavailable is not success','e2e':'not accepted'})


def build(output,root=ROOT):
    blobs,manifest,config,observed=snapshot(root);output=Path(output);output.mkdir(parents=True,exist_ok=False)
    source=output/'source';source.mkdir()
    for name,raw in blobs.items():p=source/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    raw=archive_bytes(blobs);(output/'source.tar.gz').write_bytes(raw)
    manifest.update(archive_sha256=sha(raw),archive_bytes=len(raw))
    (output/'manifest.json').write_bytes(jsonbytes(manifest));(output/'operation-plan.json').write_bytes(jsonbytes(operation_plan(manifest,config,observed)))
    return dict(directory=str(output),release_id=manifest['release_id'],files=len(blobs),archive_sha256=manifest['archive_sha256'],archive_bytes=len(raw),deployed=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--build',action='store_true');parser.add_argument('--output',default=str(ROOT/'runs/sk12-app-release-070'));args=parser.parse_args()
    if args.build:print(json.dumps(build(args.output),indent=2))
    else:
        blobs,m,c,o=snapshot();print(json.dumps({'files':len(blobs),'bytes':sum(map(len,blobs.values())),'manifest_identity':m['snapshot_sha256'],'operation_plan':operation_plan(m,c,o)},indent=2))
