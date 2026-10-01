# SK04 — Creator Z, 2026-09-27

Capacidad: recuperar evidencia citable para preguntas SBS por familia, disposición y par de versiones. No decide vigencia ni aprueba impacto. Reutiliza SK01contratos, SK02rawtext, SK03alineamientos, SK05bundle, SK08permisos y SK09métricas.

Fuentes: /Users/macdenix/.codex/skills/estrategia-rag/SKILL.md y strategies/span-limpio-contexto-v1.md, leídas; separación span/embedding/contexto e identidad versionada obligatorias. La preferencia histórica no certifica este corpus.

Primaria Databricks consultada/reutilizada: https://docs.databricks.com/aws/en/ai-search/query-ai-search (actualizada Sep11,2026). Admite ANN, híbrido, filtros y reranker. Filtros y su semántica difieren por endpoint; storage-optimized puede retornar vacío aun existiendo registros por overfetch. Verificar API instalada y permisos. Fuente de algoritmos: https://docs.databricks.com/aws/en/vector-search/vector-search, recuperada en investigación del plan; no reproducir fusión sobre salida híbrida yafusionada.

Alternativas: híbrido administrado Databricks requiere índice/infra real, menor implementación; índice local léxico+vectores permite inspección reproducible y desarrollo sin cloudnuevo, pero no sustituye Genie ni validación del destino. Adoptar interfaz explícita para ambas; seleccionar con disponibilidad/costo/prueba. Bibliotecas de embeddings/reranking y tokenizer corresponden SK05. No fingir embedding semántico con hashes oTFIDF.

Evaluación: baseline6casos antes deSKILL. Congelar cuatro variantes léxico/vectorial/RRF/RRF+reranking y qrels porpasaje/contraparte. Medir recuperación y calidad de respuesta separado. Pruebas numéricas deRRF/coseno prueban algoritmo, no relevancia. Revisión independiente pendiente.
