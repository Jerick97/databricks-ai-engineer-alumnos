# Driver cloud escritor — SK11 v0.1.13, construcción offline

`cloud_driver.py` ensambla `DeltaControl`, `SharedLedger`, `CloudDispatcher`, `VolumeArtifacts`, `SnapshotWriter` y `prepare_and_publish`. No modifica sus contratos ni crea recursos. Las pruebas ejecutan preparación real de seis PDFs/vectores sellados y dobles locales en las fronteras remotas; no son E2E cloud.

## Configuración cerrada y bindings

`DriverConfig.from_dict(data)` acepta exclusivamente `writer`, `control_table`, `control_table_id`, `warehouse_id`, `volume_prefix`, `expected_acl`, `policy`, `release_manifest`. `writer` corresponde a WriterConfig. Para serverless: cluster_id=null, compute_mode=serverless, environment_version explícito y environment_dependencies array de versiones exactas; para legacy exige cluster existente observado. No hay cluster disponible observado en preflight014; no inventar uno. Serverless sigue candidato documental, no habilitación/coste acreditados.

`policy` contiene trusted_administrators (lista no vacía), maintenance, exclusive_writer, singleton_control y storage_authorized (declaraciones explícitas), issued_at_ms y expires_at_ms. writer.boundary_policy_id = digest(policy). No son observaciones de ausencia de otros administradores ni nueva aprobación. La política pertenece al servidor y se entrega dentro del archivo fijado por SHA.

writer.snapshot_backend_id = digest({control_table,control_table_id,warehouse_id,volume_prefix}). writer.release_id es SHA256 de bytes del archivo release_manifest relativo al snapshot; éste contiene files (path→SHA256). El driver coteja todos los archivos antes de metadata/SQL. El hash del manifiesto generado de publicación es diferente: identifica preparación de salida, no cambia identidad del snapshot de entrada.

`load_config(server_path, expected_sha256)` verifica archivo<=64KiB, pin y esquema; rechaza secretos/campos extra. Pin y path son configuración del servidor, nunca autoridad desde requests. `preflight(None)` explica pendientes, sin SDK/auth. `bind_driver(config, services, evidence_mode=...)` solo ensambla y no llama servicios. `execute_from_config(config, project_root, job_id=..., run_id=..., release_id=...)` es el entrypoint futuro con Config.authenticate normal y serializers SDK; puede escribir SQL/Files SOLO en ejecución autorizada. El notebook entregado usa preflight por defecto y parámetros de entorno explícitos, sin tokens.

## Evidencia y supuestos

Tables.get observa full_name/UUID UC/DELTA/MANAGED/owner, propiedad delta.isolationLevel=Serializable y ausencia visible de filtro/máscara. Si la propiedad no se devuelve, rechaza; nunca rellena expected como observed ni hace ALTER. Warehouse GET debe mostrar RUNNING: no se envía SQL a warehouse STOPPED. DeltaControl SELECT de toda la tabla (límite2) prueba singleton observado; la continuidad administrativa es supuesto explícito.

Jobs settings/ACL/run/task/effective params se validan con CloudDispatcher. CurrentUser.me debe coincidir con writer principal y activo. Legacy cluster GET verifica RUNNING; serverless no invoca cluster GET ni inventa ID. Un run periódico real se registra mediante observe_daily; on-demand debe existir en ledger. Antes de preparar y al claim/publicar se repite guard. No se llama Jobs.run_now/start/create desde este driver. El Run SDK no ofrece run-as ni environments históricos; settings actuales y task snapshot no prueban esa continuidad. Hereda execution_contract_sha256 en record/request_hash; cambio de entorno invalida reuso, no migra silenciosamente ledger antiguo.

Las declaraciones pinned de administrador sirven de frontera operativa, no scan global de Jobs/principales. No afirmar que metadata GET prueba MODIFY/WRITE VOLUME: las operaciones reales y sus errores aún deben observarse. La app lectora no recibe este driver/capacidad escritora.

## Transporte acotado

SDK0.102 `_BaseClient` usa retry_timeout_seconds or300; configurar0 NO desactiva retries. `SingleAttemptApi` usa Session sin retries, una request por método SDK, timeout(10,60), redirects=False, respuesta<=32MiB y cuota4000 por instancia. Solo GET, POST StatementExecution, PUT Files/directories; no Jobs POST, DELETE ni SQL arbitrario desde notebook. DeltaControl construye SQL cerrado y lleva su cuota propia. No resetear instancias para aumentar cuota. Autenticación normal puede refrescar OAuth internamente; no afirmar control de ese tráfico del proveedor de credenciales. Errores públicos son códigos seguros, no headers, prompts ni excepciones originales.

## Notebook y pendientes

`notebooks/sbs-radar-cloud-writer.ipynb` lee SBS_PROJECT_ROOT, SBS_WRITER_CONFIG, SBS_WRITER_CONFIG_SHA256 y SBS_WRITER_MODE (default preflight). Job task aporta job_id/run_id/release_id dinámicos, corroborados por APIs; esos widgets no autentican por sí mismos. Entrega de archivos/env/SDK deps al notebook requiere integración del Job futuro. No activar horario ni recursos en esta construcción.

Pendientes: control table/preseed/property/permisos reales, Volume, Job/ACL/compute/env observados, snapshot entregado y manifest externo, autorización de ejecución, y prueba cloud de readback/errores/CAS. `cloud_acceptance=False` permanece incluso cuando un run devuelve published. Preparación genera135raw, no export002141 ni promoción runtime; no verifica frescura remota. El verificador posterior de resultado del dispatcher requiere enlazar recibo de salida con el release de entrada: este driver no declara ese gate satisfecho.

## Fuentes concretas reutilizadas/contrastadas 2026-09-28

- https://databricks-sdk-py.readthedocs.io/en/latest/workspace/catalog/tables.html — tables.get/properties, no UUID Delta histórico supuesto.
- https://docs.databricks.com/aws/en/optimizations/isolation/isolation-levels — Serializable.
- https://databricks-sdk-py.readthedocs.io/en/latest/authentication.html — autenticación normal.
- https://docs.databricks.com/aws/en/compute/serverless/dependencies y https://docs.databricks.com/aws/en/dev-tools/bundles/examples — researchroot de serverless, registrado en runs/sk11-serverless-compute-014-invocation.json.
- SDK0.102 instalado: Config, _BaseClient.do, FilesAPI, StatementExecutionAPI, JobsAPI serializers inspeccionados offline.

## Separación de hashes y alcance de captura

Evitar ciclo de hashes: primero congelar el manifiesto del snapshot de código/datos, después calcular writer.release_id=SHA256(bytes_manifest), después crear el driverconfig externo que contiene ese valor y fijar SHA256(driverconfig) por configuración externa confiable. El manifiesto no puede incluir ese archivo activo driverconfig ni su propio hash autoreferente. Un ejemplo de esquema sin identidad real puede estar en el repositorio; no equivale a la configuración desplegable. `load_config` verifica el pin externo; no pretende que ese archivo forme parte del cierre que se autohashea.

`execute_from_config` carga `load_sealed_plan`: exclusivamente reutiliza los seis PDFs sellados y embeddings compatibles. El Job queda conectado a preparación de caché y publicación de esos artefactos; descubrimiento/captura web de novedades y frescura remota siguen pendientes. No llamar a este modo actualización regulatoria diaria completa aunque se programe a las08:00Lima.
