from pathlib import Path
import json,html
R=Path(__file__).resolve().parents[1]; D=R/'slides'; slides=json.loads((D/'content.json').read_text())
e=html.escape
# Keep resource links across regeneration of the narrative.
link_manifest=D/'resource-links.json'
if link_manifest.exists():
 for slide in slides:
  slide.update(json.loads(link_manifest.read_text()).get(slide['id'],{}))
for slide in slides:
 for link in slide.get('resource_links',[]):
  if not link['url'].startswith('codigo/'): continue
  source=R/link['url'].removeprefix('codigo/').removesuffix('.html').replace('--','/')
  target=D/link['url']; target.parent.mkdir(exist_ok=True)
  relative=source.relative_to(R).as_posix()
  lines=''.join('<span id="L'+str(i)+'"><a href="#L'+str(i)+'">'+str(i)+'</a> '+e(line)+'</span>\n' for i,line in enumerate(source.read_text().splitlines(),1))
  target.write_text('<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+e(relative)+' · S08</title><style>body{font:18px system-ui;margin:32px;color:#122b43}header{max-width:1000px}a{color:#533afd}pre{font:14px/1.6 ui-monospace,monospace;overflow:auto;background:#f6f9fc;padding:20px}pre span{display:block}pre span:target{background:#fff0ad}pre a{display:inline-block;width:4ch;color:#65788a}p{line-height:1.5}</style><header><h1>'+e(relative)+'</h1><p>Código del repositorio local · Neptuno S08. Esta copia permite examinar el script sin ejecutarlo.</p><p>GitHub: acceso pendiente de verificar; los remotos configurados devolvieron 404 el 30/09/2026. No se presenta esta copia como una publicación remota.</p><p><a href="../../'+e(relative,quote=True)+'">Abrir archivo original</a> · <a href="../S08-autonomo.html#'+str(int(slide['id'].split('-')[1]))+'">Volver a las diapositivas</a></p></header><pre>'+lines+'</pre></html>')

def resource_block(s):
 links=s.get('resource_links',[])
 if not links:return ''
 return '<div class="resource-block"><p>'+e(s.get('resource_summary',''))+'</p><div>'+ ' · '.join('<a href="'+e(x['url'],quote=True)+'" target="_blank" rel="noopener">'+e(x['title'])+'</a>' for x in links)+'</div></div>'


def body(s):
 b=s['body']; k=s['kind']
 if k=='glossary': return '<p class="glossary-hint">Haz clic en un término para ver su significado · desplázate para consultar los demás.</p><div class="glossary-list" tabindex="0" aria-label="Términos del glosario">'+''.join('<details><summary>'+e(term)+'</summary><p>'+e(definition)+'</p></details>' for term,definition in b)+'</div>'
 if k=='metrics':
  return '<div class="metrics">'+''.join('<div class="metric-row"><strong>'+e(m['label'])+'</strong><div class="metric-track"><div class="metric-fill" style="width:'+str(100*m['correct']/m['total'])+'%"></div></div><span>'+str(m['correct'])+'/'+str(m['total'])+'</span></div>' for m in s['metrics'])+'</div><p class="note">20/20 casos juzgados por versión · cero errores de ejecución<br>Mismo benchmark y juez · revisión humana pendiente</p>'
 if k=='hero':return '<p class="lead">'+e(b[0])+'</p><p class="sub">'+e(b[1])+'</p>'
 if k=='task':return '<p class="task">'+e(b[0])+'</p><div class="accept"><strong>Checkpoint · </strong>'+e(b[1])+'</div>'
 if k=='quiz':return '<div class="quiz">'+''.join('<div class="question"><p>'+e(q)+'</p><p class="solution">'+e(a)+'</p></div>' for q,a in b)+'</div>'
 css='flow' if k=='flow' else 'pair'; sub='node' if k=='flow' else 'column'
 return '<div class="'+css+'">'+''.join('<div class="'+sub+'"><div class="label">'+e(a)+'</div><p>'+e(t)+'</p></div>' for a,t in b)+'</div>'
parts=[]
for s in slides:
 dark=' dark' if s['kind']=='hero' else ''
 refs=''.join('<a class="mk" href="'+e(u,quote=True)+'" target="_blank" rel="noopener" aria-label="Fuente oficial">★</a>' for u in s['refs'])
 parts.append(f'<section id="{s["id"]}" class="slide layout-{s["kind"]}{dark}" data-requirement="'+e(' '.join(s['requirements']))+'"><main class="stage"><p class="ey">'+e(s['ey'])+refs+'</p><'+('h1' if s['kind']=='hero' else 'h2')+'>'+e(s['title'])+'</'+('h1' if s['kind']=='hero' else 'h2')+'><div class="body">'+body(s)+resource_block(s)+'</div></main><div class="foot"><span>Databricks AI Engineer · Manuel Argüelles</span><span>S08 · Deployment y monitoreo</span></div><aside class="speaker-note">'+e(s['notes'])+'</aside></section>')
controls='''<nav id="ctl" aria-label="Controles"><button id="bPrev" aria-label="Anterior">←</button><button id="bNext" aria-label="Siguiente">→</button><button id="bTema" aria-pressed="false">Tema: índigo</button><button id="bMenos" aria-label="Reducir texto">A−</button><button id="bMas" aria-label="Aumentar texto">A+</button><button id="bMarcas" aria-expanded="false">★ Fuentes</button><button id="bNotes" aria-expanded="false">Notas</button><button id="bAnswers" aria-pressed="false">Respuestas</button></nav><div id="num"></div><div id="hint">← → navegar · N notas · T tema · F pantalla completa</div><div id="bar"></div>'''
refs=list(dict.fromkeys(u for s in slides for u in s['refs']))
labels={}
p=R/'sources.json'
if p.exists():
 data=json.loads(p.read_text())
 entries=data if isinstance(data,list) else data.get('sources',[])
 for x in entries:
  if isinstance(x,dict):labels[x.get('url','')]=x.get('title',x.get('name',x.get('url','')))
panels='<aside class="panel" id="refsPanel" hidden><button id="refsClose">Cerrar ×</button><h3>Fuentes y documentación</h3>'+''.join('<p class="refs-item"><a target="_blank" rel="noopener" href="'+e(u,quote=True)+'">★ '+e(labels.get(u,u))+'</a></p>' for u in refs)+'</aside><aside class="panel" id="notesPanel" hidden><button id="notesClose">Cerrar ×</button><h3>Notas del instructor</h3><p id="notesTitle" class="note-heading"></p><p id="notesText"></p></aside>'
base='<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>S08 · Deployment y monitoreo</title>{style}</head><body>'+''.join(parts)+controls+panels+'{script}</body></html>'
(D/'S08-deck.html').write_text(base.replace('{style}','<link rel="stylesheet" href="deck.css">').replace('{script}','<script src="deck.js"></script>'))
(D/'S08-autonomo.html').write_text(base.replace('{style}','<style>'+(D/'deck.css').read_text()+'</style>').replace('{script}','<script>'+(D/'deck.js').read_text()+'</script>'))
print('Rendered',len(slides),'slides')

