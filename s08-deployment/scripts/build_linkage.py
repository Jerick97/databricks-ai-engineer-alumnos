from pathlib import Path
import json
R=Path(__file__).resolve().parents[1]
slides=json.loads((R/'slides/content.json').read_text())
reqs=json.loads((R/'requirements.json').read_text())
rows=reqs.get('requirements',reqs.get('items',[]))
byid={r['id']:r for r in rows}
extra={
'S08-SERVING':['lab/lab_deploy.py'], 'S08-DEPLOY':['lab/agent.py','lab/requirements.txt','lab/config.json'],
'S08-ROLLOUT':['lab/lab_rollout.py','lab/lab_custom_rollout.py','lab/lab_custom_rollout_verify.py','lab/rollout_model.py'], 'S08-APPS':['app/app.py','app/app.yaml','app/requirements.txt','lab/lab_app.py'],
'S08-BUNDLES':['bundle/databricks.yml'], 'S08-INFERENCE':['lab/lab_monitor.py'], 'S08-MONITOR':['lab/lab_monitor.py'],
'S08-PROMPTS':['lab/lab_prompts.py'], 'S08-GATEWAY':['lab/lab_costs.sql'], 'S08-CERT':['CERTIFICACION.md'], 'S08-CLOUD':['CERTIFICACION.md'],
'S08-FINAL':['CONSIGNA.md'], 'S08-CONTINUITY':['lab/agent.py','lab/CONTINUIDAD.md','lab/lab_config.py']}
items=[]
for r in rows:
 shown=[s['id'] for s in slides if r['id'] in s['requirements']]
 r['shown_in']=shown
 files=list(dict.fromkeys(r.get('provided_files',[])+extra.get(r['id'],[])))
 r['provided_files']=files
 items.append({'id':r['id'],'kind':'concept','shown_in':shown,'taught_in':r['explanation']+[f'guion.md#{x}' for x in shown],'practiced_in':r['practice'],'delivered_as':['s08-deployment/'+f for f in files],'availability':'student','notes':r['acceptance']})
for source in json.loads((R/'sources.json').read_text()):
 shown=[s['id'] for s in slides if source['url'] in s['refs']]
 if shown: items.append({'id':'REF-'+source['id'],'kind':'external-resource','shown_in':shown,'taught_in':['guion.md#'+s for s in shown],'practiced_in':['Panel ★ de fuentes'],'delivered_as':[],'availability':'external','url':source['url'],'notes':'Documentación oficial enlazada desde marcador y panel.'})
(R/'requirements.json').write_text(json.dumps(reqs,ensure_ascii=False,indent=2))
(R/'coverage-manifest.json').write_text(json.dumps({'session':'S08','artifacts':{'deck':'s08-deployment/slides/S08-autonomo.html','script':'s08-deployment/guion.md','student_repo':'/Users/macdenix/clawd/databricks-ai-engineer-alumnos'},'items':items},ensure_ascii=False,indent=2))
out=['# S08 · Guion por diapositiva','', 'Lunes 28 de septiembre de 2026. Agenda de 180 minutos reloj estimados, incluida pausa de 10 minutos. Abrir GUIA-DOCENTE.md para el recorrido técnico y CONSIGNA.md para aceptación; agenda.json contiene distribución de teoría, demo, práctica y recuperación. Las notas no afirman que las salidas esperadas ya se observaron.','']
for s in slides:
 out += [f'<a id="{s["id"]}"></a>', f'## {s["id"]} · {s["title"]}', '',s['notes'],'', 'Contrato: '+', '.join(s['requirements'])+'.']
 for rid in s['requirements']:
  r=byid.get(rid)
  if r: out += ['Abrir: '+', '.join(r['practice'])+'. Evidencia de aceptación: '+r['acceptance']]
 if s['refs']: out += ['Fuentes: '+' · '.join(s['refs'])]
 out+=['']
(R/'guion.md').write_text('\n'.join(out))
print({'slides':len(slides),'requirements':len(rows),'manifest_items':len(items),'unmapped':[s['id'] for s in slides if any(r not in byid for r in s['requirements'])]})
