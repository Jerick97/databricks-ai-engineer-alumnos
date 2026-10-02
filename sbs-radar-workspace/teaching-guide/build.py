from pathlib import Path
import json,html
R=Path(__file__).resolve().parents[1]; O=Path(__file__).resolve().parent
host='https://dbc-0410b264-20c7.cloud.databricks.com';org='7474657121564806'
links={
'app':('SBS Radar · aplicación real','https://sbs-radar-pilot-7474657121564806.aws.databricksapps.com/'),
'graph':('Diagrama Archify E2E','../../.archify/dataflow-sbs-e2e-20260930-082301/index.html'),
'ui':('Réplica explicada con hover y Foquito','../teaching-ui/index.html'),
'framework':('9 capas · 9 etapas · 12 decisiones','../web/index.html'),
'genie':('Espacio Genie del piloto',host+'/genie/rooms/01f1bb81787b118c9bbc8980e3523a21?o='+org),
'warehouse':('SQL Warehouse del piloto',host+'/sql/warehouses/828756322bedff37?o='+org),
'catalog':('Catálogo de tablas SBS Radar',host+'/explore/data/neptuno_manuel_arguelles/sbs_radar?o='+org),
'job':('Job SBS Radar · consultar estado',host+'/?o='+org+'#job/989326861421503'),
'run':('Ejecución histórica real del writer',host+'/?o='+org+'#job/989326861421503/run/817327291004649'),
'notebook':('Notebook SBS · writer','../notebooks/sbs-radar-cloud-writer.ipynb'),
'publish':('Notebook SBS · publicación Genie','../notebooks/sbs-radar-genie-publication.ipynb'),
'promotion':('Notebook SBS · promoción runtime','../notebooks/sbs-radar-runtime-promotion.ipynb'),
's08':('Notebook del curso S08 · distinto del notebook SBS',host+'/editor/notebooks/3142549814418784?o='+org),
'inventory':('Inventario exacto de las seis copias','../runs/ui246/test-source246/runs/sk06-pilot-002/documents.jsonl'),
'state':('Estado y pendientes de la entrega','../ESTADO-ENTREGA.md'),
'review':('Revisión independiente de consultas reales','../runs/sk09-astra-actual244-review.json'),
'appdocs':('Documentación oficial · Databricks Apps','https://docs.databricks.com/aws/en/dev-tools/databricks-apps/'),
'geniedocs':('Documentación oficial · Genie','https://docs.databricks.com/aws/en/genie/'),
'volumes':('Documentación oficial · Unity Catalog Volumes','https://docs.databricks.com/aws/en/volumes/'),
'jobsdocs':('Documentación oficial · Lakeflow Jobs','https://docs.databricks.com/aws/en/jobs/'),
'modeldocs':('Documentación oficial · Model Serving','https://docs.databricks.com/aws/en/machine-learning/model-serving/'),
'codeingest':('Código · captura y contratos','../src/sbs/foundation/__init__.py'),
'codeextract':('Código · extracción','../src/sbs/foundation/extract.py'),
'coderag':('Código entregado · recuperación híbrida','../runs/ui246/test-source246/src/sbs/retrieval/__init__.py'),
'codehybrid':('Código entregado · comparación y propuestas','../runs/ui246/test-source246/src/sbs/conversation/hybrid_125.py'),
'codeapp':('Código entregado · rutas de la App','../runs/ui246/test-source246/src/sbs/webapp/__init__.py')}
steps=[
('Definir qué problema resuelve', 'SK00–SK01 · canal, contratos y gobierno',
 'Un analista necesita saber qué dice una copia anterior, qué dice otra y qué podría revisar en un proceso bancario ficticio.',
 'Se fija la familia normativa, la norma, el par de copias y la disposición. El alcance de una consulta debe conservarse en todas sus herramientas.',
 'Un contexto explícito de consulta, no una pregunta sin referencia documental.',
 '“El agente nos ayuda a localizar, contrastar y documentar evidencia. Una implicancia propuesta todavía no es una decisión del banco.”',
 'Abre el diagrama y presenta las dos rutas: preparar datos y responder preguntas. Usa ciberseguridad, Resolución 504-2021, artículo 20.3 como hilo conductor.',
 'Pide al alumno identificar qué datos faltan en “¿qué cambió?”. Debe responder: norma, copias y punto a comparar.', ['graph','framework','app']),
('Registrar e ingerir los PDF oficiales','SK02 · entrada y seguridad',
 'URLs explícitas de fuentes SBS y una lista de hosts permitidos.',
 'Se valida la URL, se descarga el PDF, se revisa su formato y se calcula SHA256. El original se conserva por contenido; el registro guarda procedencia e intento de captura. Una descarga repetida idéntica no crea un contenido nuevo.',
 'SourceDocument: identidad de norma, familia, URL, hash y fecha de captura. Publicación y vigencia pueden quedar desconocidas.',
 '“Guardar la fuente es conservar la prueba. El hash identifica estos bytes; no indica cuándo entró en vigor la norma.”',
 'Muestra dos enlaces SBS del inventario y contrasta sus identificadores. Explica las seis copias y los dos pares disponibles.',
 '¿Seis PDF significan seis normas? No: hay cuatro resoluciones y seis versiones documentales únicas.', ['inventory','codeingest']),
('Extraer texto con trazabilidad','SK02 · normalización',
 'Los PDF originales identificados por hash.',
 'pypdf extrae texto y registra páginas, posiciones de caracteres —offsets— y señales de calidad. Se conservan el texto extraído y la relación con el original. Tablas, anexos y cortes de palabras requieren atención adicional.',
 'Texto verificable por página y fragmento, con límites de cobertura explícitos.',
 '“El modelo no debe inventar dónde está una frase. Guardamos el camino desde el fragmento hasta la página del PDF.”',
 'En Comparación abre un original y busca el artículo seleccionado. Un texto extraído correcto no sustituye la revisión visual del PDF.',
 'Comprueba una frase literal y su página. Si difieren, marca el problema de extracción antes de interpretar.', ['codeextract','app']),
('Identificar pares y comparar disposiciones','SK03 · versiones y razonamiento',
 'Dos copias de la misma norma y unidades documentales alineadas.',
 'Se resuelven las correspondencias antes/después y se comparan pasajes. Se mantienen separadas la diferencia textual, la interpretación del cambio y la implicancia propuesta.',
 'Un par documental y evidencia de comparación. Cobertura parcial no permite afirmar que no existan otros cambios.',
 '“El selector ofrece un par por familia. Una opción contiene dos copias, A y B; no significa una única versión.”',
 'Selecciona 504-2021 / artículo 20.3. Después cambia a conducta de mercado / 3274-2017 / artículo 27 y observa que el contexto cambia completo.',
 '¿Cambiar un salto de línea implica cambiar una obligación? No: hay que revisar el contenido y su contexto.', ['ui','codehybrid','app']),
('Preparar la recuperación RAG','SK04–SK05 · recuperación',
 'Fragmentos con identidad de documento, versión, familia, página y offsets.',
 'Se preparan unidades de recuperación y sus embeddings. Un embedding es una representación numérica útil para buscar similitud. Se fija modelo e identidad del índice; los vectores compatibles ya calculados pueden reutilizarse. El piloto conserva limitaciones de segmentación y cobertura.',
 'Un índice local de pasajes y vectores, más metadatos para filtrar y citar.',
 '“No enviamos todos los PDF en cada pregunta. Primero preparamos una forma de localizar fragmentos pertinentes.”',
 'Abre el código RAG o el nodo Índice local del diagrama. Aclara que este piloto usa LocalIndex: no hay que presentarlo como Databricks Vector Search desplegado.',
 'Distingue el fragmento usado para buscar de la evidencia ampliada y autorizada usada para responder.', ['graph','coderag','modeldocs']),
('Curar y publicar datos para consumo','SK06–SK11 · herramientas y persistencia',
 'Metadatos, comparación, identidad del índice RAG y procesos bancarios ficticios.',
 'Se forman ocho tablas: documents, versions, provisions, pairs, changes, evidence, reviews y processes. Hay dos publicadores: publication_writer publica tablas Genie en Delta UC; cloud_writer publica artefactos en UC Volumes y un control/puntero Delta. Publicar esos artefactos no actualiza automáticamente la App.',
 'Datos estructurados y artefactos verificables. RAG y Genie conservan snapshots distintos reconciliados mediante un mapping explícito.',
 '“Las tablas sirven para contar y relacionar datos. Los PDF y artefactos conservan evidencia. Deben corresponder al mismo contenido verificado, aunque sus identificadores de snapshot no sean iguales.”',
 'Abre el catálogo y después la ejecución histórica del writer. Muestra el notebook como explicación de implementación; no ejecutes una publicación nueva sólo para enseñar que existe.',
 '¿Una fila en changes prueba un cambio normativo material confirmado? No; revisa granularidad, cobertura y estado de revisión.', ['catalog','publish','notebook','run','volumes']),
('Recibir la pregunta y aplicar controles','SK07–SK08 · canal, borde y ruteo',
 'Pregunta del usuario, sesión y selección de familia, par y disposición.',
 'La App verifica identidad y acceso. El backend resuelve el contexto autorizado y los límites de consumo. Clasifica si la pregunta pide conteo, comparación o implicancias. Los datos del cliente o del PDF no conceden permisos.',
 'Una consulta delimitada y dirigida a la herramienta correspondiente.',
 '“Antes de buscar, debemos saber para quién buscamos y dentro de qué documentos.”',
 'En la App selecciona el artículo y pregunta “¿Cómo estaba antes y cómo está ahora?”. Para ambas familias usa el alcance cruzado explícito; conserva conclusiones y citas separadas.',
 'Comprueba que cambiar de familia no arrastre una disposición incompatible de la anterior.', ['app','codeapp','appdocs']),
('Recuperar evidencia: híbrida, RRF y reranking','SK04–SK05–SK08 · grounding',
 'La pregunta y el conjunto de documentos autorizado.',
 'BM25 encuentra coincidencias léxicas; la búsqueda vectorial aproxima el significado. RRF combina posiciones de ambas listas; no suma directamente sus puntuaciones incompatibles. El reranker vuelve a evaluar relevancia sobre candidatos. Se aplican alcance y correspondencias A/B para formar evidencia utilizable.',
 'Un EvidencePack con pasajes, citas, trazas y límites. Obtener resultados no certifica completitud normativa.',
 '“BM25 ayuda con términos exactos; vectores con maneras distintas de decir algo; RRF reúne candidatos; el reranker ordena cuáles responden mejor.”',
 'En el mapa sigue Índice local → Recuperación híbrida. Embedding del piloto: databricks-qwen3-embedding-0-6b. Reranker: cross-encoder/mmarco-mMiniLMv2-L12-H384-v1, ONNX local.',
 'Ejemplo didáctico: un pasaje puesto 1 en una lista y 3 en otra recibe 1/(k+1)+1/(k+3) en RRF. k es una constante de la configuración; este ejemplo no fija su valor en producción.', ['coderag','graph']),
('Usar Genie para preguntas estructuradas','SK06–SK07 · consulta de datos',
 'Una pregunta de conteo/listado y contexto delimitado.',
 'Genie consulta las tablas estructuradas mediante el SQL Warehouse. El adaptador verifica alcance y procedencia según sus controles. La ruta de conteo puro devuelve una respuesta tipada sin pasar por el generador normativo; Genie sigue siendo un servicio de IA.',
 'Filas o conteos con su alcance. No son una opinión jurídica ni un resumen completo de los PDF.',
 '“Para contar versiones consultamos datos estructurados. Para explicar un pasaje recuperamos evidencia textual. Son capacidades complementarias.”',
 'Pregunta por cuántas versiones hay en el par seleccionado: se esperan dos. El inventario completo contiene seis copias; son dos alcances diferentes. No uses el conteo del par como total del corpus.',
 'Pide al alumno decidir si “¿cuántas versiones?” va a Genie y si “¿qué dice el artículo?” necesita evidencia RAG.', ['genie','warehouse','geniedocs','inventory']),
('Construir y validar la respuesta','SK07–SK08–SK09 · razonamiento y validación',
 'Pasajes anteriores/posteriores, contexto y resultados de herramientas.',
 'La ruta híbrida conserva la parte extractiva y puede usar databricks-qwen35-122b-a10b para propuestas de impacto. El servidor compone el contrato de respuesta y verifica citas y referencias contra evidencia autorizada. La evaluación semántica independiente es un control adicional; no queda resuelta sólo porque una cita exista.',
 'Antes, después, explicación y, cuando corresponde, implicancia propuesta con límites y fuentes.',
 '“Una respuesta convincente no basta: debemos poder volver de cada afirmación a la evidencia. Además, una cita correcta puede acompañar una interpretación equivocada.”',
 'Pide una propuesta para un proceso ficticio. Abre las citas y distingue la afirmación literal de la recomendación. La revisión pendiente no impide conversar; no hay aprobación institucional disponible en esta sesión.',
 'Pregunta “¿qué evidencia respalda esa implicancia?”. Si falta sustento, se declara la limitación; no se inventa una obligación.', ['app','codehybrid','review','modeldocs']),
('Presentar el recorrido en Databricks Apps','SK10–SK12 · experiencia y despliegue',
 'Backend, frontend, fuentes y configuración del paquete entregado.',
 'Novedades permite elegir un par; Comparación muestra A/B y originales; Chat permite preguntas y seguimiento. Databricks Apps aloja la aplicación. La App utiliza un paquete/snapshot verificado; la promoción automática desde el writer sigue pendiente.',
 'Un recorrido visible de usuario que conecta selección, evidencia y conversación.',
 '“La App reúne las capacidades: no reemplaza los datos, la recuperación ni las validaciones.”',
 'Abre el agente real para consultar datos. Usa la réplica con hover para explicar controles: su Foquito es un tutor separado, no ejecuta Genie ni el backend SBS. Actualizar catálogo en la réplica sólo muestra una explicación; en la App relee el corpus publicado y no ejecuta el Job.',
 'El alumno debe poder decir en qué pantalla ve una fuente, dónde cambia el alcance y cuándo está usando una guía local.', ['app','ui','appdocs','promotion']),
('Observar, evaluar y operar','SK09–SK11–SK12 · mejora y operación',
 'Ejecuciones, hashes, métricas, resultados de pruebas y revisión de muestras.',
 'Se conservan trazas y versiones para reconstruir resultados. Se revisan recuperación, citas, propuestas y fallos. La última evidencia aprobó muestras reales; no acredita cobertura universal, ahorro humano ni funcionamiento continuo.',
 'Estado de entrega y gates pendientes: Job diario pausado, promoción continua, recuperación cloud y evaluación independiente completas abiertas.',
 '“Un piloto demostrable y una operación continua tienen criterios de cierre distintos. Un Job configurado no es un Job diario funcionando.”',
 'Muestra el Job en lectura y la evidencia histórica de ejecución. Antes de la demo verifica sesión, catálogo, originales y cupo del chat. Un cupo vencido no implica que la App esté apagada.',
 'Si el chat no está disponible, muestra comparación y originales, y explica el bloqueo real. No presentes una respuesta guardada como generada en vivo.', ['job','run','state','jobsdocs'])]
def a(key):
 label,url=links[key];return '<a href="'+html.escape(url,quote=True)+'" target="_blank" rel="noopener">'+html.escape(label)+'</a>'
from skill_mapping import build as build_skill_mapping
skill_section,skill_map,skill_link=build_skill_mapping(steps)
sections=[]
for i,(title,skill,inp,work,out,script,demo,check,refs) in enumerate(steps,1):
 sections.append(f'<section id="paso{i}"><span class="tag">PASO {i:02} · {html.escape(skill)}</span><h2>{html.escape(title)}</h2>'+''.join('<div class="'+c+'"><h3>'+t+'</h3><p>'+html.escape(v)+'</p></div>' for c,t,v in [('','Qué entra',inp),('','Qué ocurre',work),('','Qué sale',out),('say','Cómo explicarlo',script),('demo','Qué mostrar',demo),('','Pregunta para los alumnos',check)])+'<div class="refs">'+''.join(a(k) for k in refs)+'</div></section>')
rows=[json.loads(json.loads(l)['payload_json']) for l in (R/'runs/ui246/test-source246/runs/sk06-pilot-002/documents.jsonl').read_text().splitlines() if l]
pdfs=''.join('<tr><td>'+html.escape(r['document_id'].upper())+'</td><td>'+('Ciberseguridad' if r['family']=='cybersecurity' else 'Conducta de mercado')+'</td><td><a href="'+html.escape(r['url'],quote=True)+'" target="_blank" rel="noopener">PDF original SBS ↗</a></td><td><code>'+r['sha256'][:12]+'</code></td></tr>' for r in sorted(rows,key=lambda r:(r['document_id'],r['url'])))
nav=''.join(f'<a href="#paso{i}">{i:02} · {html.escape(s[0])}</a>' for i,s in enumerate(steps,1))
for i,(primary,support) in enumerate(skill_map):
 skill_box='<div class="refs"><strong>Skills principales:</strong> '+', '.join(skill_link(n) for n in primary)+'<br><strong>Apoyo / revisión:</strong> '+', '.join(skill_link(n) for n in support)+'</div>'
 sections[i]=sections[i].replace('</section>',skill_box+'</section>')
body=''.join(sections)

page='''<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SBS Radar · Guía docente E2E</title><style>*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f4f6f3;color:#173334;font:16px/1.65 system-ui}header{padding:40px max(5%,calc((100vw - 1380px)/2));background:#103d3a;color:white}h1{font-size:38px;line-height:1.2;max-width:850px}header p{max-width:920px}header a{color:#fff}button{font:inherit;background:#fff;border:0;border-radius:7px;padding:10px 16px;cursor:pointer}main{display:grid;grid-template-columns:260px minmax(0,950px);gap:35px;max-width:1320px;margin:30px auto;padding:0 22px}nav{position:sticky;top:20px;align-self:start;font-size:13px;max-height:94vh;overflow:auto}nav a{display:block;padding:7px 9px;text-decoration:none;border-bottom:1px solid #d5dfd9}a{color:#19665e;overflow-wrap:anywhere}section{background:#fff;border:1px solid #d5dfd9;border-radius:12px;margin-bottom:26px;padding:30px;scroll-margin-top:20px}h2{font-size:27px;line-height:1.3;margin:10px 0 22px}h3{font-size:15px;margin:17px 0 4px}p{margin:4px 0 12px}.tag{font-size:11px;font-weight:700;letter-spacing:1px;color:#51766a}.say{background:#edf5ef;border-left:4px solid #357263;padding:6px 16px;margin:18px 0}.demo{background:#fff8e6;border-left:4px solid #c49a40;padding:6px 16px}.refs{display:flex;gap:8px;flex-wrap:wrap;margin-top:20px}.refs a{border:1px solid #d5dfd9;border-radius:6px;padding:6px 10px;font-size:12px}table{width:100%;border-collapse:collapse;font-size:13px}td,th{vertical-align:top;padding:10px;text-align:left;border-bottom:1px solid #d5dfd9}small{color:#56716a}.resource{margin:14px 0}.resource a{font-weight:650}.url{display:block;font-size:11px;overflow-wrap:anywhere;color:#5b726d}details{padding:10px 0}summary{cursor:pointer;font-weight:650}@media(max-width:850px){main{display:block}nav{position:static;max-height:220px;margin-bottom:25px}header{padding:25px}h1{font-size:30px}section{padding:21px}}@media print{nav,button{display:none}main{display:block;margin:0;max-width:none}header{background:white;color:#173334;padding:15px}section{break-inside:avoid;border:0;border-bottom:1px solid #aaa;border-radius:0;padding:15px}a{color:#173334}h1{font-size:27px}}</style><header><span>GUÍA DOCENTE · DATABRICKS AI ENGINEER</span><h1>Cómo funciona SBS Radar, de principio a fin</h1><p>Una explicación que puedes seguir en clase: fuentes → preparación → publicación → recuperación → conversación → aplicación → operación.</p><p>Estado documentado: 30 de septiembre de 2026. Piloto probado por muestras; operación continua aún incompleta. Estos 12 pasos didácticos no sustituyen las 9 capas, las 9 etapas de preparación ni las 12 decisiones del framework.</p><button onclick="window.print()">Imprimir / guardar PDF</button></header><main><nav aria-label="Contenido"><a href="#inicio">Preparar la explicación</a>'''+nav+'''<a href="#skills">Pasos y skills SK00–SK12</a><a href="#demo">Guion de demostración</a><a href="#documentos">Los seis PDF SBS</a><a href="#recursos">URLs y recursos</a><a href="#preguntas">Preguntas frecuentes</a></nav><article><section id="inicio"><span class="tag">ANTES DE EMPEZAR</span><h2>Qué van a aprender</h2><p>Seguir una respuesta hasta su documento de origen; distinguir recuperación textual de consulta estructurada; explicar por qué una cita, una diferencia y una aprobación son cosas distintas.</p><p><strong>Duración sugerida: 50–60 minutos.</strong> Presentación del caso 5 min; preparación y publicación 15 min; consulta y validación 15 min; demostración 15 min; preguntas 10 min. Es una propuesta docente, no tiempo medido de ejecución.</p><p>Abre primero el diagrama, después la App real y dos PDF. Usa la guía de hover para enseñar controles. Los recursos del workspace requieren sesión y permisos; los archivos locales sólo abren en una máquina que tenga esta carpeta.</p><div class="refs">'''+a('graph')+a('app')+a('ui')+a('framework')+'''</div></section>'''+skill_section+body+'''<section id="demo"><span class="tag">RECORRIDO PARA MOSTRAR EN CLASE</span><h2>Demostración de 15 minutos</h2><ol><li><strong>Antes de comenzar:</strong> abre la App real, verifica catálogo y acceso a originales. Revisa el estado de consultas y su cupo. No uses saldos históricos como si fueran actuales.</li><li><strong>Novedades:</strong> selecciona ciberseguridad, 504-2021, artículo 20.3. Explica que la opción contiene un par.</li><li><strong>Comparación:</strong> abre ambas copias y localiza el artículo. Pide al alumno señalar una diferencia observable sin concluir aún su efecto jurídico.</li><li><strong>Chat:</strong> “En el artículo seleccionado, ¿cómo estaba antes y cómo está ahora? Cita ambas copias”. Contrasta la respuesta con los PDF.</li><li><strong>Seguimiento:</strong> “Sobre ese mismo punto, ¿qué proceso ficticio deberíamos revisar y qué evidencia sustenta tu propuesta?”. Señala lo literal y lo propuesto.</li><li><strong>Genie:</strong> “¿Cuántas versiones documentales hay en este par?”. Esperado: dos; no confundir con las seis copias del inventario completo.</li><li><strong>Segunda familia:</strong> cambia a conducta de mercado, artículo 27; luego artículo 29.1.4. Repite una pregunta y comprueba que las citas cambian con el contexto.</li><li><strong>Cierre:</strong> vuelve al diagrama y pide a un alumno recorrer el camino de una pregunta y el de una fuente nueva.</li></ol><p><strong>Si una consulta falla:</strong> conserva el error, revisa sesión, disponibilidad y cupo. Continúa mostrando fuentes y comparación si están disponibles. Usa evidencias archivadas sólo identificándolas como históricas.</p></section><section id="documentos"><span class="tag">INVENTARIO VERIFICADO EN EL PAQUETE</span><h2>Seis copias · cuatro resoluciones · dos pares</h2><p>504-2021 tiene dos copias, v4 y v5; 3274-2017 tiene dos, v7 y v8. 2286-2024 y 2220-2025 aportan una copia cada una. Los dos pares comparables visibles utilizan cuatro de estos seis PDF. Las otras copias no se convierten automáticamente en nuevos pares.</p><p>Las etiquetas vN provienen de las rutas del repositorio SBS. No certifican fechas de vigencia. El hash distingue contenidos, no interpretaciones jurídicas.</p><table><thead><tr><th>Resolución</th><th>Familia</th><th>Fuente</th><th>SHA256 abreviado</th></tr></thead><tbody>'''+pdfs+'''</tbody></table></section><section id="recursos"><span class="tag">ABRIR, MOSTRAR Y PROFUNDIZAR</span><h2>URLs y archivos del recorrido</h2><p>La App y el run usan URLs conservadas en la evidencia. Los enlaces de navegación a Genie, Warehouse y Catálogo se construyeron con IDs registrados; requieren sesión y no se validaron autenticados en esta entrega. Si la interfaz cambia, usa el ID indicado en la URL desde el menú correspondiente del workspace.</p>'''+''.join('<div class="resource">'+a(k)+'<span class="url">'+html.escape(url)+'</span></div>' for k,(label,url) in links.items())+'''<details><summary>Procedencia y alcance de esta guía</summary><p>Se reutilizaron el código de App246, el inventario documents.jsonl, ESTADO-ENTREGA, la evidencia del writer y los diagramas Archify. La documentación oficial de Apps, Genie, Volumes, Jobs y Model Serving fue consultada el 30/09/2026. Los enlaces oficiales explican productos; no prueban que todas sus capacidades estén desplegadas aquí.</p><p>Esta elaboración documental no vuelve a ejecutar notebooks, no activa Jobs, no publica tablas ni renueva inferencia. El notebook S08 corresponde al curso y no debe presentarse como el notebook SBS final ejecutado con App246.</p></details></section><section id="preguntas"><h2>Preguntas que conviene anticipar</h2><details><summary>¿Por qué usamos RAG si ya tenemos Genie?</summary><p>RAG recupera pasajes para fundamentar afirmaciones. Genie consulta datos estructurados. El problema exige ambas capacidades.</p></details><details><summary>¿El LLM compara todos los PDF cada vez?</summary><p>No. Se prepara y recupera evidencia delimitada; la ruta híbrida preserva extracción y usa generación cuando corresponde. La conversación no implica que toda la norma entre en cada llamada.</p></details><details><summary>¿Necesitamos aprobación experta para conversar?</summary><p>No. Se puede conversar sobre evidencia pendiente de revisión. La aprobación institucional del impacto es otra acción y no está disponible en esta sesión.</p></details><details><summary>¿La solución se actualiza sola todos los días?</summary><p>No en el estado documentado: el Job está pausado y la promoción continua del nuevo snapshot a la App sigue pendiente.</p></details><details><summary>¿Cómo sabemos que está bien?</summary><p>Combinamos contratos, comprobaciones de citas, pruebas reales y revisión semántica de muestras. Ninguna de esas comprobaciones aislada acredita cobertura completa o vigencia jurídica.</p></details></section></article></main></html>'''
(O/'index.html').write_text(page)
(O/'content.json').write_text(json.dumps({'steps':steps,'resources':links,'date':'2026-09-30'},ensure_ascii=False,indent=2))
print('Guía generada:',O/'index.html')
