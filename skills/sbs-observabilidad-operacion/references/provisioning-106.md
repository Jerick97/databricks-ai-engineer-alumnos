# Provisioning106: ejecutor concreto, revisión y operación

Complementa105 sin modificar su freeze. SK11/SK12 y skill-creator-z exacta, estado provisional. Constructor implementó código local; coordinador evalúa independiente antes de remoto. Ninguna ejecución cloud se atribuye a estas pruebas.

## Funcionalidad y entradas

`src/sbs/operations/provision_106.py` contiene CLI preflight/execute, adaptador HTTP acotado para serializadores SDK0.102.0, validadores específicos y callbacks concretos. No hace falta escribir callbacks para usarlo. SDK import real y tests de serializers constituyen investigación acotada del contrato instalado; no prueban wire remoto ni habilitación serverless. Fuentes: contratos SK11 cloud-driver/shared-control, selector SK12 existente y documentación en docstrings oficiales SDK0.102.0 instalada. Reusa step_once105, atomic/exclusive_lock, job_settings y DriverConfig. No cambia SP ni credenciales, data tables ni modelos.

Pins: workspace dbc-0410b264-20c7.cloud.databricks.com; operador sociosdosmilveintiseis@gmail.com/userID76826984571984 activo; SP72803555975940/applicationId33b6f37c-7e6a-489f-b313-f886418b0319 activo. Warehouse828756322bedff37 debe estar RUNNING; Volume existente release_artifacts. Sólo crea refresh_control dedicada y Job sbs-radar-single-writer PAUSED. Directorios/artifacts bajo sbs-refresh/bootstrap106/<archiveSHA> y notebook /Shared/sbs-radar/writer106-<archiveSHA16>. No adapta host/owner silenciosamente.

## Secuencia y límites

1. Validar revisión independiente exacta (review_inputs), approved=true, scope=provision106, modo y límites idénticos, ventana actual <=30min. Verificar versiones/hash antes de autenticar. Auth normal de SDK, nunca secretos en archivos. Autenticación puede renovar OAuth internamente; cuota de120 workspaceHTTP no pretende contar tráfico interno del proveedor auth.
2. GET operador, SP, warehouse, Volume; GET tabla ausente. CREATE exacto una vez, GET identidad UC/owner/schema/Serializable/filtros. Registrar table_id exclusivamente de GET validado.
3. SELECT completa límite2; cero filas se admite con zero-chunk/result ausente o chunk0 vacío, esquema exacto/truncated=false. INSERT initial_state exacto una vez y SELECT singleton revisión0. SQL fuera de CREATE/INSERT exactos o SELECT exacta se rechaza. No DROP/ALTER/DELETE/MERGE ni datos preexistentes.
4. Añadir SELECT+MODIFY al SP exclusivamente sobre tabla nueva, readback Grants GET. Directorio Volume con HEAD/readback; subir bundle inmutable overwrite=false y descargar/hash. Directorio workspace GET y mkdirs sólo si falta. Importar notebook bootstrap preflight, GET status+export SOURCE. Añadir CAN_READ SP; bloquear escritores ajenos a owner/admins y SP con CAN_EDIT/CAN_MANAGE.
5. job_settings reutilizado sin job_id ficticio; create con ACL owner IS_OWNER y SP CAN_MANAGE_RUN. GET lista exacta sin paginación y GET Job fijan ID/settings/run_as. ACL readback rechaza actores no confiables con permisos de escritura/ejecución; admins permanece supuesto explícito.
6. Config final DriverConfig con IDs observados/ACL completa/policy persistida fuera del snapshot, upload por SHA+readback. Notebook final fija bundleSHA/manifiesto/configSHA y copia/descomprime bajo tmp con paths/tipos/tamaños/hash closure validados; lee configuración de Volume directamente, sin depender de SBS_* en serverless. Import final sólo sustituye bytes bootstrap conocidos o transición preflight→execute revisada; GET export valida bytes normalizados de final.
7. GET final Job+ACL y singleton; guardar resultado y DriverConfig. No run-now, start, unpause ni deploy. Config y notebook ya contienen ruta ejecutable; servidor debe permitir la lectura efectiva de Volume/notebook por SP antes del primer run.

Cuotas **acumulativas del journal**, sin reset por reanudación:120HTTP,12SQL,12mutaciones. Cada request reserva durable antes de auth/envío; timeout(10,60), sin retries/redirects, respuesta y upload<=32MiB. Transporte permite una sola escritura con cuerpo/path/dataSHA esperado, además de allowlist de operación/namespace. Política y payloads se preservan al renovar sólo ventana de revisión. Cada intento tiene intención fsync; resultado incierto habilita readback, nunca reenvío. Preservar journal en mismo host controlado (POSIX, no Volumes); no borrar/editar ni cambiar root para reintentar. Lock exterior único serializa presupuesto y fases.

## Uso

Preflight (default; no SDK config/auth/network/writes):

```bash
PYTHONPATH=src .venv/bin/python -m sbs.operations.provision_106
```

El coordinador revisa `runs/sk11-provision-106-freeze.json`, ejecuta sus pruebas y genera **su** capacidad temporal a partir de `deployment/provision106-review-template.json`; el constructor entrega approved=false y tiemposnull, nunca concede aprobación. `files` debe coincidir exactamente con review_inputs(root). Con autorización revisada existente:

```bash
PYTHONPATH=src .venv/bin/python -m sbs.operations.provision_106 --execute --review-file deployment/provision106-authorization.json --journal deployment/state/provision106 --writer-mode execute
```

Omitir --writer-mode conserva preflight en notebook. `--execute` aprovisiona; `--writer-mode execute` sólo prepara notebook para que un run futuro explícito ejecute el writer. El Job continúa PAUSED. Se puede pasar preflight→execute bajo nueva revisión y mismo journal dentro del presupuesto, verificando bytes anteriores; no hay downgrade silencioso. On-demand posterior se realiza por CloudDispatcher/SharedLedger del **mismo Job**, no Jobs fixture ni run-now suelto sin ledger.

## Evidencia y límites

105 conserva prueba real sealed de6PDF/hooks/source/archive/tmp y782hashes.106 añade fixture HTTP en memoria con **serializadores SDK reales**, incluyendo create/readbacks/bootstrap/config/final; retoma con otra ventana sin nuevas escrituras y preserva policy/settings/config; transición explícita preflight→execute aún PAUSED. Notebook generado ejecutado localmente en preflight sobre archivo portable real y config **fixture**, sin inferencia. Estos datos no son observaciones del workspace.

Tests adversos: host incorrecto, SQL fuera de alcance incluso con permit, SELECT vacío variantezerochunk, schema/seed inválidos, y los8tests de durabilidad105. Resultado congelado en green106. El flujo fixture de tres pasadas consumió110HTTP/12mutaciones/10SQL simuladas; no es estimación de latencia ni costo cloud.

Primer run real, permisos efectivos USE CATALOG/SCHEMA/CAN_USE warehouse/READ+WRITE Volume, disponibilidad serverless, publicación/readback/fallo/recuperación y aceptación independiente siguen pendientes. No conceder ACL broad para superar esos gates. Política administrativa writer expira con ventana inicial: revisión renovada conserva payload/policy pero **no extiende** su vigencia; necesita renovación operativa posterior de config/notebook antes de que el Job pueda seguir escribiendo. No habilitar diario como disponible hasta resolverlo. Este componente prepara sealed bootstrap; no prueba frescura web ni captura regulatoria diaria completa.

Diario objetivo08:00America/Lima + on-demand usan mismo Job; activar únicamente después de primer run validado y renovación operativa. Genie tiene certificado independiente TTL5min: job diario no proporciona disponibilidad continua ni renovación de ese certificado. Recuperación/rollback de publicaciones conservan CAS/fence e históricos; este provisioning no ofrece DROP/reseed/reset como rollback.
