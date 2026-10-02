from pathlib import Path
R=Path(__file__).resolve().parents[1]; cells=[]
def section(md,code):
 cells.append('# MAGIC %md\n'+'\n'.join('# MAGIC '+x for x in md.strip().splitlines()));cells.append(code.strip())
section('''# S08 · Neptuno se despliega y se observa vivo
180 minutos reloj estimados. Importa **la carpeta completa**, no sólo este notebook.
Cada celda explica entrada, efecto y resultado. `modo=verificar` recorre recursos existentes; `crear` habilita acciones en tu laboratorio. No ejecutar Run all en crear: Serving, Apps y logs son asíncronos.
**Widgets:** catálogo y warehouse propios; sufijo opcional por equipo (vacío genera hash de identidad); esquema vacío genera `ais08_<sufijo>`; s07_schema identifica la fuente sintética de S07. Los campos no aceptan credenciales. Sólo el instructor usa explícitamente sufijo `neptuno` y esquema `ais08_lab` para su ensayo.
Crear recursos, consultar SQL y llamar modelos genera consumo. La App comparte identidad de backend para el corpus autorizado; no promete permisos personales por fila.''','''dbutils.widgets.text("catalogo", "", "Catálogo propio")
dbutils.widgets.text("warehouse_id", "", "Warehouse asignado")
dbutils.widgets.text("sufijo", "", "Sufijo del equipo o automático")
dbutils.widgets.text("esquema", "", "Esquema AIS08 o automático")
dbutils.widgets.text("s07_schema", "", "Schema S07 propio, opcional")
dbutils.widgets.dropdown("modo", "verificar", ["verificar", "crear"], "Recorrido")
dbutils.widgets.dropdown("rollout", "inspeccionar", ["inspeccionar", "preparar", "canary", "rollback"], "Acción CP3")
dbutils.widgets.text("candidata", "", "Versión candidata evaluada")
dbutils.widgets.text("source_sha256", "", "Hash source provisto por validador")''')
section('''## CP0 · Instala dependencias del notebook
Esto instala Python en este cómputo, no en Serving. Las dependencias del modelo se registran aparte. Las versiones de rangos se documentan en la evidencia del entorno resuelto.''','''# MAGIC %pip install "mlflow[databricks]==3.16.1" "databricks-sdk==0.143.0" "openai==2.54.0" "jsonschema==4.26.0" "PyYAML>=6,<7"''')
section('''## CP0 · Reinicia Python
Los widgets permanecen. Continúa en la siguiente celda después del reinicio.''','''dbutils.library.restartPython()''')
section('''## CP0 · Conserva una configuración para notebook y Terminal
Entrada: widgets + config base sin secretos. Calcula nombres aislados; persiste **en tu copia del repo** `lab/config.json` para los scripts de esa misma copia. Si ejecutarás Terminal local, primero sincroniza con lab_import_workspace.py --pull-config según la guía; Workspace y ZIP local son copias distintas. No trabajar sobre la copia de otro equipo.
Comprueba funciones S05, tabla RAG S04 y Safety S07. La tabla sintética `documentos_aprobados` de S07 ilustra licencias; no sustituye el corpus real S04. Si un requisito falta, detén el paso dependiente.''','''import sys, json, os, hashlib, importlib
from pathlib import Path
from datetime import datetime, timezone
from databricks.sdk import WorkspaceClient
ROOT=Path.cwd()
assert (ROOT/"lab/agent.py").exists(), "Abre notebook.py dentro de s08-deployment del repo"
sys.path.insert(0,str(ROOT/"lab"))
from lab_config import build_config
w=WorkspaceClient(); identity=w.current_user.me().user_name
MODE=dbutils.widgets.get("modo")
CONFIG=build_config(json.loads((ROOT/"lab/config.json").read_text()),dbutils.widgets.get("catalogo").strip(),dbutils.widgets.get("warehouse_id").strip(),identity,dbutils.widgets.get("sufijo").strip(),dbutils.widgets.get("esquema").strip())
CONFIG['approved_schema']=dbutils.widgets.get('s07_schema').strip() or 's07_no_configurado'
(ROOT/"lab/config.json").write_text(json.dumps(CONFIG,indent=2))
(ROOT/"reports").mkdir(exist_ok=True)
for name in ['ventas_categoria','productos_reponer']:
    w.functions.get(f"{CONFIG['catalog']}.{CONFIG['source_schema']}.{name}")
w.tables.get(f"{CONFIG['catalog']}.rag.chunks_embeddings")
w.warehouses.get(CONFIG['warehouse_id'])
gate=w.serving_endpoints.get(CONFIG['moderation_endpoint']).ai_gateway.guardrails
assert gate.input.safety and gate.output.safety, "Configura filtros Safety S07 antes de continuar"
report={'session':'S08','mode':MODE,'started_utc':datetime.now(timezone.utc).isoformat(),'notebook_sha256':dbutils.widgets.get('source_sha256') or None,'checks':{},'resources':{k:CONFIG[k] for k in ['catalog','schema','model_name','endpoint','app_name']}}
report['checks']['CP0_inventory']=True
print(json.dumps(report['resources'],indent=2))''')
section('''## CP1 · Prueba el agente con APIs reales
El LLM selecciona herramientas; S08 formatea cifras/citas de sus resultados de manera determinista para conservar los hechos. Esto es un cambio explícito respecto al agente de notebook, no una medición de mejora universal.
Prueba ventas con año y aclaración sin año. Para la referencia del docente Bebidas2026=116024.88; otros datos requieren otra referencia. Safety sigue activo entrada/salida; un falso positivo se registra y se investiga, no se oculta.''','''from agent import AgenteNeptuno
from mlflow.types.responses import ResponsesAgentRequest
agent=AgenteNeptuno(CONFIG)
def text_of(response):
    d=response.model_dump() if hasattr(response,'model_dump') else response
    return '\\n'.join(p.get('text','') for item in d.get('output',[]) for p in item.get('content',[]) if p.get('type')=='output_text')
question='¿Cuánto vendimos de Bebidas en 2026?'
local=agent.predict(ResponsesAgentRequest(input=[{'role':'user','content':question}]))
assert text_of(local)
clarify=agent.predict(ResponsesAgentRequest(input=[{'role':'user','content':'¿Cuánto vendimos de Bebidas?'}]))
assert clarify.custom_outputs['tool_calls']==0
report['checks']['CP1_real_agent_and_clarification']=True
print(text_of(local));print(text_of(clarify))''')
section('''## CP1 · Registra o inspecciona la versión estable
En crear, empaqueta código/dependencias/recursos y prompt fijado. En verificar, consulta el alias existente, sin registrar ni promover otra versión. Alias mutable y versión numérica son cosas distintas.
La evidencia completa del harness vive en los reportes del laboratorio; estas dos solicitudes no sustituyen todos los casos S06/S07.''','''import mlflow
from mlflow import MlflowClient
mlflow.set_tracking_uri('databricks');mlflow.set_registry_uri('databricks-uc')
client=MlflowClient()
if MODE=='crear':
    import lab_deploy
    lab_deploy.CONFIG=CONFIG
    sys.argv=['lab_deploy.py','--package-only'];lab_deploy.main()
    package=json.loads((ROOT/'reports/lab-package.json').read_text())
else:
    version=client.get_model_version_by_alias(CONFIG['model_name'],'champion')
    package={'model_name':CONFIG['model_name'],'version':str(version.version),'source':version.source}
report['package']=package
print(package)''')
section('''## CP2 · Configura Serving con versión numérica
Crear solicita un endpoint nuevo y exige nombre libre; si ya existe, usa verificar. Una actualización del agente se gestiona como sustitución de versión única evaluada, no con el script de split CP3. No reemplaza recursos silenciosamente. La respuesta de creación sólo confirma envío.
En verificar se consulta configuración existente. Inference Tables usa configuración AI Gateway vigente, no legacy auto_capture. `scale_to_zero` admite arranque en frío.''','''from databricks.sdk.service import serving
if MODE=='crear':
    entity=serving.ServedEntityInput(name='champion',entity_name=CONFIG['model_name'],entity_version=package['version'],workload_size='Small',scale_to_zero_enabled=True)
    w.serving_endpoints.create(name=CONFIG['endpoint'],config=serving.EndpointCoreConfigInput(name=CONFIG['endpoint'],served_entities=[entity]),ai_gateway=serving.AiGatewayConfig(inference_table_config=serving.AiGatewayInferenceTableConfig(enabled=True,catalog_name=CONFIG['catalog'],schema_name=CONFIG['schema'],table_name_prefix='ais08_neptuno')))
endpoint=w.serving_endpoints.get(CONFIG['endpoint'])
print(endpoint.state.as_dict());print(endpoint.config.as_dict() if endpoint.config else 'Configuración pendiente')''')
section('''## CP2 · Consulta el servicio, no sólo su estado
Espera READY antes de ejecutar. La prueba produce tráfico real y consumo. Guarda ID de cliente para buscar la inferencia. Si falla, revisa permisos/logs; no conviertas error en éxito vacío.
Aceptación: respuesta no vacía y metadatos de versión del agente/prompt. Quality smoke completo se revisa aparte.''','''import uuid,time
assert endpoint.state.ready.value=='READY' and endpoint.state.config_update.value=='NOT_UPDATING','Provisioning/update pendiente: espera READY sin actualización'
assert str(package['version']) in {str(e.entity_version) for e in endpoint.config.served_entities},'La versión estable no está en la configuración activa'
request_id='s08-notebook-'+uuid.uuid4().hex
started=time.monotonic()
result=w.api_client.do('POST',f"/serving-endpoints/{CONFIG['endpoint']}/invocations",body={'input':[{'role':'user','content':question}],'client_request_id':request_id})
assert text_of(result), 'Respuesta vacía'
report['checks']['CP2_serving_invocation']=True
report['serving']={'client_request_id':request_id,'elapsed_seconds':round(time.monotonic()-started,3),'custom_outputs':result.get('custom_outputs',{}),'served_versions':[{'name':e.name,'version':e.entity_version} for e in endpoint.config.served_entities]}
print(text_of(result));print(report['serving'])''')
section('''## CP3 · Demuestra canary en un endpoint custom compatible
El agente principal `agent/v1/responses` **no admite traffic splitting**. Esta práctica usa otro endpoint `CONFIG.endpoint + '-rollout'`: un PythonModel que consulta ventas reales de UC. Sus dos versiones sólo cambian la etiqueta de revisión; no acreditan mejora de calidad ni un A/B causal.
En crear, selecciona rollout=preparar y ejecuta **sólo esta celda** para registrar/desplegar el custom; puede tardar más que el bloque de 15 minutos, por eso el docente lo prepara antes. Incluso los cambios de rutas pueden reprovisionar: la guía adelanta la solicitud de canary al bloque CP2 y verifica rollback después de la pausa o al cierre. Después de READY, usa canary con candidata=N y finalmente rollback. Inspeccionar sólo lee. No vuelvas a CP2 para medir este endpoint: su contrato es dataframe_records, no input de Responses.
El snapshot anterior es el contrato de reversión. Conserva reporte de configuración efectiva y consulta SQL real posterior; no basta la solicitud de actualización.''','''action=dbutils.widgets.get('rollout')
rollout_endpoint=CONFIG['endpoint']+'-rollout'
rollout_model=f"{CONFIG['catalog']}.{CONFIG['schema']}.ventas_rollout"
if action!='inspeccionar':
    assert MODE=='crear','Acción de CP3 exige modo crear'
    if action=='preparar':
        import lab_custom_rollout
        lab_custom_rollout.CONFIG=CONFIG
        sys.argv=['lab_custom_rollout.py','--deploy'];lab_custom_rollout.main()
    else:
        import lab_rollout
        lab_rollout.CONFIG=CONFIG
        if action=='canary':
            candidate=dbutils.widgets.get('candidata').strip()
            stable=client.get_model_version_by_alias(rollout_model,'champion')
            assert candidate.isdigit() and candidate!=str(stable.version),'Candidata custom distinta y evaluada'
            sys.argv=['lab_rollout.py','--challenger-version',candidate,'--percent','10']
        else:sys.argv=['lab_rollout.py','--rollback']
        lab_rollout.main()
rollout_state=w.serving_endpoints.get(rollout_endpoint)
effective=rollout_state.config
report['traffic']={'endpoint':rollout_endpoint,'task':rollout_state.task,'state':rollout_state.state.as_dict(),'routes':effective.traffic_config.as_dict() if effective and effective.traffic_config else {}}
print(report['traffic'])
if action=='inspeccionar':
    assert rollout_state.state.ready.value=='READY' and rollout_state.state.config_update.value=='NOT_UPDATING','Custom pendiente de preparación'
print('Inspección no acredita canary/rollback: adjunta reports/lab-rollout y verificación posterior del endpoint custom.')''')
section('''## CP4 · Despliega o inspecciona la App y prueba el navegador
Crear carga app/ y solicita deploy. Verificar consulta estado/URL. **ACTIVE de cómputo no demuestra respuesta de UI**: abre la URL, entra con identidad corporativa, consulta ventas y prueba una entrada inválida.
El backend usa su principal de servicio para el endpoint; no tiene tokens en browser ni autorización por usuario a cada fila.''','''if MODE=='crear':
    import lab_app
    lab_app.CONFIG=CONFIG
    sys.argv=['lab_app.py'];lab_app.main()
app=w.apps.get(CONFIG['app_name'])
report['app']={'url':app.url,'compute_status':app.compute_status.as_dict() if app.compute_status else {},'app_status':app.app_status.as_dict() if app.app_status else {}}
print(json.dumps(report['app'],indent=2))
print('Prueba UI y respuesta: seguir CONSIGNA CP4; status de API no la reemplaza.')''')
section('''## CP5 · Verifica logs reales y el resultado del flatten
Crear ejecuta MERGE por request_id mediante lab_monitor; repetirlo no debería duplicar filas. Verificar sólo consulta conteos/tablas ya procesadas. Los logs son asíncronos: el request recién creado puede tardar; inspecciona ventana e IDs de evidencia previa sin fingir inmediatez.
Tabla raw administrada no se modifica. Tabla flat conserva métricas, errores de parseo y longitudes sin texto completo. Cero filas bloquea la aceptación.''','''import lab_monitor
lab_monitor.CONFIG=CONFIG
if MODE=='crear':
    sys.argv=['lab_monitor.py'];lab_monitor.main()
schema=f"{CONFIG['catalog']}.{CONFIG['schema']}"
def query(statement):
    r=lab_monitor.sql(w,statement)
    return r.result.data_array or []
raw=query(f'SELECT count(*) FROM {schema}.ais08_neptuno_payload')
flat=query(f"SELECT count(*), count(DISTINCT request_id), sum(CASE WHEN parse_status='parse_error' THEN 1 ELSE 0 END) FROM {schema}.inference_flat")
assert int(raw[0][0])>0 and int(flat[0][0])>0,'Esperar logs y ejecutar flatten; no inventar filas'
assert flat[0][0]==flat[0][1],'IDs duplicados'
report['checks']['CP5_real_rows_and_unique_ids']=True
report['inference']={'raw_rows':int(raw[0][0]),'flat_rows':int(flat[0][0]),'parse_errors':flat[0][2]}
print(report['inference'])
# Elegimos un evento que ya llegó y fue aplanado; prioridad al request de CP2.
example=query(f"""SELECT r.databricks_request_id,r.client_request_id,r.request_time,r.status_code,
 get_json_object(r.response,'$.custom_outputs') AS raw_custom_outputs,
 f.latency_ms,f.tool_calls,f.tool_errors,f.parse_status
 FROM {schema}.ais08_neptuno_payload r JOIN {schema}.inference_flat f ON r.databricks_request_id=f.request_id
 ORDER BY CASE WHEN r.client_request_id='{request_id}' THEN 0 ELSE 1 END,r.request_time DESC LIMIT 1""")
assert example,'No se pudo correlacionar raw con flat'
keys=['request_id','client_request_id','request_time','status_code','raw_custom_outputs','latency_ms','tool_calls','tool_errors','parse_status']
report['inference_example']=dict(zip(keys,example[0]))
print(json.dumps(report['inference_example'],indent=2,default=str))
print('La ruta $.custom_outputs.tool_calls del JSON se convierte en tool_calls; compara ambos valores. latency_ms viene de execution_duration_ms.')
if example[0][1]!=request_id:print('Ejemplo previo real: el request de CP2 aún no está en la tabla plana. Conserva ambos IDs y espera ingestión.')
fixture=query((ROOT/'lab/lab_parse_contract.sql').read_text())
assert {x[0]:x[2] for x in fixture}=={'valido':'ok','texto_movido':'parse_error','error_http':'http_error'}
print('Fixture de extracción, NO tráfico real',fixture)
report['checks']['CP5_parser_fixture']=True''')
section('''## CP6 · Inspecciona perfil, baseline y métricas
Crear solicita un monitor; verificar lee el existente y sus salidas. Baseline es un snapshot real de eventos exitosos iniciales, no una referencia de verdad semántica. Con muestras pequeñas/similares, drift nulo o cero no demuestra calidad.
Revisa las tablas profile/drift y el refresh. El perfil puede representar un refresh anterior al SELECT de la tabla plana: compara ventanas y denominadores antes de mezclar sus cifras. Un monitor creado sin métricas es pendiente. Los juicios S06 y la revisión humana siguen midiendo calidad.''','''if MODE=='crear':
    sys.argv=['lab_monitor.py','--create-monitor'];lab_monitor.main()
table=w.tables.get(schema+'.inference_flat')
monitor=w.data_quality.get_monitor(object_type='table',object_id=table.table_id)
report['monitor']=monitor.as_dict()
report['monitor_refreshes']=[x.as_dict() for x in w.data_quality.list_refresh('table',table.table_id)]
print('Refreshes',report['monitor_refreshes'])
profile=query(f'SELECT count(*) FROM {schema}.inference_flat_profile_metrics')
drift=query(f'SELECT count(*) FROM {schema}.inference_flat_drift_metrics')
assert int(profile[0][0])>0 and int(drift[0][0])>0,'Refresh pendiente o fallido: revisar antes de aprobar'
report['checks']['CP6_profile_metrics_observed']=True
report['monitor_metrics']={'profile_rows':int(profile[0][0]),'drift_rows':int(drift[0][0])}
print(report['monitor_metrics'])
# Lectura de métricas, además de verificar que las tablas existen.
profile_name=schema+'.inference_flat_profile_metrics'
drift_name=schema+'.inference_flat_drift_metrics'
for label,name in [('profile',profile_name),('drift',drift_name)]:
    columns=[c.name for c in w.tables.get(name).columns]
    predicate=" WHERE column_name='latency_ms'" if 'column_name' in columns else ''
    examples=query(f'SELECT * FROM {name}'+predicate+' LIMIT 3')
    report[label+'_examples']=[dict(zip(columns,x)) for x in examples]
    print(label,json.dumps(report[label+'_examples'],default=str,indent=2))
window=query(f"SELECT min(event_time),max(event_time),count(*),avg(latency_ms),sum(CASE WHEN status_code>=400 THEN 1 ELSE 0 END) FROM {schema}.inference_flat")
report['metric_reading']=dict(zip(['start','end','requests','avg_latency_ms','http_errors'],window[0]))
print('Ventana y denominador observados',report['metric_reading'])
print('Compara las ventanas del perfil y drift con este agregado. Una media de N solicitudes sólo describe esas N; drift frente al baseline no mide veracidad semántica. Si drift es nulo, revisa tipo de columna, tamaño de muestra y baseline antes de concluir.')''')
section('''## CP7 · Valida la entrega declarativa desde Terminal
El CLI de bundles corre en Terminal del repo, no se presupone instalado en el runtime del notebook. Abre GUIA-DOCENTE sección Terminal: `databricks bundle validate -t dev --var ...` con tus variables. El ejemplo CI está en bundle/; una validación no equivale a corrida CI remota.
Aquí inspeccionamos el YAML entregado. Targets en un workspace no son aislamiento total; producción requiere identidades/recursos y destino separados. Costos incluyen modelo, Safety, SQL, App, Serving y monitoreo.''','''import yaml
bundle=yaml.safe_load((ROOT/'bundle/databricks.yml').read_text())
assert 'resources' in bundle and {'dev','prod'}<=set(bundle['targets'])
print('Recursos declarados',list(bundle['resources']))
print('Validación CLI real: revisar reporte lab-bundle-validation y repetir comandos de la guía con tu perfil.')
print((ROOT/'lab/lab_costs.sql').read_text())''')
section('''## CP7 · Observa versiones de prompt sin confundirlas con tráfico
El artefacto de Serving fija una versión de prompt. En verificar se consulta el alias y versión reportada por servicio. Para la práctica crear, registra una versión con el mismo contrato más una regla didáctica, mueve alias, comprueba resolución y restaura el alias anterior; **esto no despliega el texto nuevo al modelo fijo**.
Aceptación: IDs antes/después y retorno a la versión anterior. Un cambio de conducta requiere empaquetar/evaluar/desplegar otra versión; requiere empaquetar y actualizar la versión única; CP3 sólo demuestra split custom, no se atribuye al alias solo.''','''name=f"{schema}.neptuno_system"
before=mlflow.genai.load_prompt(f'prompts:/{name}@champion')
report['prompt']={'alias_before':str(before.version),'served_prompt_version':result.get('custom_outputs',{}).get('prompt_version')}
if MODE=='crear':
    candidate=mlflow.genai.register_prompt(name=name,template=before.template+'\\nMantén respuestas breves con fuente.',commit_message='S08 ejercicio de alias; no despliega Serving')
    try:
        mlflow.genai.set_prompt_alias(name,'champion',candidate.version)
        report['prompt']['candidate_resolved']=str(mlflow.genai.load_prompt(f'prompts:/{name}@champion').version)
    finally:mlflow.genai.set_prompt_alias(name,'champion',before.version)
    report['prompt']['alias_after']=str(mlflow.genai.load_prompt(f'prompts:/{name}@champion').version)
    assert report['prompt']['alias_after']==report['prompt']['alias_before']
print(report['prompt'])''')
section('''## CP8 · Conserva resultados y completa el portfolio
El reporte automatizado acredita sólo sus checks, no UI/canary/calidad universal. Completa las 13 entregas nombradas en CONSIGNA.md; `s08-final.md` enlaza todas, incluidas S06/S07 y límites de alcance.
No exportar payloads sensibles. Para el lunes consulta RUNBOOK.md: recursos detenidos requieren activación/prewarm. Después del ensayo conserva evidencia y limita consumo de recursos aislados.''','''report['finished_utc']=datetime.now(timezone.utc).isoformat()
(ROOT/'reports/notebook-observed.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str))
print('Checks observados',report['checks'])
print('Pendientes manuales: UI de usuario, juicio negocio completo, canary/rollback y decisiones de operación se prueban con evidencia separada.')
dbutils.notebook.exit(json.dumps(report,ensure_ascii=False,default=str))''')
(R/'notebook.py').write_text('# Databricks notebook source\n'+'\n\n# COMMAND ----------\n\n'.join(cells)+'\n')
print('Notebook generated',len(cells),'cells')
