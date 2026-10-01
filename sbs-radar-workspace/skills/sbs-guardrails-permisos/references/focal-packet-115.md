# Vista focal 115

Invocación explícita SK07/SK08 + CreatorZ; auditoría de retención anterior al código en runs/sk07-sk08-focal-packet-115-retention-audit.json. Variante opt-in para rag/comparison, rechaza Genie y campos desconocidos. El EvidencePack original del servidor, sus validadores y la traza permanecen completos.

El modelo recibe exactamente las dos citas focales originales con texto completo, offsets y metadatos sin modificaciones, junto con pregunta, contexto, memoria, procesos ficticios, límites y metadatos del pack. Se eliminan duplicados y citas no focales sólo de la vista del modelo; esto no demuestra suficiencia semántica ni ausencia global. La tabla required_citations se deriva del par actual; Antes exige before, Después after y cada Cambio ambos. El guardrail 094 permanece intacto.

Los opcodes compactos indexan los textos completos por rangos Unicode y reconstruyen ambos lados sin duplicar sus cadenas; no adjudican materialidad. El manifiesto lateral conserva los campos retirados, posiciones, hashes de citas y bytes UTF-8 para restaurar exactamente el objeto fuente. Fuente y mapa se archivan antes de la llamada.

La política 115 sustituye expresamente la cláusula antigua de compaction/tool_results; conserva las demás instrucciones y el esquema GeneratedClaims. El adaptador rechaza cambios de la política fuente. No incorpora gold, evaluaciones de respuestas anteriores ni frases correctivas de casos.

Ensayo 115 independiente bajo 053: máximo 4 generaciones Qwen, 2 embeddings de consulta, 8000 tokens, 120000 caracteres, transporte 60 segundos; sin retry ni fallback. El historial 110 de dos POST permanece intacto. Pruebas locales no equivalen a calidad normativa ni ejecución remota.
