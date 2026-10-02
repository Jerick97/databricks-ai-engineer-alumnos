# Reader cloud → runtime — checkpoint15

`create_service(..., mode='cloud', cloud_config_path=None, cloud_reader_factory=None, cloud_clock=None)` adjunta el conector de `sbs.operations.runtime_cloud`. Ausencia de `config/runtime-cloud.json` o `{"enabled":false}` deja `runtime_refresh.status=disabled`, sin SDK. Config activa inválida falla; no vuelve silenciosamente a modo congelado. Un bootstrap local existente se conserva con estado pending hasta observar publicación. Un fallo remoto conserva el snapshot anterior con unavailable.

La app existente usa `for_actor`, catálogo, comparación, fuentes y ask. El hook refresca antes del lock que cubre autorización y lectura; nunca entre ambos. `catalog` también dispara refresh. Poll síncrono, sin scheduler/Job/thread nuevo: intervalo `poll_seconds`, cuotas por instancia para polls, promociones retenidas, HTTP, SQL y Files. Peticiones concurrentes no duplican poll; siguen usando snapshot verificado anterior mientras otra prepara. Primera descarga puede ser lenta: invocar fronteras síncronas desde threadpool si el host usa event loop async. No resetear instancias para ampliar cuotas.

## Config servidor cerrada

Campos exactos: `version=1`, `enabled=true`, `workspace_host`, `client_id`, `executor_id`, `control_table`, `control_table_id`, `warehouse_id`, `volume_prefix`, `backend_sha256`, `policy`, `policy_sha256`, `poll_seconds`, `max_polls`, `max_promotions`, `max_http_calls`, `max_sql_statements`, `max_files_calls`, `cache_root` (relativo al proyecto, sin symlinks).

- Host HTTPS AWS Databricks fijado, client_id UUID OAuth M2M y executor_id SCIM entero positivo observado. Credenciales provienen del Config normal del servidor, jamás del JSON ni HTTP. Se comparan host/auth_type/client_id antes de requests y Me activo/id/userName antes de SELECT. Si Me no devuelve esos campos, no fabricarlos: queda unavailable.
- Tabla `catalog.sbs_radar.table`, UC table_id observado y warehouse_id observado; volumen `/Volumes/catalog/sbs_radar/volume/sbs-refresh`. `backend_sha256 = digest({control_table,control_table_id,warehouse_id,volume_prefix})` usando canonical JSON del módulo compartido.
- `policy` exacta: `trusted_administrators` lista no vacía, `maintenance`, `singleton_control`, `reader_access` (declaraciones operativas no vacías), `issued_at_ms`, `expires_at_ms`. `policy_sha256=digest(policy)`. No son observaciones de exclusividad global ni grants probados. La política y archivo pertenecen al servidor confiable.
- Límites enteros positivos: poll_seconds≤86400, max_polls≤1000, max_promotions≤32, max_http_calls≤4000, max_sql_statements≤1000, max_files_calls≤3000. No hay configuración activa entregada: recursos/permisos cloud siguen pendientes.

## Binding concreto

`CloudSnapshotReader` reutiliza exclusivamente `DeltaControl.read` y `VolumeArtifacts` con transporte `ReadOnlyApi`, sobre serializers oficiales SDK. Me, UC table GET, warehouse GET y SQL SELECT fijo preceden a Files download. GET observa UC ID/formato/owner/Serializable y ausencia visible de filtros/máscaras; continuidad y singleton administrado son supuestos explícitos. SELECT verifica la fila singleton y esquema/estado/recibos mediante contrato SK11. Warehouse debe devolver RUNNING antes del SELECT; no se inicia compute. Una carrera administrativa posterior al GET no se declara imposible.

Transporte deriva de SingleAttemptApi revisado: único intento, errores stream/close seguros, timeout/caps, y puerta exacta que rechaza PUT/DELETE/Jobs/start/SQL distinto incluso antes de autenticar. Esta puerta no prueba grants: app necesita SELECT del control, READ VOLUME y visibilidad metadata; nunca darle MODIFY/WRITE para resolver una falta del reader.

Nuevo receipt → `materialize_release` download-only → `LocalService.promote_release`; verificación completa de cierre/hash/originales/modelo antes del swap. Snapshot y estado de promoción se actualizan bajo lock. Mismo publication_id observado evita repetir descarga; `current` significa identidad del puntero observado, no una nueva verificación remota de todos los bytes en cada GET. Directorios previos se retienen para lectores existentes; cuota de promociones limita su crecimiento, sin limpieza de snapshots activos. Genie sigue unavailable para releases no publicados/mapeados.

## Salida pública segura

Catálogo y vista autorizada conservan filtros y añaden `snapshot`, `runtime_refresh={enabled,status,reason,last_checked_at,last_success_at,publication_id,checks,evidence_mode}`. Comparación y ask incluyen snapshot. Status: disabled, pending, current, unavailable, quota_exhausted. Razones cerradas: CLOUD_NOT_CHECKED, NO_PUBLISHED_RELEASE, CLOUD_REFRESH_FAILED, POLL_QUOTA_EXHAUSTED, PROMOTION_QUOTA_EXHAUSTED o null. No URLs, excepciones SDK ni credenciales. evidence_mode fixture/real describe la dependencia utilizada; no es aprobación E2E.

## Evidencia y pendientes

Reutilizados: contratos/revisión SK11 shared-control/Files/CD01, server.py host/OAuth pins, runtime-release014, SDK0.102 serializers locales y PDFs/vectores sellados. No investigación amplia repetida, inferencia, SQL o GET cloud durante construcción. Pruebas conectan create_service y request reales locales a fixtures remotos; incorporación de segunda familia, corrupt closure, throttle, quotas y preservación del snapshot. Faltan configuración y permisos observados del reader real, ensayo autorizado y revisión SK09 independiente; no certificar nube, frescura de normas ni calidad semántica.

La selección del cliente puede pertenecer al snapshot anterior mientras una request activa promoción. El backend devuelve el snapshot real de comparison/ask, pero el contrato actual no recibe expected_snapshot del cliente. La UI debe contrastarlo antes de presentar, limpiar/refrescar selección y evitar atribuir respuesta nueva al snapshot anterior; no afirmar coherencia cliente/servidor solo porque el par conserva su ID.
