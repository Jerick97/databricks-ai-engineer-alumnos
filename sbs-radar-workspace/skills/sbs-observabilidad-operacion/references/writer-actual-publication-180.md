# SK11/SK12 — actualización de evidencia real179/180

29 de septiembre de2026. Referencia aditiva: no modifica las versiones ni los bytes congelados de SKILL.md. El notebook y Job writer167 completaron una ejecución real con publicación persistida verificada independientemente. Esta conclusión sustituye únicamente la condición «writer cloud aún no observado» de la preparación167; no declara terminada la App ni las13skills.

## Evidencia y alcance

Job989326861421503, run817327291004649, task404938644790018: estado TERMINATED/SUCCESS y salida no truncada con status=published y evidence_mode=real. El transporte del writer registró178HTTP/10SQL/38FilesPUT. El operador registró63HTTP/6SQL/1configPUT/2imports/1run-now. Coste desconocido: null.

El readback180 es PASS_ACTUAL_PUBLICATION_READBACK: control revision6, fence1, pointer ligado al mismo Job/run y23artefactos verificados por hash exacto, con24HTTP/1SQL. PublicationID: d7704356b7610750c7194f8422b12f4e7d5057404f9c36812adccddfa80b0d10. SHA256 del manifiesto: 0b2a1cd1da619764f9dd082ace5f9e88c437eb6ffc0ef892b25a15017495f168.

Fuentes locales: deployment/state/writer-observation179/run.json, output.json, deployment/state/writer-readback180/result.json y sus24respuestas conservadas. La invocación runs/sk11-sk12-writer-180-reference-invocation.json fija sus hashes. El valor cloud_acceptance=false del notebook se conserva: el veredicto independiente es aceptación de esta publicación, no aceptación global del producto.

El recorrido real167 requirió exportar el notebook protegido bajo el SP y verificar su núcleo/declaración antes de escribir; esa capacidad queda observada en esta ejecución satisfactoria, no garantizada indefinidamente. La procedencia ACL sigue siendo owner_live_pre_and_postdispatch, no lectura ACL por el writer. Los campos históricos ausentes max_retries/timeout_seconds/disable_auto_optimization siguen etiquetados attested_only; no se inventa resolved_values.

## Nota para el instructor

Abrir el [notebook writer privado](https://dbc-0410b264-20c7.cloud.databricks.com/?o=7474657121564806#notebook/3178573112927427) y el [run real verificado](https://dbc-0410b264-20c7.cloud.databricks.com/?o=7474657121564806#job/989326861421503/run/817327291004649). El enlace del run procede de run_page_url observado; el enlace del notebook usa el ID observado3178573112927427. Los permisos normales del instructor siguen siendo necesarios.

Mostrar SUCCESS junto con output=published y el readback180 del control/manifiesto/23artefactos. No pulsar Run para reproducir sin preparar una declaración nueva: la autorización está ligada a este run/token y vence1790712479826ms (20:07:59.826UTC). Una repetición con otra identidad/run o después del TTL debe rechazarse. El Job diario08:00America/Lima permanece PAUSED; la emisión de declaración por cada ejecución sigue siendo requisito. Esta ejecución no acredita disponibilidad continua ni la renovación del certificado Genie cada cinco minutos.

Pendientes separados: prueba final de la App y experiencia de usuario, aceptación integral E2E, operación diaria con autoridad renovada por ejecución y cierre de las13skills. No activar el schedule ni promover permisos para sustituir estos controles. La preparación utiliza el paquete sellado105: publicación real no significa nueva captura de todas las fuentes ni validación jurídica de sus interpretaciones.
