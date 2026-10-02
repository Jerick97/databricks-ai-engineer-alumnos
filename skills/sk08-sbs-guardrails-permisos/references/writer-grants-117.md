# Writer117 — grants aditivos mínimos, provisional

SK08/SK11 y skill-creator-z exacta; constructor local, revisión independiente root antes de remoto. Reusa069 (GETraw, unknown-before, deltas aditivos, preservar ajenos) y105(step_once durable sin resend), atomic/lock106 y pins host/operador/SP. Fuentes: SK08v0.1.4, runs/sk08-app-grants-069.py, baseline real116; no consultas cloud nuevas del constructor. Metadata no prueba M2M.

## Alcance exacto

Principal existente SP72803555975940/applicationId33b6f37c-7e6a-489f-b313-f886418b0319. Operador activo ID76826984571984/userName sociosdosmilveintiseis@gmail.com; host dbc-0410b264-20c7.cloud.databricks.com, sin puertos/userinfo/redirects.

- USE_CATALOG en neptuno_manuel_arguelles.
- USE_SCHEMA en neptuno_manuel_arguelles.sbs_radar.
- READ_VOLUME+WRITE_VOLUME en neptuno_manuel_arguelles.sbs_radar.release_artifacts. El grant UC cubre todo el Volume, no sólo bootstrap106/sbs-refresh. Alcance mínimo disponible de ese securable existente; no afirmar aislamiento por prefijo.
- CAN_USE en warehouse828756322bedff37.

No grants Applectora, ocho tablas, controltable(SELECT/MODIFY ya106), grupos, ownership, MANAGE, CREATE ni SQL/Jobs/start. Cuotas persistentes117:64HTTP/4PATCH acumulados, sin retries, timeout(10,60), respuesta<=1MiB. PATCH aditivo con un principal; nunca PUT/set_permissions/remove.

## Observación y decisión

FreshGET identidad/SP/grupos visibles; negar admins. UC GETdirect permissions y GETeffective-permissions con max_results150; negar paginación. Conservar rawJSON. Objeto{} exacto sólo antes significa unknown, no falta de acceso; null/tipos inválidos fallan. Warehouse ACL object_id/type exactos. Grupos SCIM observados sin equiparar users/account users ni presumir membresía implícita. Grupos no listados/indirectos siguen no demostrados.

Derechos disponibles directos o efectivos para principal/grupos explícitamente observados: no PATCH. Rechazar privilegios excesivos visibles; no revocar. Delta sólo privilegiosfaltantes, calculado con baseline durable. Freshreadback previo al efecto debe coincidir con baseline si faltan derechos; drift bloquea. PATCH tiene intentfsync previo y una tentativa.

Readback posterior exige asignación directa explícita requerida; nunca{}como éxito. Guardar direct/effective separados y marcar effective{} desconocido. Comparar todas las filas directas ajenas observadas; baseline{} sólo acredita preservación de filas visibles, no universoACL. Actor/grupos otra vez al final. Cambios ajenos concurrentes bloquean sin corregirlos. HTTP200 no reemplaza readback.

Journal117 separado106. Reanudación conserva before/identity/intents/contadores; ambiguous permite sólo readback. Review puede renovar ventana<=30min sin cambiar payloads. No borrar journal para reintentar.

## Ejecución revisable

CLIoffline default:

PYTHONPATH=src .venv/bin/python -m sbs.guardrails.writer_grants_117

Template deployment/writer-grants117-review-template.json tiene approvedfalse/tiemposnull. Tras revisiónroot:

PYTHONPATH=src .venv/bin/python -m sbs.guardrails.writer_grants_117 --execute --review-file deployment/writer-grants117-authorization.json --journal deployment/state/writer-grants117

## Evaluación y riesgos

RED módulo ausente. GREEN6tests: unknown-before/readback, paginación, deltaWRITE_VOLUMEsolo, preservaciónajenos, pipeline4PATCH+resume y ambiguousnoretry. HTTPfixture reproduce patrón069, no metadata real: primera29HTTP/4PATCH, resume40HTTP/4PATCH acumulado. Otros actores intactos. Constructor no llamó cloud.

Riesgo de sobrescribir ACL: PATCH1principal+comparación ajenos; concurrencia bloquea. Riesgo de inventar aislamiento: rawdirect/effective/unknown separado; grupos implícitos no inferidos. Riesgo de duplicados: intentdurable+readback, bajo hostjournal confiable. Riesgo de writeamplio: Volume completo explícito, no controlporprefijo. Resultado runtime_identity_verified=false; Job real/permisos efectivos/E2E siguen pendientes. Skill provisional sin benchmark conductual. JobPAUSED; políticas writer/GenieTTL5min se renuevan aparte.
