# Writer167 — implementación provisional, revisión independiente pendiente

Implementa el diseño164 aceptado para construcción. No acredita nube, permisos de exportación del SP ni aceptación E2E. No concede CAN_MANAGE ni cambia Jobsettings: el Job989326861421503 sigue PAUSED. Sustituye explícitamente el notebook diagnóstico158 sólo al ejecutar el runner revisado.

## Autoridad y procedencia

El operador autenticado como owner lee ACL reales y settings antes y después de enviar un único run mediante CloudDispatcher/SharedLedger existentes. Importa primero un núcleo PENDING y después el mismo núcleo con una declaración AUTHORIZED ligada al run observado, token, Job, SP, política, configuración, notebookID/path, release, archive y código. La segunda importación no reenvía run-now. Los presupuestos e intenciones se conservan en writer-operator167; incertidumbre no permite repetir efectos.

El writer exporta su notebook privado con CAN_READ, verifica su ID y compara literalmente DELIVERY167 con los datos del núcleo ya cargado. AST acepta solamente dos asignaciones literales superiores, DELIVERY167 y ATTESTATION167. El hash del template sustituye esas asignaciones por None; DELIVERY contiene el hash del módulo ejecutable, configuración y archive105. La declaración contiene el hash de DELIVERY. No hay dependencia circular ni respuestas SDK fabricadas. El núcleo dinámico es un módulo nuevo, no un monkeypatch de servicios existentes.

La confianza procede del ACL privado de Workspace y TLS, no de una firma criptográfica. Owner y administradores siguen siendo autoridades confiables. No se confía en Volume para declarar permisos: los bytes de configuración y archive allí almacenados sólo se consumen tras verificar los hashes protegidos en notebook. La declaración dura como máximo cinco minutos; no ofrece revocación instantánea. El operador comprueba ACL también después del readback de importación; una deriva impide declarar entrega correcta. No se promete operación diaria autónoma: requiere un futuro emisor de declaraciones.

GetRun aporta el subconjunto observado, los widgets de dbutils aportan parámetros efectivos etiquetados separadamente, y max_retries/timeout_seconds/disable_auto_optimization ausentes quedan expresamente attested_only. Contradicciones, campos desconocidos, otro intento/run/token, notebooks modificados o expiración rechazan la ejecución. No se reconstruye resolved_values ni se inventa historia a partir de settings actuales. El wrapper comprueba TTL justo antes de cada SQL/Files mutation y al recibir respuesta; SnapshotWriter conserva fences/CAS/publicación y readbacks.

## Ejecución y límites

Preflight sin autenticación: `PYTHONPATH=src .venv/bin/python -m sbs.operations.writer_operator_167`.

Tras revisión independiente, el root materializa únicamente approved/issued_at_ms/expires_at_ms en una copia de deployment/writer-operator167-review-template.json y ejecuta `PYTHONPATH=src .venv/bin/python -m sbs.operations.writer_operator_167 --execute --review-file <registro>` con el perfil normal si corresponde. No se emite una nueva política al preparar este paquete; se emite una vez durante ejecución y permanece inmutable en resume. Historial106/146/158/162 no se modifica.

Operador: máximo128HTTP/24SQL/1FilesconfigPUT/2imports/1run-now; no PATCH/DELETE/Jobs update/start/unpause. Writer: máximo4000HTTP/100SQL/512FilesPUT por única ejecución sin retries; SQL sólo SELECT/UPDATE del control dedicado, Files sólo release_artifacts mediante almacén existente. Hasta32GET de autoridad, con espera acotada de PENDING. Warehouse debe estar RUNNING: este runner no lo arranca.

La exportación Workspace bajo SP es una dependencia aún no observada: si falla, writer termina antes de SQL o publicación. Expiración o presupuesto agotado no se renueva/resetea automáticamente. Restaurar/cambiar el notebook después de un fallo exige variante revisada; no se restaura automáticamente sobre una ejecución activa.

## Pruebas y alcance

Siete pruebas locales cubren núcleo/hash no circular, literal/tamper, TTL antes y después del transporte, ACL sin permiso de escritura SP, runtime real capturado156/162 con contradicciones, espera acotada, y flujo SDK completo del operador con resume. El fixture integrado extrae archive105 en temporal y usa sus PDFs/config/schema/assets para los preparadores reales, uploads/readbacks simulados y CAS hasta published. No es E2E de Databricks. Los módulos base usados localmente se fijan en el freeze;105 permanece cerrado por hash.

La prueba integral detectó DUPLICATE_PAIR_ID: los contextos Genie repiten pares idénticos.167 deduplica exactamente por pair_id y rechaza colisiones distintas; no modifica105. Se conserva el fallo inicial. No se deducen costos: cost=null. Las advertencias locales de PDFs y conexiones SQLite del pipeline base no se presentan como aceptación cloud.

## Cierre portable aislado

La prueba del operador ahora lanza un proceso Python -I separado, con cwd temporal y src exclusivamente extraído de105. Ejecuta los bytes exactos module_base64 del DELIVERY167, compara su SHA y verifica que cada módulo sbs importado procede del archivo extraído. El transporte fixture prohíbe conexión de sockets. Llega a published con artefactos/readbacks/CAS; la evidencia registra todos los módulos y hashes. No usa módulos sbs ya cargados en el proceso padre. Esto sigue siendo una prueba local, sin autenticar SP ni acreditar nube. Freeze inicial conservado; esta revisión sólo sustituye la comprobación portable y documentación.
