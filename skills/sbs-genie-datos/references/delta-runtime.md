# Runtime Delta v2 — contrato local, 0.1.8 provisional

Fuentes reutilizadas: `docs/propuesta-procedencia-version-delta.md` y `runs/sk09-publication-resolution-review.json`. Sin consultas remotas nuevas. Este componente acepta capacidades de servidor; no implementa ni certifica un registro desplegado, servicio de gobernanza o proceso de publicación.

## API de servidor

Construir `DeltaPublication(certificate, certificate_sha256, mapping_sha256, registry_lookup, identity_access_probe)` desde `sbs.genie.delta`. `certificate` es `Certificate` v2 del almacén servidor confiable, con `evidence_mode=real`. La capacidad es frozen y sus mapas retornan copias. El pin identifica bytes; el registro autentica el origen por la frontera de confianza del servicio desplegado. Nunca construir estos callbacks desde payloads del usuario o valores esperados.

Pasar la capacidad en `ServerDependencies(..., publication_lookup=None, delta_publication=capability)`. `load_runtime_binding(...)` verifica localmente certificado, ocho hashes/conteos, configuración y mapa original, sin callbacks. El catálogo genera las mismas referencias documentales con `VERSION AS OF N` por tabla. El modo se selecciona explícitamente por capacidad; no se autodetecta desde un certificado de solicitud. Sin capacidad Delta, permanece el contrato v1 de intervalo sin escrituras. Sin IDs/configuración, `ask_scoped` permanece unavailable y no consulta capacidades.

El loader conserva `genie_snapshot`, `rag_snapshot`, `mapping_sha256`, `contexts`, `snapshot_map`, `readiness()` y `ask_scoped`. `readiness.available` solo describe capacidades configuradas. La publicación se comprueba por solicitud. Contexto exacto se valida antes de callbacks; SQL/filas/lineage conservan snapshots originales.

## Registro independiente

`registry_lookup(certificate_sha256=...)` devuelve un registro confiable, obtenido por hash exacto y con:

- `certificate_sha256`, `mapping_sha256`, `status=active`, `evidence_mode=real`, `publisher_identity`, `attestation_id`, `valid_from_ms`, `valid_until_ms`.
- `readback_execution_verified=true`, `publisher_warehouse_id`, `publisher_executor_id` entero.
- `readback_executions`, exactamente 32 registros en orden certificado/tabla/prueba. Cada uno vincula `statement_id` único y `observed_sql_sha256` con la prueba del certificado, y conserva `warehouse_id`, `executor_id`, `status=FINISHED`, `is_final=true`, `started_at_ms`, `ended_at_ms`, `history_record_sha256`. Cache/error presentes rechazan.

Esos registros deben proceder del historial independiente realmente observado, no del SQL enviado por PublicationReader. El lector v2 no los produce automáticamente. La implementación real del registro y la observación de esos 32 historiales siguen pendientes. Etiquetar un fixture como `real` no lo autentica; los tests hacen esa simulación únicamente para recorrer ramas locales y lo declaran explícitamente.

## Identidad, derechos y disponibilidad histórica

`identity_access_probe(source_tables, executor_id, warehouse_id, space_id, started_at_ms, ended_at_ms)` recibe identidad de ejecución y período; no recibe los hashes/UUID esperados para construir una supuesta prueba. El servicio debe recuperar evidencia independiente de su publicación fijada.

Salida: `evidence_mode=real`, `evidence_id`, identidad exacta de ejecutor/warehouse/space, cobertura `valid_from_ms/valid_until_ms`, y booleanos exactos `select_authorized`, `backend_select_only`, `ddl_identity_controlled`, `retention_controlled`, `policies_absent`. `tables` contiene la tabla seleccionada con `full_name`, `uc_table_id`, `metastore_id`, `delta_table_id`, `location_sha256`, `delta_version` y `schema_sha256`, iguales a la publicación certificada. No devolver True por copiar una solicitud. Un par de GET no justifica cobertura de controles DDL ni elimina ABA. Si el servicio no puede justificar estos controles, la capacidad debe faltar o rechazar.

Se comprueban registro y gobernanza antes de Genie y después sobre el intervalo observado en Query History. El intervalo acredita controles/identidad/derechos; no prohíbe DML que preserve versión e historial. La ausencia por VACUUM/retención o prueba insuficiente debe producir rechazo. Se preservan warehouse, ejecutor, space, finalización, ausencia de cache y SQL del historial Genie. El AST exige una tabla plenamente calificada y literal entero `VERSION AS OF`, luego igualdad estructural de toda referencia contextual y filas esperadas; ninguna equivalencia aproximada sustituye eso.

## Límites

`aba_prevented=false` permanece explícito. Los callbacks son frontera de confianza, no autenticación criptográfica incorporada. No se implementa aquí servicio cloud de revocación/gobernanza, consulta de historia del publicador ni promoción de runtime de aplicación. La implementación local no demuestra que Genie emitirá SQL temporal exacto. Si no lo hace, el resultado es conflict sin filas. No hay publicación, inferencia, cambios a recursos ni E2E cloud en esta fase; requiere SK09 independiente antes de promover.

La identidad observada del ejecutor requiere tipo int exacto. Todas las 32 lecturas deben haber finalizado a más tardar en valid_from_ms del registro, que a su vez debe preceder la ejecución Genie cubierta. Esta relación es obligatoria; no hay tolerancia que convierta tiempos futuros en prueba.
