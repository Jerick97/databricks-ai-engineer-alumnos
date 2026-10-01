# Control durable compartido — SK11 0.1.11

Implementación offline en `sbs.operations.shared_control`. Diseño confirmado por root antes de código. Ningún recurso, SQL o permiso remoto aplicado. Registros `runs/sk11-shared-storage-*`.

## Infraestructura y semántica

Una tabla Delta dedicada, previamente creada y verificada por despliegue, con exactamente una fila: `control_id STRING`, `revision BIGINT`, `state_json STRING`. Fila inicial: control_id=`control`, revision=0, state_json=`canonical(initial_state())`. No ejecutar preseed repetidamente ni insertar con IF NOT EXISTS/MERGE para resolver concurrencia. Este componente no crea, inserta, borra ni cambia propiedades. Namespace/warehouse/identidad siguen siendo valores observados que entrega servidor, no placeholders ni entradas de usuario.

Exigir perfil Serializable observado, identidad fijada y administración que controle insert/delete/DDL. El SELECT lee toda la tabla con límite2 y rechaza cero/varias filas, incluso IDs distintos. La unicidad observada no es restricción UNIQUE frente a administradores; estos son confiables y están fuera del modelo adversarial.

Delta documenta commits atómicos y resolución de conflictos optimista. Serializable impone el orden serial fuerte; el default WriteSerializable es más débil. La implementación exige el primero, no lo configura silenciosamente. [Aislamiento](https://docs.databricks.com/aws/en/optimizations/isolation/isolation-levels), [conflictos](https://docs.databricks.com/aws/en/optimizations/isolation), [ACID](https://docs.databricks.com/aws/en/lakehouse/acid), consultados2026-09-28UTC.

Actualización cerrada:

```sql
UPDATE `catalog`.`schema`.`control_table`
SET revision = revision + 1, state_json = :state
WHERE control_id = :control AND revision = :revision
```

Parámetros SDK `StatementParameterListItem`: state STRING, control STRING, revision BIGINT. Reemplaza un único documento de control; solicitudes y puntero se serializan sobre la misma revisión. No exige transacción entre tablas, PRIMARY KEY enforced ni rename de Volumes.

No se ha comprobado en cloud el manifiesto/affected rows de UPDATE. **No se depende de ese formato para declarar commit.** Antes del UPDATE se añade un recibo de operación determinista al estado propuesto; tras respuesta o error se vuelve a leer. Solo recibo exacto y revisión suficiente confirman commit. UPDATE exitoso sin recibo => Conflict; timeout/error sin recibo o readback fallido => UnknownCommit con operation_id seguro. No reintentar automáticamente. `reconcile(operation_id)` es lectura; ausencia permanece unknown.

## API e integración

```python
control = DeltaControl(statement_execution,
    table=observed_full_name, warehouse_id=authorized_warehouse,
    identity_probe=observed_identity_and_governance,
    expected_table_id=pinned_table_identity)
ledger = SharedLedger(control)
# Inyectar ledger en CloudDispatcher; no modifica su contrato.
writer = SnapshotWriter(control, job_id=pinned_job_id,
    writer_guard=independent_current_run_verifier,
    artifact_validator=immutable_artifact_closure_verifier,
    artifact_prefix=validated_volume_prefix)
fence = writer.claim(observed_run_id)
publication = writer.publish(observed_run_id, fence,
    previous=observed_previous_release_id,
    release_id=validated_new_release_id, artifacts=absolute_volume_path_to_sha256)
```

`identity_probe` obtiene identidad/formato/isolation y evidencia de administración reales; copiar campos esperados no sirve. `writer_guard` debe confirmar el Job/run autorizado actual; un token del cliente no autentica al escritor. El run debe estar registrado en ledger. `claim` aumenta fence; publish rechaza fence antiguo y previous distinto antes de mutar. Una publicación repetida idéntica devuelve el recibo anterior. El cambio de puntero y su recibo se confirman en el mismo CAS.

`artifact_validator` comprueba existencia, inmutabilidad, hashes y cierre completo antes del cambio de puntero. Este módulo no implementa upload ni almacenamiento de artefactos. Cualquier fallo deja el release previo. `current()` entrega copia del puntero observado; no significa que runtime/cloud hayan consumido el release.

App lectora: exponer solamente lectura mediante un backend con SELECT y sin acceso a credenciales MODIFY. Dispatcher y writer son capacidades de servidor separadas; no exponer `DeltaControl.cas` a solicitudes. Como requests y pointer comparten state_json, MODIFY sobre la tabla **no impone ACL por campo JSON**: el dispatcher escritor debe ser servicio backend confiable, no el principal lector de la app. Una separación adversarial más fuerte entre dispatcher/writer requeriría otra frontera de servicio/datos; no se finge con clases Python.

`SharedLedger.get/reserve/update` usa el mismo CAS. Reserva persistente precede a run_now; conflictos se devuelven al caller, sin POST oculto. Si la reserva se confirmó pero el proceso murió antes del POST, el registro queda submission_unknown y exige conciliación; no se inventa run_id. No hay retry automático ni exactamente-una-vez de toda la cadena cloud.

## Límites y pruebas

Defaults: state_json1,000,000 bytes, requests100, receipts1,000, SQL statements100 por instancia, polls2 por statement. Los límites de fila/bytes/estado se comprueban; al llenarse no se borran recibos ni solicitudes. Se necesita política de archivo/migración antes de operación prolongada. La fila única es deliberadamente de escala piloto y puede crear contención; no se presenta como arquitectura de alto volumen.

StatementExecution SDK0.102 inyectado; flags INLINE/JSON_ARRAY, parámetros tipados, wait_timeout10s y lectura finita. El integrador debe fijar timeout HTTP y desactivar retries POST del SDK, además de verificar warehouse activo y autorización antes de operaciones reales. El módulo no arranca warehouse por API explícita, pero ejecutar StatementExecution en cloud puede usar/activar compute: aquí no se ejecutó.

11 tests de shared_control y21dispatcher pasan localmente: reserva, conflicto, otro cliente, timeout antes/después, recibo recuperable desde nueva instancia, UPDATE sin cambios, duplicados, límites, stale fence y validación de artefactos fallida. Dobles no acreditan concurrencia Delta real. Pendientes: preseed/identidad/ACL/grants, probes concretos, artifact store, notebook writer, ensayo autorizado de carreras/errores SDK/recuperación y revisión SK09. Coste null.


Refinamiento SK09 S01–S04: schema SDK LONG admitido (BIGINT permanece tipo SQL), continuaciones y chunks contradictorios rechazados, run/fence int exactos, recibos cerrados con SHA64 y revisión positiva no futura. Evidencia preservada y resolución: runs/sk11-shared-storage-resolution.json. El recibo de publicación ahora incluye manifest_path/manifest_sha256 bajo prefix servidor fijado; recovered exige readback del cierre, Job/run/receipt verificados. Ver cloud-writer.md. La suite combinada actual pasó 60 pruebas; artifact store y coordinador offline implementados, pendientes bindings/notebook y nube real.
