# Propuesta SK06: publicación por identidad y versión Delta

Investigación al 2026-09-28 UTC. SK06 0.1.4, mediante CreatorZ. **Diseño provisional; sin implementación, SQL remoto, publicación ni recursos iniciados.**

## Decisión

Sí, de forma condicionada: SQL cerrado con `VERSION AS OF <entero exacto>` y un certificado independiente del readback completo de **esa identidad de tabla y esa versión** permite aceptar nuevas escrituras de datos sin exigir una ventana global sin escrituras. No basta el trío nombre/version/hash si no se garantiza qué objeto resolvió el nombre durante la ejecución. Se sustituye la inmovilidad de datos por estabilidad de identidad y disponibilidad histórica, no por confianza en cualquier nombre coincidente.

La sintaxis documentada admite versión numérica obtenida del historial; también existe `@v`, que este primer perfil no necesita aceptar. No usar timestamp, versión relativa ni “latest”. [Referencia SQL](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-qry-select-table-reference).

**Recomendación mínima:** tablas Delta base gestionadas por Unity Catalog, referencias plenamente calificadas, una tabla por consulta como ahora; certificado con vector de versiones por publicación; namespace con controles verificables sobre DDL, políticas y retención. Permitir DML posterior que conserve el historial. Si no puede probarse ese control, conservar `unavailable/conflict`: dos GET antes/después no eliminan una sustitución intermedia (ABA). No se ha identificado aquí una API observada que vincule atómicamente el statement de Genie con los UUID y versiones resueltos.

## Baseline existente y brecha

`DatabricksHistoryProbe` comprueba statement ID, warehouse, ejecutor, atribución Genie, finalización SELECT, ausencia de cache y SQL observado. `publication_lookup(source_tables, started_at_ms, ended_at_ms)` exige hashes y ventana que cubra la ejecución. `RuntimeBinding.ask_scoped` repite la exigencia antes de llamar a Genie. El mapa local SK06/RAG verifica bytes locales, no tablas desplegadas. El runtime de aplicación solo conecta ese binding; no debe construir certificados desde solicitudes.

El nuevo diseño requiere otro modo de certificado y referencias temporales. **No es compatible como sustitución silenciosa del callback actual.** No eliminar checks de historia, contexto, filas esperadas ni permisos. Query History no acredita por sí solo contenido completo ni identidad Delta.

## Hechos documentados y alcance

- `DESCRIBE HISTORY` ofrece versión, operación y procedencia de escrituras. Historial no equivale a lectura de filas. [Comando](https://docs.databricks.com/aws/en/sql/language-manual/delta-describe-history).
- El time travel depende de conservar logs y archivos. Los valores predeterminados documentados son 30 días para logs y 7 para archivos eliminados; VACUUM y limpieza de logs pueden volver inaccesible una versión. Aumentar retención implica almacenamiento adicional. No usarlo como archivo permanente. [Historial y retención](https://docs.databricks.com/aws/en/tables/history).
- `DESCRIBE DETAIL` devuelve identificador, formato, ubicación y protocolo; sus columnas dependen de runtime/features. Registrar el ID Delta separadamente del `table_id` de Unity Catalog, sin suponer que coinciden. [Detalle](https://docs.databricks.com/aws/en/tables/operations/table-details).
- El GET de tabla documenta `table_id`, `metastore_id`, formato, tipo, ubicación y políticas; permite detectar vistas y objetos incorrectos. Ni `updated_at` ni el campo genérico de propiedades Delta son prueba de versión leída. [API de tablas](https://docs.databricks.com/api/uc-tables/v1/get-table).
- `CREATE OR REPLACE TABLE` conserva identidad e historial; no debe confundirse con `DROP` seguido de creación. Aun con identidad conservada, hay que verificar versión, esquema y políticas del perfil autorizado. [Drop/replace](https://docs.databricks.com/aws/en/tables/operations/drop-table), [CREATE TABLE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-table-using).
- La documentación excluye time travel con filtros de filas/máscaras a nivel de tabla; ABAC tiene soporte Beta condicionado. El primer perfil rechazará ambos, sin ampliar permisos ni desactivar controles existentes. [Filtros y máscaras](https://docs.databricks.com/aws/en/data-governance/unity-catalog/filters-and-masks/).

## Contrato mínimo propuesto, no implementado

`publication_certificate/v2` contiene:

- `attestation_id`, `mode=delta_version`, `publisher_identity`, fecha de emisión, estado/revocación, ancla de confianza del almacén servidor y hash/firma del certificado. Un hash autorreferido no autentica al emisor.
- `publication_id`, `sk06_snapshot`, `rag_mapping_sha256`, hash de configuración y de plantillas cerradas. No igualar hashes SK06 y RAG.
- Por tabla: `full_name`, workspace/metastore, `uc_table_id`, `delta_table_id`, tipo/formato, fingerprint de ubicación, `delta_version` entero no negativo, esquema de la versión con hash, protocolo/features observados.
- `content_sha256`, `row_count`, `canonicalization_id`, columnas/tipos explícitos y clave estable. Preservar duplicados, nulls y literalidad de `payload_json`; detectar claves duplicadas. Canonicalización idéntica para export y readback; no confiar en orden incidental del servidor.
- Prueba de lectura real: statement ID, SQL/hash, ejecutor, warehouse, estado final, versión especificada, schema/result-manifest hash, chunks completos, conteos y hash calculado desde filas efectivamente recibidas. Separar hash esperado de observado.
- `identity_control_evidence`, configuración de retención observada, horizonte de servicio conservador y política de revocación. La fecha de caducidad expresa política operativa, no una garantía física de archivos.

API propuesta: `lookup(publication_id, table_bindings)` recupera certificado inmutable; `verify_identity_and_access(table_bindings, executor)` verifica gobernanza vigente; el probe extrae `[{full_name, delta_version}]` del SQL realmente ejecutado y los compara exactamente. No aceptar versiones enviadas por el usuario. El callback de identidad no debe declarar cobertura temporal que sus fuentes no prueban.

## Publicación verificable, futura y bajo autorización separada

1. Verificar configuración del namespace, warehouse y ejecutores, privilegios y capacidades de SQL/Genie. El lector necesita USE CATALOG/SCHEMA y SELECT; los permisos del publicador son independientes. GET visible no prueba SELECT. [Privilegios UC](https://docs.databricks.com/aws/en/data-governance/unity-catalog/access-control/privileges-reference).
2. Publicar los artefactos curados con linaje SK06 bajo control del publicador. Obtener candidato de versión mediante historial y comprobar identidad UC/Delta. Un “último commit de sesión” compartida puede competir con otras escrituras: no asumir que pertenece a la tabla buscada. Confirmar contenido por readback; un candidato incorrecto se rechaza.
3. Leer columnas explícitas desde `catalog.schema.tabla VERSION AS OF N`; no hacer `SELECT *` sobre el esquema actual ni usar solo COUNT. Recibir todos los chunks, comprobar ausencia de truncamiento y cobertura de filas, calcular hash y contrastarlo con el export sellado. El API documenta manifiesto, esquema, chunks y `truncated`; falta probarlo en este workspace. [Statement results](https://docs.databricks.com/api/statement-execution/v1/get-statement-result).
4. Repetir para cada tabla. Versiones distintas por tabla son válidas únicamente si todos los readbacks coinciden con la misma publicación local y las invariantes cruzadas. Un vector de versiones no implica transacción global de todas las tablas.
5. Verificar controles sobre sustitución/renombrado/drop, políticas y retención; publicar atómicamente el certificado y después el puntero de release. Ante cualquier fallo conservar release previo. Los DML posteriores no invalidan automáticamente el certificado histórico.
6. Antes de Genie comprobar certificado, autorización y disponibilidad dentro del horizonte aprobado. Tras ejecución conservar historia real y comparar AST exacto con la plantilla ya fijada a N y contexto. Comparar columnas/filas con el resultado determinista local; ausencia de atribución, versión distinta, cache o datos incompletos implica conflicto sin filas. Una cuenta igual no prueba identidad de tabla.
7. Si el warehouse no permite esa versión o cambia identidad/política/retención, revocar o marcar unavailable. Nunca reemplazar por lectura actual ni ampliar la retención automáticamente.

## Riesgos y límites que deben quedar como gates

| Riesgo | Tratamiento propuesto |
|---|---|
| DROP/recreate o rebinding del nombre | Comparar UUID UC/Delta y ubicación; controlar DDL durante servicio. Pre/post GET detecta algunos cambios, no demuestra ausencia de ABA. No afirmar garantía contra administrador privilegiado. |
| Esquema histórico, cambio de tipo, protocolo incompatible | Esquema tipado del readback de N, proyección explícita y validación de runtime/features. No deducir esquema de N del GET actual. Delta permite evolución; probar cada incompatibilidad antes de habilitar. [Delta batch](https://docs.delta.io/delta-batch/). |
| VACUUM, cleanup, retención reducida | Retención operativa y comprobación de lectura; fallo cerrado. Hash certificado conserva evidencia, no recupera archivos. |
| Vista, función, shallow clone, tabla externa | Fuera del perfil inicial. Una vista puede ocultar referencias actuales; expandirla sin prueba no fija sus fuentes. No convertir rutas en atajo para evitar UC. |
| Equivalencia SQL | Mantener AST exacto: probar temporal clause, literal entero, quoting y aliases permitidos. Rechazar `@v` inicialmente, timestamps, joins, CTE, subqueries o funciones no presentes en plantilla. SQL equivalente semánticamente no es automáticamente aceptable. |
| Permisos y políticas | Vigentes al ejecutar; el certificado histórico no otorga derechos. No asumir snapshot de autorizaciones. |
| Cache y resultados incompletos | Mantener rechazo actual de cache; readback sin truncamiento y con todos los chunks. |

## Capacidades observadas y pendientes

Reutilizado `runs/sk06-provenance-metadata.json`: GET Query History funcionó por statement ID; muestra sin atribución Genie y warehouse STOPPED. No prueba SBS cloud. Inspección local del SDK 0.102.0: existen `TablesAPI.get(include_delta_metadata=...)`, `TableInfo.table_id`, APIs execute/get/chunk; `QueryInfo` no tiene campos directos de tablas/versiones. **Métodos instalados no equivalen a permisos o funcionamiento remoto.**

SQLGlot 30.20.0 parseó localmente una referencia `VERSION AS OF 7` como nodo temporal. Esto solo acredita sintaxis local; faltan tests de comparación exacta/extracción y ejecución Databricks. No se llamó a SDK remoto en esta investigación. Se intentó URL antigua `/aws/en/tables/drop-table`, inaccesible; se usó la página oficial vigente de operaciones.

Siguiente implementación requiere RED/GREEN para versión ausente/equivocada, nombre igual con UUID distinto, certificado falsificado, readback parcial, DML posterior aceptado, VACUUM denegado, schema/policies, release parcial y contexto cruzado. Luego una prueba cloud expresamente autorizada debe publicar, certificar N, escribir N+1 y demostrar que Genie ejecuta N con procedencia completa. Si Genie no conserva SQL temporal exacto, seguirá en conflicto; no simularlo con SQL fijo presentado como Genie.

**Estado final:** alternativa recomendada para implementación controlada; no lista para producción. Coste de SQL/almacenamiento no medido (`null`). Skills y código conservados.
