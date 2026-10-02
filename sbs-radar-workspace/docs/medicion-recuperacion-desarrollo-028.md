# Medición de recuperación de desarrollo — 028

La referencia de GPT-6 Astra high, ejecutada mediante SK09, cubre358 relaciones pregunta/pasaje sobre221pasajes elegibles. Una revisión técnica independiente verificó citas, offsets, páginas y derivación de juicios; otra reprodujo las fórmulas de las métricas. Es referencia IA de desarrollo expuesto: no aprobación humana, holdout ni aceptación jurídica/operacional.

Los rankings se congelaron antes de recibir los juicios. Se ejecutaron BM25 y el reranker ONNX local sobre el mismo top20 léxico. No hay ejecución vectorial/RRF sobre este corpus: faltan231embeddings documentales.

| Pregunta | Recall@5 léxico | Recall@5 +reranker | nDCG@5 léxico | nDCG@5 +reranker | Sustento directo antes/después en top5 |
|---|---:|---:|---:|---:|---|
| Ciberseguridad20.3 |5/13|5/13|1.0000|0.9218|Sí, ambas variantes|
| Conducta27 |5/16|5/16|0.8106|0.8106|Sí, ambas variantes|
| Conducta29.1.4 |3/13|4/13|0.6622|0.8390|Sí, ambas variantes|

El reranker mejora la tercera pregunta, no cambia la segunda y empeora el orden en la primera. La muestra no demuestra una mejora general. En top20 el recall léxico es9/13,8/16y11/13; rerankear ese mismo conjunto no cambia su cobertura. No se ajustaron modelo, preguntas ni juicios tras observar resultados.

## Incompatibilidad del diseño pendiente

El diseño018 proponía recall≥90% conk5. Con13/16/13positivos, incluso un ranking ideal queda limitado a38.46%/31.25%/38.46%. Se preservaron los solapamientos entre pasajes automáticos y anotados; son denominadores por pasaje, no obligaciones independientes. No se cambian aquí qrels, presupuesto ni umbral. Antes de una prueba de aceptación futura debe resolverse explícitamente el presupuesto de evidencia y la unidad de evaluación, con protocolo nuevo congelado antes de dicha prueba. Estas mediciones no congelan ni aprueban el protocolo018.

## Evidencia

- Referencia: `context/evaluation-028/frozen-record.ai-review-028.json`.
- Revisión técnica: `runs/sk09-reference-028-review.json`.
- Resultados con numeradores/denominadores y promedios separados por familia: `runs/sk09-measure-development-028-result.json`.
- Verificación matemática independiente: `runs/sk09-measure-development-028-review.json`.
- Rankings ciegos: `runs/sk04-lexical-development-028-rankings-lexical.json` y `runs/sk04-lexical-development-028-rankings-reranker.json`.

## Pendientes del E2E

Acceso/autenticación Databricks y generación real;231vectores documentales; autorización SQL/start solicitada previamente; ejecución Genie/Apps/Jobs y pruebas visuales del navegador; evaluación de aceptación independiente y tiempo humano pareado. No se acredita ninguno con los resultados anteriores. La conversación no requiere aprobación experta previa.
