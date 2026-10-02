from pathlib import Path
import json,wave,math,html,hashlib
R=Path(__file__).resolve().parent
E=html.escape
# Diagrams preserve the distinction between preparation, runtime and pending automation.
DETAILS={
'01-ingesta-publicacion':[
['Alcance: 2 familias normativas','Documento → pasaje → evidencia','Datos preparados para dos rutas'],
['Sólo destinos autorizados','Mismos bytes → mismo contenido','Fecha de captura ≠ fecha de vigencia'],
['PDF original + texto extraído','Comparar unidades correspondientes','Diferencia / interpretación / implicancia'],
['504-2021 × 2 · 3274-2017 × 2','2286-2024 × 1 · 2220-2025 × 1','4 documentos participan en 2 pares'],
['Fragmentos con familia, versión y página','Embeddings: databricks-qwen3-embedding-0-6b','documents · versions · provisions · pairs\nchanges · evidence · reviews · processes'],
['Tablas estructuradas para Genie','Artefactos y control de publicación','La App usa su paquete verificado']],
'02-consulta-aplicacion':[
['01 Novedades: elegir el par','02 Comparación: contrastar originales','03 Chat: preguntar y dar seguimiento'],
['El cliente no concede permisos','El contexto acompaña a las herramientas','Conteos / pasajes / implicancias'],
['Términos exactos + similitud semántica','Fusionar posiciones, no puntuaciones','Reranker ONNX local + citas trazables'],
['¿Cuántas versiones tiene este par?','Tablas Delta + alcance autorizado','Respuesta: 2 en el par; 6 en el inventario'],
['Preservar pasajes A y B','Validar referencias autorizadas','Generación cuando corresponde: Qwen 3.5'],
['Selección, evidencia y seguimiento','Foquito es un tutor separado','13 skills creadas; 13 provisionales']]}
css='''@font-face{font-family:Montserrat;src:url("assets/Montserrat.ttf")}@font-face{font-family:JetBrainsMono;src:url("assets/JetBrainsMono.ttf")}*{box-sizing:border-box}html,body{margin:0;width:1920px;height:1080px;overflow:hidden;background:#f1f5f1}#root{width:100%;height:100%;font-family:Montserrat,sans-serif;color:#173334} .clip{position:absolute;inset:0} .stage{height:100%;padding:68px 86px 54px;display:flex;flex-direction:column;background:#f1f5f1}.top{display:flex;justify-content:space-between;border-bottom:2px solid #91b2a4;padding-bottom:22px;font:24px JetBrainsMono,monospace;color:#19665e}.heading{font-weight:800;font-size:66px;line-height:1.13;letter-spacing:-2px;max-width:1690px;margin:48px 0 12px}.skill{font:25px JetBrainsMono,monospace;color:#19665e;margin:0}.diagram{flex:1;display:flex;align-items:center;gap:24px;padding:34px 0}.node{background:#e0ebe3;border:2px solid #91b2a4;border-radius:18px;padding:34px;flex:1;min-height:235px;display:flex;flex-direction:column;justify-content:center}.node strong{font-size:37px;line-height:1.22;display:block}.node small{font-size:25px;line-height:1.4;display:block;margin-top:22px;white-space:pre-line;overflow-wrap:anywhere}.number{font:23px JetBrainsMono,monospace;color:#19665e;margin-bottom:18px}.arrow{font-size:48px;color:#19665e}.note{font-size:30px;line-height:1.4;padding:24px 30px;border-top:2px solid #91b2a4;margin:0;min-height:102px}.bottom{font:20px JetBrainsMono,monospace;display:flex;justify-content:space-between;color:#19665e;margin-top:20px}.progress{height:6px;background:#19665e;transform-origin:left center;margin-top:20px}.metric .node strong{font-size:56px}.branches .node:first-child{background:#173334;color:#f1f5f1}.branches .node:first-child .number{color:#bce0cd}.app .node{border-top:12px solid #19665e}.compare .node:nth-of-type(3){border-style:dashed}.tables .node:last-child{flex:1.5}.tables .node:last-child small{font-family:JetBrainsMono;font-size:22px}.publish .node:last-child{background:#f0e5c8;border-color:#a68b43}.publish .node:last-child .number{color:#70591c}'''
for p in sorted(R.glob('0*')):
 if not p.is_dir():continue
 data=json.loads((p/'script.json').read_text());scenes=data['scenes'];start=0;hosts=[];audios=[];meta=[]
 for i,s in enumerate(scenes):
  with wave.open(str(p/'assets'/f"{s['id']}.wav")) as w: duration=w.getnframes()/w.getframerate()
  slot=math.ceil((duration+1.5)*30)/30;sid=s['id'];display=['flow','flow','compare','metric','tables','publish'][i] if p.name.startswith('01') else ['app','branches','flow','metric','compare','app'][i]
  nodes=''.join((('<span class="arrow" aria-hidden="true">→</span>' if j else '')+f'<div class="node" id="{sid}-n{j}"><span class="number">{j+1:02}</span><strong>{E(label)}</strong><small>{E(DETAILS[p.name][i][j])}</small></div>') for j,label in enumerate(s['nodes']))
  # Reveal early, then keep the chapter progress indicator as a useful reading cue.
  section=f'''<div class="stage"><div class="top"><span>SBS RADAR / {"PREPARACIÓN" if p.name.startswith("01") else "CONSULTA"}</span><span>{i+1:02} / 06</span></div><h1 class="heading" id="{sid}-heading">{E(s['title'])}</h1><p class="skill">{E(s['skills'])}</p><div class="diagram {display}">{nodes}</div><p class="note">{E(s['note'])}</p><div class="bottom"><span>Databricks AI Engineer · guía docente</span><span>Estado documentado · 30 SEP 2026</span></div><div class="progress" id="{sid}-progress"></div></div>'''
  timeline=f'''const tl=gsap.timeline({{paused:true}});tl.fromTo("#{sid}-heading",{{y:20,opacity:0}},{{y:0,opacity:1,duration:0.5,ease:"power3.out"}},0);'''
  for j in range(3):timeline+=f'tl.fromTo("#{sid}-n{j}",{{scale:0.92,opacity:0}},{{scale:1,opacity:1,duration:0.55,ease:"power3.out"}},{0.4+j*0.18});'
  timeline+=f'tl.fromTo("#{sid}-progress",{{scaleX:0}},{{scaleX:1,duration:{slot},ease:"none"}},0);window.__timelines["{sid}"]=tl;'
  sub=f'<!doctype html><html lang="es"><meta charset="utf-8"><body><template><style>#root{{position:absolute;inset:0;width:100%;height:100%}}</style><div id="root" data-composition-id="{sid}" data-width="1920" data-height="1080" data-duration="{slot}">{section}</div><script>{timeline}</script></template></body></html>'
  (p/'compositions'/f'{sid}.html').write_text(sub)
  (p/'compositions'/f'{sid}.motion.json').write_text(json.dumps({'duration':slot,'assertions':[{'kind':'appearsBy','selector':f'#{sid}-heading','bySec':0.7},{'kind':'staysInFrame','selector':f'#{sid}-n0'}]},indent=2))
  hosts.append(f'<div id="{sid}" class="clip" data-composition-id="{sid}" data-composition-src="compositions/{sid}.html" data-start="{start:.3f}" data-duration="{slot:.3f}" data-width="1920" data-height="1080" data-track-index="0"></div>')
  audios.append(f'<audio id="voice-{sid}" src="assets/{sid}.wav" data-start="{start+0.35:.3f}" data-duration="{duration:.3f}" data-track-index="1"></audio>')
  meta.append(dict(id=sid,start=round(start,3),duration=round(slot,3),voice_duration=duration,title=s['title']))
  start+=slot
 page=f'<!doctype html><html lang="es"><head><meta charset="utf-8"><title>{E(data["title"])}</title><script src="assets/gsap.min.js"></script><style>{css}</style></head><body><div id="root" data-composition-id="main" data-width="1920" data-height="1080" data-duration="{start:.3f}">{"".join(hosts+audios)}</div><script>window.__timelines["main"]=gsap.timeline({{paused:true}});</script></body></html>'
 (p/'index.html').write_text(page)
 (p/'timing.json').write_text(json.dumps({'duration':round(start,3),'fps':30,'voice':'ef_dora','chapters':meta},ensure_ascii=False,indent=2))
 (p/'STORYBOARD.md').write_text('\n\n'.join(f"## Frame {i+1}\nstatus: animated\nsrc: compositions/{s['id']}.html\nMotion: spring-pop-entrance\nStart: {meta[i]['start']}\nDuration: {meta[i]['duration']}\nBeat: {s['title']}\nNarración: {s['narration']}" for i,s in enumerate(scenes)))
 print(p.name,round(start,2),'segundos')
