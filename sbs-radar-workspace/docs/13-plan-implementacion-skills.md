# SBS Radar — Plan de implementación mediante skills

Fecha: 2026-09-27. Spec aprobado: [v0.2](12-spec-agente-v0.2.md). Estado: plan; ninguna de las skills nuevas está construida, evaluada ni ejecutada todavía.

**Para ejecutores:** aplicar este plan a través de sus skills especializadas, con ejecución por tareas y evaluación independiente. La skill de planificación usada es `superpowers:writing-plans`; no sustituye las skills de construcción pedidas por el usuario.

**Objetivo:** implementar y demostrar el E2E en dos familias normativas, con conversación, Genie, RAG híbrido, evidencia citable, revisión separada y UI real.

**Arquitectura:** pipeline de datos y diferencias; recuperación híbrida; consultas estructuradas Genie; orquestación conversacional; aplicación privada. Las skills dirigen construcción y operación reproducible; el runtime se implementa en código y configuraciones versionadas. Las skills no son trece agentes que deban ejecutarse en cada consulta.

**Stack objetivo:** Databricks, Unity Catalog, tablas Delta, SQL/Genie, búsqueda híbrida y reranking; Python para datos/backend, web para usuario. Versiones y capacidades se congelan en SK00/SK05 antes de implementar sus adaptadores. El plan no presupone recursos cloud habilitados.

## Restricciones globales

- Construir primero la skill responsable mediante `/skill-creator-z`; probarla; ejecutarla; evaluar su componente; avanzar únicamente con evidencia.
- Todo trabajo delegado debe referenciar skill, versión, tarea, entradas y assertions. Se permiten parámetros e instrucciones de tarea; no sustituyen una skill por un prompt improvisado.
- Seguridad/ciberseguridad y conducta de mercado: corpus y métricas separados; conducta de mercado es la segunda familia propuesta aceptada con el spec.
- RAG léxico + vectorial + RRF + reranking; no duplicar RRF nativo; preservar ambas versiones y contexto citable.
- Conversación sin aprobación experta previa; revisión humana para registrar impacto aprobado y acciones institucionales.
- Banco de procesos ficticio explícitamente identificado; no se usa como fuente jurídica.
- US$100 es hipótesis presupuestaria, no autorización ni demostración de suficiencia. No contratar ni habilitar recursos facturables por el mero hecho de aprobar este plan.
- Las pruebas del notebook se ejecutan con la configuración entregada. UI y respuestas reales son condición de cierre; HTTP 200 no las reemplaza.

## Dos ciclos distintos

**Ciclo de la skill:** brief → investigación reutilizada y brechas → baseline sin skill → diseño mínimo → ejecución con skill → casos nuevos → revisiones → estado y versión.

**Ciclo del componente:** invocar skill → verificar entradas → crear prueba fallida → implementar → ejecutar prueba → artefactos y evidencia → revisión independiente → publicar checkpoint local.

Una skill puede superar su evaluación de comportamiento sin que el componente haya sido construido. Un componente que funciona no demuestra por sí solo que su skill sea reutilizable. Registrar ambos estados por separado.

## Estructura prevista

```text
skills/<nombre>/SKILL.md
skills/<nombre>/references/{research-brief,requirements-risks}.md
skills/<nombre>/evals/{cases,results,benchmark}.json
skills/<nombre>/scripts/                  # solo operaciones deterministas justificadas
skills/<nombre>/CHANGELOG.md
context/{source-register,artifact-register,decisions}.json
contracts/{domain,run,evidence,conversation}.json
config/{sources,permissions,model-bundle,pipeline}.yaml
src/sbs/{foundation,comparison,retrieval,models,genie,conversation,guardrails,evaluation,observability}/
app/                                    # tres espacios en una aplicación
notebooks/                              # instalación, ejecución y evaluación reproducibles
tests/{unit,integration,e2e}/
runs/<run_id>/{invocation,artifacts,validation,verdict}.json
```

El proyecto conserva la fuente canónica de las skills. El registro en un runtime usa referencias a estas rutas, sin copiar versiones divergentes. Comprobar el mecanismo de descubrimiento antes de instalar; no sobrescribir skills existentes.

## Orden y checkpoints

| Ola | Skills / trabajo | Evidencia para avanzar |
|---|---|---|
| 0 | Crear SK00; recuperar contexto y capacidades. Crear SK01 y fijar contratos. | Contexto mínimo por tarea, fuentes con estado, spec/hash, esquemas y decisiones explícitas. |
| 1 | Crear SK08 y SK11: políticas y contrato de trazas tempranos. Crear y ejecutar SK02. | Dos inventarios oficiales, originales/huellas, calidad de extracción, errores visibles; controles de origen activos. |
| 2 | Crear SK09 en modo diseño de evaluación: gold, particiones y baseline humano. Crear y ejecutar SK03. | Comparación por disposición y referencia separada de ajuste/prueba. Puede avanzar código con fixtures etiquetados; no aceptación jurídica sin referencia humana. |
| 3 | Crear SK05 y medir candidatos; crear/ejecutar SK04 y SK06 en paralelo con interfaces estables. | Bundle de modelos reproducible, recuperación híbrida medida y consultas Genie sobre tablas reales. |
| 4 | Crear/ejecutar SK07 y SK10; integrar SK08 y SK11. | Conversación contextual y tres espacios funcionando, permisos y citas comprobados. |
| 5 | Reejecutar SK09 en modo aceptación; crear/ejecutar SK12. | E2E real en ambas familias y pregunta cruzada, notebook reproducible, despliegue/recuperación, evidencia UI y runbook. |

La evaluación se diseña antes del ajuste; guardrails y observabilidad se diseñan antes de conectar el modelo. Sus pruebas integradas se repiten después. No son etapas relegadas al final.

## Encadenamiento permitido

Pipeline de datos: comprobar fuentes → capturar → extraer → controlar calidad → alinear → comparar → indexar → publicar snapshot consultable. Cada paso conserva estado e idempotencia. Una publicación nueva puede disparar trabajo incremental; no invalida todo el corpus.

Pipeline conversacional: contexto/permisos → ruteo → Genie y/o recuperación híbrida → validaciones → síntesis → evidencias y traza. No ejecuta creación de skills ni benchmarks durante la respuesta.

Se detiene la rama afectada ante fuente no permitida, anexo faltante, extracción deficiente, alineamiento ambiguo o validación fallida. Puede entregar evidencia parcial claramente etiquetada. Crear/modificar políticas, elegir modelos, adjudicar gold, cambiar contratos, aceptar un despliegue y aprobar impacto tienen checkpoints explícitos; no se autoaprueban por terminar una cola.

## Contrato de ejecución y reutilización

Cada invocación registra `task_id`, `skill_id`, `skill_version`, `spec_hash`, `input_artifact_ids`, `configuration_hash`, `mode`, `outputs`, `checks`, `cost`, `status` y `next_action`. Estado: planned/running/passed/failed/blocked. No guardar secretos.

Clave de reuso: skill/version + hashes de entradas + configuración. Reutilizar un resultado compatible y verificado; si cambia una dependencia, invalidar solo sus descendientes. Reuso de una revisión documental no equivale a reuso de permisos o disponibilidad actual del workspace.

La recuperación empieza por el registro compartido, no por búsqueda global. Cada fuente guarda ID, ruta/URL, afirmación, fecha de consulta, versión/hash, estado, cobertura y dependientes. Estados: reutilizable, requiere-actualización, sustituida y no-verificada.

Reconsultar una fuente únicamente por brecha concreta, cambio de versión, contradicción, expiración definida o comprobación operativa necesaria. Para documentación SaaS y precios, comprobar vigencia antes de provisionar y guardar la versión usada. Para originales normativos conservar cada captura y contenido; una comprobación de novedades no reescribe el pasado.

Contexto ya disponible: spec12; docs01/08/09 para marcos; docs03/04 y evidence/sbs-forensic-* para antecedentes; evidence/fuentes-web.md y source-hashes.json para procedencia; estrategia-rag/span-limpio-contexto-v1 para fragmentación. No reauditar 108 repos ni buscar nuevamente las nueve capas. No reutilizar como evidencia E2E los fixtures S05, el benchmark no pareado Apex ni una UI bloqueada.

## Interfaces y tareas por skill

Los tipos citados abajo se definen en SK01 y se validan con JSON Schema. Cada tarea crea el módulo indicado y `tests/unit/test_<modulo>.py`, además de los casos de integración citados. Los comandos se ejecutarán dentro del entorno fijado por SK00; son previstos, no ejecutados en esta entrega.

| Skill | Interfaz y archivos propios | Prueba discriminante de componente |
|---|---|---|
| SK00 sbs-contexto-ejecucion | `context/`; `resolve_context(task_id: str) -> ContextBundle`; validador de invocaciones y checkpoints. | Cambio de hash invalida descendientes; misma fuente compatible evita nueva búsqueda; recurso no verificado no figura disponible. |
| SK01 sbs-contratos-gobierno | `contracts/`; `validate_contract(kind: str, payload: dict) -> ValidationResult`; incluye SourceDocument, Provision, VersionPair, ChangeSet, EvidencePack, QueryContext, Answer, ReviewDecision, RunRecord y ModelBundle. | Estado aprobado sin actor/rol/evidencia se rechaza; fechas de captura/efecto no se intercambian; separar estado de proceso y revisión. |
| SK02 sbs-fundacion-datos | `src/sbs/foundation/`; `ingest(manifest: dict, run: RunRecord) -> list[SourceDocument]`; `extract(source: SourceDocument) -> list[Provision]`. | Reingesta idempotente; cambio de bytes genera versión nueva; anexo ausente o OCR deficiente produce cobertura parcial, no éxito completo. |
| SK03 sbs-versiones-cambios | `src/sbs/comparison/`; `compare(pair: VersionPair) -> ChangeSet`. | Renumeración no es automáticamente alta/baja; alineamientos 1:n/n:1; una reconstrucción conserva actos fuente y no se llama consolidación oficial. |
| SK04 sbs-rag-hibrido | `src/sbs/retrieval/`; `retrieve(question: str, context: QueryContext, bundle: ModelBundle) -> EvidencePack`. | Filtros previos, RRF único, reranking trazable y ambos pasajes; top-k vacío no produce “sin cambios”; fragmentos de tablas mantienen encabezados/unidades. |
| SK05 sbs-modelos-configuracion | `src/sbs/models/`, `config/model-bundle.yaml`; `select_bundle(candidates: list[dict], evaluation_id: str) -> ModelBundle`. | Conteo de entrada completa; no truncación silenciosa; no mezcla embeddings; latencia/costo desconocidos marcados no medidos. |
| SK06 sbs-genie-datos | `src/sbs/genie/`; `query_genie(question: str, context: QueryContext) -> EvidencePack`; tablas/vistas y configuración versionada. | Respuesta SQL contrastada con consulta de referencia, sin fuga de permisos ni escrituras de aprobación; warehouse ausente detectado antes de entregar notebook. |
| SK07 sbs-conversacion-orquestacion | `src/sbs/conversation/`; `answer(question: str, context: QueryContext) -> Answer`. | “Ese punto” mantiene selección; cambiar versión cambia evidencia; conflicto SQL/RAG se expone; sin revisión humana previa se responde con estado propuesto. |
| SK08 sbs-guardrails-permisos | `src/sbs/guardrails/`, `config/permissions.yaml`; `authorize(actor: dict, action: str, resource: dict) -> ValidationResult`; `validate_answer(answer: Answer, evidence: EvidencePack) -> ValidationResult`. | Documento intenta ordenar otra herramienta: se trata como datos; URL redirige fuera de lista: se bloquea captura; permisos aplicados antes del modelo; cita/fecha sin evidencia falla. |
| SK09 sbs-evaluacion-jueces | `src/sbs/evaluation/`; `evaluate(run_ids: list[str], reference_id: str) -> dict`; gold, particiones, rúbrica y reportes. | Fuga de documentos compartidos detectada; métricas por familia con denominadores; juez LLM no reemplaza referencia experta; caso adversarial reservado falla cuando se introduce regresión. |
| SK10 sbs-canal-revision | `app/`, `tests/e2e/`; endpoints de consulta/comparación/revisión consumen QueryContext, Answer, ReviewDecision; procesos ficticios versionados. | UI abre ambas fuentes, muestra parcial/error y conversación sin aprobación; usuario sin rol no aprueba; revisión móvil y teclado; aprobación antigua no se hereda tras nueva evidencia. |
| SK11 sbs-observabilidad-operacion | `src/sbs/observability/`; `record_event(run: RunRecord, event: dict) -> str`; costos/latencias y monitoreo de fuentes. | Una conversación se reconstruye con IDs/configuración; no secretos en trazas; gasto no disponible no se registra como cero; última captura exitosa distinta de último intento. |
| SK12 sbs-despliegue-e2e | `notebooks/`, configuración de despliegue y runbook; `verify_release(release_id: str) -> dict`. | Notebook entregado ejecuta con sus parámetros; UI real y respuesta verificadas; rollback/restauración probados; HTTP 200 sin respuesta correcta no pasa. |

Pasos obligatorios por tarea:

- [ ] Construir y evaluar su skill mediante el expediente descrito en el plan de skills.
- [ ] Resolver entradas con SK00 y validar contratos de SK01; registrar faltantes sin inventarlos.
- [ ] Escribir los casos discriminantes de la tabla en `tests/unit/test_<modulo>.py` y comprobar su fallo antes de implementar.
- [ ] Implementar la interfaz, scripts/configuración y documentación del componente mediante su skill.
- [ ] Ejecutar `python -m pytest tests/unit/test_<modulo>.py -q`; exigir PASS. Las pruebas cloud/UI se registran aparte y no se sustituyen por mocks.
- [ ] Ejecutar integración con dependencias reales y guardar evidencia en `runs/<run_id>/`.
- [ ] Obtener veredicto de evaluador distinto del constructor con alcance de lectura acotado; corregir hallazgos materiales.
- [ ] Registrar checkpoint y cambios en git cuando exista repositorio preparado; nunca incluir secretos, originales privados ni cambios ajenos por un `git add` indiscriminado.

## Protocolo RAG antes del ajuste

En ola 2, SK09 crea `config/retrieval-evaluation.json` con IDs/hashes del corpus y preguntas, qrels por pasaje y contraparte, particiones sin fuga, valores de k y umbrales de aceptación numéricos. Se fijan a partir del corpus real y referencia humana antes de ejecutar el benchmark; no se ajustan al holdout. Hasta fijarlos, no se declara lista la evaluación RAG.

SK04/SK05 ejecutan cuatro variantes sobre ese protocolo congelado: léxica sola, vectorial sola, híbrida RRF y RRF+reranking. SK09 compara Recall@k, nDCG@k, recuperación de ambas contrapartes, sustento de respuestas, latencia y costo, desglosados por familia. Misma fragmentación y bundle de embeddings cuando corresponda; cambios de modelo son experimentos separados. El híbrido con reranking sigue siendo requisito; si no alcanza los criterios se corrige, no se elimina silenciosamente. La aceptación de SK09/SK12 exige este informe además de métricas de cambios.

## Riesgos de revisión y sus pruebas propietarias

1. Publicación nueva corrige retroactivamente una anterior: SK03 conserva conocimiento/efecto y SK10 no hereda aprobación.
2. Misma disposición aparece en anexos o versiones duplicadas: SK02 deduplica por contenido sin borrar identidades, SK04 recupera contexto correcto.
3. Conversación cambia de familia y usa “eso”: SK07 hace explícito el alcance y pregunta si sigue ambiguo.
4. Retries después de fallo parcial: SK02/SK03 idempotentes; SK11 registra intento y resultado sin duplicar expedientes.
5. Cita literal correcta pero de versión equivocada: SK04/SK08 verifican correspondencia de par/fecha, no solo coincidencia de texto.

## Cierre

Recall de cambios ≥95%, precisión ≥90%, ningún cambio crítico omitido en prueba, citas fieles/localizables, insuficiencias señaladas, mejora de tiempo mediano ≥30% con retrabajo; reportar denominadores por familia. Además, evaluación de recuperación y conversaciones contextuales y E2E de ambas familias. Un conjunto pequeño no certifica fiabilidad de producción.

Se entrega aplicación, configuración, skills y sus evaluaciones, notebooks ejecutados, corpus/manifiesto, evidencia de pruebas, límites y runbook. La implementación termina cuando pasa esta evidencia, no cuando se redacta la última skill.
