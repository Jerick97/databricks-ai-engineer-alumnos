# Bootstrap098 — activación servidor de rotación078

Variante opt-in SK06 0.1.17 / SK07 0.1.17 / SK12 0.1.16 creada mediante CreatorZ exacto. Activar para conectar el runtime base con el lector078; no para publicar, refrescar SQL o promover la app. Mantener SKILL.md y todos los componentes congelados anteriores intactos; esta referencia se invoca explícitamente.

Reutilizar el plan integration-next-plan y loader078 revisado. App098 es una nueva entrada, sin modificar App080/default. La variable de servidor SBS_GENIE_ROTATION_CONFIG acepta sólo config/genie-bootstrap-098.json; ausente conserva create_server_service080. Nunca aceptar rutas, clientes ni capabilities desde HTTP. El schema Question continúa extra=forbid. La allowlist de selección de generación080 permanece073/077; GPTOSS094 no está promovido.

Validar configuración cerrada y pins antes de crear SDK. Exigir modo cloud, runtime base135, mappingSHA275b921a065e66c2f7ffa75ef9b5ffc2b1eb1410ca4445246b2aa67e26296580 y Genie164filas8tablas. Los snapshots distintos se relacionan por pruebas de fuentes; no igualarlos. Rechazar perfiles structural231, releases y cloud_refresh activo porque cambiarían el snapshot sin soporte Genie revisado. Mantener initialize_genie original y sus guards; inyectar únicamente el binding verificado.

Usar loader078 con Config oauth-m2m del App reader, client_id y executor fijos distintos del publicador. Nunca leer/copiar credenciales operadoras ni importar publicador081/conector081. Separación por identidad local no demuestra grants efectivos: callbacks078 verifican SCIM/permisos/registro al consultar, y M2M real sigue pendiente. No arrancar warehouse desde App.

Copiar el certificado histórico únicamente como ancla estática de identidad a config/genie-bootstrap-certificate-098.json, bytes/hash idénticos; server-template098 cambia sólo su ruta. Config rotation098 cambia sólo ruta/hash de template. No copiar admisiones/journals o simular frescura: current.json y generación remota protegida son necesarios en cada consulta y conservan TTL/revocación. Ningún timestamp se renueva durante bootstrap.

La solicitud selecciona una generación078 coherente y conserva sus callbacks durante toda ejecución; rotar pointer afecta la próxima solicitud, revocar snapshot o expirar evidencia deniega la actual. readiness declara pendiente remoto, nunca publicación verificada por haber cargado el servicio.

Dependencias: audit098 registra imports Python transitivos y lecturas de bootstrap/catalog, incluyendo SQLite de procedencia que se abre por C y no aparece en Path.open. La primera copia aislada falló CAPTURE_MISSING por ese archivo; conservar RED y agregarlo explícitamente. La copia temporal actual pasa con lectura del árbol original bloqueada, sin SDK/red. No es paquete final: builder existente omite app098.py, que deberá incorporarse al futuro release revisado. Modelos lazy, identidad App real, permisos y consultas/UI E2E siguen fuera de esta prueba; no atribuirles PASS. No modificar builder080 para cerrar este componente.

Evidencia:44tests locales,42/43baselines intermedios conservados donde hubo fallo, pruebas de contexto inválido antes de Files, snapshot/perfiles, M2M shape, contexto de generación080, rotación/revocación/expiry con fixtures078 y entradaApp local real. Default/config/data closure y fuente portátil se revisan aparte de nube. No paquete, despliegue, SQL o inferencia.

## Revisión098-01 — procedencia por llamada de herramienta

El probe independiente confirmó que Conversation retiene trace pero pierde execution_provenance cuando llega como campo hermano. TraceBinding098 conserva una copia exacta de ese dict en trace.execution_provenance y añade snapshot_binding_sha256 y alcance explícito, sin alterar078 ni reparar evidencia. El resultado original también conserva su campo. Guardar así publication_certificate_sha256/publication_registry_sha256 por llamada Genie en last_result y run SK07.

La unidad de consistencia es cada llamada de herramienta, no todo el HTTPcross_family: dos consultas de un agregado pueden seleccionar generaciones distintas del mismo snapshot binding inmutable. Revalidar revocación/expiry por los callbacks078. Test real LocalService.ask cross_family con fixtures explícitas demuestra que ambos pares de hashes diferentes sobreviven, mientras snapshot binding permanece idéntico.45testsPASS; evidencia inicial y freeze archivados. No prueba nube, grants ni autenticación App.
