"""Local App153 candidate/materialization. No cloud or claim of Linux evidence."""
from pathlib import Path
import argparse,hashlib,json,shutil,time
ROOT=Path(__file__).resolve().parents[1]
BASE='runs/sk12-app-133-source-v3'
BASE_SHA='afa0e1a63851af5d8419a2af16ef674d1602f65d06de1edd254cf1a18388a432'
QUALITY='runs/sk09-astra-hybrid-139-review.json'
APP='sbs-radar-pilot'
HOST='https://dbc-0410b264-20c7.cloud.databricks.com'
ORIGIN='https://sbs-radar-pilot-7474657121564806.aws.databricksapps.com'
def require(v,code):
 if not v:raise ValueError(code)
def encoded(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def sha(v):return hashlib.sha256(v).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def files(source):return {p.relative_to(source).as_posix():sha(p.read_bytes()) for p in source.rglob('*') if p.is_file()}
def verify(stage,*,exact=True):
 stage=Path(stage);m=read(stage/'manifest.json');require(sha(encoded(m['files_sha256']))==m['source_sha256'],'SOURCE_MANIFEST_INVALID')
 for name,pin in m['files_sha256'].items():
  p=stage/'source'/name;require(not Path(name).is_absolute() and '..' not in Path(name).parts and not p.is_symlink() and p.resolve().is_relative_to((stage/'source').resolve()) and sha(p.read_bytes())==pin,'SOURCE_DRIFT')
 if exact:require(files(stage/'source')==m['files_sha256'],'UNMANIFESTED_SOURCE')
 return m

def app_config():
 env={'SBS_MODE':'cloud','SBS_GENIE_ROTATION_CONFIG':'config/genie-bootstrap-098.json','DATABRICKS_HOST':HOST,'SBS_PUBLIC_ORIGIN':ORIGIN,'PYTHONDONTWRITEBYTECODE':'1','PYTHONUNBUFFERED':'1','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','TOKENIZERS_PARALLELISM':'false','OMP_NUM_THREADS':'2','WEB_CONCURRENCY':'1'}
 return {'command':['python','app133.py'],'env':[{'name':k,'value':v} for k,v in env.items()]}

def prepare(destination,*,root=ROOT):
 root=Path(root);base=root/BASE;m=verify(base,exact=False);require(m['source_sha256']==BASE_SHA,'BASE133_CHANGED')
 require(read(base/'source/config/app-integration-133.json')['deadline_unix']==0,'BASE_DEADLINE_NOT_ZERO')
 obs=read(root/'runs/sk12-app-metadata-001-observation-002.json')['app'];require(obs['name']==APP and obs['url']==ORIGIN and obs['service_principal_client_id']=='a947eccf-5f94-4369-a3d4-8f83b4ea98a1','APP_OBSERVATION_CHANGED')
 dest=Path(destination);require(not dest.exists(),'DESTINATION_EXISTS');dest.mkdir(parents=True);source=dest/'source';source.mkdir()
 for name in m['files_sha256']:
  target=source/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(base/'source'/name,target)
 (source/'deployment').mkdir(exist_ok=True);(source/'deployment/requirements-app.txt').write_bytes((root/'runs/sk12-linux-installed.txt').read_bytes())
 require((source/'requirements.txt').read_text().strip()=='-r deployment/requirements-app.txt','REQUIREMENTS_ENTRY_CHANGED')
 (source/'app.yaml').write_text(json.dumps(app_config(),indent=2)+'\n')
 out={'kind':'candidate153_deadline0_not_deployable','base_source133_sha256':BASE_SHA,'deadline_unix':0,'files_sha256':files(source),'linux_verified':False,'cloud_executed':False,'e2e':False}
 out['source_sha256']=sha(encoded(out['files_sha256']));(dest/'manifest.json').write_text(json.dumps(out,indent=2)+'\n');return out

def gates(root,linux_evidence,linux_sha):
 root=Path(root);inv=read(root/'runs/sk12-app-candidate-153-invocation.json');require(sha((root/QUALITY).read_bytes())==inv['files'][QUALITY],'QUALITY139_CHANGED')
 q=read(root/QUALITY);require(q.get('status')=='PASS_CONTROLLED_SAMPLE' and q.get('demo_sample_accepted') is True and q.get('reviewer',{}).get('model')=='gpt-6-astra' and q['reviewer'].get('reasoning_effort')=='high','QUALITY139_REQUIRED')
 for p,h in {**q['inputs_sha256'],**q['responses_sha256']}.items():require(sha((root/p).read_bytes())==h,'QUALITY139_INPUT_DRIFT')
 raw=Path(linux_evidence).read_bytes();require(sha(raw)==linux_sha,'LINUX_EVIDENCE_PIN');report=json.loads(raw)
 require(report.get('status')=='PASS_LINUX_CANARY_RUNTIME_ONLY' and report.get('source133_sha256')==BASE_SHA,'ACTUAL_LINUX_CANARY_REQUIRED')
 require(report.get('platform',{}).get('system')=='Linux' and report['platform'].get('python','').startswith('3.11.') and report['platform'].get('machine') in ('x86_64','amd64','aarch64','arm64'),'LINUX_PLATFORM_REQUIRED')
 require(report.get('numeric_comparison',{}).get('status')=='passed' and report['numeric_comparison'].get('same_input') is True and report['numeric_comparison'].get('tolerance')==.001,'LINUX_NUMERIC_REQUIRED')
 deps=dict(line.split('==') for line in (root/'runs/sk12-linux-installed.txt').read_text().splitlines() if line and not line.startswith('#'))
 require(report.get('dependencies')==deps and report.get('local_onnx_calls')==1 and report.get('provider_calls')==report.get('sql_calls')==0,'LINUX_CLOSURE_REQUIRED')
 return {'quality139_sha256':sha((root/QUALITY).read_bytes()),'linux_evidence_sha256':linux_sha,'linux_source133_sha256':BASE_SHA,'scope':'controlled quality sample + diagnostic Linux runtime; not final M2M/UI'}

def materialize(template,destination,*,linux_evidence,linux_sha,expires_at,root=ROOT,clock=time.time):
 require(type(expires_at) is int and clock()<expires_at<=clock()+1800,'ABSOLUTE_DEADLINE_REQUIRED')
 gate=gates(root,linux_evidence,linux_sha);m=verify(template);require(m['kind']=='candidate153_deadline0_not_deployable' and m['deadline_unix']==0,'TEMPLATE_REQUIRED')
 require(m.get('base_source133_sha256')==BASE_SHA,'TEMPLATE_LINEAGE_REQUIRED')
 baseline=verify(Path(root)/BASE,exact=False)['files_sha256']
 for name,pin in baseline.items():require(m['files_sha256'].get(name)==pin,'TEMPLATE_BASE_CODE_DRIFT')
 require(set(m['files_sha256'])==set(baseline)|{'app.yaml','deployment/requirements-app.txt'},'TEMPLATE_EXTRA_FILES')
 require((Path(template)/'source/deployment/requirements-app.txt').read_bytes()==(Path(root)/'runs/sk12-linux-installed.txt').read_bytes(),'TEMPLATE_REQUIREMENTS_DRIFT')
 app=read(Path(template)/'source/app.yaml');require(app==app_config(),'TEMPLATE_APP_CONFIG_DRIFT')
 dest=Path(destination);require(not dest.exists(),'DESTINATION_EXISTS');dest.mkdir(parents=True);shutil.copytree(Path(template)/'source',dest/'source')
 source=dest/'source';p=source/'config/app-integration-133.json';c=read(p);require(c['deadline_unix']==0 and c['worker_count']==1 and (c['generation_posts_per_process'],c['embedding_posts_per_process'],c['embedding_tokens_per_process'])==(4,2,20000),'CAPS_CHANGED');c['deadline_unix']=expires_at;p.write_bytes(encoded(c))
 out={'kind':'materialized153_pending_independent_release_review','base_source133_sha256':BASE_SHA,'template_sha256':sha((Path(template)/'manifest.json').read_bytes()),'deadline_unix':expires_at,'files_sha256':files(source),'gates':gate,'worker_count':1,'model_limits_per_process':{'generation_posts':4,'embedding_posts':2,'embedding_tokens':20000},'cloud_executed':False,'m2m_verified':False,'ui_verified':False,'e2e':False};out['source_sha256']=sha(encoded(out['files_sha256']))
 (dest/'manifest.json').write_text(json.dumps(out,indent=2)+'\n')
 payload={'app_name':APP,'observed_public_origin':ORIGIN,'host':HOST,'source_code_path':'/Workspace/Users/sociosdosmilveintiseis@gmail.com/sbs-radar/releases/app153-'+out['source_sha256'],'mode':'SNAPSHOT','source_sha256':out['source_sha256'],'manifest_sha256':sha((dest/'manifest.json').read_bytes()),'expires_at_unix':expires_at,'limits':{'upload_max':len(out['files_sha256']),'deploy_max':1,'start_max':0,'model_calls_by_publisher':0},'required_next':['independent release review of exact materialized diff','fresh App metadata/ACL and compute RUNNING','new external demo ledger; no silent restart/redeploy','publisher081/current098 selector readback','final M2M and visible UI after deployment','stop existing compute at absolute deadline; no continuous availability claim']}
 (dest/'deployment-payload.json').write_text(json.dumps(payload,indent=2)+'\n');return out

def main():
 p=argparse.ArgumentParser();p.add_argument('--destination',type=Path,required=True);p.add_argument('--materialize',type=Path);p.add_argument('--linux-evidence',type=Path);p.add_argument('--linux-sha256');p.add_argument('--expires-at-unix',type=int);a=p.parse_args()
 out=materialize(a.materialize,a.destination,linux_evidence=a.linux_evidence,linux_sha=a.linux_sha256,expires_at=a.expires_at_unix) if a.materialize else prepare(a.destination)
 print(json.dumps({k:v for k,v in out.items() if k!='files_sha256'}))
if __name__=='__main__':main()
