# SK09 — Referencia IA de relevancia028

Revisor designado: GPT-6 Astra, high; skill SK09 v0.1.2. Se leyeron íntegramente los221 pasajes elegibles y se adjudicaron358 relaciones, sin rankings, scores, resultados RAG ni referencias previas. Rúbrica congelada antes de juzgar; los scripts sólo ensamblan juicios manuales y verifican citas.

| Pregunta | Elegibles/juzgadas | Grado0 | Grado1 | Grado2 | No juzgables/faltantes |
|---|---:|---:|---:|---:|---:|
| cyber-art20-3 |84/84|71|9|4|0/0|
| market-art27 |137/137|121|12|4|0/0|
| market-art29-1-4 |137/137|124|9|4|0/0|
| Total |358/358|316|30|12|0/0|

Cada juicio conserva pregunta, pasaje, documento, versión, lado, grado, razón y cita exacta con offsets/página. Se verificaron358 citas contra raw local, páginas de extracción y la cadena de hashes de los4 originales y derivados de los pares. Las10 unidades fuera de estos pares están enumeradas, sin juicios forzados.

Las12 unidades de sustento directo incluyen duplicados y solapamientos: artículo completo/subpasaje para20.3 y29.1.4, y duplicación exacta del artículo27. Se conservan por identidad del inventario. Cada consulta dispone de sustento directo en ambos lados. Estos conteos no equivalen a12 cambios ni prueban eficacia de recuperación.

La comparación literal y las decisiones de frontera están en alignment-and-limits.ai-review-028.json. El antes/después es documental; no se determina vigencia global ni inexistencia de reglas en todo el ordenamiento. Las fórmulas dañadas de prima en Octava no impiden juzgar la relevancia de los párrafos legibles sobre contratación, pero tampoco se evalúa la fórmula.

Referencia **ai_review**: human_approved=false, development_exposed=true, holdout=false. Exhaustividad relativa al inventario, sin certificar cobertura jurídica completa, tablas/anexos o segmentación. No se hizo inspección visual exhaustiva del PDF. Un revisor, sin rondas de acuerdo. No métricas de desempeño, aprobación institucional, coste/ahorro humano ni eficacia operacional derivados de esta revisión.

Salidas: judgments.ai-review-028.json (objeto con metadata y lista judgments), qrels.ai-review-028.json (objeto con qrels, counterparts relevantes y direct_support_counterparts), coverage.ai-review-028.json, rúbrica y registro congelado. La revisión técnica independiente puede comparar estas referencias sin reescribirlas para mejorar resultados.
