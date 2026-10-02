"""Paquete local reproducible. No publica, no cambia evidencia de ejecución."""
from pathlib import Path
import json,hashlib,zipfile,shutil,uuid
R=Path(__file__).resolve().parents[1]
STUDENT=R.parent.parent/'databricks-ai-engineer-alumnos'/'s08-deployment'
def notebook_ipynb():
 text=(R/'notebook.py').read_text()
 cells=[]
 for block in text.split('# COMMAND ----------'):
  lines=[x for x in block.strip().splitlines() if x!='# Databricks notebook source']
  if not lines: continue
  # PEP723 metadata at top is harmless source comment; preserve with code.
  magic=[x[len('# MAGIC '):] if x.startswith('# MAGIC ') else '' if x=='# MAGIC' else x for x in lines]
  is_md=any(x.strip()=='%md' for x in magic)
  if is_md:
   start=next(i for i,x in enumerate(magic) if x.strip()=='%md')
   cell={'cell_type':'markdown','metadata':{},'source':'\n'.join(magic[start+1:])+'\n'}
  else:
   cell={'cell_type':'code','metadata':{},'source':'\n'.join(magic)+'\n','execution_count':None,'outputs':[]}
  cell['id']=uuid.uuid5(uuid.NAMESPACE_URL,cell['source']).hex[:12]
  cells.append(cell)
 nb={'nbformat':4,'nbformat_minor':5,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python'}},'cells':cells}
 (R/'notebook.ipynb').write_text(json.dumps(nb,ensure_ascii=False,indent=1))
 return len(cells)
def selected():
 roots=['course-context.json','notebook-docente.py','ABRIR-NOTEBOOK-DOCENTE.md','STATE.md','README.md','CONSIGNA.md','CERTIFICACION.md','notebook.py','notebook.ipynb','index.html','slides','app','lab','bundle','GUIA-DOCENTE.md','PLAN-CLASE.md','agenda.json','EJEMPLO-RESUELTO.md','requirements.json','VALIDACION.md','RUNBOOK.md','ENTREGA.md','guion.md','sources.json','coverage-manifest.json']
 roots += ['reports/'+x for x in ['class-day-smoke-serving.json','class-day-local-tests.json','class-day-closure-constructor.json','notebook-docente-submit.json','class-day-browser.json','class-day-start.json','class-day-review.json','teacher-delivery-judge.json','notebook-docente-observed.json','teacher-delivery-regression.json','visual-qa.json','structural-qa.json','app-visual.json','import-validation.json','lab-monitor-values.json','lab-monitor-refresh.json','lab-freeze.json','lab-rollout-api-limitation.json','lab-app-source-check.json','lab-source-hashes.json','lab-status.json','lab-parse-fixtures.json','lab-preflight.json','lab-package.json','lab-artifact-check.json','lab-smoke-local.json','lab-smoke-serving.json','lab-security-smoke.json','lab-app-http.json','lab-flatten.json','lab-monitor.json','lab-monitor-verified.json','lab-prompts.json','lab-bundle-validation.json','lab-unit-tests.json','lab-custom-rollout-package.json','lab-rollout-before.json','lab-rollout.json','lab-custom-rollout-verified.json','lab-custom-canary-verified.json','lab-custom-rollback-verified.json','notebook-observed.json','app-browser.json','curriculum-judge.json','coverage-judge.json','pedagogy-judge.json','execution-judge.json','closure.json'] if (R/'reports'/x).exists()]
 for name in roots:
  p=R/name
  if not p.exists(): continue
  for q in ([p] if p.is_file() else sorted(p.rglob('*'))):
   if q.is_file() and not any(s in q.parts for s in ['__pycache__','.venv','.databricks','.pytest_cache']) and not q.name.startswith('.env') and q.suffix not in ['.pyc']:
    yield q
if __name__=='__main__':
 count=notebook_ipynb();STUDENT.mkdir(parents=True,exist_ok=True)
 entries=[];out=R/'entregables';out.mkdir(exist_ok=True)
 with zipfile.ZipFile(out/'S08-material-alumnos.zip','w',zipfile.ZIP_DEFLATED) as z:
  for f in selected():
   rel=f.relative_to(R);dest=STUDENT/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dest)
   sha=hashlib.sha256(f.read_bytes()).hexdigest();assert sha==hashlib.sha256(dest.read_bytes()).hexdigest()
   entries.append({'path':str(rel),'sha256':sha});z.write(f,'s08-deployment/'+str(rel))
 with zipfile.ZipFile(out/'S08-material-alumnos.zip') as z:
  for e in entries: assert hashlib.sha256(z.read('s08-deployment/'+e['path'])).hexdigest()==e['sha256']
 report={'status':'local_copy_only','files':len(entries),'ipynb_cells':count,'student_root':str(STUDENT),'parity_pass':True,'entries':entries}
 (R/'reports/publication-parity.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='entries'}))
