# Publicación fresca081 — provisional, sin ejecución cloud

## Brecha, fuentes y decisión (2026-09-29)

Reutiliza plan078, publicación/registro016–068, revisión `runs/sk09-rotation-078-review.json` y ledger histórico99/112. Investigación nueva limitada al control de result cache y transporte del conector.

| Fuente primaria | Hecho observado | Decisión |
| --- | --- | --- |
| https://docs.databricks.com/aws/en/sql/language-manual/parameters/use_cached_result (actualizada2026-09-11) | `USE_CACHED_RESULT` es parámetro de sesión mediante SET | Ejecutar SET false y las32lecturas dentro de una conexión persistente |
| https://docs.databricks.com/aws/en/sql/user/queries/query-caching (actualizada2026-09-11) | Caché remota disponible para Statement API; persiste reinicios, ciclo24h; desactivar se recomienda para pruebas/benchmark | No reiniciar ni mutar tablas para invalidar caché. Fase081 es readback de validación, no configuración global de operación |
| https://docs.databricks.com/api/statement-execution/v1/execute-statement | Contrato consultado no expone session_id ni opción result-cache; tags describen atribución | No afirmar que SET enviado por SEA separado afecta SELECT posterior; no usar nonce/comments como bypass |
| https://docs.databricks.com/aws/en/dev-tools/python-sql-connector | Conexión SQL persistente, cursor.execute/fetchmany/description; autenticación normal | Adaptador de sesión Thrift; conector exacto revisado, sin cambiar la aplicación |
| https://github.com/databricks/databricks-sql-python/tree/v4.2.6 | Código distribuido oficial4.2.6 confirma session.open una vez, cursor.query_id, descripciones tipadas, retry knobs y transporte | Pin4.2.6 e intervención acotada en THttpClient; prueba con clase real y HTTPfixture |

Se inspeccionó primero4.6.0 (distribución disponible); su `Connection._open_session_with_recovery` puede cambiar automáticamente de Thrift a kernel ante warehouse Reyden. Se seleccionó4.2.6 porque `Connection` abre directamente una Session y no contiene esa recuperación de protocolo. No atribuir a4.2.6 APIs/hallazgos exclusivos4.6. Las dos wheels y hashes se registran en el cierre081. La versión seleccionada es una decisión de compatibilidad, no una recomendación general de downgrade.

## Implementación y límites

`runs/sk06-sk11-fresh-081.py` sin argumentos ejecuta preflight sin credenciales. Detecta dependencia ausente en runtime actual. `--execute` requiere revisión independiente del freeze; autenticación079 sigue sin acreditar. `--reconcile` sólo GET de IDs archivados, nunca reenviar. Para probar/ejecutar usar entorno aislado con `deployment/requirements-fresh-081.txt`; la instalación de prueba está en `/private/tmp/sbs-081-runtime`, no modifica `.venv` ni depsRAG.

Cap33SQL: SET false + DETAIL/HISTORY/SELECT VERSION/DETAIL ×8; ninguna DDL/DML. Ledger081 nuevo en `deployment/state/fresh-readback-081`; cada intención se fsync antes del envío, lock exclusivo, IDs y resultados separados. Una reserva/resultado ambiguo en una sesión perdida no se reenvía ni se devuelve al presupuesto. Reconciliación de ID desconocido queda pending explícito; no se inventa un match por SQL igual. El runner no ofrece reanudación de los brackets en otra sesión ni una segunda fase automática.

CapHTTP:256Thrift+256publisherGET+32Files/gobernanza+5warehouse=549 requests de workspace como máximo por ejecución; OAuth interno no está contado por esos transportes. Thrift socket20s, statement timeout30s, deadline operativo240s; los GET reutilizados tienen timeouts finitos del transporte existente. CaprespuestaThrift20MB y resultados10,000filas/20MB por lectura; sin cloud fetch/telemetría, sin retries de HTTP/backend. Sólo warehouse existente fijado; start053 se usa únicamente después de GET STOPPED y con intención durable; no auto-stop ni creación. No se ejecutó aquí.

`SessionReader` reutiliza `PublicationReader.read` para identidadUC/Delta, versión, esquema y contenido8tablas. Los tipos nativos del conector se normalizan al formato escalar del validador; `manifest_sha256` identifica explícitamente un manifiesto **normalizado del conector**, no un wiremanifestSEA. Los bytes/resultados normalizados quedan archivados como tales. `HistoryRegistryBuilder` mantiene32GET independientes, SQL exacto, publisher/warehouse y tiempos originales, y rechaza cualquier `cache_query_id`. SET también exige GET independiente terminado; que SET sea exitoso no sustituye comprobar historial de las32lecturas.

Certificado named<=5min, registro<=5min, política administrativa<=30min sin alterar reglas078. Snapshot binding exacto incluye todas las identidades/versiones/contenido. La renovación de declaraciones administrativas no afirma observación histórica ni evita ABA. Gobernanza publisher pre/post y metadatos de cada tabla provienen de GET; no prueba derechos del SP lector ni GenieE2E, que siguen gates del runtime078.

Antes de Files exige propietario exacto del volumen y grants efectivos completos sin escritores externos (paginación no cubierta falla cerrado). `status` se crea mediante PUT exclusivo administrativo, nunca sobrescribe una revocación. Paquete inmutable completo, readback byte a byte y pointer al final. RespuestaPUT perdida: GET exacto, ningún resend. StoreSHA es integridad, owner/grants observados son el supuesto de autenticación. No hay CAS del pointer ni defensa contra administrador malicioso; mantenimiento exclusivo y administradores confiables siguen explícitos. Los8readbacks deben coincidir antes de publicar, no se fabrica historia fresca.

## Evaluación CreatorZ

BaselineRED: módulo ausente y planSEA32 sin mecanismo de sesión. GREEN/adversariales: SET antes de lecturas, SQL cerrado, intención durable/cap33, respuesta perdida sin retry, EOF/rowcap, contenido8tablas+historial32, rechazo de caché, transporte real4.2.6 con fixture HTTP, publicacióninmutable/readback/pointer, respuestaPUT perdida, revocación irreversible por create-only. Evidencia es técnica local; no benchmark conductual completo ni validación producción. Revisión independiente sobre freeze pendiente. Costecloud desconocido (`null`).
