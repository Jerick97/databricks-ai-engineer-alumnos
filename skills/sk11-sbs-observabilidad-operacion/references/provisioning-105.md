# Preparación de aprovisionamiento 105 — provisional, sólo local

Reutiliza SK11 0.1.21, SK12 0.1.15/refinamiento080 y skill-creator-z exacta; no cambia esos contratos ni sus versiones. Entrada: spec12, autonomía053, refresh-job v3, observación104 y GET104b. Revisión independiente: coordinador root. Esta referencia no concede permisos.

## Brief y decisiones

Fuentes locales consultadas 2026-09-29: `deployment/refresh-control.sql`, `cloud_dispatch.py` (WriterConfig/job_settings/verify), `cloud_driver.py` (DriverConfig/preflight/execute_from_config), `shared_control.py` (initial_state/DeltaControl), `remote_refresh.py`, `cloud_writer.py`, `capture_recovery.py`, `deployment/build_bundle.py`, referencias cloud-driver/cloud-dispatch. Las referencias existentes documentan SDK0.102 y fuentes oficiales. No se hizo consulta remota nueva en105; vigencia API y habilitación serverless pendientes de observación real. La alternativa de reutilizar Jobs fixtures fue descartada: no son metadata de producción. No se crea otro SP ni credencial.

Hechos104: SP activo id72803555975940/applicationId33b6f37c-7e6a-489f-b313-f886418b0319; lista Job nombre exacto vacía; GET104b TABLE_DOES_NOT_EXIST. Son histórico, no sustituyen GET fresco antes de mutar. Warehouse828756322bedff37 y Volume candidatos existentes; permisos efectivos y estado RUNNING deben comprobarse.

## Resolución mínima del ciclo de configuración

WriterConfig requiere un job_id existente, pero job_settings no lo usa. `creation_settings` compone un objeto de creación sin job_id y reutiliza exactamente job_settings: pausa, cola, concurrencia1, run-as SP existente y dependencias fijadas. No construye DriverConfig hasta GET Job, GET tabla y GET ACL válidos. Primero snapshot→SHA manifiesto; luego tabla observada+política→backend pin; luego settings/create Job; luego GET/ACL→DriverConfig externo; finalmente notebook ligado al config. No incluir config operativo en el manifiesto que referencia su SHA. No usar IDs placeholder ni presentar plan como API request.

## Secuencia remota todavía no ejecutada

1. Revisar hashes del plan/código, autorización vigente y presupuesto. GET fresco SP, warehouse, Volume/permisos, ausencia tabla, Jobs lista completa. Verificar identidad del operador y permiso de usar SP sin leer secretos.
2. CREATE exacto del paso `control_steps()[0]`, una sola vez. GET UC debe confirmar ID, nombre, MANAGED/DELTA, columnas no nulas exactas, Serializable, owner confiable y ausencia de filtros/máscaras. El ID viene exclusivamente de GET.
3. SELECT completo con límite2 confirma cero filas sobre mismo ID y ventana de mantenimiento exclusiva. INSERT exacto `control_steps()[1]`, una vez. SELECT exacto del singleton usando contrato DeltaControl prueba revisión0+initial_state; respuesta DML no basta. Ausencia de restricciones UNIQUE sigue siendo supuesto administrativo explícito.
4. Subir snapshot inmutable y verificar cada byte/hash. Preparar notebook/source bajo `/Shared/sbs-radar/` que entregue snapshot local/config externo mediante mecanismo probado en serverless. El notebook existente sólo lee entorno SBS_*; **esa entrega en serverless aún no está resuelta por105**. No asumir que widgets config son autoridad.
5. Generar política administrativa temporal con hechos y supuestos separados; sin ampliar ventana anterior silenciosamente. Crear Job PAUSED con creation_settings, nunca con el documento refresh-job entero. GET Job confirma ID/settings/run_as sin paginación; conflicto nombre obliga GET y revisión, no segundo create.
6. Leer ACL actual antes de proponer delta mínimo. No sobrescribir propietarios/desconocidos. Configurar sólo ACL revisada; volver GET. DriverConfig contiene ACL completa observada y backend ID observado; ejecutar preflight real antes de guardar el pin externo confiable.
7. Primer run controlado con el mismo Job requiere notebook entregado y config/config-hash exactos, policy vigente, permisos UC/Volume, warehouse RUNNING y límite de gasto. Verificar identidad efectiva, artefactos y CAS/readback completo, fallo antes de commit y recuperación. No habilitar schedule hasta aceptación independiente. Después UNPAUSED 08:00 America/Lima y on-demand usan el mismo Job y SharedLedger, no otro writer.

## Ejecutor y gates

`step_once` implementa sólo el núcleo durable acotado: callbacks de autorización/observación/efecto son capacidades confiables que deben entregarse, fijarse y revisarse. **No incluye adapter remoto ni validadores específicos de respuesta UC/Jobs/SQL. No es un CLI de aprovisionamiento cloud listo.** effect debe usar transporte sin retries, cuota global y timeout; observe devuelve dict sólo tras readback validado, None sólo ante ausencia demostrada. Una excepción de observe bloquea o conserva unknown; una respuesta create/INSERT jamás prueba éxito. Autorizar de nuevo después de fsync. Journal POSIX en host único controlado; no Volumes ni lock distribuido. Cambiar payload de step_id previamente intentado bloquea. Intent/receipt se fsync, incluida carpeta, y no se reescriben. No se reenvía una operación ambigua aunque una lectura posterior sea vacía.

Recuperación operacional posterior conserva fencing/CAS/publicaciones inmutables; rollback requiere release previo válido y acción escritora autorizada, nunca DROP/DELETE tabla ni edición manual de state_json. El diario no renueva disponibilidad Genie: certificado TTL5min precisa renovación/readback independiente ligada a cada ventana de uso. Captura remota precisa recuperación de estado con capture_recovery; entrada nueva sin embeddings autorizados queda pending. Sealed valida preparación de135raw, no actualidad ni agente conversacional completo.

## Evaluación y riesgos

RED: import ausente. GREEN: ocho pruebas de ambiguity/no-resend, readback único, autorización negada sin writes, creación sin ID ficticio/PAUSED, seed exacto, conflicto al cambiar payload, error de GET y vencimiento posterior a intención. Pruebas con callbacks sintéticos son contrato local, no API/E2E. Snapshot usa selector existente con exclusión namespace capacidades deployment/*-authorization.json y deployment/state. Prueba source/archive/tmp debe registrar hashes y notebook real ejecutado en preflight; nunca interpretar ese resultado como publicación cloud. Costos/tokens desconocidos null. Falta benchmark conductual y evaluación independiente de skill; estado provisional.

## Evidencia portable ejecutada

`runs/sk12-writer-portable-105-verification.json`: source/archive/tmp pasaron preparación real sealed de seis PDFs y notebook (celdas Python reales en preflight, no Jupyter UI).782hashes verificados; red y lectura del origen bloqueadas con audit hook en copias. Archivo15.6MB es snapshot de bytes: incluye extras como conversación102 y tests anteriores a los últimos tres casos105, sin dependencia efectiva writer ni revisión semántica de esos extras. El ejecutor105 no cambió tras empaquetar. Pruebas complementarias y este informe quedan externos y fijados por freeze105. No requiere origen mutable; no convierte sealed en captura remota actual ni acredita serverless.
