# Diseño164: autoridad del operador y verificación del writer separadas

Estado: diseño para decisión técnica raíz, sin implementación, nueva política, grants, restauración o ejecución cloud. Preparación167 sólo después de revisión164. Autorización operativa053 persiste; aquí se cambia el contrato de evidencia, no se amplían privilegios del SP.

## Diagnóstico demostrado

Diagnóstico162 ejecutado como SP33b6f37c...: Me/Job/tabla/warehouse200; JobACL403 PERMISSION_DENIED exige Manage. La corrida146 terminó antes de expirar su política. La causa no es un deadline vencido. El catch112 de CloudDispatcher.verify ocultó el detalle. Evidencia raw permanece en deployment/state/diagnostic-monitor162/result.json y análisis estructurado164.

La documentación distingue controles del Job y privilegios Run as; ampliar a CAN_MANAGE daría poder de cambiar el Job. Mantener CAN_MANAGE_RUN. Fuentes primarias: [privilegios Jobs](https://docs.databricks.com/aws/en/jobs/privileges), [Permissions API](https://docs.databricks.com/api/access-management/v1/permission), [Jobs API](https://docs.databricks.com/api/jobs/v2/job). No encontré un endpoint respaldado que exponga toda ACL asignada al writer sin Manage. permissionLevels enumera niveles posibles; Jobs.get identifica configuración, no sustituye la ACL. No presentar esa búsqueda limitada como prueba universal de inexistencia.

El run156 real omite max_retries, timeout_seconds, disable_auto_optimization y resolved_values; incluye effective_performance_target. Ello rompe también el verificador runtime estricto146 cuando alcance esa etapa. No completar campos históricos con Jobs.get actual, ni inventar resolved_values para pasar el SDK.

## Decisión recomendada

Separar explícitamente dos clases de verificador:

- OperatorDispatcherVerifier: identidad de propietario observada; Job/ACL/notebook y datos metadata live antes del dispatch y después de obtener run_id. Conserva la prueba ACL original y los checks actuales. Puede emitir una atestación de alcance único.
- AttestedWriterVerifier167: prueba de autoridad desde el notebook privado protegido, más identidad/runtime realmente observados por el writer. No llama get_permissions para simular éxito, no fabrica respuestaSDK, no cambia el método global de CloudDispatcher. Devuelve objeto tipado WriterAuthorityEvidence con proveniencia; jamás lo etiqueta ACL live del writer.

SnapshotWriter, fencing, CAS, registro idempotente y validación de artefactos permanecen. El driver167 usa explícitamente su verificador de writer en los puntos de guardia; el dispatcher de operador sigue usando ACL live. Las interfaces nuevas deben ser visibles en constructor/bind_driver167. Métodos compartidos que hoy dependen de dispatcher.verify/_execution_contract se separan de modo explícito, con pruebas discriminantes. No basta un lambda que retorna True ni atrapar403 y continuar.

## Canal de autoridad sin permisos nuevos

Usar el notebook privado existente3178573112927427 como canal, no el Volume release_artifacts ni refresh_control: el SP escribe estos últimos y no constituyen autoridad independiente. El SP sólo CAN_READ en el notebook; owner/admins pueden modificarlo. Sus privilegios actuales y los de ancestros son auditados por el operador. El writer lee fuente mediante Workspace export SOURCE del path exacto, verificando también object_id por get-status. Export bajo SP todavía NO está observado: debe verificarse con GET acotado y fallar cerrado si no funciona, sin sustituir credenciales.

No hay firma criptográfica en esta propuesta. La autenticidad proviene del control de escritura del recurso y del GET autenticado/TLS, bajo la misma confianza administrativa ya explícita. El término atestación describe esa proveniencia; no afirmar firma digital.

Fuente167 tendrá un único bloque de datos delimitado, fuera de funciones, con asignación literal ATTESTATION167. Para calcular core_sha256, reemplazar exactamente el contenido de ese único bloque por el literal canónico ATTESTATION167 = None y conservar todos los demás bytes normalizadosLF. Rechazar duplicación de markers, ausencia, orden inválido, asignaciones extra al mismo nombre, código/llamadas dentro del bloque y tamaño excesivo. Parsear el valor con AST literal_eval, nunca exec de fuente descargada. Verificar core_sha256 contra valor embebido en el código del run. El propio campo esperado core_sha no forma parte circular de su cómputo: se coloca en configuración inmutable previamente revisada; el algoritmo excluye únicamente el bloque de datos de atestación, no otras líneas.

Importante circularidad: NO insertar un core_sha autorreferente dentro del mismo core. El notebook ejecutado recibe el hash revisado como pin externo en su configuración inmutable, cuyo hash ya fija la fuente. Resolver el grafo en167 con plantilla/corecode separado de bootstrap: hash del módulo de ejecución independiente, hash del bootstrap con slots canónicos, hash del registro de entrega; demostrar por test que cambiar cualquier byte ejecutable rompe al menos un pin. Root revisa ese grafo antes de remoto.

## Dos fases necesarias para enlazar run_id real

1. Operador prepara nueva configuración/política167 versionada y notebook con mismo core revisado y bloque PENDING, request_token único nuevo. Nunca reutiliza/reset el request146 fallido ni su ledger. Registra antes del dispatch identidadowner, ACLJob, ACLnotebook+ancestro, settings, notebookobjectID/path, timestamps y hashesraw.
2. Dispatcher original con nueva request_id reserva SharedLedger y emite a lo sumo un run-now. Se conserva intent antes del POST. Obtiene run_id candidato y lo confirma por Jobs.get_run(job_id/run_id). Si falta confirmación, NO publica atestación autorizada. Writer puede haber empezado y debe esperar sólo lectura, sin claim ni SQL/Files effects.
3. Operador repite Jobsettings/ACL/notebookACL inmediatamente después de GETconfirmado. Exige igualdad del contrato aprobado y ausencia de escritores/ejecutores no confiables. Importa una segunda revisión del MISMO core con bloque AUTHORIZED limitado al run_id confirmado. Readback export+objectID+core verifica identidad y atestación exacta. Nunca actualiza Jobsettings ni grants.
4. Writer observa el bloque mediante máximo30GETexport, separación2s (hasta60s); get-status antes y después de aceptación, sin retries ocultos. Timeout/PENDING/revocado/expiry/mismatch aborta sin publicación. Ante fallo no se inventa aceptación ni nuevo token.

La segunda importación es un efecto adicional EXPLÍCITO, no parte de las antiguas cuotas2writes146. Propuesta167 de presupuesto separado a revisar: Filesconfig1, notebookimports2, run-now1, SQLdispatcher24, HTTPoperador128. Worker authority reads adicionales máximo32GET (2status+30export), contados en transporte de writer y sin reset. No emitir ventana hasta ejecución inmediata. Restauración automática desactivada; tras diagnóstico158 el notebook sigue diagnóstico hasta reemplazo167 revisado, o restauración146 histórica explícita que no resolvería sus fallos.

## Contenido mínimo de la atestación

schema_version; state; issuer observado(ownerID/name); issued_at_ms; expires_at_ms; nonce/request_id/idempotency_token; JobID; parentRunID observado; expected writerSP; bundle105 archiveSHA/releaseID; overlay167/core/driver config hashes; backendID/controlTableID; notebookpath/objectID; prelaunch y postdispatch settingsSHA/ACLrawSHA/notebookACLrawSHA y fechas; allowlisted dispositions (on_demand only); causa de emisión; policyID; delivery method = protected_workspace_notebook; claimed evidence sources.

TTL máximo300000ms desde segunda lectura ACL, además <=expires de política. Reloj real al ejecutar; no retimestamp para reanudar. Verificar ventana antes de claim, cada SQL/Files mutation y CASpublicación, no sólo al arrancar. Si pipeline excede TTL, abortar publicación/registrar intento según fencing existente; nueva ventana requiere nuevo documento/decisión técnica, no renovación implícita.

Vincular request token al registro durable ORIGINAL de esa solicitud y al Job/run GET, no confiar en un widget aislado ni una fila escrita por el mismoSP. Atestación protegida contiene el run_id y token confirmados por operador; actor actual/Job/runtime también deben coincidir. SharedLedger sigue comprobando idempotencia, nunca reemplaza la autoridad protegida.

## Evidencia runtime y campos ausentes

Usar tres fuentes separadas, sin reconstruir un JobRun ficticio:

1. Jobs.get_run observado: Job/run/task IDs, notebookpath/source/base parameter templates presentes, environment_key, lifecycleRUNNING, attempt_number, runtime campos presentes. Un único taskrefresh; rechazar tareas adicionales, tipo alternativo, notebookpath distinto, retries observados >0, campos desconocidos no revisados. effective_performance_target sólo aceptar el valor realmente observado PERFORMANCE_OPTIMIZED, etiquetado runtime, sin convertirlo a un default de settings.
2. Widgets del notebook ejecutado: request_id, release_id, job_id, run_id, snapshot_backend_id leídos allí; comparar contra atestación protegida y contexto GET. Etiqueta runtime_widget, no APIresolved_values. Parámetro ausente/alterado aborta.
3. Atestaciónprelaunch: max_retries0, timeout_seconds600, disable_auto_optimizationtrue y entorno/dependencies. Etiqueta operator_prelaunch_config; NO evidencia históricaAPI. Campos correspondientes si aparecen en GET deben concordar. Ausencia no es false/zero ni permiso de ignorar un valor contradictorio.

Resultado tipado enumera observed_fields, attested_only_fields, missing_api_fields y checks satisfechos. Opción diaria aún bloqueada: este protocolo requiere emisor por cada run; JobPAUSED permanece hasta servicio/runbook de atestación porrun y renovación real. Un Jobdiario no renueva política ni certificadoGenie5min.

## Límite de garantía / alternativa fuerte

Existe ventana de carrera entre ACL postdispatch y uso por writer. El control no detecta revocación instantánea durante TTL, ni demuestra retrospectivamente todos los settings no expuestos por API. Confía en owner/admins y en que el core privado y su política no cambian fuera del flujo autorizado. Lecturas frecuentes del bloque y recheck final del operador reducen la ventana, no prueban control global de administradores. Exponer este cambio como operator-attested authority, no equivalencia a ACLlive en cada mutación.

Si el requisito exige revocación instantánea/ACLlive del writer, esta propuesta no lo satisface: alternativa es un servicio/broker de atestación que posea únicamente la autoridad lectora necesaria en contexto privilegiado y respuestas firmadas porrun, con disponibilidad/coste/secretos/diseño propios. No construirlo implícitamente para la demo ni dar CAN_MANAGE al writer.

## Evals y gates antes167 remoto

- Raw162403 reproducido y otras4lecturas200; ningún fallbackACLSDK.
- Corehash: modificar cualquier byte ejecutable, duplicar bloques, ASTcall en attestation, cambiar configpin o path/objectID ⇒rechazo.
- Run/Job/token/release/backend/principal distinto, atestación vieja/futura/vencida, TTL>5min o expiry durante readback/mutación ⇒rechazo sin efectos siguientes.
- PENDING→AUTHORIZED sólo tras GET operador confirmado; POSTrun ambiguo no reenvío; attestationimport ambiguo sóloreadback.
- Writer no dispone de CAN_MANAGE/CAN_EDIT; Volume/ledger/widget por sí solos no autorizan.
- Runtimefields faltantes quedan etiquetados; contradicción explícita o attempt_number>0 aborta; widgets son lectura realruntime, no fixtureproducción.
- Transportes fixture+realGETexport bajo SP; luego un nuevo run acotado con notebook167 y registros de autoridad, sin borrar146/158.
- Publicación/CAS/closure readback, recuperación y aceptaciónE2E siguen gates separados; salidaJobSUCCESS no los sustituye.

No hay implementación167 ni prueba de mecanismo nuevo en164. Root debe decidir/registrar la aceptación de este contrato de autoridad y sus límites antes de construir167.
