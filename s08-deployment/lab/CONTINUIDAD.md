# Del notebook S05/S07 al proceso de Serving

| Contrato | Conservado / cambio S08 | Evidencia |
|---|---|---|
| UC ventas y reposición | Mismas funciones S05 y Gold S02. SQL Statement Execution parametrizado sustituye ejecución Spark. | lab-smoke-local/serving |
| RAG | Mismos chunks y embeddings qwen3 S04, coseno top3; consulta original preservada para no perder intención al reformular el LLM. No es Vector Search. | respuesta con documento_id/chunk_id |
| Tools | Llama70 S05 selecciona herramienta. Allowlist, JSON Schema, máximo4 llamadas y6 turnos. | tests y custom_outputs |
| Respuesta factual | **Cambio explícito:** renderiza cifras/citas desde evidencia validada; el LLM selecciona tools pero no reescribe cifras ni decide cuáles productos requieren reposición. | render_evidence + smoke |
| S07 regex/PII | Copia de check_text/sanitize_output, inspección de tool result antes de reenviar, sin monkeypatch global. | tests |
| S07 Safety | Usa el mismo endpoint con Safety input/output; no configura ni modifica endpoint compartido. Verifica config en preflight. Fallos bloquean. | preflight + metadata moderation |
| Política aprobada S07 | Excluida del RAG de negocio: tabla docente contiene sólo `demo-1`, política **sintética**. No se hace pasar por política real Neptuno. | inventario S07 |
| MCP/Genie S05 | No incluidos en este artefacto: superficie de recursos reducida a SQL/RAG para practicar deploy, no se afirma paridad completa de todas las extensiones S05. | allowlist explícita |
| Prompt registry | Template exacto registrado y copiado a model_config con versión inmutable. Mover alias no modifica modelo ya servido. | config del artefacto + metadata |

Safety es probabilístico: se observaron falsos positivos en respuestas benignas durante desarrollo; no se deshabilitó ni se degradó a regex para conseguir PASS. Las pruebas cloud registran el resultado de cada ejecución. Una ejecución aprobada no demuestra ausencia de falsos positivos futuros. La App muestra error genérico ante fallo; el operador distingue controles y disponibilidad en logs restringidos.

El contenido raw y las trazas requieren ACL y retención. No compartas payloads de usuarios en entregas. `inference_flat` conserva métricas sin texto/identidad, pero el servicio de inferencia sí conserva raw; define su retención con el dueño de datos. No borres ni alteres manualmente el esquema de la tabla administrada.
