"""Execute a real local kernel; preserve separate evidence for every attempt."""
import hashlib
import json
import sys
from pathlib import Path
from datetime import datetime,timezone
from uuid import uuid4
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager

ROOT=Path(__file__).resolve().parents[1]


def execute(root=ROOT):
    root=Path(root)
    source=root/'notebooks/sbs-radar-local.ipynb'
    run_id='sk12-notebook-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid4().hex
    output=root/'runs'/f'{run_id}-executed.ipynb'
    record_path=root/'runs'/f'{run_id}.json'
    output.parent.mkdir(parents=True,exist_ok=True)
    notebook=None; error_class=None; source_hash=None
    started_at=datetime.now(timezone.utc).isoformat()
    try:
        source_bytes=source.read_bytes()
        source_hash=hashlib.sha256(source_bytes).hexdigest()
        notebook=nbformat.reads(source_bytes.decode(),as_version=4)
        manager=KernelManager(kernel_name='python3',transport='ipc')
        manager.kernel_spec.argv=[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}']
        client=NotebookClient(notebook,timeout=180,km=manager,resources={'metadata':{'path':str(root)}})
        client.execute()
    except (Exception,KeyboardInterrupt) as exc:
        # Keep raw cell outputs in their local notebook, not exception text in console/metadata.
        error_class=type(exc).__name__
    cells=notebook.cells if notebook is not None else []
    errors=[out for cell in cells if cell.cell_type=='code' for out in cell.get('outputs',[]) if out.output_type=='error']
    if notebook is not None:
        with output.open('x') as handle:nbformat.write(notebook,handle)
    record={'run_id':run_id,'status':'failed' if error_class or errors else 'passed',
            'started_at':started_at,'executed_at':datetime.now(timezone.utc).isoformat(),
            'kernel':'python3','python_executable':sys.executable,
            'code_cells':sum(c.cell_type=='code' for c in cells),
            'executed_cells':sum(c.cell_type=='code' and c.execution_count is not None for c in cells),
            'errors':len(errors),'error_class':error_class,
            'source_sha256':source_hash,
            'output_path':str(output.relative_to(root)) if notebook is not None else None,
            'output_sha256':hashlib.sha256(output.read_bytes()).hexdigest() if notebook is not None else None,
            'scope':'Local offline corpus verification and declarative remote preflight; no deployed/E2E claim'}
    with record_path.open('x') as handle:json.dump(record,handle,indent=2);handle.write('\n')
    latest={'run_id':run_id,'status':record['status'],'record_path':str(record_path.relative_to(root))}
    temporary=root/'runs'/f'.{run_id}-latest.tmp'
    temporary.write_text(json.dumps(latest,indent=2)+'\n')
    temporary.replace(root/'runs/sk12-notebook-latest.json')
    return record


if __name__=='__main__':
    result=execute()
    print(json.dumps(result,indent=2))
    if result['status']!='passed':raise SystemExit(1)
