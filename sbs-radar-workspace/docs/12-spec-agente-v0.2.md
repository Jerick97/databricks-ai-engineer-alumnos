# SBS Radar — Spec v0.2 para revisión

Fecha: 2026-09-27. Estado: aprobado por el usuario; no implementado. Sustituye las decisiones de alcance y conversación del spec v0.1 presentado en chat. El plan de implementación detallado sigue siendo el siguiente entregable.

## Objetivo

Detectar publicaciones oficiales, localizar y comparar disposiciones, documentar cambios y conversar sobre qué cambió, cómo estaba antes, cómo está ahora y qué implicancias podría tener. Mantener las fuentes, versiones y límites visibles durante toda la conversación.

## 12 decisiones

| ID | Decisión vigente |
|---|---|
| A01 Usuario, dueño y decisión | Analista de cumplimiento de banco peruano genérico. Responsable de cumplimiento como dueño funcional. Priorizar revisión y proponer acciones sustentadas. |
| A02 Valor y baseline | Localizar, comparar, documentar y conversar con seguimiento contextual. Comparación contra lectura humana con comparador documental; medir tiempo total con retrabajo y calidad. |
| A03 Alcance | Dos frentes: seguridad de la información/ciberseguridad y, como segunda familia propuesta, conducta de mercado del sistema financiero. Cada familia tendrá manifiesto y evaluación propios. Meta inicial hasta 10 pares completos por familia; disponibilidad por verificar. No sustituir faltantes con fixtures. |
| A04 Fuentes | Originales oficiales, modificatorias, anexos y correcciones identificadas; URL, captura y hash. Listas permitidas explícitas. Proyectos normativos separados de normas publicadas; nunca presentarlos como obligación vigente. |
| A05 Verdad temporal | Separar cambio textual, relaciones normativas, vigencia, aplicabilidad e impacto. Publicación, efecto y conocimiento son fechas distintas. Reconstrucciones de texto se etiquetan como tales y conservan sus actos fuente; no se presentan como consolidación oficial. |
| A06 Mecanismo | Pipeline determinista de evidencia y diff; RAG híbrido léxico + vectorial, RRF y reranking; Genie para consultas estructuradas; orquestador para combinar resultados y generar respuestas citadas. |
| A07 Autonomía | Conversación habilitada sin aprobación experta previa tras controles técnicos de acceso, extracción y evidencia. Interpretaciones disponibles como propuestas. Revisión humana necesaria para registrar impacto como aprobado o autorizar acciones de negocio. |
| A08 Respuesta | Antes/después, cambio, implicancias propuestas, fuentes y pasajes, cobertura, versión/fecha consultada, incertidumbre y estado de revisión. Referencias de cada afirmación material. |
| A09 Riesgos | Omisiones, emparejamiento incorrecto, pérdida de anexos, fechas sin sustento, contaminación entre familias/versiones, instrucciones maliciosas y fallos de permisos. Estado incompleto/error explícito; no transformarlo en “sin cambios”. |
| A10 Evaluación | Referencia humana, casos reservados por pares/documentos completos, pruebas deterministas y jueces complementarios. Métricas por familia, recuperación, conversación y E2E; promedio global no oculta fallos de una familia. |
| A11 Operación | Databricks como plataforma objetivo, web privada, revisión diaria 08:00 Lima y bajo demanda. Trazas y costos por documento/expediente/conversación. US$100 permanece como hipótesis presupuestaria por confirmar y recalcular con RAG y dos familias; no constituye autorización de gasto ni garantía de suficiencia. |
| A12 Cierre | Flujo real de detección a conversación, apertura de evidencias y revisión en UI para ambas familias. Prueba adicional de pregunta cruzada. Si un criterio falla, corregir y repetir sin declarar E2E completo. |

Familia/frente de trabajo no equivale a unidad atómica: comparación por artículo, inciso, disposición o segmento de anexo. La segunda familia es una elección propuesta por el asistente, aún revisable por el usuario.

## Tres aplicaciones funcionales en una web

1. Bandeja de novedades: filtrar por familia, fechas, cobertura, estado y pendientes; mostrar última revisión de fuentes.
2. Comparador: seleccionar disposición y par; ver antes/después, alineamiento, diferencia, anexos y originales.
3. Conversación y revisión: preguntar sobre el punto seleccionado, seguir el hilo, cambiar alcance explícitamente, generar propuesta y registrar revisión humana.

La sesión conserva familia, norma, par de versiones, fecha objetivo y disposición seleccionada. “Ese punto” se resuelve contra este contexto. Ante ambigüedad, pedir una aclaración concreta. Cambiar de versión actualiza el contexto de evidencia; el historial conversacional no se trata como fuente normativa. Mostrar el alcance activo y un control para reiniciarlo.

## Conversación y aprobación

Estados de procesamiento: detectado, procesando, listo para consultar, parcial y error.

Estados de revisión independientes: sin revisar, propuesta, revisado con observaciones, aprobado y rechazado. Un resultado aprobado permanece vinculado a sus fuentes, contexto y versión; nuevas evidencias generan revisión nueva y no heredan aprobación automáticamente.

El usuario puede conversar sobre resultados listos o parciales, con sus límites visibles. Se puede explicar implicancias probables sobre el banco ficticio antes de revisión. El especialista no desbloquea el chat: valida el paso de interpretación propuesta a decisión institucional aprobada. La referencia experta de evaluación tampoco es una autorización por cada pregunta.

## RAG híbrido obligatorio

Flujo: pregunta + contexto → filtros de permisos/fuentes/familia/versiones → búsqueda léxica y vectorial → RRF → reranking → recuperación de contraparte y contexto → validación → respuesta citada.

- Búsqueda léxica: identificadores, artículos, plazos y términos exactos. Búsqueda vectorial: paráfrasis y relaciones semánticas.
- RRF combina posiciones de las dos listas; no promedia puntuaciones incompatibles. Reranking evalúa la relevancia de los candidatos frente a la pregunta y contexto. Son dos pasos distintos.
- Preferir implementación híbrida nativa si cumple el contrato y observabilidad; no aplicar RRF dos veces si el motor ya fusiona. La disponibilidad y parámetros del servicio se verificarán en el workspace.
- Recuperación por versión: no filtrar todo a “última versión”. Las preguntas antes/después recuperan ambas versiones mediante alineamientos, además de los candidatos relevantes. La contraparte no se pierde solo por tener menor ranking.
- La búsqueda de una consulta no determina exhaustividad: la detección completa de cambios la realiza el pipeline contra el inventario. El RAG explica y localiza evidencias; un top-k vacío no acredita ausencia de cambios.
- Citas con documento, versión, disposición, página/offsets e identificador estable. Expansión de vecinos dentro del contexto documental correcto; anexos/tablas preservan encabezados, unidades y relaciones de celdas.
- Fuentes normativas y procesos ficticios recuperados como colecciones diferenciadas. El catálogo ficticio jamás se cita como fuente legal.
- Trazabilidad de candidatos, configuración de fusión, reranking cuando sea observable, pasajes finales y citas. No inventar puntuaciones que el motor no exponga.
- El embedding y reranker concretos se elegirán por disponibilidad, español, calidad, presupuesto y benchmark, sin declararlos ya elegidos o validados. Congelar revisión, tokenizer, dimensión y parámetros antes del experimento.

### Estrategia de fragmentación

Base: `span-limpio-contexto-v1`, versión 1, skill [estrategia-rag](/Users/macdenix/.codex/skills/estrategia-rag/SKILL.md). Adaptación SBS propuesta, todavía no validada en este corpus.

Separar span citable continuo y verificable, texto de embedding con contexto previo y contexto de respuesta expandido. Conservar crudo, offsets, páginas y huellas. Preferir límites de disposición y estructura, sin prometer que el extractor siempre conserva ideas completas. Tablas/anexos requieren adaptación evaluada. No copiar el recorte histórico en caracteres ni truncar silenciosamente: contar entrada completa según el modelo seleccionado. Registrar extractor/normalización, fronteras, expansión y modelos como bundle versionado; no mezclar vectores de bundles incompatibles.

### Whitelists: supuesto terminológico

Se interpreta “wiselists” como whitelists/listas permitidas; pendiente de corrección si el usuario se refería a otra técnica.

Listas separadas para orígenes de documentos, corpus/versiones admitidos, tablas/herramientas consultables y acciones por rol. Validar destino final de redirecciones al ingerir; no habilitar navegación libre a URLs sugeridas por un PDF. Los permisos se aplican antes de entregar contenido al modelo/reranker y se comprueban al abrir evidencias. Un dominio permitido no prueba por sí solo autenticidad, vigencia ni completitud del documento.

## Responsabilidades técnicas

Pipeline: ingesta, originales, extracción, alineamiento y diff exhaustivo dentro del corpus acordado.

Genie: consultas a tablas curadas de normas/versiones/cambios/cobertura/revisiones. SQL de consulta; las escrituras de aprobación pertenecen al backend de revisión con autorización explícita.

RAG: recuperación de pasajes, contexto temporal/documental y contrapartes citables.

Orquestador: decide SQL, RAG o ambos; mantiene contexto y elabora respuesta. Une resultados por IDs, no solo por semejanza de texto; si discrepan muestra el conflicto y evita una conclusión definitiva. No se supone que añadir instrucciones a Genie implemente por sí solo este RAG.

Backend/UI: permisos, navegación de documentos, expedientes y decisiones humanas. Observabilidad transversal.

## Nueve capas

| Capa | Aplicación |
|---|---|
| Canal y experiencia | Tres espacios, contexto activo, preguntas de seguimiento y estados separados. |
| Entrada y normalización | Documentos de dos familias, extracción estructural y spans citables. |
| Borde, seguridad y gateway | Autenticación, roles, listas permitidas y filtros antes de recuperación. |
| Clasificación y ruteo | Consultas SQL, documentales, temporales, de comparación y de impacto; rutas mixtas. |
| Recuperación / grounding | RAG híbrido con RRF y reranking, contrapartes y expansión controlada. |
| Razonamiento y decisión | Explicación de cambios y propuestas de implicancias sobre procesos ficticios. |
| Validación y guardrails | Evidencia, citas, cobertura, temporalidad y contradicciones; conversación con límites explícitos. |
| Acción y herramientas | Consultar, abrir fuentes, comparar, crear expediente y registrar revisión por rol. |
| Observabilidad, evaluación y mejora | Trazas de recuperación y conversación; métricas por familia, costo y regresiones. |

## Nueve etapas de preparación

1. Fundación: manifiestos y corpus completo para ambas familias.
2. Contratos/gobierno: IDs, fechas, diccionario, roles y estados independientes.
3. Conocimiento/recuperación: fragmentación, índice híbrido y referencia de relevancia por pasaje.
4. Orquestación: rutas Genie/RAG, estado conversacional, idempotencia y errores.
5. Modelo: selección medida y bundle reproducible de embeddings/reranker/generación.
6. Seguridad: listas permitidas, permisos, pruebas negativas y tratamiento del corpus como datos.
7. Evaluación: referencia de cambios y consultas, holdout, jueces y aceptación por familia.
8. Observabilidad: trazas completas, costos, errores y auditoría de revisión.
9. IA responsable/despliegue: UI real, explicación de límites, runbook, recuperación y aceptación.

## Banco ficticio

Catálogo versionado con procesos, responsables ficticios, políticas, controles y evidencias esperadas. Ejemplos: gestión de accesos, respuesta a incidentes, terceros tecnológicos, información al cliente, contratación y atención de reclamos. Procesos marcados como simulados y mapeados a ambas familias. Su existencia no acredita cumplimiento de una entidad real.

## Ejemplos de consultas

1. En este punto, ¿qué cambió exactamente?
2. ¿Cómo estaba antes y cómo está ahora? Muéstrame los dos pasajes.
3. ¿Cambió la obligación o solo la redacción/numeración?
4. ¿Qué implicancias podría tener para nuestro proceso ficticio de respuesta a incidentes?
5. ¿Qué controles del banco ficticio convendría revisar y por qué?
6. ¿Qué parte de esa conclusión está explícita en la norma y cuál es tu interpretación?
7. ¿De dónde sale ese plazo? Abre la cita y su contexto.
8. ¿Qué se conocía en la fecha X y qué efecto estaba sustentado para la fecha Y?
9. ¿Qué cambió en conducta de mercado durante el periodo seleccionado?
10. Compara los cambios que afectan nuestros canales digitales entre ambas familias.
11. ¿Qué dice el anexo y modifica lo que acabas de explicar?
12. ¿Falta algún documento que impida concluir?
13. Manteniendo estas versiones, explícame ese mismo cambio en lenguaje sencillo.
14. Ahora cambia a la versión anterior a estas dos y muestra qué alcance estás usando.
15. Prepara un resumen para el comité, separando hechos, interpretación y acciones propuestas.
16. ¿Cuáles de estas propuestas ya fueron revisadas y cuáles siguen sin aprobar?

## Aceptación

Se conservan los criterios propuestos y aceptados: cobertura sin omisiones silenciosas; recall de cambios ≥95%; precisión ≥90%; ningún cambio crítico omitido en prueba; todas las citas emitidas fieles/localizables; casos insuficientes de prueba señalados; reducción de tiempo mediano de revisión ≥30% incluyendo retrabajo; UI E2E con configuración/permisos reales.

Aplicar métricas por familia y reportar denominadores y tamaño de muestra. Mantener holdout por pares completos evitando fuga de documentos/versiones compartidos entre conjuntos. El gold no puede ser únicamente generado o aprobado por el propio modelo.

Agregar evaluación léxica sola, vectorial sola, híbrida RRF y RRF+reranking con corpus/preguntas congelados. Medir recuperación de pasajes relevantes y de ambas contrapartes, nDCG/Recall@k, sustento de respuestas, latencia y costo. Definir k y umbrales de recuperación en el plan con el corpus real; no reutilizar umbrales de detección como si fueran de retrieval.

Pruebas adicionales: conversación disponible con estado sin revisar; seguimiento de “ese punto”; cambio explícito de versión/familia; comparación cruzada; respuesta parcial; fuente fuera de whitelist; permisos denegados; instrucción maliciosa; conflicto SQL/RAG; promoción de propuesta a aprobado solo por rol autorizado. Ninguna revisión experta previa obligatoria para consultar.

## Fuentes técnicas y normativas consultadas

- [SBS: normativa](https://www.sbs.gob.pe/normativa-y-estandares/normativa/normativa-sbs).
- [SBS: regulación](https://www.sbs.gob.pe/regulacion).
- [Genie Agents](https://docs.databricks.com/aws/en/genie-agents/concepts).
- [Databricks: búsqueda híbrida y RRF](https://docs.databricks.com/aws/en/vector-search/vector-search).
- [Databricks: consultas y reranking](https://docs.databricks.com/aws/en/ai-search/query-ai-search).

Estas fuentes respaldan contexto y capacidades documentadas, no disponibilidad comprobada en el workspace ni validación del futuro agente.
