# Preparación, artefactos y publicación — integración SK11

Estado: componente offline probado; no ejecución cloud. Módulos `volume_artifacts.py` y `cloud_writer.py`, sin modificar RefreshRunner/preparers. Investigación2026-09-28UTC: [Files upload](https://docs.databricks.com/api/files/v2/upload-file) y [download](https://docs.databricks.com/api/files/v2/download-file), contrastada con SDK0.102 local.

FilesAPI admite `/Volumes/catalog/schema/volume/path`; upload recibe bytes y `overwrite=False` devuelve error si existe. Omitir overwrite o usar true sobrescribe: este adaptador fija false. Download devuelve stream de bytes; la recepción se coteja por tamaño y SHA256. Directory creation es idempotente. Esto no acredita permisos ni WORM; administración/writer confiables deben impedir overwrite/delete externos. FilesAPI puede generar costes de transferencia; coste desconocido=null.

## API ejecutable

```python
artifacts = VolumeArtifacts(workspace.files,
    prefix="/Volumes/OBSERVED_CATALOG/sbs_radar/OBSERVED_VOLUME/sbs-refresh")
writer = SnapshotWriter(control, job_id=observed_job_id,
    writer_guard=verified_current_job_run,
    artifact_validator=artifacts.verify, artifact_prefix=artifacts.prefix)
result = prepare_and_publish(project_root, sealed_plan_with_pairs,
    run_id=observed_run_id, artifact_store=artifacts, writer=writer,
    local_parent=local_temporary_disk)
```

Los nombres OBSERVED son ilustrativos; no desplegar literalmente. Se validan prefijo absoluto exacto y namespace sbs_radar. La función no crea clientes, recursos ni grants; recibe capacidades servidor. NotebookSK12 integrará este entrypoint tras revisión y bindings reales. Nunca apuntar SQLite/localstate a Volumes.

Flujo: `RefreshRunner` prepara en un directorio temporal aislado usando `build_real_hooks`, sin inferencia habilitada. `pending_validation`/failed retorna sin subir ni hacer claim/CAS. El puntero local solo selecciona la preparación. Se recoge release.json, los tres artifacts preparados y todas sus dependencias declaradas; se verifica cierre y hashes locales antes de cualquier upload.

Los objetos se suben a `prefix/runs/<run_id>/<closure_sha256>/<relative_path>`, sin rutas absolutas/escape/symlink. Un conflicto de nombre existente solo se acepta tras GET y hash idéntico. Otros errores de upload quedan sin confirmar, sin retry/delete. Manifest versionado contiene paths relativos, bytes y hashes; se sube al final y luego se relee TODO el cierre antes del claim/publish. SnapshotWriter vuelve a usar artifacts.verify para validar antes del CAS. Artefactos huérfanos tras fallo quedan preservados; no hay limpieza automática ni rename.

Límites predeterminados:500archivos incluyendo manifest,128MiB total,32MiB por archivo y3000llamadas FilesAPI por instancia. Cap local/hash se evalúan antes de upload. El SDK requiere retries/timeout acotados por integración; el módulo no incorpora reintentos. El output conserva counts, publication y manifest URI, y separa runtime_promoted=false/cloud_e2e_validated=false.

Las pruebas locales cubren paths/symlinks/caps, overwrite=False, conflictos, readback corrupto, 6PDF reales/2comparaciones/135vectores reutilizados/135provisions, pending/fallo sin claim y recuperación durable sin recaptura. FilesAPI/Delta son dobles; no se declara durabilidad cloud probada. Registro final: runs/sk11-cloud-writer-record.json.

## Recuperación y límites

SnapshotWriter conserva manifest_path y manifest_sha256 (=release_id) en current y releases. `VolumeArtifacts.recover(path, sha)` reconstruye y valida el cierre entero con los mismos caps. El coordinador detecta un mismo run con tipo int exacto, verifica Job y el recibo canónico contra releases mediante `confirm_current`, además de writer_guard, y retorna recovered=true sin SK02/recaptura. Bytes cambiados o locator ajeno se rechazan; no se declara recuperación por igualdad de IDs sola. El retorno recovered omite counts antes que inventarlos.

No asumir que este camino ya es operativo cloud: siguen pendientes bindings/probes/grants/notebook y un ensayo autorizado. Fencing/CAS no reemplaza gobernanza del único escritor. Shared control necesita preseed y Serializable verificados; FilesAPI no es WORM. Coste desconocido=null; sin promoción runtime.
