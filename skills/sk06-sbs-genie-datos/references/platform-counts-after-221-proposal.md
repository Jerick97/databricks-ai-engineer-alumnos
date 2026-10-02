# Propuesta mínima posterior a221: conteos Genie con autorización de plataforma

Estado: DISEÑO, sin implementación/cloud. Propietarios SK06/SK08; revisión independiente SK09 requerida. Se preservan221 PASS_CODE y FAIL_E2E. Causa observada: `PermissionDenied` en `governance_service_principal_get`, antes de SQL (`runs/ui221/count-failure-logs.txt`). El GET del operador no acreditaba capacidad M2M del App.

## Decisión y fundamento

Crear perfil servidor opt-in `platform_enforced_historical_counts_v1`, sin degradación automática desde `trusted_admin_observed_v1`. Mantener íntegros snapshot/219/guard221/pins/revocación/SQL/versiones/filas. Retirar de este perfil la enumeración de ServicePrincipals/{id}, Groups, grants efectivos y ACL de warehouse/Genie: sus permisos administrativos no son requisito para ejecutar una lectura autorizada. No conceder admin ni nuevos grants/credenciales.

Barrera preventiva de escritura: el PRODUCTO Genie genera y ejecuta consultas sólo lectura. La documentación primaria [Genie concepts](https://docs.databricks.com/aws/en/genie-agents/concepts) lo afirma para Genie Agents, antes Genie Spaces; [REST Chat](https://docs.databricks.com/api/genie/v1/genie-start-conversation) corresponde al mismo POST `/api/2.0/genie/spaces/{space_id}/start-conversation` y messages permitido por GenieTransport. No es una propiedad de Genie Code. Se conserva el transporte confinado a ese producto y espacio; no habilitar StatementExecution, comandos generales, herramientas, funciones nuevas ni endpoints administrativos.

Ésta es una garantía del proveedor, no una demostración de que el principal carece de MODIFY/ownership. Debe declararse `read_only_basis=genie_product_contract`, `effective_privileges_enumerated=false`, `principal_select_only=not_observed`. La ejecución real de SQL y acceso a datos siguen aplicados por Databricks/UC; el token es AppM2M, no el token UC del humano. Autorización humana/familia del App permanece separada.

La [documentación de recurso Genie en Apps](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/genie) describe permisos de consulta del service principal; la [API Genie](https://docs.databricks.com/aws/en/genie-agents/conversation-api) enlaza el modo Chat. Esa evidencia permite conservar Genie y no sustituirlo por SQL manual etiquetado como E2E Genie. No afirma que la configuración real esté probada.

## Identidad: comparación y decisión

A. `GET /api/2.0/preview/scim/v2/Me` identifica al llamador autenticado; la [referencia](https://docs.databricks.com/api/scim/v1/me) permite cualquier token con scope. No necesita leer SCIM de otro recurso ni grupos. Se propone observar Me con la MISMA configuración M2M usada para Genie, comparar ID decimal exacto con AppSP77041447522099 y rechazar mismatch/false active. Si active falta, no inventar ese campo: registrar no observado; la respuesta autenticada y la ejecución atribuida forman la prueba. No usar nombre visible, cabeceras del navegador ni owner como identidad App.

B. `host/auth_type/client_id` fijados en servidor acreditan configuración esperada, no identidad ejecutora por sí solos. Por eso no sustituyen Me ni Query History. El resultado sólo se devuelve después de comprobar `executed_as_user_id` entero exacto del historial de la consulta nueva. Si Me no es accesible bajo AppM2M, el perfil propuesto permanece bloqueado; no fallback silencioso a config-only.

## Lecturas reales mínimas y observación previa

No presumir acceso por documentación. Incluir en el mismo candidato una comprobación fija de capacidades M2M, antes de habilitar el primer POST Genie. Una acción administrativa autenticada+CSRF «Comprobar consultas documentales» ejecuta exclusivamente estos GET, con IDs/config del servidor y sin parámetros de recurso del navegador:

1. Me: igualdad de ID; no grupos/roles.
2. `tables.get` de las dos tablas elegibles documents/provisions, include_browse=false: UCID/metastore/location, MANAGED/DELTA y columnas reales comparables al certificado. [Get table](https://docs.databricks.com/api/uc-tables/v1/get-table) admite principal con USE_CATALOG/USE_SCHEMA/SELECT; no requiere ownership/admin. Mantener rechazo de filtros/máscaras visibles incompatibles; no inferir ausencia de ABAC.
3. Genie get_space del único espacio: IDs/warehouse configurados y metadatos básicos. Sin leer ACL.
4. Warehouse get del único warehouse: ID/tipo/estado observados. Estado STOPPED/STARTING no es falta de permiso ni motivo de start manual.
5. Files GET no-cache de estado binding y generación219 fijada: validación221 íntegra. No nuevo certificado/puntero ni escrituras.
6. Query History GET filtrado por AppSP/warehouse y período acotado, max_results=1: discriminar endpoint denegado de accesible sin registros. La [referencia](https://docs.databricks.com/api/query-history/v1/list-queries) documenta el endpoint, pero no demuestra acceso real App. Un resultado vacío sólo acredita respuesta al GET; no el historial de una consulta futura.

Máximo8 GET, una pasada, sin SQL, POST Genie, start/stop, grants ni reintentos. Guardar sólo resultados fijos por operación, IDs públicos esperados/observados necesarios, hashes de metadatos y códigos/clase seguros; no cuerpos SCIM/SQL/excepciones/tokens. Nunca convertir una excepción en éxito ni hacer que un error temprano impida observar las otras capacidades independientes. Cada requisito desconocido/denegado se muestra claramente.

El App actual221 no expone esta operación; sin introducir credenciales fuera del App no podemos prometer prueba M2M previa a desplegar código que la ejecute. La estrategia evita otro intento ciego de consulta: un único candidato revisado reúne observación y perfil, y no hace POST Genie si las capacidades requeridas fallan. Ninguna señal de diagnóstico habilita un bypass. El resultado de diagnóstico no queda como permiso cacheado permanente: las comprobaciones necesarias se repiten por pregunta.

## Flujo de consulta

- Guard cerrado221 antes de cualquier lectura remota: sólo conteos documentales/disposiciones registrados; listas/latest/vigencia/SQL libre denegados con cero llamadas. Enviar a Genie instrucciones de servidor con contexto y COUNT cerrado; no confiar en que el modelo obedecerá: comprobar después SQL real.
- Antes de Genie: Me actual + metadata actual de la tabla exacta elegida + estado remoto activo + generación219 íntegra. Mantener bindings de UC/metastore/location y tipo; no consultar grant/group APIs. La autorización final de ejecución la aplica UC, no un booleano inventado por el preflight.
- Preflight nuevo con esquema propio (`authorization_profile`, `configuration_verified`, `execution_authorization=pending_platform_check`); NO rellenar `can_use/tables_read/read_only_backend=true` para satisfacer el perfil antiguo. Legacy no cambia. Resultado terminado de plataforma aún no es resultado verificado del App.
- Permitir warehouse RUNNING, STOPPED o STARTING en este perfil. [Databricks](https://docs.databricks.com/aws/en/compute/sql-warehouse/) documenta autoarranque al consultar un warehouse detenido con acceso. No llamar /start ni desactivar autostop; no garantizar que el arranque ocurrirá. Bounded GET polling continúa distinguiendo running/timeout/denied/error, sin reenviar POST ambiguo. Usar el límite existente de espera; si resulta insuficiente, registrarlo antes de cambiarlo, no ampliar silenciosamente.
- Después: historial independiente de la NUEVA consulta, actor AppSP exacto, space/warehouse, final SELECT sin caché/error, SQL AST y VERSION AS OF exactos, parámetros/filtros de contexto, columnas/filas reales iguales al snapshot. Un resultado vacío de plataforma por falta de acceso no se trata como cero verificado.
- Repetir Me/metadata/revocación después, con identidad estable, tiempos reales que abarcan ejecución y TTL de observación existente≤60s. No retener afirmaciones de grants/grupos ni inventar pruebas DDL/retención. Conservar límites ABA/continuidad y relación física no probada. Si falla cualquier prueba, no mostrar filas/respuesta Genie como verificadas.
- Mantener etiqueta histórica221 y scope del par seleccionado, ambos documentos y seguimiento. No cambiar cuota de inferencia, prompts normativos ni corpus.

## Corrección de tipado del rechazo

El guard221 rechazó «¿Cuántas versiones documentales están vigentes?» pero la UI mostró «Fuentes en conflicto». Usar estado específico `scope_not_answered` + mensaje «Esta consulta admite conteos del snapshot publicado; no determina vigencia jurídica». Conversation debe reconocer este rechazo antes de comparar snapshots o llamar otra herramienta. Conservar evidencia del fallo221; cero SDK sigue siendo requisito.

## Implementación prevista (después de revisión, no realizada)

- Nuevo `src/sbs/genie/platform_counts.py`: capacidad explícita, Me/metadata observados y permiso aplicado por plataforma, sin heredar ni simular collector administrativo.
- `server_rotation.py`, `delta.py`, `runtime.py` de Genie: elegir perfil sólo por configuración fijada, sesiones pre/post propias; conservar historical reader221.
- `genie/__init__.py`: preflight específico por capacidad de servidor, warehouse stopped/starting y mismos guards/SQL/resultados.
- `conversation/__init__.py`: tipado correcto de scope no admitido.
- Config rotación/política/bootstrap pinned y manifest de delta. No sobrescribir paquete221.
- Webapp existente: una operación administrativa fija de capacidades, con identidad/CSRF originales y controles visibles, sin endpoint de proxy genérico.
- Tests del archivo de matriz adjunto, regresiones221+legacy y revisión SK09. Evidencia real posterior requerida, sin adjudicar éxito mediante mocks.

## Riesgos y límite de cierre

Proveedor garantiza lectura, no exactitud semántica ni mínimo privilegio del App. No afirmar que los privilegios efectivos fueron enumerados; esa garantía se retira explícitamente en el nuevo perfil. Me/table/get_space/history accesibles siguen por observar bajo AppM2M. Warehouse puede tardar o fallar. Sin historial real completo no hay E2E aceptado. Los permisos desconocidos no justifican conceder admin. No reabrir221 ni borrar fallos anteriores para presentar continuidad de éxito.
