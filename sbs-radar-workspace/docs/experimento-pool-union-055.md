# Experimento causal de pool055

Estado: medición local de desarrollo expuesto; revisión SK09 independiente pendiente. No cambia runtime, qrels, umbrales ni aceptación.

Se varió sólo el corte previo al reranker: RRF20 frente a la unión de léxico20 y vector20, ordenada mediante el mismo RRF60. Mismos231 pasajes/vectores041, queries compatibles046, filtros de familia/par, modelo ONNX ARM64047, ventanas contiguas completas de hasta512 tokens y agregación max logit. No hubo nuevos embeddings, descargas, SDK ni cloud.

| Consulta | Pool RRF/unión | Recall pool RRF→unión | Recall final20 RRF→unión | nDCG5 RRF→unión | nDCG20 RRF→unión |
| --- | --- | --- | --- | --- | --- |
| cyber-art20-3 | 20/30 | 11/13 → 11/13 | 11/13 → 11/13 | 0.921838 → 0.921838 | 0.919395 → 0.913155 |
| market-art27 | 20/29 | 7/16 → 11/16 | 7/16 → 8/16 | 0.810561 → 0.810561 | 0.624167 → 0.652300 |
| market-art29-1-4 | 20/35 | 5/13 → 11/13 | 5/13 → 9/13 | 0.773468 → 0.839049 | 0.610494 → 0.783257 |

La unión incorpora los4+6 positivos identificados en048 como descartados por fusión. Con candidatos comunes que conservan scores exactos, el cambio de resultados se atribuye a esta política de pool en estas consultas, no a un modelo distinto. El baseline calculado nuevamente reproduce exactamente IDs/orden/scores047.

No todos los positivos restaurados al pool llegan al corte final20: artículo27 incorpora dos, pero desplaza un positivo previo (neto+1); artículo29 incorpora cuatro de seis (neto+4). Ciberseguridad no recupera positivos nuevos y su nDCG20 baja al desplazar posiciones con candidatos sin relevancia positiva en esta referencia. La presencia de ambas versiones con soporte directo grade2 sigue1/1 en top5 y top20 en ambos brazos: ese diagnóstico no sustituye recall de todos los positivos ni es expansión/alineación uno-a-uno SK03. No se expandieron contrapartes.

| Consulta | Ventanas RRF→unión | Pair tokens RRF→unión | Segundos reranking RRF→unión | Razón tiempo |
| --- | --- | --- | --- | --- |
| cyber-art20-3 | 28 → 46 | 9761 → 16097 | 1.078 → 1.765 | 1.64× |
| market-art27 | 34 → 46 | 12416 → 16458 | 1.425 → 1.836 | 1.29× |
| market-art29-1-4 | 34 → 55 | 13040 → 20649 | 1.463 → 2.305 | 1.58× |

Carga compartida ONNX: 0.655s. Seis llamadas locales,154 pasajes puntuados,243 ventanas y88421 tokens de pares procesados entre ambos brazos. Son unidades de trabajo, no tokens facturados a un servicio; coste monetario desconocido=null. Se hizo una medición por brazo y consulta, alternando el orden (baseline/unión; unión/baseline; baseline/unión). Sin repetición/distribución ni control de ruido no se afirma significación estadística ni una razón de latencia general.

## Límites y decisión

Se mantienen fuera de ambas ramas nueve ocurrencias positivas:2 en ciberseguridad,5 en artículo27 y2 en artículo29. Cambiar profundidad de ramas corresponde a otro experimento; aquí no se cambió. Qrels028 revisados por IA, tres preguntas expuestas y pasajes solapados: los denominadores no equivalen a obligaciones independientes ni referencia humana ciega. El recall final20 sigue limitado, especialmente artículo27(8/16). No hay aprobación, superioridad universal ni promoción del perfil049.

No se modificó ningún componente de recuperación: RRF20 era una política fijada, no un error de implementación. La intervención sólo produjo rankings nuevos de experimento. El refinamiento de SK04 añade diagnóstico por etapas y experimento de un factor; no se declara validación conductual general de la skill.

## Evidencia congelada

- Invocación/política previa: `runs/sk04-pool-union-055-invocation.json`, `runs/sk04-pool-union-055-policy.json`.
- Script: `runs/sk04-pool-union-055.py`; tests de deduplicación, cardinalidad y orden RRF en `tests/unit/test_pool_union_055.py` (RED2→GREEN2).
- Resultados: `runs/sk04-pool-union-055/rankings.json`, `metrics.json`, `record.json`; cada ranking incluye pool, scores, ventanas, tokens, tiempos, fuentes y modelo.
- Rankings guardados exclusivamente antes de leer qrels para métricas; los juicios no puntúan candidatos. Métricas reutilizan evaluador018/047 con ganancia lineal y denominadores íntegros.
- Baselines047/048, queries046, vectores041, qrels028 y umbrales018 permanecen intactos. La propuesta de unión no se incorpora al runtime.
