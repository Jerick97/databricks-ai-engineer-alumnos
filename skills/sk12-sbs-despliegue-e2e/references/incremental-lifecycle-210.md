# SK12 / CreatorZ — despliegue incremental y sesión210

Fecha: 2026-09-29. Estado provisional, pendiente revisión independiente y E2E real. Constructor separado del revisor root. Usa CreatorZ exacto exigido por AGENTS.md; corrige fallo observado207/209, no evalúa calidad general de skill.

## Evidencia y decisión

207 completó paquete234archivos/162830863bytes mediante226imports nuevos+8adoptados y consumió la ventana de30min entre staging y prueba. Supervisor apagó compute y chat quedó condeadline expirado; UI209 ahora maneja HTML pero no restaura servicio. Baseline: STATE primeras secciones, result/cleanup207, fuente199, review209. El usuario pide disponibilidad y pruebas completas; la nueva instrucción sustituye shutdown automático, preservando historial y límites explícitos.

Fuentes primarias consultadas: SDK Workspace https://databricks-sdk-py.readthedocs.io/en/latest/workspace/workspace/workspace.html (export/import AUTO incluye archivos; no asumir copia servidor rápida), Apps deploy https://docs.databricks.com/aws/en/dev-tools/databricks-apps/deploy (SNAPSHOT), Apps scaling https://docs.databricks.com/aws/en/dev-tools/databricks-apps/horizontal-scaling (estado temporal porinstancia). No se observó copia servidor que garantice los234bytes del paquete. Export/import directorios no se presenta como mejora medida. Local disk App no se trata como ledger durable.

Se modifica sólo delta sobre directorio propio199, con beforeimages locales exactas, readback remoto antes de cualquier overwrite y después de cada import. Modelo/chunks grandes intactos; manifest lógico se escribe último. Snapshot207 y paquete199 local permanecen. El nombre hash histórico de la ruta ya no describe su contenido mutable: nuevo plan contiene hash real resultante. Archivos sin delta reutilizan verificación histórica207; no se afirma hash remoto fresco de esosbytes. Bootstrap existente vuelve a verificar manifiesto completo al iniciar.

Un runner independiente no importa la cadena de200ejecutores: identidad workspace/SCIM/App exacta, estadoSTOPPED/deployment207, una start, esperaautorestore terminal, una deploy SNAPSHOT, readiness separado. No parada automática ni supervisor persistente. Error conserva intent/result, no reintenta mutaciones ambiguas. Recursos nuevos: ninguno. Compute existente se deja encendido conforme instrucción; tasa observada0.5DBU/h, no tarifaUSD demostrada.

## Activación y presupuesto

App inicia epoch aleatorio e inferenciaINACTIVE; fuentes/comparaciones disponibles. Tras UI real ready, coordinador local reserva de forma durable SQLite8generation/8embedding/80000tokens y firma un permisoEd25519 para eseepoch, duraciónmáxima8h. Es asignaciónNUEVA explícita, no continuidad oculta del cupo anterior: prior192/199 reserva1generation/1embedding/20000tokens e intents originales se preservan sin reembolso. Además se conserva un intento externo del usuario de consumo desconocido: el POST original de la pregunta con HTML no fue capturado. Cap210 permite UNA asignación total; reinicio cambiaepoch, no resetea ledger ni genera nueva firma. Otra asignación necesita revisión explícita que reconozca consumo previo. No claims de cuota universal entre otros operadores/otros scripts.

Firma se entrega mediante panel administrativo visible protegido por identidad+CSRF. Claveprivada0600 en directorioignorado local; sólo pública entra alpaquete. Solicitudes reservan conservadoramente antes de network, fallos no devuelven cuota. Expirar bloquea inferencia y comunica estado; nunca apaga App. La ventana no existe durante upload/start/deploy. Signedpayload <=120s alactivar: emitir únicamente cuando UI está lista.

## Requisitos, riesgos, pruebas

| Riesgo observado | Corrección | Evidencia requerida |
|---|---|---|
|234uploads repetidos|delta exacto, grandes sin copiar|planfilecount/bytes + imports reales|
|ventana gastada desplegando|activación despuésready|timestamp readiness y firma|
|restart resetea contadores|epoch+firma+ledger durable de asignación|restart rechaza firma anterior, segundaasignación bloqueada|
|timeout duplicamutación|intent durable y no retry|test excepción unPOST|
|fuenteajena|SCIM/App/source/deployment exactos|tests adversos y GET real|
|apagado mientrasusuario usa|sin supervisor/STOP|result + UI real activa|
|código local presentadoE2E|estatus provisional y matriz aceptación210|UI broadquestion, dosfamilias, antes/después, originales, seguimiento, Genie|

Pruebas discriminantes: deriva remota impide primerPOST; preflight de todosbeforeimages antesoverwrite; timeoutimport deja intent sinretry; firma verificable; readback de mismoephoch no extiendehora; reinicio/DBborrada no reinicializa cuota. Runtime prueba firma/epoch/CSRF/identidad/expiry/cupos compartidos. No equivalen a demostracióncloud. Numeric188FAIL y final153bloqueado permanecen. Root revisa código/plan/pins antesexecute; tras despliegue sigue runs/sk12-acceptance-210-plan.json. No prometer calidad final por readiness.
