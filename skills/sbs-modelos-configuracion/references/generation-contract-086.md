# Refinamiento086 opt-in — captura y clasificación, provisional

Fuente creadora exacta: `/Users/macdenix/clawd/openclaw-codex/openclaw-workspace/skills/skill-creator-z/SKILL.md`, SHA en invocación086. Reutiliza fuentes y observaciones072–077; esta corrección no introduce una capacidad nueva del proveedor ni modifica modelo/prompt/parámetros.

Baseline real077: una llamada, HTTP200, identidad Llama exacta, finish_reason stop, contenido2263caracteres,659completiontokens,14.66segundos. `generated_json` se asigna **antes** de `json.loads` y del rechazo de valores no objeto; no significa JSON correcto. `completed` no se alcanzó. No se guardó el contenido. Error JSON y JSON no objeto siguen alternativas, y markdown fences es sólo hipótesis no observada. Schema/citas se validan después, no son causa acreditada de077.

En un ensayo diagnóstico expresamente acotado, conservar el sobre HTTP JSON recibido antes de interpretar message.content. Etiquetar reserialización del sobre parseado, no byteswire. Preservar el stringcontent exacto, SHA, manifiesto, archivo exclusivo0600 y cuota consumida. El archivo es salida no confiable del modelo, no Answer aprobado. Nunca incluir headers/credenciales ni poner contenido arbitrario en logs/last_attempt; allí usar sólo etapa, código, SHA, tamaño, tipoJSON y posicionesnuméricas de error.

Clasificar por separado fallo antes de contenido, sintaxisJSON, JSON no objeto y JSON objeto pendiente de contrato. No remover fences, buscar un substringJSON, corregir comas/citas, reintentar ni convertir fallos en respuestas válidas. Si persistir la respuesta falla, conservar estado unconfirmed y reserva; no declarar captura ni aceptación. Una respuesta objeto requiere GeneratedClaims+EvidencePack/citas y revisión semántica posteriores intactas.

Nuevo artefacto086 independiente: un POST idéntico al body077 archivado, tomado de sus tres llamadas restantes. Reserva durable:1previo+1diagnóstico=2de4, quedan2; ceroembeddings, ceroSQL, ceroresource mutation. Directorio fijo086 y O_EXCL impiden replay/reset. No editar077 ni aceptar un segundo diagnóstico mediante otro directorio. Root coordina ejecución después de revisión independiente.

Pruebas con contenidos sintéticos discriminan las dos causas y que raw queda capturado antes del error, no reconstruyen077. Estado: implementación local provisional; no calidad, producción ni E2E. Los SKILL.md congelados080/081 se conservan; este refinamiento se invoca explícitamente mediante runner086 y debe revisarse por separado antes de integrar a runtime.
