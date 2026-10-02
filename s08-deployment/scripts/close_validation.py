"""Cierre basado en gates y hashes actuales; no edita dictámenes de los jueces."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
R=Path(__file__).resolve().parents[1];P=R/'reports'
def read(name):
 p=P/name
 return json.loads(p.read_text()) if p.exists() else {}
def hashof(p):return hashlib.sha256(p.read_bytes()).hexdigest()
gates={};judges={}
for name in ['curriculum','pedagogy','execution']:
 d=read(name+'-judge.json');bad=[]
 hashes=d.get('artifact_hashes',{})
 if isinstance(hashes,dict):
  for raw,expected in hashes.items():
   p=Path(raw)
   if not p.is_absolute():p=R/raw if (R/raw).exists() else R.parent/raw
   if not p.is_file() or hashof(p)!=expected:bad.append(raw)
 else:bad=['unsupported artifact_hashes format']
 judges[name]={'verdict':d.get('verdict'),'scope':d.get('scope'),'stale_hashes':bad}
 gates['judge_'+name]=d.get('verdict')=='PASS' and d.get('scope')=='full-session' and bool(hashes) and not bad
coverage=read('coverage-judge.json')
gates['coverage']=coverage.get('verdict')=='PASS' and all(not coverage.get(k) for k in ['orphan_items','misleading_items','missing_files'])
for label,file in [('visual','visual-qa.json'),('structure','structural-qa.json'),('material','material-audit.json'),('app_http','lab-app-http.json'),('app_render','app-visual.json'),('monitor','lab-monitor-verified.json'),('canary','lab-custom-canary-verified.json'),('rollback','lab-custom-rollback-verified.json')]:gates[label]=read(file).get('pass') is True
nb=read('notebook-observed.json');gates['notebook']=nb.get('pass') is True and nb.get('notebook_sha256')==hashof(R/'notebook.py')
browser=read('class-day-browser.json')
gates['live_browser_flow']=isinstance(browser,dict) and browser.get('live_browser_flow_pass') is True
teacher=read('teacher-delivery-judge.json');teacher_path=R/'notebook-docente.py'
teacher_hashes=teacher.get('artifact_hashes',{}) if isinstance(teacher,dict) else {}
gates['teacher_delivery']=isinstance(teacher,dict) and teacher.get('verdict')=='PASS' and isinstance(teacher_hashes,dict) and teacher_path.is_file() and teacher_hashes.get('notebook-docente.py')==hashof(teacher_path)
for label,file,minimum in [('local_cases','lab-smoke-local.json',6),('served_cases','lab-smoke-serving.json',6),('security_cases','lab-security-smoke.json',3)]:
 d=read(file);gates[label]=isinstance(d,list) and len(d)>=minimum and all(x.get('pass') is True for x in d)
unit=read('lab-unit-tests.json');gates['unit_contracts']=unit.get('status')=='PASS' and unit.get('tests',0)>=14
artifact=read('lab-artifact-check.json');gates['registered_source']=artifact.get('source_matches') is True and artifact.get('sha256')==hashof(R/'lab/agent.py')
package=read('lab-package.json');served=read('lab-smoke-serving.json');gates['served_current_model']=isinstance(served,list) and bool(served) and all(str(x.get('served_model_version'))==str(package.get('version')) for x in served) and str(artifact.get('version'))==str(package.get('version'))
requirements=json.loads((R/'requirements.json').read_text())['requirements'];gates['requirements']=all(x.get('status')=='satisfied' for x in requirements if x.get('required'))
for file in ['visual-qa.json']:
 d=read(file);gates['current_visual_hashes']=all((R/p).is_file() and hashof(R/p)==h for p,h in d.get('artifact_hashes',{}).items()) and bool(d.get('artifact_hashes'))
result={'validated_at':datetime.now(timezone.utc).isoformat(),'session':'S08','scope':'full-session','class_ready':all(gates.values()),'gates':gates,'judges':judges,'unverified':{'browser_sso':browser.get('sso_status','not_recorded') if isinstance(browser,dict) else 'not_recorded','historical_browser_sso':read('app-browser.json').get('sso_status'),'remote_ci':'not_executed; bundle validation only','publication':'local student copy and ZIP; no remote push','cohort_runtime':'Each participant needs assigned permissions/resources; teaching times estimated'},'notebook_run_id':nb.get('job_run_id'),'notebook_sha256':hashof(R/'notebook.py')}
result['live_browser_evidence']='reports/class-day-browser.json'
result['teacher_delivery_evidence']='reports/teacher-delivery-judge.json'
result['teacher_notebook_sha256']=hashof(teacher_path) if teacher_path.is_file() else None
previous=P/'closure.json'
if previous.exists():
 archive=P/('closure-history-'+hashof(previous)+'.json')
 if not archive.exists():archive.write_bytes(previous.read_bytes())
previous.write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
if not result['class_ready']:raise SystemExit(1)
