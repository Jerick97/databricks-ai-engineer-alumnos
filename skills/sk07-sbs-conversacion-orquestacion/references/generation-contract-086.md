# SK07 — diagnóstico086 antes del contrato

Aplicar junto con [SK05 captura086](../../sk05-sbs-modelos-configuracion/references/generation-contract-086.md). No modificar GeneratedClaims, EvidencePack, validación de citas ni renderer. Un JSON objeto es candidato; no es respuesta utilizable hasta pasar todos los validadores existentes. El runner diagnóstico no ejecuta Conversation ni afirma validación semántica/E2E.

Cuando falla el generador, conservar etapa específica fuera de Answer y no descartar el único contenido necesario para reproducir el fallo dentro de un ensayo autorizado. Mantener salida vacía/error para el usuario si el contrato no pasó. No hardcodear contenido normativo ni reetiquetar fixtures como respuesta real. Si077 no archivó cuerpo, declarar causa exacta no observada; la nueva captura pertenece a086, no reescribe077.
