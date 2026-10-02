# SK11 coordinación de despacho cloud — diseño implementado parcialmente

Consultado 2026-09-28 UTC. Componente `sbs.operations.cloud_dispatch`; ninguna llamada remota realizada. [Invocación](../../../sbs-radar-workspace/runs/sk11-cloud-dispatch-invocation.json).

## Frontera concreta

Un Job escritor fijado por ID, `max_concurrent_runs=1`, `queue.enabled=true`, principal de servicio run-as exclusivo. El Job comparte el mismo camino de escritura para diario y bajo demanda. La concurrencia y la cola operan a nivel de Job: no protegen otro Job ni otro principal. La cola puede retener ejecuciones hasta 48 horas; no implica frescura inmediata. [Configuración oficial](https://docs.databricks.com/aws/en/jobs/configure-job).

`WriterConfig` exige job ID, application ID del escritor, cluster existente autorizado, notebook workspace entregado, release SHA, ID del backend snapshot y política de frontera. Ninguno está inventado en el código: se rechaza configuración vacía/placeholder. `job_settings(config)` produce settings compatibles con Jobs, inicialmente PAUSED, cron `0 0 8 * * ?`, America/Lima, timeout Job900/task600 y retries0. No aplica settings ni crea Job. Cambiar `schedule_enabled=True` solo prepara/verifica UNPAUSED tras autorización externa; no lo activa.

El notebook de recuperación existente no es el escritor cloud. La ruta configurada deberá corresponder a un notebook entregado y verificado que consuma `request_id`, `release_id`, `job_id`, `run_id`, `snapshot_backend_id`. Ese notebook y backend cloud son dependencias pendientes. No pasar rutas arbitrarias desde una solicitud de usuario.

Diario: scheduler nativo del mismo Job, con parámetros `request_id={{job.run_id}}` y release fijado. `observe_daily(run_id)` requiere GET de ese Job/run y trigger PERIODIC, registra run real y compara valores efectivos de parámetros. No sintetiza runs ni deduplica calendarios externos. Un colector autorizado deberá suministrar IDs del scheduler; no se implementa descubrimiento/polling global.

Bajo demanda: aplicación autentica/autoriza una clave estable del evento y llama `request(id)`. El token SHA256 depende de Job+clave; la reserva durable detecta reutilización de esa clave con otro release. Payload SDK exacto:

```python
jobs.run_now(job_id=config.job_id,
             idempotency_token=token_sha256,
             job_parameters={"request_id": token_sha256, "release_id": config.release_id},
             queue=QueueSettings(enabled=True))
```

No se usan submit, parámetros de notebook del cliente ni selección parcial de tareas. SDK 0.102.0 observado localmente: `run_now` devuelve Wait con `response.run_id`; no se llama `.result()`. La API documenta idempotency_token de hasta64 caracteres y reutilización del run existente; eliminar ese run cambia la respuesta a error. [Run-now](https://docs.databricks.com/api/jobs/v2/run-now).

## Permisos que faltan observar

`verify()` compara GET job/settings/run-as y ACL exacta con la expectativa servidor. También requiere un `boundary_probe` independiente y del mismo modo fixture/real, enlazado a política, Job, escritor y backend: exclusividad de escritor, control de DDL/ACL, autorización de almacenamiento y backend atómico. Este callback **no debe copiar expectativas**: tiene que demostrar grants efectivos e identidades capaces de escribir, quién puede editar Job/notebook/cluster, quién puede usar el SP en otros Jobs, y protección de código/config. Un administrador privilegiado queda en el modelo de confianza; preflight no elimina carreras de cambios administrativos. [Identidades y permisos Jobs](https://docs.databricks.com/aws/en/jobs/privileges).

Propuesta ACL: dispatcher puede gestionar runs, no editar Job ni escribir datos; escritor tiene solo grants de datos requeridos; custodio de despliegue controla settings/código. Es una propuesta, no permisos observados ni concedidos. `max_concurrent_runs=1` por sí solo nunca cumple boundary_probe. SDK GET disponible en código no prueba acceso remoto.

## Registro durable y snapshot

Implementado `SqliteLedger` con reserva única y actualizaciones transaccionales en disco local servidor; probado con proceso nuevo. **No es almacenamiento cloud compartido ni se admite /Volumes.** El controlador permite inyectar un ledger que ofrezca `get`, `reserve` linearizable con detección de conflictos y `update` transaccional durable. Antes del POST persiste estado `submission_unknown`; caída antes/durante/después del POST no se convierte en éxito. Una nueva instancia no reenvía automáticamente. Recuperar una respuesta perdida requiere conciliación autorizada con el mismo token, no un token nuevo ni borrar ledger. El SDK debe configurarse con límites de timeout/retry; el módulo no agrega bucles de reintento.

Elección para snapshot cloud: un escritor reduce contención, pero no elimina fallos de proceso. Usar artefactos inmutables direccionados por contenido y un backend transaccional para el puntero (preferencia de integración: tabla Delta dedicada de releases/puntero, con compare-and-swap y fencing por Job/run/versión esperada). La transacción publica el puntero únicamente después de validar cierre y hashes; conservar release anterior. El backend debe impedir commits de writers/run obsoletos y probar recuperación/idempotencia; está **pendiente**, no simulado por el dispatcher.

Volumes puede alojar artefactos, pero esta investigación no establece una garantía de rename atómico para publicar el puntero. Sus operaciones de archivos tienen limitaciones respecto a POSIX. No trasladar flock/SQLite/rename local a Volumes por semejanza de ruta. [Archivos en Volumes](https://docs.databricks.com/aws/en/volumes/volume-files).

## Resultado y límites

GET Run valida Job/run/parámetros antes de registrar ciclo/resultado. `TERMINATED/SUCCESS` significa `job_succeeded_publication_unverified`; solo un result_probe independiente con Job/run/release y publicación verificada permite `publication_verified`. Es estado operativo, no E2E o vigencia normativa. Queue/pending/running/failure no son éxito. Coste null.

13 pruebas locales: configuración, cola/concurrencia/run-as/compute/ACL, reserva durable, timeout sin retry, parámetros equivocados, diario y publicación con/sin evidencia. Backend cloud, controlador de permisos, notebook escritor y evaluación distribuida siguen pendientes. El deployment/refresh-job.json anterior no se modificó ni pasa automáticamente este perfil más estricto.


### Revisión DISPATCH-01 (0.1.9)

21 tests locales pasan tras RED de ocho casos adversos. GET Run ahora pide include_resolved_values=True, exige una sola tarea refresh con notebook_task/config compute iguales a los fijados, cero tareas adicionales/libraries/compute alternativo/overrides y parámetros efectivos exactos. Falta/inconsistencia de task metadata no acredita ejecución: registra execution_contract_not_verified conservando estado Jobs, sin llamar result_probe. No se presume campo run_as inexistente en Run del SDK0.102. Settings actuales siguen siendo un preflight; controles históricos de identidad/código dependen de gobernanza. No hubo acceso remoto.
