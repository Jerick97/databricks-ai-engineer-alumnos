"""Reviewed existing-App deployment. No cloud work without explicit execute.

SDK WorkspaceExt multipart RAW upload supports large files without base64 JSON.
Durable per-effect intents forbid mutation resend after ambiguous outcomes.
"""
from pathlib import Path
from types import SimpleNamespace
import argparse,hashlib,io,json,os,re,time,fcntl,uuid
ROOT=Path(__file__).resolve().parents[1]
APP='sbs-radar-pilot';HOST='https://dbc-0410b264-20c7.cloud.databricks.com'
AUTONOMY='runs/sk00-autonomy-053.json';AUTONOMY_SHA='241b0946ab052ead92a8e29a4abb8bc98d064030c5933a45397465df6fcb8d43'
def require(ok,code):
    if not ok:raise ValueError(code)
def read(p):return json.loads(Path(p).read_bytes())
def sha(raw):return hashlib.sha256(raw).hexdigest()
def rawjson(v):return (json.dumps(v,sort_keys=True,indent=2)+'\n').encode()
def obj(v):return v.as_dict() if hasattr(v,'as_dict') else v

def durable(path,value):
    from sbs.genie.publication_registry import _directory,_append
    fd=_directory(Path(path).parent,True)
    try:_append(fd,Path(path).name,rawjson(value))
    finally:os.close(fd)


def quality_paths(review):
    default=[ROOT/'deployment/state/generation-rag-073'/f'turn-{i}-result.json' for i in range(4)]
    if not review or 'responses_sha256' not in review:return default
    pins=review['responses_sha256'];require(isinstance(pins,dict) and len(pins)==4,'QUALITY_RESPONSE_CLOSURE')
    names=sorted(pins);match=[re.fullmatch(r'deployment/state/(generation-rag-(?:073|075))/turn-([0-3])-result\.json',n) for n in names]
    require(all(match) and len({m.group(1) for m in match})==1 and {m.group(2) for m in match}=={'0','1','2','3'},'QUALITY_RESPONSE_SCOPE')
    return [ROOT/n for n in names]


# Runtime behavior inputs, not authoring/review documentation. The execution
# admission binds the exact plan that authorized the four observed responses.
TESTED_REQUIRED=frozenset({
 'src/sbs/runtime.py','src/sbs/conversation/__init__.py',
 'src/sbs/conversation/databricks.py','src/sbs/conversation/compaction.py',
 'src/sbs/conversation/process_context.py','src/sbs/models/generation_selection.py',
 'config/generation-selection-073.json','config/pilot-model-bundle.json',
 'config/fictitious-processes-075.json','runs/sk06-pilot-002/processes.jsonl',
 'runs/sk05-generation-candidates-072-databricks-qwen3-next-80b-a3b-instruct.json',
 'runs/sk04-real-001-protocol.json','data/retrieval/sk04-real-001/index.json',
 'data/retrieval/sk04-real-001/queries-000.json',
 'skills/sbs-conversacion-orquestacion/assets/generator-instructions.md'})

def tested_implementation(needed,staged):
    family=needed[0].parent.name
    require(family=='generation-rag-075','TESTED_IMPLEMENTATION_PLAN_REQUIRED')
    plan_path=ROOT/'deployment'/f'{family}-plan.json'
    admission_path=needed[0].parent/'admission.json'
    require(plan_path.is_file() and admission_path.is_file(),'TESTED_IMPLEMENTATION_CHAIN_MISSING')
    plan=read(plan_path);admission=read(admission_path)
    require(admission.get('plan_sha256')==sha(plan_path.read_bytes()),'TESTED_PLAN_ADMISSION_MISMATCH')
    inputs=plan.get('inputs',{})
    require(isinstance(inputs,dict) and TESTED_REQUIRED<=inputs.keys(),'TESTED_IMPLEMENTATION_CLOSURE_MISSING')
    behavior={n:h for n,h in inputs.items() if n in TESTED_REQUIRED or n.startswith(('src/','config/','data/')) or '/assets/' in n}
    require(all(staged.get(n)==h for n,h in behavior.items()),'TESTED_IMPLEMENTATION_MISMATCH')
    return {str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in (plan_path,admission_path)}


def preflight(package,quality_review):
    package=Path(package).resolve();manifest=read(package/'manifest.json');plan=read(package/'operation-plan.json');source=package/'source'
    require(manifest['release_id']=='sbs-app-070-'+manifest['snapshot_sha256'][:16],'RELEASE_ID_INVALID')
    require(plan['app_name']==APP and plan['app_client_id']=='a947eccf-5f94-4369-a3d4-8f83b4ea98a1' and plan['app_executor_id']==77041447522099,'APP_SCOPE_CHANGED')
    require(plan['source_code_path']=='/Workspace/Users/sociosdosmilveintiseis@gmail.com/sbs-radar/releases/'+manifest['release_id'],'RELEASE_PATH_CHANGED')
    require(sha(rawjson(manifest['files_sha256']))==manifest['snapshot_sha256'],'MANIFEST_IDENTITY_INVALID')
    for name,h in manifest['files_sha256'].items():
        p=source/name;require(not Path(name).is_absolute() and '..' not in Path(name).parts and p.resolve().is_relative_to(source) and not p.is_symlink(),'SOURCE_PATH_ESCAPE')
        require(p.is_file() and p.stat().st_size<=500_000_000 and sha(p.read_bytes())==h,'SOURCE_HASH_OR_SIZE_INVALID')
    require(sha((package/'source.tar.gz').read_bytes())==manifest['archive_sha256'],'ARCHIVE_HASH_INVALID')
    from sbs.models.generation_selection import load_selection
    selection=load_selection(source)
    require(sha((ROOT/AUTONOMY).read_bytes())==AUTONOMY_SHA,'AUTONOMY_CHANGED')
    review=read(quality_review) if Path(quality_review).is_file() else None
    needed=quality_paths(review)
    missing=[str(p) for p in needed if not p.is_file()]
    ready=not missing and bool(review and review.get('status')=='PASS_CONTROLLED_SAMPLE' and review.get('demo_sample_accepted') is True)
    implementation_pins={}
    if ready:
        implementation_pins=tested_implementation(needed,manifest['files_sha256'])
        turns=[read(p) for p in needed]
        require(all(t.get('answer',{}).get('status') in ('answered','answered_partial') and isinstance(t['answer'].get('citations'),list) and t['answer']['citations'] and t.get('generation',{}).get('http_status')==200 and t['generation'].get('endpoint')==selection['endpoint'] and t['generation'].get('response_model')==selection['expected_response_model'] for t in turns),'SBS_GENERATION_NOT_ANSWERED')
        require(review.get('responses_sha256')=={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in needed},'QUALITY_RESPONSE_PINS_MISMATCH')
    pins={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in needed if p.is_file()}
    pins.update(implementation_pins)
    pins.update({AUTONOMY:AUTONOMY_SHA,'deployment/app_deploy_070.py':sha((ROOT/'deployment/app_deploy_070.py').read_bytes()),'deployment/app_release_070.py':sha((ROOT/'deployment/app_release_070.py').read_bytes())})
    contract=dict(status='PENDING',manifest_sha256=sha((package/'manifest.json').read_bytes()),operation_plan_sha256=sha((package/'operation-plan.json').read_bytes()),generation_quality_review_sha256=sha(Path(quality_review).read_bytes()) if review else None,files_sha256=pins,source_code_path=plan['source_code_path'],window_ms=1800000)
    return dict(status='ready_for_review' if ready else 'generation_sbs_quality_pending',review_contract=contract,missing=missing,files=len(manifest['files_sha256']),max_file_bytes=max((source/n).stat().st_size for n in manifest['files_sha256']),sql=0,resource_mutations=0,start_max=1,deploy_max=1,endpoint=selection['endpoint'])


class ScopedApi:
    """Generated SDK serializers over one HTTP attempt; no provider retry layer."""
    def __init__(self,cfg,prefix,admit,session):
        self._cfg=cfg;self.prefix=prefix;self.admit=admit;self.session=session;self.calls=0
        require(cfg.host.rstrip('/')==HOST,'HOST_MISMATCH')
        require(all(a.max_retries.total==0 for a in session.adapters.values()),'RETRIES_FORBIDDEN');session.trust_env=False
    def do(self,method,path=None,*,query=None,body=None,files=None,data=None,headers=None,raw=False,**extra):
        require(not extra,'SDK_ARGUMENTS_UNSUPPORTED')
        is_workspace=path in ('/api/2.0/workspace/get-status','/api/2.0/workspace/export','/api/2.0/workspace/import','/api/2.0/workspace/mkdirs')
        if is_workspace:
            target=(query or data or body or {}).get('path','')
            require(isinstance(target,str) and (target==self.prefix or target.startswith(self.prefix+'/')) and '..' not in target.split('/'),'WORKSPACE_PATH_OUTSIDE_RELEASE')
            allowed=(method=='GET' and path.endswith(('/get-status','/export'))) or (method=='POST' and path.endswith(('/import','/mkdirs')))
            if path.endswith('/import'):require(files is not None and set(files)=={'content'} and data.get('format')=='RAW' and not data.get('overwrite'),'RAW_MULTIPART_REQUIRED')
        else:
            base='/api/2.0/apps/'+APP
            allowed=(method=='GET' and (path==base or re.fullmatch(re.escape(base)+r'/deployments(?:/[A-Za-z0-9_-]+)?',path or ''))) or (method=='POST' and path in (base+'/start',base+'/deployments'))
            if method=='POST' and path==base+'/deployments':require(body=={'source_code_path':self.prefix,'mode':'SNAPSHOT'},'DEPLOY_BODY_OUTSIDE_SCOPE')
        require(allowed,'CLOUD_OPERATION_FORBIDDEN');require(self.calls<4000,'HTTP_CAP');self.admit();self.calls+=1
        auth=self._cfg.authenticate();self.admit()
        r=self.session.request(method,HOST+path,params=query,json=body,data=data,files=files,headers={**(headers or {}),**auth},timeout=(15,180),allow_redirects=False,stream=True)
        try:
            cap=500_000_000 if raw else 4_000_000;content=r.raw.read(cap+1,decode_content=True);require(len(content)<=cap,'RESPONSE_SIZE_LIMIT')
            if not 200<=r.status_code<300:
                from databricks.sdk.errors import DatabricksError
                code=None
                try:code=json.loads(content).get('error_code')
                except Exception:pass
                safe=code if code in ('RESOURCE_DOES_NOT_EXIST','RESOURCE_ALREADY_EXISTS') else 'CLOUD_HTTP_UNCONFIRMED'
                raise DatabricksError(message=safe,error_code=safe)
            if raw:return {'contents':io.BytesIO(content)}
            return json.loads(content) if content else {}
        finally:r.close()


def services(cfg,prefix,admit):
    import requests
    from databricks.sdk.mixins.workspace import WorkspaceExt
    from databricks.sdk.service.apps import AppsAPI
    api=ScopedApi(cfg,prefix,admit,requests.Session())
    return SimpleNamespace(workspace=WorkspaceExt(api),apps=AppsAPI(api),api=api)


def execute(package,quality_review,review_path,*,clock=lambda:int(time.time()*1000),sleep=time.sleep,services_factory=services,config_factory=None):
    require(review_path is not None,'DEPLOY_REVIEW_REQUIRED');report=preflight(package,quality_review)
    require(report['status']=='ready_for_review','GENERATION_SBS_QUALITY_REQUIRED');require(read(review_path)=={**report['review_contract'],'status':'PASS'},'DEPLOY_ADMISSION_MISMATCH')
    package=Path(package).resolve();manifest=read(package/'manifest.json');prefix=report['review_contract']['source_code_path'];state=ROOT/'deployment/state'/manifest['release_id'];state.mkdir(parents=True,exist_ok=True)
    lock=os.open(state,os.O_RDONLY);fcntl.flock(lock,fcntl.LOCK_EX)
    server=None;result={'status':'incomplete','sql':0,'resource_binding_updates':0,'grants':0,'start_posts':0,'deploy_posts':0}
    try:
        binding={'manifest_sha256':report['review_contract']['manifest_sha256'],'admission_sha256':sha(Path(review_path).read_bytes()),'source_code_path':prefix}
        durable(state/'binding.json',binding)
        window=state/'window.json'
        if not window.exists():durable(window,{'issued_at_ms':clock(),'expires_at_ms':clock()+1800000})
        end=read(window)['expires_at_ms']
        def admit():require(clock()<end,'DEPLOY_WINDOW_EXPIRED')
        admit()
        if config_factory is None:
            from databricks.sdk.core import Config
            config_factory=Config
        server=services_factory(config_factory(profile='databricks-ai-engineer-aws'),prefix,admit)
        app=obj(server.apps.get(APP));require(app.get('service_principal_id')==77041447522099 and app.get('service_principal_client_id')=='a947eccf-5f94-4369-a3d4-8f83b4ea98a1' and 'iam.current-user:read' in app.get('effective_user_api_scopes',[]),'APP_OBSERVATION_MISMATCH')
        if not (state/'app-before.json').exists():durable(state/'app-before.json',app) # preserves prior active deployment for rollback
        attempt=state/('attempt-'+uuid.uuid4().hex);attempt.mkdir()
        durable(attempt/'app-observed.json',app)
        from databricks.sdk.service.workspace import ImportFormat,ExportFormat
        def status(path):
            try:return obj(server.workspace.get_status(path))
            except Exception as e:
                if getattr(e,'error_code',None)=='RESOURCE_DOES_NOT_EXIST':return None
                raise
        directories=sorted({prefix,*[prefix+'/'+str(Path(n).parent) for n in manifest['files_sha256'] if str(Path(n).parent)!='.']},key=lambda p:(p.count('/'),p))
        for directory in directories:
            key=sha(directory.encode());intent=state/('mkdir-'+key+'.json')
            existing=status(directory)
            if existing:
                require(intent.exists() and existing.get('object_type')=='DIRECTORY','PREEXISTING_RELEASE_DIRECTORY');continue
            require(not intent.exists(),'DIRECTORY_MUTATION_UNCONFIRMED');durable(intent,{'path':directory});server.workspace.mkdirs(directory)
        for name,h in sorted(manifest['files_sha256'].items()):
            remote=prefix+'/'+name;key=sha(name.encode());intent=state/('upload-'+key+'.json');receipt=state/('uploaded-'+key+'.json')
            if not intent.exists():
                payload=(package/'source'/name).read_bytes();require(sha(payload)==h,'SOURCE_CHANGED_BEFORE_UPLOAD')
                require(status(remote) is None,'PREEXISTING_RELEASE_FILE');durable(intent,{'path':remote,'sha256':h})
                with io.BytesIO(payload) as content:
                    try:server.workspace.upload(remote,content,format=ImportFormat.RAW,overwrite=False)
                    except Exception:pass # reconcile by one GET, never resend
            with server.workspace.download(remote,format=ExportFormat.RAW) as stream:observed=sha(stream.read(500_000_001))
            require(observed==h,'UPLOADED_FILE_HASH_MISMATCH');durable(receipt,{'path':remote,'sha256':h})
        durable(state/'source-verified.json',{'manifest_sha256':binding['manifest_sha256'],'files':len(manifest['files_sha256'])})
        current=obj(server.apps.get(APP));phase=current.get('compute_status',{}).get('state');start=state/'start-intent.json'
        if phase=='STOPPED':
            require(not start.exists(),'START_UNCONFIRMED_NO_RETRY');durable(start,{'app':APP})
            try:server.apps.start(APP);result['start_posts']=1
            except Exception:result['start_posts']=1
        else:require(phase in ('ACTIVE','RUNNING','STARTING'),'APP_STATE_UNSUPPORTED')
        for i in range(30):
            current=obj(server.apps.get(APP));durable(attempt/f'start-observation-{i:02}.json',current)
            if current.get('compute_status',{}).get('state') in ('ACTIVE','RUNNING'):break
            sleep(5)
        else:raise ValueError('APP_START_PENDING')
        intent=state/'deploy-intent.json';receipt=state/'deploy-receipt.json'
        if not intent.exists():
            durable(intent,{'source_code_path':prefix,'mode':'SNAPSHOT'})
            from databricks.sdk.service.apps import AppDeployment,AppDeploymentMode
            try:
                response=obj(server.apps.deploy(APP,AppDeployment(source_code_path=prefix,mode=AppDeploymentMode.SNAPSHOT)).response);durable(receipt,response);result['deploy_posts']=1
            except Exception:result['deploy_posts']=1
        if receipt.exists():deployment_id=read(receipt)['deployment_id']
        else:
            from itertools import islice
            matches=[obj(d) for d in islice(server.apps.list_deployments(APP,page_size=20),20) if obj(d).get('source_code_path')==prefix]
            require(len(matches)==1,'DEPLOY_UNCONFIRMED_NO_RETRY');durable(receipt,matches[0]);deployment_id=matches[0]['deployment_id']
        for i in range(40):
            deployment=obj(server.apps.get_deployment(APP,deployment_id));durable(attempt/f'deploy-observation-{i:02}.json',deployment)
            state_name=deployment.get('status',{}).get('state')
            if state_name=='SUCCEEDED':result.update(status='deployed_runtime_verification_pending',deployment_id=deployment_id);break
            require(state_name not in ('FAILED','CANCELLED'),'APP_DEPLOY_FAILED');sleep(5)
        else:raise ValueError('APP_DEPLOY_PENDING')
    except Exception as error:
        code=str(error);result.update(error_class=type(error).__name__,error_code=code if re.fullmatch('[A-Z0-9_]{1,100}',code) else 'BOUNDED_CLOUD_OR_LOCAL_FAILURE')
    finally:
        if server:result['workspace_http_calls']=server.api.calls;server.api.session.close()
        durable(state/('result-'+str(clock())+'-'+uuid.uuid4().hex+'.json'),result);os.close(lock)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--package',required=True);p.add_argument('--generation-review',required=True);p.add_argument('--review');p.add_argument('--execute',action='store_true');a=p.parse_args()
    out=execute(a.package,a.generation_review,a.review) if a.execute else preflight(a.package,a.generation_review);print(json.dumps(out,indent=2))
