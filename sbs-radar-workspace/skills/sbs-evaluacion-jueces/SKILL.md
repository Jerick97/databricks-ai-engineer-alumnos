---
name: sbs-evaluacion-jueces
description: Diseña referencias, particiones y benchmarks o evalúa calidad de cambios, recuperación, conversación y E2E de SBS Radar. Usar para medir aceptación y regresiones; no para sustituir al especialista ni para registrar solamente latencia o fallos operativos.
---

# SK09 — Evaluación y jueces

Versión0.1.2, provisional. Creada y refinada con skill-creator-z. [Brief](references/research-brief.md), [matriz](references/requirements-risks.md), [casos](evals/cases.json), [protocolo de revisión IA](references/revision-ia.md).

## Contrato

Entrada: referencia por familia/disposición/pasaje con procedencia de revisión, corpus/config congelados, particiones y resultados de corrida. Salida: reporte con numeradores/denominadores, gates passed/failed/not_evaluated, errores, citas y límites. No confundir validación del harness con desempeño del agente.

## Diseñar antes de ajustar

1. Recuperar criterios aceptados del spec mediante SK00. Registrar hipótesis y versión de protocolo; no cambiar umbrales al ver holdout.
2. Separar referencias humanas adjudicadas, revisión IA, anotaciones provisionales y fixtures sintéticos. El usuario designó GPT-6 Astra con razonamiento high para revisar el piloto: ejecutar esa revisión mediante esta skill, sin exigir una revisión humana previa para conversar o avanzar técnicamente. Conservar procedencia IA; nunca adjudicar en nombre de una persona ni convertir un juez LLM en verdad jurídica. Sin originales o contrapartes, marcar el caso no evaluado.
3. Reservar pares completos; identificar versiones/documentos/derivaciones compartidas y artículos vecinos para evitar fuga entre ajuste y prueba. IDs de preguntas distintos no bastan. Los documentos pueden estar indexados para responder; respuestas gold, rúbricas específicas del caso o feedback del holdout no entrenan los ejemplos/prompts.
4. Congelar qrels por pasaje y contraparte, valores k y umbrales numéricos RAG antes del ensayo sobre corpus real. Comparar léxico, vectorial, RRF y RRF+reranking con fragmentos/preguntas/corpus y embeddings comparables. Cambiar varios factores evalúa un paquete, no demuestra causalidad del reranker.

## Medir y aceptar

5. Por cada familia medir cambios correctos/detectados/reales, críticos omitidos, citas fieles/localizables, insuficiencia/abstenciones y tiempo humano incluido retrabajo. No usar promedio global para ocultar una familia reprobada.
6. Gates aceptados: recall≥0.95, precisión≥0.90, cero críticos omitidos en prueba, todas las citas emitidas fieles/localizables, insuficiencias de prueba señaladas y reducción de tiempo mediano≥0.30. Informar conjunto/denominadores; denominador cero o casos críticos no incluidos es no evaluado, no100%.
7. Separar disponibilidad de métricas de aceptación: Recall/nDCG sin protocolo aplicable son medidas, no passed/failed con un umbral implícito. Para RAG reportar Recall@k/nDCG@k, ambas contrapartes, sustento de respuestas y costo/latencia por familia. Sin qrels o sin k/umbral congelado no declarar aceptación RAG.
8. Conservar procedencia de revisión en el informe sin convertirla en autenticación. Etiquetar juicios booleanos de citas como suministrados; la fidelidad de originales y cobertura de afirmaciones requiere gates separados, no pasa por un booleano. Jueces LLM explican hallazgos según rúbrica y referencias; no pueden crear hechos ni aprobación humana. Antes de ejecutarlos, registrar invocación con ID/versión/hash de esta skill, entradas/hash, modelo, esfuerzo y protocolo. Usar el recurso de revisión IA como contrato del encargo, no un prompt independiente. Añadir comparaciones ciegas/consistencia según nivel; conservar desacuerdos y adjudicación.
9. Tiempo: comparar muestras pareadas, incluir correcciones. Agente1min+revisor15min frentehumano10min equivale a16min, empeora60%, no ahorra90%. Costo sin datos se reporta desconocido, no cero.
10. Escribir testsRED antes de src/sbs/evaluation/ y tests/unit/test_evaluation.py; probar familias desiguales, denominadores cero, referencias ficticias, fuga entre versiones y métricas no finitas. Después ejecutar resultados reales; éxito del código no sustituye muestra experta.

## Refinar

Guardar resultados brutos y razones de fallos; corregir la skill/componente propietario y repetir regresiones. Nunca editar referencia solo para elevar score sin adjudicación y versión nueva. Una muestra pequeña sirve para decidir avance, no certificar fiabilidad operacional.
