# Protocolo de evaluación por familia — diseño 018 v1

Estado: **pending_refs**. [Diseño preregistrado](../context/evaluation-018/design.json), [manifiesto de trabajo](../context/evaluation-018/dataset-manifest.json) y [schema de registros](../context/evaluation-018/records.schema.json). El hash del diseño identifica sus decisiones; **no** es un protocolo efectivo validado por `freeze_protocol`. No se ejecutó inferencia, SQL ni cloud. El coste sigue desconocido. Esto no solicita permisos adicionales ni bloquea conversación o revisión normativa con Astra.

## Decisiones congeladas antes de la futura prueba

Separar `cybersecurity` y `market_conduct`; nunca promediar ambas para aprobar una familia. Comparar léxico, vectorial, RRF y RRF+reranking sobre las mismas preguntas, corpus/pasajes, filtros y bundle de embeddings. Registrar hash de código/config, índice, modelos/revisión/backend/arquitectura, semilla cuando exista, parámetros de fusión/expansión y candidatos. Una modificación de esos factores es otro experimento; no atribuir causalidad al reranker si cambian varios.

Retrieval: candidatos20; medición k=5 y20; **gate primario k5** por familia: macro Recall≥0.90, macro nDCG≥0.80 (ganancia lineal), y cobertura antes/después=1 en **cada** pregunta comparativa evaluable. k20 es diagnóstico, no rescate de un fallo k5. Se proponen estos objetivos de ingeniería prospectivos para limitar la primera inspección a cinco pasajes, conservar al menos90% de evidencia relevante media y80% del orden ideal, y nunca omitir por completo una contraparte. No son umbrales jurídicos ni estimaciones calibradas con tres consultas. Mantenerlos aunque un caso conocido no pase. No se han aplicado retrospectivamente a001. Si un conjunto tiene más pasajes relevantes que el presupuesto puede recuperar, se registra esa dificultad; no se recortan qrels para mejorar el resultado. La cobertura de contrapartes tampoco demuestra entailment ni cobertura de todas las afirmaciones.

Los umbrales de detección aceptados se conservan sin cambios: recall≥0.95, precisión≥0.90, cero críticos omitidos, todas las citas fieles/localizables, insuficiencias señaladas y ahorro mediano pareado≥0.30 incluyendo retrabajo. Reportar numerador/denominador, TP/FP/FN y fallos por caso. La ausencia de críticos, citas, referencias, tiempos o preguntas de insuficiencia produce `not_evaluated` para ese gate; no100%. Una métrica conocida que falla sigue fallando aunque otras estén no evaluadas. El gate de familia no es passed mientras falten evidencias obligatorias. No convertir10pares máximos iniciales en un mínimo de aceptación ni afirmar precisión poblacional con muestra pequeña.

## Conjunto y exposición

| Familia | Evidencia reutilizable | Falta concreta para aceptación reservada |
|---|---|---|
| Cyber | Astra003: muestra art20.3 y actos temporales;004:00771/2286/2220;005:G140v1/v2+G167, comparación histórica con límites. | Par/componentes completos elegibles no expuestos; referencias por pasaje y cobertura material, casos críticos/insuficientes y tiempos reales. G140/G167 tiene vínculo declarado con504 en el inventario (Astra005 no verificó esa arista contra el original504) y ya está revisado; conservar agrupación preventiva, no declararlo holdout limpio. |
| Market | Astra003:3274v7/v8 art27 y29.1.4; dos preguntas sobre el mismo par. | Al inicio faltaba contraparte4036; suplemento concurrente SK02 market018 capturó4036v6 y3240 anotada. Falta revisar el par y su independencia: ambas copias nuevas remiten a2286 ya usada.4143-2019 es seguros y queda excluida del piloto bancario. Faltan qrels reservados, referencias y tiempos. |

`runs/sk04-real-001-report.json`: tres preguntas reales sobre135páginas, evidencia de desarrollo expuesta con qrels muestreados. No denominador exhaustivo, aceptación ni prueba independiente. El inventario llamado holdout es inventario de candidatos, no certificación de partición. Astra005 compara dos estados consolidados y un párrafo operativo en tres facetas; no contar esas facetas como tres pares independientes ni inferir vigencia de los nombres v1/v2.

Seleccionar la partición por componente de dependencias: pares completos, documentos/versiones, derivados, artículos vecinos, modificatorias compartidas. Registrar aristas y motivo; reservar el componente entero. `check_leakage` solo ve identidades declaradas: no descubre relaciones normativas ni historia de exposición. La ausencia de coincidencia de hashes no basta. Los originales pueden estar en el índice para responder; gold, feedback y ejemplos de evaluación reservada no pueden alimentar prompts/ajuste. Los casos ya consultados pasan a desarrollo. Mantener `acceptance_pairs=[]` hasta encontrar pares reales aptos; no fabricar pares ni qrels.

## Contrato de datos y referencias

Un directorio de corrida contiene `dataset-manifest.json`, `questions.json`, `passages.json`, `judgments.json`, `reference.json`, `protocol.input.json`, `protocol.frozen.json`, `rankings.json`, `runs.json` y evidencias originales por hash. Los archivos vacíos actuales son estado pendiente, no una corrida. Guardar registros con los tipos del schema. El manifiesto final fija corpus, archivos, SHA256, bundle e historial de exposición; conserva también este diseño por hash.

Reglas entre registros (además del schema): IDs únicos; familia/pair de pregunta coincide con el par; versiones y pasajes pertenecen exactamente a cada lado; `end>start`, página física y `rawtext[start:end]==quote` verificados contra derivado y PDF original. Ningún booleano suministrado reemplaza esa comprobación. La cadena antes/después es relación textual documentada; no ordenar por número de versión para inventar cronología. Consultas cruzadas se descomponen en contextos tipados por familia/par y se puntúan en cada familia, sin citas prestadas de otro contexto.

Construir qrels antes de obtener rankings: grado0 irrelevante,1 contexto relevante,2 sustento directo; juzgar el conjunto completo de pasajes elegibles para la pregunta o declarar qrels parciales y dejar aceptación no evaluada. Conservar pasajes relevantes no recuperados; un pool creado exclusivamente por el sistema evaluado no demuestra exhaustividad. Grado y cobertura son decisiones de referencia registradas con revisor/procedencia/razón/desacuerdo, no inferencias del score. `counterparts[query_id][pair_id]` contiene listas distintas, no vacías y relevantes de before/after. No forzar contrapartes ficticias en consultas sin evidencia: evaluarlas por el gate de insuficiencia, fuera del benchmark de comparación recuperable.

Astra003/004/005 siguen etiquetadas `ai_review`, no referencia humana. El usuario autorizó Astra para revisión normativa: se puede ampliar esa referencia con salida ciega del sistema evaluado, inspección de originales y desacuerdos preservados; no hay una aprobación humana por pregunta. La referencia del modelo evaluado no se autoaprueba. Informar por separado la aceptación experta del spec cuando no exista adjudicación humana. Una clasificación crítica no se deduce del resultado del detector; congelarla antes y conservar sus fundamentos.

`reference.json` alimenta `evaluate`: `{kind,review_provenance,families:{family:{changes:[change_id],critical:[change_id],insufficient_cases:[case_id]}}}`. `runs.json` es lista `{run_id,family,detected:[change_id],flagged_insufficient:[case_id],citations:[{faithful:boolean,localizable:boolean}],times:[{case_id,baseline,agent,review}]}`. Los juicios necesitan un archivo de evidencia enlazado por citation_id/claim_id con URL/originalSHA, versión, página, offsets, cita exacta, claim y resultado razonado de cobertura. El harness actual deja `citation_evidence` y `claim_coverage` no evaluados deliberadamente; no sustituirlos con true. Reporte complementario independiente requerido para esos gates. No modificar harness para obtener passed.

## Ejecución local reproducible con APIs existentes

Desde la raíz, comprobar el evaluador sin endpoints:

```sh
PYTHONPATH=src .venv/bin/python -m pytest tests/unit/test_evaluation.py -q
PYTHONPATH=src .venv/bin/python - <<'PY'
import json
from pathlib import Path
from sbs.evaluation import evaluate
p=Path('context/evaluation-018')
r=evaluate(json.loads((p/'runs.pending.json').read_text()),json.loads((p/'reference.pending.json').read_text()))
assert r['status']=='not_evaluated'
Path('runs/sk09-evaluation-protocol-018-readiness.json').write_text(json.dumps(r,indent=2)+'\n')
print(r['status'])
PY
```

Cuando los archivos reales estén completos, crear `protocol.input.json` con `corpus_hash`, `questions_hash`, `k:[5,20]`, `thresholds` exactamente del diseño, `qrels:{query_id:{passage_id:grade}}`, `counterparts:{query_id:{pair_id:{before:[],after:[]}}}`, `partitions:{tune:[pair],holdout:[pair]}`. Incluir `design_sha256`, criterios de elegibilidad/exposición y hashes de referencias como metadatos. No pasar el manifiesto pendiente a esta API ni llenar faltantes con placeholders. Para un conjunto de desarrollo sin holdout, reportar solo mediciones; `freeze_protocol` exige ambos conjuntos reales no vacíos.

```sh
# DATASET_DIR apunta al directorio real completado, no al template pendiente.
PYTHONPATH=src .venv/bin/python - <<'PY'
import os,json
from pathlib import Path
from sbs.evaluation import freeze_protocol,verify_protocol
p=Path(os.environ['DATASET_DIR'])
f=freeze_protocol(json.loads((p/'protocol.input.json').read_text()))
assert verify_protocol(f)
with (p/'protocol.frozen.json').open('x') as out: json.dump(f,out,indent=2)
print(f['sha256'])
PY
```

Antes de cualquier llamada futura de SK04/SK05, registrar protocolo efectivo/hash, autorización de inferencia aplicable, identidad observada de endpoint/bundle, caps y destino de resultados. Este documento no ejecuta ni autoriza llamadas. Guardar rankings completos sin duplicados y errores con query_id/variante: `rankings.json` lista `{query_id,family,variant,ranking:[passage_id],status,latency_seconds,usage,cost}`. No reemplazar errores por ranking vacío exitoso ni descartarlos del denominador. Cada combinación pregunta/variante esperada debe aparecer exactamente una vez; ausencia/error deja gate de completitud fallido o no evaluado, nunca passed.

```sh
PYTHONPATH=src .venv/bin/python - <<'PY'
import os,json
from pathlib import Path
from sbs.evaluation import retrieval_metrics,verify_protocol
p=Path(os.environ['DATASET_DIR']);f=json.loads((p/'protocol.frozen.json').read_text())
assert verify_protocol(f);protocol=json.loads(f['json']);rows=[]
for r in json.loads((p/'rankings.json').read_text()):
    q=r['query_id']
    rows.append({**r,'measurements':None if r['status']!='completed' else
      [retrieval_metrics(r['ranking'],protocol['qrels'][q],k,protocol['counterparts'][q]) for k in protocol['k']]})
with (p/'retrieval.measurements.json').open('x') as out:json.dump(rows,out,indent=2)
PY
```

Esta llamada mide; no decide aceptación automáticamente. Antes del informe comprobar completitud y partición, luego aplicar macro por familia a k5 y gate por consulta de contraparte. Incluir tabla por consulta/variante con numeradores, denominadores, latencia/coste y una tabla por familia con thresholds del diseño. k20 separado. `evaluate(runs,reference)` calcula cambios/tiempo por familia; conservar no evaluados de evidencia material y requisitos E2E/permiso real. No confundir el éxito de SQL con calidad conversacional o UI.

## Tiempo pareado sin baseline inventado

[Plantilla CSV vacía](../context/evaluation-018/time-pairs.csv). Misma tarea/caso, mismo material y criterio de finalización; misma persona en ambos brazos cuando sea factible. Aleatorizar y contrabalancear AB/BA entre casos antes de medir; registrar orden, familiaridad/exposición y separación temporal para hacer visible el aprendizaje. No exponer la respuesta de un brazo antes del otro; si ya la conoce, marcar contaminación. No inferir baseline humano de latencia del agente ni de recuerdos estimados.

Por brazo medir lectura/análisis, verificación y retrabajo; en asistido añadir tiempo de interacción/espera no solapado. `baseline=baseline_read+baseline_verification+baseline_rework`; `agent=assisted_interaction_wait`; `review=assisted_read+assisted_verification+assisted_rework`. Registrar inicio/fin, persona seudónima, tarea, orden, errores, abandono y motivo. Evitar doble conteo de intervalos solapados. No excluir lentos o fallidos silenciosamente: informar todos; abandonos, baseline0 o pares incompletos mantienen el gate no evaluado hasta resolver según criterio predefinido, no se convierten en segundos0. Mediana por familia de `(baseline-agent-review)/baseline`; meta≥0.30. No extrapolar con una muestra reducida. La medición requiere personas y tiempos reales, aunque la revisión normativa sea Astra; no se inventan ni se exige esa medición para habilitar chat.

Actualización acotada durante construcción: el inventario cambió de SHA43cb17ac1f9f2e8d25ef14343f3c38e4a9fd39a871c3f00551501157c977d430 a417ede9de76746dc20a62db191eaacacf1f09108e72290a880235609165155ee. Se conserva la invocación original y se registra el suplemento en el manifiesto. No se analizaron las nuevas normas ni se crearon qrels; el diseño/métricas no cambian. La brecha actual es validación de par y partición, ya no ausencia material de contraparte4036.
