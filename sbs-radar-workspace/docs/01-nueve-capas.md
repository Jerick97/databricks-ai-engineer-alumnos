# Las nueve etapas de preparación — terminología acordada

**Corrección de terminología tras tu aclaración:** estas nueve responsabilidades se usarán como etapas/ejes de preparación. Las capas de arquitectura que pediste son las de canal, entrada, recuperación, razonamiento, etc., recuperadas en [08-capas-arquitectura.md](08-capas-arquitectura.md). El nombre de este archivo se conserva para no romper enlaces anteriores.

**Recuperadas de tu método, no inventadas para este caso.** Fuente: [pieza del recorrido, capa 01](/Users/macdenix/clawd/artifacts/scrollytelling-recorrido/pieza-moderno-v2/index.html:559), corroborada por [contrato del recorrido](/Users/macdenix/clawd/artifacts/scrollytelling-recorrido/pipeline/recorrido-v2.json:10). No es un estándar oficial de Databricks. La interpretación como preparación es apropiada al contenido; la fuente también las presenta como arquitectura.

Los nombres son originales; preguntas y evidencias son una operacionalización propuesta para evaluar un caso nuevo.

| Capa | Qué prepara | Pregunta antes de construir | Evidencia de salida propuesta |
|---|---|---|---|
| 1. Fundación de datos | Calidad, estructura y disponibilidad del dato; Medallion | ¿Sobre qué dato confiable responderá? | Inventario, perfilado, linaje y controles de calidad; para SBS, originales y cobertura del corpus |
| 2. Contratos y gobierno | Esquemas, versiones, permisos y propietarios | ¿Quién garantiza significado, acceso y cambios? | Contrato de datos, propietarios, matriz de acceso, semántica temporal |
| 3. Conocimiento y recuperación | Documentos, histórico, búsqueda y reranking | ¿Cómo encuentra evidencia suficiente y correspondiente a la versión? | Corpus versionado, recuperador medido, citas localizables y casos sin evidencia |
| 4. Orquestación | Ruteo, herramientas, memoria y subagentes | ¿Qué decide el código, qué el modelo y qué el humano? | Flujo de estados, contratos de herramientas, presupuestos, errores y escalamiento |
| 5. Modelo | Selección y ajuste del modelo | ¿Qué capacidad exige IA y qué alternativa más simple se comparó? | Benchmark del caso, selección justificada y límites; no elegir por ranking genérico |
| 6. Seguridad y cumplimiento | Identidades, datos personales, trazabilidad y regulación | ¿Quién puede ver/actuar y qué consecuencias tiene una salida indebida? | Pruebas de permisos, modelo de amenazas, retención y revisión aplicable |
| 7. Evaluación y calidad | Casos reales, pruebas automáticas y revisión humana | ¿Quién sabe cuál es la respuesta correcta y cómo se detecta una regresión? | Referencias expertas, conjunto reservado, métricas por error y umbrales acordados |
| 8. Observabilidad | Trazas, costo, latencia y fallos | ¿Podremos reconstruir por qué respondió y cuánto costó? | IDs de ejecución, versiones, evidencia usada, consumo y métricas por etapa |
| 9. IA responsable y despliegue | Uso responsable, publicación, prompts versionados y reversión | ¿Quién acepta el riesgo, opera y puede volver atrás? | Aceptación humana, versión liberada, rollback probado, runbook y soporte |

Una capa puede estar **sin evaluar / diseñada / implementada / verificada / operada / no aplicable con justificación**. Una marca binaria no refleja toda la evidencia. Esta graduación es nueva propuesta, no la escala original del catálogo.

## Cómo revisar el caso SBS con las capas

Antes de diseñar el prompt, capas 1–3 deben responder cuáles versiones se comparan y dónde está cada pasaje. Las capas 4–6 delimitan que detectar texto cambiado no autoriza interpretar una obligación ni modificar un control bancario. Las capas 7–9 deben demostrar omisiones, falsos cambios, referencias, costo, operación y revisión experta.

No hace falta terminar una capa para pensar en otra: seguridad, evaluación y operación se diseñan desde el inicio. Las capas no son una secuencia temporal obligatoria.

## Tres mapas diferentes que tus materiales llaman nueve capas

| Mapa | Para qué sirve | Fuente |
|---|---|---|
| Preparación anterior | Diseñar y revisar el sistema completo | Recorrido del método, capas 1–9 |
| Runtime | Seguir una solicitud: canal, entrada, borde, ruteo, recuperación, razonamiento, validación, acción, observabilidad | [S03 apéndice](/Users/macdenix/clawd/databricks-ai-engineer/s03-genai/S03-append.html:11) |
| Capacidades del inventario | Ver qué se construyó: servicio, estructura, retrieval, HITL, UI, evals, guardrails, deploy, observabilidad | [Catálogo](/Users/macdenix/clawd/agent-lab/agentlab.json:57) |

No hay correspondencia uno a uno: por ejemplo, contratos intervienen en entrada, tools, datos y salida; seguridad cruza todo el runtime. Las fichas del inventario conservan su rúbrica original: no se reinterpretaron como preparación cumplida.
