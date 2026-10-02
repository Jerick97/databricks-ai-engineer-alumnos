# Experimental199 — overlay197 y continuidad de reservas192

SK12 0.1.16 provisional, preparado mediante Creator Z. Reutiliza decisión190, Linux runtime185, numeric188 FAIL, revisiones191/194 y revisión independiente197. No promoción153. Construcción199 offline, sin autenticación, deadline operacional, materialización persistente ni cloud.

## Fuente y ventana

Aplicar tres archivos del overlay197 revisado sobre234 archivos191; cambiar deadline de configuración solamente al ejecutar y actualizar cuatro hashes lógicos en chunks163. Total cinco archivos físicos cambian: app.yaml, app133.py, webapp/__init__.py, config/app-integration-133.json y chunks163-manifest.json. Pesos/modelos, recuperación, cuotas4generation/2embedding/20000tokens y1worker permanecen. El gate ready199 compara todos los234 hashes con esa transformación exacta, verifica manifest/sourcehash y payload; no usa un bypass del gate final153.

`execute` exige revisión199, autenticación por proveedor normal e identidad del operador antes de emitir30min. `materialize` es helper interno probado en directorio temporal; CLI no expone materialize independiente. La revisión199 cubre la transformación determinista y los inputs fijados; el manifest exacto resultante queda durable antes de upload. Un paquete existente bloquea ejecución; no reanudar con estado virgen ni sustituirdeadline.

## Despliegue y parada

Reutiliza transporte191 con nuevos directorios199 y prefix experiment199-sourcehash. Límites adicionales:234upload,50mkdir,1start,1deploy,1600HTTP. Totales anteriores191+194 se fijan en234upload,42mkdir,2start,2deploy,904HTTP; resultado199 suma ambos sin reset. Identity/cleanup conservan sus transportes limitados separados y no entran en contador SDK. El nuevo ensayo no declara renovación de autorización original191: es ejecución experimental nueva dentro del alcance autónomo confirmado por coordinador.

Antes de start: App existente/identidad/fuente previa exactas, STOPPED observado nuevamente; anterior STOPPED por UI es evidencia histórica, no sustituto de GET nuevo. Tras start, adopta únicamente autorestore del mismo source, owner y ventana de creación. Reutiliza corrección194: pendingnull no basta; active.status y get_deployment fresco deben estar terminales explícitos, con id/source/owner/create_time ligados. Una sola POSTdeploy; reconciliaciónGET sin reintento ante ambigüedad.

`supervised_execute(root, cfg=cfg)` o config_factory retiene exactamente el mismo Config/proveedor hasta deadline y cleanup. No recrea perfil ni credenciales; OAuth200 es dependencia inyectada, no parte del código199. Fallo después del start limpia recurso conocido. Supervisor se mantiene vivo y observa `demo-ledger/ui-failed.json` cada5s. Operador que observe UI incorrecta ejecuta `--ui-failed`; no continuar preguntas. `--stop` acepta cfg en Python; para proveedor en memoria usar supervisor ya vivo. Reiniciar CLI no preserva ese proveedor.

## Reservas192, sin devolución ni nuevas asignaciones

Root informó explícitamente: cuatrointents192 fueron reservas locales, nunca clickConsultar ni POST/apiask; sólo UIHost403. No se presenta como monitoreo universal de usuarios. Revisión199 debe incluir `operator_attests_no_192_actions_sent:true`, además de status PASS_EXPERIMENTAL_199 y freeze_sha256.

Preservar ledger192 completo. Copiar cuatrointents a history192 y migrarlos al binding199 con hashes de origen, mismos turnids/actionhash/costs. Turn0/1/2 reservan0, turn3 conserva1generation+1embedding+20000tokens. Suma sigue1/1/20000; no refund y ningún aumento. Binding199 conserva techcaps4/2/20000; no autoriza nuevas acciones por capacidad aparentemente restante.

`--claim turnN --observation FILE` consume una sola vez el derecho transferido a enviar esa acción visible: observación<=120s, mismo deployment/source y ventana vigente. No reserva otra cuota, no admite turn4, no resetea intents ni reenvía ante incertidumbre. `--receipt turnN [--trace FILE]` reutiliza170 manteniendo reservas y contabilizando desconocidos sin deducir consumo de HTTP200. No es cuota global del servidor; epoch sigue desconocido. `--ui-failed` bloquea posterioresclaims y pide parada.

## Evidencia local y límites

Seis tests199 pasan: transformación234/fivechanged/deadline y rechazo de drift, preflight sin autenticar ni estado, migración de cuatro identidades sin modificar originales, claims únicos, autenticación fallida sin ventana, cfg compartido hasta parada, terminal gate194 antesdeploy y cleanup ante fallo. Reutilizan HTTPtests197 paraHost y tests194 para pendingnull+IN_PROGRESS. Doble de servicio/HTTP no acredita proxy real, SSO, proveedores, UI ni finalrelease. Root revisa código/freeze antes de autenticación/ejecución.

Pruebas: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m unittest tests.unit.test_experimental_199 -v`. Evitar bytecode dentro de source congelado al cargar módulos históricos.
