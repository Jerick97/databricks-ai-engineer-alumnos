from pathlib import Path
import importlib.util
import json
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('offline',ROOT/'deployment/offline.py')
offline=importlib.util.module_from_spec(spec);spec.loader.exec_module(offline)

def test_archived_path_rebases_and_cannot_escape(tmp_path):
    assert offline.local(tmp_path,'/Users/old/sbs-genie-e2e/data/x.pdf')==tmp_path/'data/x.pdf'
    with pytest.raises(ValueError):offline.local(tmp_path,'/etc/passwd')
    with pytest.raises(ValueError):offline.local(tmp_path,'../../etc/passwd')
    (tmp_path/'outside').symlink_to('/tmp')
    with pytest.raises(ValueError):offline.local(tmp_path,'outside/file.pdf')

def test_tampered_seal_rejected(tmp_path):
    path=tmp_path/'sealed.json';path.write_text(json.dumps({'payload':{'value':'modified'},'sha256':'0'*64}))
    with pytest.raises(ValueError,match='Sealed artifact changed'):offline.unseal(path)

def test_remote_gaps_are_declared_without_local_failure():
    result=offline.remote_preflight(ROOT)
    assert not result['ready_for_remote_execution']
    assert result['resource_actions']==0
    assert result['warehouse_candidate']['id']=='828756322bedff37'
    assert 'budget_new_resources' in {x['gate'] for x in result['gates']}


def test_executor_preserves_success_and_records_failed_attempt(tmp_path,monkeypatch):
    import runpy
    import nbformat
    import nbclient
    import jupyter_client
    (tmp_path/'deployment').mkdir(); (tmp_path/'notebooks').mkdir(); (tmp_path/'runs').mkdir()
    script=tmp_path/'deployment/execute_notebook.py'
    script.write_text((ROOT/'deployment/execute_notebook.py').read_text())
    nbformat.write(nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell('assert True')]),tmp_path/'notebooks/sbs-radar-local.ipynb')
    class Manager:
        kernel_spec=type('Spec',(),{'argv':[]})()
        def __init__(self,**kwargs):pass
    class Client:
        fail=False
        def __init__(self,notebook,**kwargs):self.notebook=notebook
        def execute(self):
            self.notebook.cells[0].execution_count=1
            if self.fail:
                self.notebook.cells[0].outputs=[nbformat.v4.new_output('error',ename='AssertionError',evalue='private failure detail',traceback=['private failure detail'])]
                raise RuntimeError('private failure detail')
            self.notebook.cells[0].outputs=[nbformat.v4.new_output('stream',name='stdout',text='verified success')]
    monkeypatch.setattr(nbclient,'NotebookClient',Client)
    monkeypatch.setattr(jupyter_client,'KernelManager',Manager)
    runpy.run_path(str(script),run_name='__main__')
    success={p.name:p.read_bytes() for p in (tmp_path/'runs').glob('*') if p.name!='sk12-notebook-latest.json'}
    Client.fail=True
    with pytest.raises((SystemExit,RuntimeError)) as error:
        runpy.run_path(str(script),run_name='__main__')
    if isinstance(error.value,SystemExit):assert error.value.code!=0
    for name,content in success.items(): assert (tmp_path/'runs'/name).read_bytes()==content
    latest=json.loads((tmp_path/'runs/sk12-notebook-latest.json').read_text())
    record=json.loads((tmp_path/latest['record_path']).read_text())
    assert record['status']=='failed' and record['error_class']=='RuntimeError'
    assert record['errors']==1 and record['executed_cells']==1
    assert 'private failure detail' not in json.dumps(record)
    failed=nbformat.read(tmp_path/record['output_path'],as_version=4)
    assert failed.cells[0].outputs[0].output_type=='error'
