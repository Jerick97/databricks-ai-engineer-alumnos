"""Verifica archivos entregados, equivalencia notebook y contenido del ZIP."""
import ast,json,re,hashlib,zipfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
checks=[]
def check(name,ok,detail=''):checks.append({'name':name,'pass':bool(ok),'detail':detail})
requirements=json.loads((R/'requirements.json').read_text())['requirements']
missing=[f for r in requirements for f in r['provided_files'] if not (R/f).is_file()]
check('13 requisitos y archivos existentes',len(requirements)==13 and not missing,missing)
source=(R/'notebook.py').read_text();ast.parse(source)
nb=json.loads((R/'notebook.ipynb').read_text());expected=[]
for block in source.split('# COMMAND ----------'):
 lines=[x for x in block.strip().splitlines() if x!='# Databricks notebook source']
 if not lines:continue
 lines=[x[len('# MAGIC '):] if x.startswith('# MAGIC ') else '' if x=='# MAGIC' else x for x in lines]
 if '%md' in lines: expected.append(('markdown','\n'.join(lines[lines.index('%md')+1:])+'\n'))
 else:expected.append(('code','\n'.join(lines)+'\n'))
check('IPYNB equivale al source',expected==[(c['cell_type'],c['source']) for c in nb['cells']])
manifest=json.loads((R/'reports/publication-parity.json').read_text());student=Path(manifest['student_root'])
fail=[];secret=[]
with zipfile.ZipFile(R/'entregables/S08-material-alumnos.zip') as z:
 for e in manifest['entries']:
  rel=e['path'];data=(R/rel).read_bytes();sha=hashlib.sha256(data).hexdigest()
  if sha!=e['sha256'] or data!=(student/rel).read_bytes() or data!=z.read('s08-deployment/'+rel):fail.append(rel)
  if re.search(rb'\bdapi[a-fA-F0-9]{24,}\b|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',data):secret.append(rel)
check('Paridad docente/alumno/ZIP',not fail,fail)
check('Sin patrones de credenciales privadas en paquete',not secret,secret)
index=(R/'index.html').read_text();links=re.findall(r'href="([^"#]+)"',index)
check('Índice sin enlaces locales rotos',all((R/x).exists() for x in links if not x.startswith('http')),links)
for p in (R/'lab').glob('*.py'):ast.parse(p.read_text())
check('Sintaxis de módulos Python',True)
report={'pass':all(c['pass'] for c in checks),'checks':checks,'scope':'Archivos locales y ZIP; no sustituye ejecución cloud ni revisión pedagógica'}
(R/'reports/material-audit.json').write_text(json.dumps(report,indent=2,ensure_ascii=False));print(json.dumps(report,ensure_ascii=False))
if not report['pass']:raise SystemExit(1)
