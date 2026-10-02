# SK08/SK10 — host detrás del proxy Apps197

Estado: provisional; variante local con HTTP tests, pendiente revisión independiente y validación cloud. Creator Z aplicado al fallo real194: app RUNNING/deployment SUCCEEDED, pero navegador recibió `Host no autorizado.` antes de cualquier api/ask. No se capturó el valor bruto del Host interno: su discordancia es inferencia de la rama que emitió403.

## Brief reutilizable y fuentes

Consulta2026-09-29, documentación oficial AWS actualizada2026-09-11:
- https://docs.databricks.com/aws/en/dev-tools/databricks-apps/http-headers documenta X-Forwarded-Host como host original enviado por el proxy Apps.
- https://docs.databricks.com/aws/en/dev-tools/databricks-apps/networking describe autenticación OAuth inicial y rutas hacia compute serverless.

Decisión: usar el contrato documentado sólo cuando el despliegue habilita explícitamente `SBS_TRUSTED_PROXY=databricks_apps`. No habilitar confianza global de Uvicorn ni deducir proxy del nombre de una cabecera. El aislamiento de ingreso detrás de Apps es supuesto de despliegue, no propiedad demostrada por TestClient. OAuth de ingreso no sustituye autenticación delegada SK08.

## Variante y riesgos

Overlay de tres archivos basado exactamente en el source191 ya desplegado, no en src actual ni modificación del snapshot133. `runs/sk10-proxy-host-197-overlay/manifest.json` fija inputs y outputs. No lleva nueva autorización, deadline ni RAG/modelo/configuración de cuotas. El empaquetador posterior deberá actualizar el manifiesto de archivos lógicos de chunks163 para los archivos modificados y revisar el paquete completo; este overlay no es un paquete desplegable autónomo.

`create_app(..., trusted_proxy=None)` conserva defaults local/direct cloud. Única alternativa admitida `databricks_apps`, exclusivamente cloud. Ese modo exige una sola cabecera X-Forwarded-Host exactamente igual a `public_origin.hostname`; ninguna lista, duplicación, puerto, espacio, userinfo, wildcard, esquema o normalización. No recurre a Host cuando falta o falla la cabecera. app133 pasa la configuración de entorno y app.yaml hace opt-in explícito.

Host válido permite continuar al autenticador existente, que verifica token con current-user y política por ID. Nombres de usuario/email/roles de cabeceras nunca autorizan. Cookie Secure, sujeto, CSRF y Origin se conservan.

## Matriz y evaluación

- Regresión403 con host interno y forwarded exacto: baseline403; overlay200 con identidad sintética validada por adaptador real.
- Host faltante, repetido, lista, esquema/userinfo/puerto/sufijo/espacios/control:403 antes de consultar identidad.
- Host exacto con nombres falsificados o token no permitido:401; no vista de actor.
- Direct/local por defecto: siguen validando Host e ignoran forwarded-host.
- CSRF ausente, Origin ajeno y token anterior después de cambio de sujeto:403; solicitud correcta continúa al servicio sintético.
- Pins: tres inputs originales intactos, tres outputs exactos, única env añadida y única opción app133.

Seis tests pasan en `runs/sk10-proxy-host-197-tests.txt`. Pruebas HTTP locales no acreditan SSO, headers reales, ingreso, UI funcional ni chat cloud. Revisor distinto del constructor debe fijar freeze antes de empaquetar/desplegar. Numeric188 FAIL y final153 bloqueado permanecen.
