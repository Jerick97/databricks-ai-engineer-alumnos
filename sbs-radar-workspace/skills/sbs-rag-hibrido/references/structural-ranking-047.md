# Brief y contrato047

CreatorZ, 2026-09-28. Investigación reutilizada: primitives LocalIndex/retrieve/rrf/_bm25, run028, dataset026, vectores041 ejecutados045 y compatibilidad046. Ninguna búsqueda ni descarga. Brecha: no existía proyección estructural literal a LocalIndex ni ejecución de las cuatro variantes con los231 vectores reales. No reutilizar el índice de páginas cambiándole la etiqueta; no llamar chunk_spans sobre unidades anotadas solapadas, porque su contrato no admite solapamientos. Alternativa elegida: proyección explícita validada de cada unidad congelada, sin cambiar texto ni offsets.

`src/sbs/retrieval/structural_ranking.py` expone project_records, scoped_variants, run. `passage_id` se conserva exactamente como `citation_id`; no alias silencioso. Provision text=quote, input_parts íntegros, página inicial y lista completa de páginas contra rawbundle; source_kind normative identifica procedencia documental, nunca aprobación de materialidad. Origin anotado/automático queda fuera de la cita. Los registros y vectores forman un índice separado; complete significa todos los231 pasajes seleccionados, no cobertura normativa total.

Las cuatro salidas usan results[{query_id,family,pair_id,eligible_ids,ranking:[{passage_id,score,rank}],pool_top20}]. Léxico, vector y RRF conservan top20 explícitos; no son listas completas del corpus. RRF usa top20 de cada canal con k60. Reranker CPU local ejecuta sólo el poolRRFtop20 guardado antes; mismas ventanas contiguas sin truncamiento y modelo/backend fijado que028, threads2. Traces guarda stages y latencia compartida léxico/vector/RRF; ésta no se presenta como tres mediciones aisladas. Reranker mide carga y ejecución separadas. Ninguna expansión de contrapartes o vecinos para métricas.

La ejecución lee únicamente datos de entrada permitidos; no abre judgments/qrels/referencias ni métricas para puntuar. Lee el archivo028 de rankings léxicos para comprobar regresión: IDs/orden exactos y tolerancia aritmética `2*n_unique_query_terms*ulp(max(abs(scores)))`. Causa observada del primer fallo: _bm25 suma sobre set(queryterms), cuyo orden de proceso cambia redondeos; deltas3.55e-15–7.11e-15 con top20 idéntico. No cambia scorer ni orden/tie-break, no tuning semántico. El intento inicial y sus records/index/failure quedan intactos.

SK09 detectó que validar rawtext_sha solamente permitía metadata config_hash alterada. Cierre corregido: review046hash fijado → hash del informe046 → artifacts/manifest/archivos consumidos contra pins046 → result.json contra manifest026.source_files. Los tests con helper anclado rechazan reseal y metadata alterada. Preservar la revisión independiente fallida y reejecutar en salida nueva. No cambiar datos fuente para satisfacer el control.

CLI local (salida nueva; cero SDK/auth/red):

```sh
PYTHONPATH=src .venv/bin/python -m sbs.retrieval.structural_ranking --output runs/sk04-structural-ranking-047-v2
```

Política antes de corrida: runs/sk04-structural-ranking-047-policy-v2.json. Resultados reales sólo acreditan ejecución local sobre desarrollo expuesto. No inferencia remota adicional, no query nueva, no promoción, no métricas ni gates de aceptación. La compatibilidad046 es operativa bajo campos observados, no prueba de pesos remotos inmutables. La evaluación separada de SK09 no convierte estas tres preguntas expuestas en holdout.
