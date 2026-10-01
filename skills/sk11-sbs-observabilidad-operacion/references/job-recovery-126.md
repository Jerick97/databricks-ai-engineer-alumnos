# Recuperación126 — un create nuevo, provisional SK11/SK12/SK08

skill-creator-z aplicada con diagnóstico local, casos RED/GREEN y revisión independiente root. Autonomía053 sigue vigente; la revisión scoped126 es interna, no una nueva solicitud de autorización humana. Constructor no llama nube.

## Diagnóstico observado y límites

Intent118 original permanece UNKNOWN. SHA3e45f27624e368b4d45309a09d30183bfc8eb22937c0eed9bc45c482ff29dfcc. La serialización real SDK0.102.0 produce cuerpo exactamente idéntico y POST/api/2.2/jobs/create; no reproduce error predispatch. El contador original75HTTP/10mutaciones/7SQL prueba reserva, no envío: reserva precede authenticate/session.request. No existe evidencia recuperada del status/error de ese POST.

GET124 observó lista{} sinJob; no prueba por sí solo que el intento anterior nunca pueda completar.017 observó manager directo, no User directo; herencia no inventariada.128 no observó rulesetfresh: Config falló escribiendo cache antes de GET. No atribuir el fallo118 a roles sin errorHTTP. Ruta reutilizada: GET/api/2.0/preview/accounts/access-control/rule-sets con name=accounts/d07dc225-12fb-4805-91a2-735f02373714/servicePrincipals/33b6f37c-7e6a-489f-b313-f886418b0319/ruleSets/default, etag vacío.

## Ejecutor concreto y alcance

job_recovery_126.py usa SDK JobsAPI.create con payload original cerrado y hash exacto. IdentityGET fija workspace/owneruserID/SPactivo; rulesetfresh se registra separando User directo y herencia no establecida. Ausencia de User directo no se convierte en causa ni se concede ningún rol; el create autorizado permite que Jobs aplique su validación efectiva. Reviewer puede inspeccionar ese dato y corregir roles aparte antes de admitir126.

FreshGET list nombreexacto, sin paginación. Si hay1Job compatible, GETlo fija y no hayPOST. Si hay2+, registrar IDs como candidatos, no ejecutar ninguno ni borrar. Si hay0 y ningún intent126 previo: emitir un único POST nuevo PAUSED bajo nueva admisión explícita126. No es retry automático del intent118; no lo borra ni reetiqueta. GETposterior confirma ID/settings, incluso ante respuestaHTTPambigua o JSONinválido. ACL se registra sólo como observación estructural; aprobación de owner/trustedwriters pertenece a130/run.

Ledger126 separado máximo24HTTP/1POSTcreate, durable, lockhost, no retries/redirects, timeout(10,60), respuesta<=1MiB. HTTPstatus y requestIDs allowlist se persisten antes de leer/parsear cuerpo o SDK. Luego tamaño/hash y, siHTTPerror, sólo error_code<=100 y message<=1000 con redacción de token/secret/password; no rawbody ni credenciales. IDs de error/transporte no se convierten en Jobbinding. La ausencia de session.request antes de authfallida puede acreditarse sólo para el nuevo intento instrumentado, nunca retroactivamente118.

POST126 tiene intentnuevo que referencia SHAintent118/payload. Reanudación sólo GET/reconciliación; contador1 impide reenviar. ReceiptHTTP126 se conserva incluso al reanudar. Resultado enlaza JobID observado, response126 e intentviejo, conservando original_attempt_outcome=unknown. NuevoJob existente no acredita éxito del intento118.

No tocar budget/journal106, SP/roles/ACL, config, política, notebook, warehouse/start, SQL, Jobrun ni unpause. Contabilidad final propuesta:12mutaciones originales máximas +1create126 separado=13, sin refund/reset. Antes de completar2writes originales restantes debe existir etapa130 nueva.

## Uso

Preflightoffline:

PYTHONPATH=src .venv/bin/python -m sbs.operations.job_recovery_126

Tras revisiónroot y login realmente válido:

PYTHONPATH=src .venv/bin/python -m sbs.operations.job_recovery_126 --execute --review-file deployment/job-recovery126-authorization.json --journal deployment/state/job-recovery126

Template126 aprobadofalse y tiemposnull; no ventana emitida por constructor. Journal original prohibido. Driver y26módulosSBS realmente importados se fijan en review_inputs; SDK0.102 comprobado. Freeze incluye closure efectivo, pruebas y diagnósticos.

## Dependencia130 sin política emitida

policy_settings_unchanged() demuestra que dos hashes de política distintos producen el mismo settings payload exacto original: boundary_policy_id no se serializa en Jobs settings. Son hashes sintéticos para assertion, no políticas activas ni IDs cloud. Política106 expirada queda histórica. Después de JobGET y login válido,130 deberá crear documento/version nuevos, DriverConfig externo nuevo y notebookpin nuevo con timestamps reales emitidos entonces. No retimestamp policy.json, no subir config vencido ni gastar2writes restantes inútilmente. Un Jobupdate puede evitarse sólo si igualdad de settings sigue demostrada.

## Evidencia local

Cinco tests PASS: igualdad del SDKbody, independencia settings/policyhash, rechazoHTTP403 conservado y sin resend, JSONinválidoHTTP200 con GETbinding posterior, duplicados sinPOST/run. FixturesHTTP explícitos y SDK real, originaljournal byte-idéntico antes/después. No prueban authcloud, causa118, Jobreal, permisos aprobados, runtime, GenieTTL5min ni E2E. No se amplía130 antes de entregar126.
