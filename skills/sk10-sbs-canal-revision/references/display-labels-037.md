# Creator Z037 — presentación y ensayo acotados

Fecha2026-09-28; investigación reutilizada del spec y SK10, con evidencia nueva en screenshot036f, runtime_release.py, runtime.py y revisión SK09 UX36-LABEL01. No búsqueda general repetida. Alcance: presentación de pares/disposiciones y ancho móvil; no algoritmo normativo, embeddings o permisos cloud.

| Requisito/riesgo | Decisión | Evidencia discriminante |
|---|---|---|
| ID opaco impide reconocer disposición | Metadato estructural verificado → display_label | Test realcorpus falla antes por títulosIDs; ambospares después |
| Renombrar label altera embeddingquery | Mantener label interno exacto; campo display separado | test_display_labels_037 verifica prefijo completo histórico y IDs |
| Confundir copia con vigencia | Copia A/B y SHA corto; sin fechas inferidas | Detalle muestra hash completo; avisos parciales/unreviewed permanecen |
| Disposición final confundida con artículo | Usar unit_kind/number observado; fallback neutral | Probes DCF/resolutivo/unknown |
| Grid y hashes producen overflow | minmax(0,1fr), min-width0, overflow-wrap; no overflowhidden | Baseline390px mide651/642; repetir medición y screenshot ambasfamilias |
| None dispara modelos lazy | Guard que rechaza inicializadores antes del SDK en harness | Prueba guard y chat sólo fallo inyectado; incidente036 preservado |

Alternativas: mapear pair_id fijo falla al renombrar un par; deducir fechas desde URL no acredita vigencia; ocultar overflow pierde contenido; cambiar label interno modifica consulta de recuperación. La solución proyecta metadatos ya validados y usa nodos de texto, preserva identificadores y referencias originales.

Archivos baseline/GREEN: runs/sk10-labels-037-{red,green,refactor,exact-prefix,webapp}.txt; navegador036: runs/sk10-036-ui-record.json; navegador037 e independienteSK09 se registran separados al concluir. No atribuir mejora conductual general de la skill ni ahorro humano: nivel provisional, evaluación técnica y visual acotada.
