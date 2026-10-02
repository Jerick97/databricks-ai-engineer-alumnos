"""SK12 actual-kernel run, immutable per-attempt outputs including failures."""
from pathlib import Path
from datetime import datetime,timezone
from uuid import uuid4
import sys,json,hashlib
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager
root=Path(__file__).resolve().parents[1]
source=root/'notebooks/sbs-radar-runtime-promotion.ipynb'
run='sk12-runtime-notebook-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid4().hex
output=root/'runs'/f'{run}-executed.ipynb';record=root/'runs'/f'{run}.json'
code_paths=['src/sbs/runtime.py','src/sbs/operations/__init__.py','src/sbs/operations/preparers.py','src/sbs/operations/runtime_release.py','src/sbs/webapp/__init__.py']
code_hashes={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in code_paths}
n=nbformat.read(source,as_version=4);error=None
try:
 manager=KernelManager(kernel_name='python3',transport='ipc')
 manager.kernel_spec.argv=[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}']
 NotebookClient(n,timeout=180,km=manager,resources={'metadata':{'path':str(root)}}).execute()
except (Exception,KeyboardInterrupt) as exc:error=type(exc).__name__
with output.open('x') as f:nbformat.write(n,f)
code_drift=[p for p,h in code_hashes.items() if hashlib.sha256((root/p).read_bytes()).hexdigest()!=h]
if code_drift:error='CodeChangedDuringExecution'
errors=sum(o.output_type=='error' for c in n.cells if c.cell_type=='code' for o in c.outputs)
r={'run_id':run,'executed_at':datetime.now(timezone.utc).isoformat(),'status':'failed' if error or errors else 'passed','error_class':error,'errors':errors,'source_path':str(source.relative_to(root)),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'output_path':str(output.relative_to(root)),'output_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'code_cells':sum(c.cell_type=='code' for c in n.cells),'executed_cells':sum(c.cell_type=='code' and c.execution_count is not None for c in n.cells),'python_executable':sys.executable,'code_hashes':code_hashes,'code_drift':code_drift,'scope':'Real six-PDF preparation and LocalService promotion; real cached embeddings; failed promotion preserves prior runtime; no cloud, UI or generation acceptance'}
with record.open('x') as f:json.dump(r,f,indent=2);f.write('\n')
(root/'runs/sk12-runtime-notebook-latest.json').write_text(json.dumps({'run_id':run,'status':r['status'],'record_path':str(record.relative_to(root))},indent=2)+'\n')
print(json.dumps(r,indent=2))
if r['status']!='passed':raise SystemExit(1)
