# trusted_admin_observed_v1 — perfil explícito del piloto

Revisión de alcance: `runs/sk09-governance-scope-review.md/json`. No cambia silenciosamente `strict_interval_v1`. El piloto puede confiar operativamente en administradores identificados; no necesita epochs, leases, fencing ni prueba contra administradores adversarios. Ese supuesto no convierte un GET actual en prueba histórica.

## API consumible por la factory del servidor

Todos los constructores siguientes son locales y no llaman al SDK. Autenticación e inyección de WorkspaceClient son exclusivamente del servidor, nunca de campos de solicitud:

```python
resolver = ScimReaderResolver(
    identity_get=workspace.service_principals.get,
    group_get=workspace.groups.get,
    kind="service_principal",  # o users.get con kind="user"
)
collector = UcAccessCollector(
    table_get=workspace.tables.get,
    catalog_get=workspace.catalogs.get,
    schema_get=workspace.schemas.get,
    effective_grants_get=workspace.grants.get_effective,
    warehouse_permissions_get=workspace.warehouses.get_permissions,
    subject_resolver=resolver,
)
policy = TrustedAdminPolicy(
    policy_id=server_policy_id,
    namespace=server_table_prefix,
    trusted_administrators=tuple(server_administrators),
    maintenance_assumption=server_maintenance_declaration,
    abac_assumption=server_abac_declaration,
    issued_at_ms=server_policy_issued_at_ms,
    expires_at_ms=server_policy_expires_at_ms,
    observation_ttl_ms=server_observation_ttl_ms,
    status_lookup=server_policy_status_lookup,  # policy_id -> active o revoked
)
capability = DeltaPublication(
    certificate=server_certificate,
    certificate_sha256=server_certificate_pin,
    mapping_sha256=server_mapping_pin,
    registry_lookup=server_registry_lookup,
    identity_access_probe=TrustedAdminObservedProbe(collector, policy),
    assurance_profile="trusted_admin_observed_v1",
)
# Usar ServerDependencies(..., delta_publication=capability) y load_runtime_binding.
```

La declaración ABAC debe describir la ausencia de políticas aplicables asumida por los administradores y su alcance. No es un descubrimiento del colector. La declaración de mantenimiento describe coordinación prospectiva en el namespace propio. policy/status provienen de configuración/estado protegidos del servidor; no de un bool aportado por cliente. Su TTL es una política de frescura y servicio, no disponibilidad histórica garantizada.

La factory de aplicación y el archivo separado de configuración son responsabilidad del coordinador. No cambiar `genie-pilot-002.json` ni tomar credenciales de una request. IDs/certificado/política faltantes deben mantener unavailable sin SDK.

## Qué observa el colector

SCIM consulta el recurso completo sin selección de atributos, comprueba ID/activo y resuelve nombres exactos de cada grupo reportado (incluidos indirectos reportados), con tope. `membership_complete` significa **cierre de esa respuesta completa y sus referencias**, no inventario de todos los grupos/roles de cuenta. Se conservan `membership_scope=full_scim_resource_reported_groups` y `role_visibility=roles_not_reported` si el recurso no devolvió roles. Roles administrativos reportados, grupo admins o lector propietario bloquean. No se infiere `users` a partir de `account users` ni de clones. Falta de datos necesarios/resolución rechaza; datos denegados y no disponibles tienen errores seguros distintos.

UC observa tipo Delta gestionado, nombre, UUID UC, metastore, ubicación y owner. Comprueba propietarios de tabla/catálogo/schema frente a los sujetos reportados. Rechaza filtros de fila/máscaras de tabla visibles; no enumera ni acredita ausencia de ABAC. Grants efectivos paginados hasta cierre capturan herencia relevante para los nombres realmente resueltos. Deben acreditar USE_CATALOG, USE_SCHEMA y SELECT; el perfil permite privilegios de lectura/metadatos pertinentes y rechaza escrituras, creación, MANAGE, ALL_PRIVILEGES y desconocidos. El warehouse debe observar CAN_USE para un sujeto real; privilegios administrativos relevantes rechazan. Grants ajenos al sujeto no se convierten en sus permisos.

`TablesAPI.get` no se interpreta como GET del UUID Delta, de versión N o del esquema histórico. El certificado/registry aportan esos hechos de publicación; la salida los etiqueta `publication_table_bindings`. El esquema actual solo es observación actual. GET de tabla exitoso no prueba SELECT ni read-only del lector.

## Pre/post, integración y límites

`RuntimeBinding` crea `capability.for_request()` para cada llamada: sesión local aislada, no lease distribuida. Captura antes de Genie y después de Query History; exige que tiempos observados encuadren la ejecución y que las observaciones relevantes coincidan. Detecta deriva en identidad, permisos, políticas visibles o metadatos y falla cerrado; no afirma qué ocurrió entre capturas. El TTL limita edad de la observación de membresías, duración de captura y distancia pre/post. Expiración y revocación de política se comprueban antes/después de capturar. Revocación/TTL del registry de publicación permanece aparte.

Las diferencias de metadatos actuales, incluso cambios legítimos concurrentes, pueden causar rechazo conservador; no se reintenta ni se sustituye por latest. Este perfil conserva los checks de historia real, entero de versión, AST contextual exacto, resultados esperados, certificado real/mapa y snapshots originales. El preflight de Genie sigue exigiendo permisos/warehouse de su contrato existente.

La salida incluye `assurance_profile`, `assurance.observation`, `assurance.assumptions`, visibilidad de políticas y límites. Siempre `identity_continuity=not_proven`, `aba_prevented=false`. No emite los booleanos de continuidad DDL/retención del perfil estricto ni un intervalo GET ficticio. El perfil estricto continúa exigiendo su evidencia original. La lectura exitosa de N acredita disponibilidad en esa ejecución; error/VACUUM no se oculta como resultado vacío.

Estado: pruebas de fixtures y contratos locales; ninguna llamada remota, permiso, recurso o inferencia en esta construcción. La evidencia SK08 existente muestra schema aún ausente y nombres de grupo que no se deben homologar: no acredita readiness. Antes de producción se requiere revisión SK09 y ensayo cloud autorizado; no se agrega aprobación institucional por consulta.


## Serialización SDK (0.1.10)

`EffectivePermissionsList.as_dict()` y `ServicePrincipal/User.as_dict()` omiten listas vacías. Se preservan sus campos tipados privilege_assignments/groups; los diccionarios raw sin campo requerido continúan rechazándose. Una página SDK vacía no acredita permisos: solo habilita continuar paginación, y los grants necesarios deben observarse en otras páginas. Un recurso SDK con grupos vacíos permite validar permisos directos. roles vacíos omitidos mantienen la etiqueta roles_not_reported.

Límite explícito: el SDK `from_dict` también puede convertir campo ausente en wire a lista vacía. Después de deserializar no es posible recuperar esa distinción; este perfil acepta la semántica tipada del recurso completo del proveedor, no certifica presencia wire. La procedencia/autorización del llamante sigue siendo una brecha a probar como app, descrita en `runs/sk06-reader-api-visibility.md`. No convertir un SDK object en prueba de visibilidad administrativa completa.
