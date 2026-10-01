# Ficha cloud observada — 28 de septiembre de 2026 UTC

SK12 creó `sbs-radar-pilot` mediante un único POST con `no_compute=true`. La URL y la identidad de servicio ya existen; no se desplegó código, ejecutó SQL, enlazó recursos ni modificó permisos. El estado final observado a las01:52:39 UTC fue **STOPPED**, con app **UNAVAILABLE**. Esto no es una aplicación operativa ni una prueba UI.

- App: `a947eccf-5f94-4369-a3d4-8f83b4ea98a1`.
- URL asignada: https://sbs-radar-pilot-7474657121564806.aws.databricksapps.com
- Principal: `77041447522099`; client ID igual al ID de la app.
- ACL observada: usuario creador CAN_MANAGE y grupo admins CAN_MANAGE heredado. No acredita autenticación de usuarios finales ni sus permisos de datos.
- Configuración local derivada de metadata: `deployment/app-cloud-observed-001.json`. No subida ni aplicada.

El primer intento se conserva como `incomplete`: interpretó STARTING como motivo de contención y pidió stop. Una observación posterior mostró preparación de URL, principal y dependencias; el segundo stop también falló400 porque la app aún estaba arrancando. Luego se observó STOPPED. No se atribuye ese estado a los stop fallidos ni se afirma coste cero. El refinamiento de SK12 separa intención, provisioning, estado observado y coste.

Evidencia: `runs/sk12-app-metadata-001-consolidated.json` enlaza y sella cada observación; no reemplaza los intentos históricos. La propuesta cloud002 permanece como snapshot anterior, no aplicada; su afirmación histórica de ausencia de app no describe este nuevo estado. La autorización para activar recursos facturables sigue pendiente de una propuesta concreta y completa.


## Esquema y volumen propios — checkpoint15

SK12 creó el esquema `neptuno_manuel_arguelles.sbs_radar` y el volumen administrado `neptuno_manuel_arguelles.sbs_radar.release_artifacts` tras comprobar ausencia y propiedad del catálogo. Ambos POST devolvieron200 y el readback confirmó los IDs `ff244e9c-7d34-4c2d-8d74-a33292cd5f2c` y `f08b4e85-862d-400e-9ade-b73fe134ea7d`, respectivamente, con el mismo propietario. No se subieron datos ni se crearon tablas, grants o Jobs. No hubo SQL ni inicio de cómputo.

Evidencia: `runs/sk12-uc-metadata-015-result.json` conserva8GET y2POST, sin reintentos. El campo `effective_grants_observed=true` de ese intento solo acredita HTTP200: el filtro no conservó la presencia de campos/paginación. El suplemento `runs/sk12-uc-grants-015-result.json` realizó2GET y confirmó respuestas vacías `{}` sin token de siguiente página. Esto no demuestra una ACL privada ni excluye permisos implícitos de propietario/administradores. Antes de cargar datos, verificar acceso de los principales concretos. Coste observado: desconocido.

`deployment/metadata-proposal-015.json` conserva la propuesta histórica previa, con aplicación automática deshabilitada. La creación acotada se registró aparte en `runs/sk12-uc-metadata-015-invocation.json`; no habilita la propuesta cloud general ni la activación facturable.


## Escritor dedicado — observación016b

El2026-09-28T04:09:25Z se confirmó `sbs-radar-writer`, ID `72803555975940`, applicationId `33b6f37c-7e6a-489f-b313-f886418b0319`, activo. GET prefijo vacío→POST201→GET exacto200; dosGET/unPOST. Resultado y revisión independiente: `runs/sk12-writer-create-016b-result.json`, `runs/sk09-writer-create-016b-post-review.json`. El400 previo se conserva; su causa exacta no está acreditada.

Solo metadata de identidad: no se asignó workspace, no se crearon secretos ni se modificaron roles/grants, SQL o compute. Pertenencia al workspace y privilegios efectivos siguen sin verificar. Binding público en `deployment/writer-observed-016.json`; no prueba de disponibilidad operacional.
