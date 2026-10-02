"""Additive paired local/Linux evidence; never mutates or upgrades remote report."""
import sys,json,hashlib,socket,platform
from pathlib import Path
r=Path(sys.argv[1]).resolve();source=r/'runs/sk12-app-133-source-v3/source';sys.path.insert(0,str(source/'src'))
manifest=json.loads((source.parent/'manifest.json').read_bytes());linux=json.loads((r/'deployment/state/linux-canary-continue-185/capture178/linux-report.json').read_bytes())
assert manifest['source_sha256']==linux['source133_sha256']
assert hashlib.sha256(json.dumps(manifest['files_sha256'],sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()==manifest['source_sha256']
for name,pin in manifest['files_sha256'].items():assert hashlib.sha256((source/name).read_bytes()).hexdigest()==pin,name
def deny(*a,**k):raise RuntimeError('NETWORK_FORBIDDEN')
socket.socket.connect=deny;socket.create_connection=deny
from sbs.comparison.pilot import build_pilot
from sbs.models.reranker import LocalOnnxReranker
from sbs.paths import resolve_model_manifest
item=build_pilot(source)['items'][0];rows=[{'citation':item[s]} for s in ('before','after')];question='¿Quién responde por las operaciones digitales no reconocidas?'
h=lambda v:hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
model=LocalOnnxReranker.from_manifest(resolve_model_manifest(json.loads((source/'context/reranker-manifest.json').read_bytes()),root=source),cpu_threads=2)
assert model.execution_identity['weights_sha256']==linux['cpu_execution']['weights_sha256']
assert model.execution_identity['onnxruntime_version']==linux['cpu_execution']['onnxruntime_version']
assert h([question,rows])==linux['smoke_input_sha256']
scores=model(question,rows);linux=json.loads((r/'deployment/state/linux-canary-continue-185/capture178/linux-report.json').read_bytes());d=[abs(a-b) for a,b in zip(scores,linux['scores'])]
print(json.dumps({'status':'PASS_PAIRED_NUMERIC_SMOKE' if all(x<=.001 for x in d) else 'FAIL_PAIRED_NUMERIC_SMOKE','remote_report_unchanged':True,'cloud_calls':0,'provider_inference_calls':0,'source133_sha256':manifest['source_sha256'],'remote_report_sha256':hashlib.sha256((r/'deployment/state/linux-canary-continue-185/capture178/linux-report.json').read_bytes()).hexdigest(),'scores':scores,'full_rows_sha256':h([question,rows]),'consumed_text_sha256':h([question,[x['citation']['text'] for x in rows]]),'linux_full_rows_sha256':linux['smoke_input_sha256'],'same_full_input':h([question,rows])==linux['smoke_input_sha256'],'absolute_deltas':d,'numeric_pass':all(x<=.001 for x in d),'tolerance':.001,'identity':model.execution_identity,'platform':platform.platform(),'trace':model.last_trace},indent=2))
