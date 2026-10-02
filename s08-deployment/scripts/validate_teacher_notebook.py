"""Importa copia aislada exacta y ejecuta notebook S08 en modo verificar."""
import argparse,base64,json,hashlib
from pathlib import Path
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.workspace import ImportFormat,Language
from databricks.sdk.service.jobs import SubmitTask,NotebookTask,JobEnvironment
from databricks.sdk.service.compute import Environment
R=Path(__file__).resolve().parents[1];OUT=R/'reports'
p=argparse.ArgumentParser();p.add_argument('--poll',type=int);p.add_argument('--profile',default='databricks-ai-engineer-aws');a=p.parse_args();w=WorkspaceClient(profile=a.profile)
if a.poll:
 run=w.jobs.get_run(a.poll);state=run.state.as_dict();print(json.dumps(state))
 (OUT/f'notebook-run-{a.poll}.json').write_text(json.dumps(run.as_dict(),indent=2))
 if run.state.life_cycle_state.value in {'TERMINATED','SKIPPED','INTERNAL_ERROR'}:
  for task in run.tasks or []:
   result=w.jobs.get_run_output(task.run_id).as_dict();(OUT/f'notebook-output-{a.poll}.json').write_text(json.dumps(result,indent=2))
   if result.get('notebook_output',{}).get('result'):
    report=json.loads(result['notebook_output']['result']);submission=json.loads((OUT/'notebook-docente-submit.json').read_text());report['notebook_sha256']=submission['notebook_sha256'];report['base_parameters']=submission['base_parameters'];report['validation_kind']=submission['validation_kind'];report['job_run_id']=a.poll;report['job_result_state']=run.state.result_state.value;report['pass']=run.state.result_state.value=='SUCCESS';(OUT/'notebook-docente-observed.json').write_text(json.dumps(report,indent=2,ensure_ascii=False));print(json.dumps(report.get('checks')))
   elif result.get('error'):print(result['error'][:2000])
else:
 target='/Shared/curso-databricks-ai-engineer/s08-docente'
 w.workspace.mkdirs(target)
 staged=[]
 for folder in ['lab','app','bundle']:
  for file in sorted((R/folder).rglob('*')):
   if file.is_file() and not any(x in file.parts for x in ['__pycache__','.databricks','.venv']):
    rel=file.relative_to(R);staged.append({'path':str(rel),'sha256':hashlib.sha256(file.read_bytes()).hexdigest()});w.workspace.mkdirs(target+'/'+str(rel.parent));w.workspace.upload(target+'/'+str(rel),file.read_bytes(),format=ImportFormat.RAW,overwrite=True)
 source=(R/'notebook-docente.py').read_bytes();digest=hashlib.sha256(source).hexdigest()
 path=target+'/S08-docente-validado';w.workspace.import_(path=path,content=base64.b64encode(source).decode(),format=ImportFormat.SOURCE,language=Language.PYTHON,overwrite=True)
 exported=base64.b64decode(w.workspace.export(path,format=ImportFormat.SOURCE).content)
 assert exported.strip()==source.strip(),'Exportado distinto del source local'
 c=json.loads((R/'lab/config.json').read_text())
 params={}  # Regression: no parameter injection; exercise defaults visible when opened.
 run=w.jobs.submit(run_name='S08-docente-defaults-sin-parametros',tasks=[SubmitTask(task_key='s08',notebook_task=NotebookTask(notebook_path=path,base_parameters=params),environment_key='s08',timeout_seconds=1800)],environments=[JobEnvironment(environment_key='s08',spec=Environment(client='5',dependencies=['mlflow[databricks]==3.16.1','databricks-sdk==0.143.0','openai==2.54.0','jsonschema==4.26.0','PyYAML>=6,<7']))]).response
 evidence={'run_id':run.run_id,'notebook_sha256':digest,'workspace_path':path,'mode':'verificar','base_parameters':params,'validation_kind':'default_widgets_no_overrides','source_export_verified':True,'staged_files':staged}
 (OUT/'notebook-docente-submit.json').write_text(json.dumps(evidence,indent=2));print(json.dumps({k:v for k,v in evidence.items() if k!='staged_files'}))
