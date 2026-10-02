# Refinamiento091 — bloques tipados observados GPT-OSS

Activar únicamente para el candidato091 y su ensayo de una petición, no como default del runtime o Apps. SK05 0.1.6 y SK07 0.1.17 conservan sus archivos congelados; esta referencia opt-in se invoca explícitamente junto con ellas y CreatorZ exacto.

Fuente reutilizada: observación090 HTTP200 del endpoint databricks-gpt-oss-120b, response_model gpt-oss-120b-080525, 64tokens y finish length. Sólo demuestra acceso y forma observada, no JSON completo, capacidad general, calidad ni selección de producción. No repetir investigación sin brecha nueva.

Conservar el envelope HTTP parseado completo mediante086 antes de examinar bloques. Admitir una sola choice, identidad exacta y finish stop; rechazar truncación. La lista contiene exclusivamente bloques text con text string y reasoning con summary de summary_text strings. Rechazar claves o tipos desconocidos, strings mezclados, ausencia de texto. Concatenar sólo text en orden sin separadores artificiales. Nunca llevar reasoning al answer, citas o metadatos expuestos. Conservarlo sólo en el archivo bruto restringido como salida no confiable del modelo.

Pasar el texto al parser088 (JSON objeto raw o una envoltura completa json). No reparar JSON ni extraer subcadenas. Validar GeneratedClaims, QueryContext y Answer con EvidencePack original077 y guardrails reales, sin inferencias ni credenciales para replay. Schema y offsets no demuestran sustento semántico; exigir evaluación Astra separada antes de ampliar alcance. El fallo semántico089 de Llama no se corrige por compatibilidad ni se traslada como resultado GPT-OSS.

Preparar una sola POST con body077 exacto, 5000outputtokens, 120000inputchars, timeout60, cero embeddings/reintentos/fallback. Admisión O_EXCL fsync antes del SDK; error o timeout consume la reserva. Default preflight, revisión SK09 por hash antes de execute. Preservar077/086/088; no copiar/resetear sus cuotas. Archivar request, respuesta, normalización, replay y resultado. No afirmar respuesta correcta si sólo pasó técnica.

Pruebas: baseline RED import inexistente; GREEN bloques partidos con reasoning intercalado, casos de casi-error, captura previa al rechazo, cuota durable, rechazo schema/citas con originales reales y replay sintético etiquetado. El ensayo real091 queda pendiente del coordinador; cuatro turnos quedan fuera del plan.
