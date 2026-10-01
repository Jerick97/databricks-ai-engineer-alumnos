"""Resume evidencia existente; nunca convierte ausencia de pruebas en éxito."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
R=Path(__file__).resolve().parents[1]
def read(name):
 p=R/'reports'/name
 return json.loads(p.read_text()) if p.exists() else {}
def row(label,file,condition):
 d=read(file)
 return f'| {label} | {"Comprobado" if d and condition(d) else "Pendiente / revisar"} | [{file}](reports/{file}) |'
rows=[
 row('Slides: visual y controles','visual-qa.json',lambda d:d.get('pass') is True),
 row('Estructura y enlaces del deck','structural-qa.json',lambda d:d.get('pass') is True or d.get('verdict')=='PASS'),
 row('Agente local: casos reales','lab-smoke-local.json',lambda d:len(d)>=6 and all(x.get('pass') is True for x in d)),
 row('Agente servido: casos reales','lab-smoke-serving.json',lambda d:len(d)>=6 and all(x.get('pass') is True for x in d)),
 row('Controles de seguridad reales','lab-security-smoke.json',lambda d:len(d)>=3 and all(x.get('pass') is True for x in d)),
 row('App: HTTP autenticado y respuesta de negocio','lab-app-http.json',lambda d:d.get('pass') is True and d.get('has_expected_business_answer') is True),
 row('Render del HTML de la App en móvil/escritorio','app-visual.json',lambda d:d.get('pass') is True),
 row('Importación y sincronización del paquete','import-validation.json',lambda d:d.get('pass') is True),
 row('Bundle dev validado','lab-bundle-validation.json',lambda d:d.get('status')=='PASS'),
 row('Prompt: cambio y reversión de alias','lab-prompts.json',lambda d:d.get('restored')==d.get('original') and d.get('challenger')!=d.get('original')),
 row('Canary custom con datos reales','lab-custom-canary-verified.json',lambda d:d.get('pass') is True),
 row('Rollback custom verificado','lab-custom-rollback-verified.json',lambda d:d.get('pass') is True),
 row('Monitor con perfil y drift','lab-monitor-verified.json',lambda d:d.get('pass') is True),
 row('Notebook completo en Databricks','notebook-observed.json',lambda d:d.get('pass') is True and d.get('notebook_sha256')==hashlib.sha256((R/'notebook.py').read_bytes()).hexdigest() and all(d.get('checks',{}).get(x) is True for x in ['CP0_inventory','CP1_real_agent_and_clarification','CP2_serving_invocation','CP5_real_rows_and_unique_ids','CP5_parser_fixture','CP6_profile_metrics_observed'])),
]
text='''# S08 · Evidencia de validación

El cierre se registra en `reports/closure.json`, junto con los dictámenes independientes de currículo, pedagogía y ejecución. El cierre histórico del 27/09 omitía CP4 de navegador; no basta para acreditar la demo actual. Consulta `reports/class-day-browser.json` para el recorrido del 28/09 y `ABRIR-NOTEBOOK-DOCENTE.md` para la copia corregida. Los resultados describen el ensayo del docente; cada alumno necesita permisos, datos y recursos propios y debe repetir sus comprobaciones.

| Prueba | Resultado observado | Evidencia |
|---|---|---|
'''+ '\n'.join(rows)+'''

## Qué se entrega

52 slides navegables, notas por slide, fuentes oficiales, plan de 180 minutos, guía docente, consigna con 13 evidencias, notebook Python e IPYNB equivalentes, agente importable, App con backend, bundle dev/prod, scripts de observabilidad y rollout, plantilla de entrega y 12 preguntas originales de certificación con respuestas razonadas.

El ZIP y la copia en el repositorio de alumnos son entregas locales. La igualdad de archivos se comprueba en `reports/publication-parity.json`; no significa publicación remota ni ejecución por cada estudiante.

## Límites que se conservan

- **Agente y canary son dos endpoints.** `agent/v1/responses` no admite traffic splitting. El complemento custom consulta ventas reales de UC y demuestra 90/10 y reversión; sus dos versiones sólo cambian la etiqueta de revisión. No es un experimento de superioridad de calidad.
- **El notebook se ejecuta en modo verificar.** El source importado se compara por hash; las mutaciones se prueban con scripts separados. No ejecutar Run all en crear ni confundir una solicitud de despliegue con READY.
- **La App usa identidad de backend.** HTTP autenticado y respuesta de negocio prueban el servicio y el HTML. CP4 del 28/09 se comprobó en Chrome tras consentimiento autorizado: ventas con fuente y solicitud de aclaración ante año ausente (`reports/class-day-browser.json`). `reports/app-browser.json` conserva el bloqueo histórico. Un usuario nuevo puede requerir su propio consentimiento. No se afirma autorización por fila del usuario final.
- **Los logs son asíncronos.** Flatten procesa payloads reales mediante MERGE por ID. Baseline y métricas operativas no acreditan veracidad semántica ni ausencia universal de drift.
- **Bundle validado no equivale a CI desplegado.** Se entrega ejemplo de pipeline y separación de targets; no se ha promovido producción ni ejecutado ese CI remoto.
- **Gateway depende del tipo de endpoint.** No se promete usage tracking/rate limiting del endpoint de agentes si la plataforma no lo admite. La consulta de costos y la matriz de capacidades acompañan el ejercicio; tokens no equivalen a factura total.
- **Seguridad y calidad tienen muestra acotada.** Se conservan Safety y controles de herramientas; los casos reales prueban ese conjunto, no seguridad absoluta. El filtro puede tener falsos positivos.
- **Continuidad explícita.** El agente conserva consultas S05 y recuperación S04; S08 añade presentación determinista de hechos/citas. Ver `lab/CONTINUIDAD.md` para controles S07, fuente sintética y extensiones no desplegadas.

## Repetir y operar

Seguir [RUNBOOK.md](RUNBOOK.md) y [GUIA-DOCENTE.md](GUIA-DOCENTE.md). Preparar los dos endpoints y el monitor antes de clase; una construcción fría no cabe en el bloque CP3. El warehouse, modelos, Safety, Serving, App y monitor generan consumo. Conservar la evidencia antes de detener recursos.

## Dictámenes independientes

- `reports/curriculum-judge.json` contrasta los 13 requisitos con el temario original.
- `reports/coverage-judge.json` busca promesas sin explicación, práctica o archivo real.
- `reports/pedagogy-judge.json` revisa continuidad, ejemplos, tiempos y aceptación.
- `reports/execution-judge.json` revisa reproducibilidad y evidencia técnica.

Cada dictamen identifica el alcance y los hashes de los archivos revisados. `class_ready` exige todos los gates del alcance, no sólo que el HTML abra.
'''
(R/'VALIDACION.md').write_text(text)
print('Validation summary generated')
