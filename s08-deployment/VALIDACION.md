# S08 · Evidencia de validación

El cierre se registra en `reports/closure.json`, junto con los dictámenes independientes de currículo, pedagogía y ejecución. El cierre histórico del 27/09 omitía CP4 de navegador; no basta para acreditar la demo actual. Consulta `reports/class-day-browser.json` para el recorrido del 28/09 y `ABRIR-NOTEBOOK-DOCENTE.md` para la copia corregida. Los resultados describen el ensayo del docente; cada alumno necesita permisos, datos y recursos propios y debe repetir sus comprobaciones.

| Prueba | Resultado observado | Evidencia |
|---|---|---|
| Slides: visual y controles | Comprobado | [visual-qa.json](reports/visual-qa.json) |
| Estructura y enlaces del deck | Comprobado | [structural-qa.json](reports/structural-qa.json) |
| Agente local: casos reales | Comprobado | [lab-smoke-local.json](reports/lab-smoke-local.json) |
| Agente servido: casos reales | Comprobado | [lab-smoke-serving.json](reports/lab-smoke-serving.json) |
| Controles de seguridad reales | Comprobado | [lab-security-smoke.json](reports/lab-security-smoke.json) |
| App: HTTP autenticado y respuesta de negocio | Comprobado | [lab-app-http.json](reports/lab-app-http.json) |
| Render del HTML de la App en móvil/escritorio | Comprobado | [app-visual.json](reports/app-visual.json) |
| Importación y sincronización del paquete | Comprobado | [import-validation.json](reports/import-validation.json) |
| Bundle dev validado | Comprobado | [lab-bundle-validation.json](reports/lab-bundle-validation.json) |
| Prompt: cambio y reversión de alias | Comprobado | [lab-prompts.json](reports/lab-prompts.json) |
| Canary custom con datos reales | Comprobado | [lab-custom-canary-verified.json](reports/lab-custom-canary-verified.json) |
| Rollback custom verificado | Comprobado | [lab-custom-rollback-verified.json](reports/lab-custom-rollback-verified.json) |
| Monitor con perfil y drift | Comprobado | [lab-monitor-verified.json](reports/lab-monitor-verified.json) |
| Notebook completo en Databricks | Comprobado | [notebook-observed.json](reports/notebook-observed.json) |

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
