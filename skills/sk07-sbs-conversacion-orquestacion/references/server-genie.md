# Factory de Genie en la app — SK07

`LocalService.initialize_genie()` llama `sbs.genie.server.load_server_binding(ROOT, mode=...)`. No tiene argumentos de configuración provenientes del navegador. Sin `config/genie-server.json` o con enabled=false conserva binding local y disponibilidad pendiente, sin construir SDK. El archivo example es una plantilla deshabilitada, no una configuración desplegada; no debe activarse con valores null.

La configuración activa exige archivos protegidos de runtime, certificado y política con SHA256 fijados. Crear el runtime cloud como copia explícita de config/genie-pilot-002.json con warehouse_id observado (`828756322bedff37`) y space_id realmente creado. Preservar el export original, mapa y snapshots. El certificado debe provenir del readback y el registro del historial independiente; no generar un certificado ficticio para habilitar la app.

Cloud exige OAuth M2M, host y client_id de la app concordantes. No emplea perfil personal ni acepta identidad del usuario como identidad del backend. La identidad SCIM y permisos de datos actuales se verifican mediante SK06. `ServerPermissionProbe` observa warehouse, espacio y ACL Genie con CAN_RUN; CAN_VIEW no concede consultas. Estado configurado no significa publicación o E2E verificado.

La fuente primaria de la distinción CAN_RUN/CAN_VIEW es https://docs.databricks.com/aws/en/dev-tools/databricks-apps/genie (consultada2026-09-28). El endpoint de ACL es GET /api/2.0/permissions/genie/{space_id}, documentado en https://docs.databricks.com/api/access-management/v1/permission. Métodos y cuerpos Genie se verificaron en SDK0.102.0 instalado.

`GenieTransport` usa la autenticación normal del SDK, pero envía cada operación exactamente una vez con requests, sin redirects ni retries. Limita endpoints al espacio fijado, conversaciones/mensajes y query-result; no implementa start de compute ni SQL directo. No invocar Wait.result: el adaptador SK06 realiza su polling acotado. Cien operaciones HTTP es un límite por proceso, no un presupuesto monetario durable.

`RemoteEvidence` lee registro/revocación y estado de política vía FilesAPI, bajo el volumen propio; no supone que Apps tiene /Volumes montado. Registro: `<certificate_sha256>.json`, tombstone opcional `<certificate_sha256>.revoked.json`; reutiliza parser SK06 revisado mediante copia temporal por observación. Ausencia explícita del tombstone permite continuar; denegación/transporte no equivalen a ausencia. Estado de política obligatorio `<policy_id>.status.json` con policy_id, policy_sha256 y status active/revoked. Administradores mantienen esos objetos; app requiere solo READ_VOLUME. No se crea ni sube nada desde la factory.

La política trusted_admin_observed_v1 debe identificar administradores y supuestos de mantenimiento/ABAC, issued/expires y TTL. Datos y supuestos son distintos; no declara continuidad histórica ni inmunidad frente administradores. El estado remoto permite revocación y se consulta nuevamente durante la verificación. Una copia empaquetada estática no es una autoridad de revocación actual.

Sin espacio, tablas publicadas, registro remoto, política y permisos observados, la configuración activa no es entregable. Tests con SDK/datos simulados prueban ensamblaje y rechazo, nunca publicación o Apps SSO. Faltan ejecución remota y UI.

## Hallazgos SK09 y corrección

Config activa exige también `genie_acl_object_id`, observado por GET permissions/genie del space_id exacto. Una observación real acotada (runs/sk07-genie-permission-format-001.json) mostró space_id opaco y object_id numérico diferente: no son intercambiables. Este registro solo acredita el formato de una muestra; la app propia debe fijar su ID real al preparar su configuración. CAN_RUN requiere object_type genie y coincidencia con ese ID fijado.

La validación de host AWS HTTPS ocurre antes de WorkspaceClient. La cuota reserva cada intento bajo lock antes de construir la sesión; no es un presupuesto durable. El resolver enlaza el applicationId observado del principal consultado con el client_id autenticado: comprobar solo los dos valores por separado no basta. La copia temporal del registro resuelve aliases del sistema antes de pasar al parser existente; el parser conserva sus restricciones.

## Perfil de servidor explícito068

Config versión1 conserva `strict_location_v1` y su forma cerrada. Versión2 exige `identity_profile`, validado contra perfiles SK06 antes de construir credenciales. El certificado debe validar con ese perfil antes de SDK; RemoteEvidence pasa el mismo valor a RegistryLookup y DeltaPublication lo recibe como certificate_identity_profile. Un cliente HTTP, pregunta o payload no puede elegirlo. El perfil `uc_managed_named_replay_v1` mantiene todas las limitaciones064; no cambia endpoints permitidos, OAuth M2M ni checks de grants actuales.

Propuesta concreta deshabilitada: `config/genie-server-068-proposal.json`, runtime `config/genie-runtime-068.json`, política `config/genie-admin-policy-068-proposal.json`. Fija Genie01f1bb81787b118c9bbc8980e3523a21, warehouse828756322bedff37, app executor77041447522099/client a947eccf-5f94-4369-a3d4-8f83b4ea98a1, ACL /genie/2365958246005085. No modifica `config/genie-server.json` ni crea una activación. La política copia la ventana y declaraciones ya existentes; es propuesta, no un archivo de estado remoto activo. backend_select_only_grants_verified sigue false: trabajo067 separado aporta sus observaciones, no esta configuración.

La referencia de certificado apunta al archivo local real064 para revisión; ese directorio deployment/state se excluye del paquete portable. Antes de desplegar, operaciones debe colocar un certificado vigente en la ruta protegida del release y regenerar su path/hash en la configuración revisada. No activar esta propuesta por cambiar únicamente enabled.

### Frescura operacional y rotación

El certificado identifica contenido inmutable; la atestación del registro064 dura300000ms. Construcción local y readiness.remote_verified=false no comprueban que el registro siga vigente. Cada request lee registro/revocación remoto y verifica su intervalo antes/después; vencido rechaza antes de ejecutar Genie. No ampliar TTL para hacer verde la integración.

Antes de app: operaciones reobserva13GET actuales, reconstruye064 bajo ventana administrativa vigente, verifica32historias originales y emite un nuevo certificado/registro con tiempos reales. La edad2h conserva tiempos SELECT originales; después de agotarla no se inventan recencia ni nuevos tiempos. Una nueva observación produce otro certificado/pin; el registro append-only no se sobrescribe. Publicar primero certificado/registro y política/status correspondientes en volumen propio, comprobar sus hashes, luego actualizar configuración servidor protegida y recargar la instancia con ese pin. Preservar archivos previos y capacidad de rollback, pero nunca tratar una atestación vencida como vigente.

La política trusted_admin del lector necesita ventana vigente y status remoto observado, más permisos SELECT-only/READ_VOLUME/CAN_USE/CAN_RUN reales del principal OAuth. Registro local publicado064 y UI Genie065 no prueban carga remota del registro, grants de app, callback, RAG ni E2E. Esos pasos siguen pendientes hasta evidencia independiente.
