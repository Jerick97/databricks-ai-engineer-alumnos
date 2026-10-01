# Propuesta cloud SBS Radar — revisión 002

Estado: **borrador reconciliado con el export 002; no aplicable todavía**. SK12 actualizó `deployment/cloud-proposal.json`; la propuesta 001 se conserva en `deployment/archive/cloud-proposal-001.json`. No se ejecutó SQL ni se crearon recursos cloud al preparar esta revisión.

## Destino y datos

El destino propuesto es `neptuno_manuel_arguelles.sbs_radar`, app `sbs-radar-pilot`, job `sbs-radar-daily` y un espacio Genie propio. El warehouse candidato es `828756322bedff37`. El preflight histórico observó STOPPED y ausencia del schema; **no se presenta esa observación como estado actual**. Antes de aplicar se revalidarán estado, identidad, permisos y colisiones. Los recursos del curso permanecen fuera del alcance.

El export 002 contiene seis documentos/versiones, 141 disposiciones —135 páginas y seis artículos estructurados—, dos pares, tres ChangeSets parciales, tres EvidencePacks, una fila de revisión IA y dos procesos ficticios. Tres ChangeSets no equivalen a tres cambios materiales. Los hashes y conteos de las ocho tablas están fijados en el JSON. La correspondencia entre snapshots distintos de RAG y Genie está verificada localmente y referenciada por hash; no acredita publicación remota.

La solicitud Genie ahora contiene seis ejemplos y seis preguntas derivados de los contextos exactos del export: familia, par, versiones y artículo. Reutilizar esos ejemplos como benchmark técnico **no los convierte en una evaluación independiente**. La API y las respuestas Genie todavía no se probaron en remoto; cualquier respuesta fuera del alcance verificable debe rechazarse. La presentación conversacional de listas sigue pendiente.

## Publicación, identidad y runtime

Las solicitudes de creación de schema, volumen, ocho tablas Delta y cargas JSONL se conservan como artefactos revisables. No usar `IF NOT EXISTS` para ocultar colisiones ni sobrescribir recursos ajenos. Los conteos de carga comprueban cardinalidad; el readback completo debe además comprobar columnas, tipos, claves, contenido e identidad de tabla.

El módulo de readback por versión Delta está implementado por SK06 y sometido a revisión SK09. Esa revisión detectó brechas de validación local que están en corrección. Las versiones Delta y el certificado reales permanecen sin asignar: no se inventa versión cero. La integración runtime mantiene su certificado por intervalo; no acepta todavía certificados Delta v2.

`app.py` ya implementa modo cloud explícito con identidad verificada en servidor, política SK08 y origen HTTPS observado. El arranque previsto es `python app.py`, con `SBS_MODE=cloud`, `DATABRICKS_HOST`, `SBS_PUBLIC_ORIGIN` y puerto de plataforma. `deployment/prepare_app_config.py` requiere la URL realmente observada de la app. La prueba local del adaptador y una lectura real de identidad no acreditan Apps SSO ni autorización del principal de servicio en producción.

La comprobación de historial y SQL literal ejecutado ya está implementada. Distingue valores literales verificados de parámetros vinculados realmente observados. Faltan dependencias servidor reales de permisos/publicación/historial y su ejecución integrada; sin ellas, Genie permanece explícitamente indisponible. No se sustituye una respuesta no disponible por cero.

## Operación y límites

Los preparadores reales SK03/SK04/SK06 de refresco local están bajo revisión independiente. Reutilizan fuentes y embeddings compatibles; no habilitan por sí mismos promoción del runtime ni coordinación distribuida. El job diario continúa propuesto a las 08:00 de Lima, inicialmente PAUSED, concurrencia uno, sin reintentos y timeout de 600 segundos. Faltan estado/bloqueo distribuido, identidad escritora separada, elección de cómputo y notebook cloud completo ejecutado.

La app reubicada ARM64 se probó offline. Linux emulado ejecutó el reranker, pero mostró diferencias de puntuación y orden; una variante adicional no demostró mejora y no se promovió. Se requiere validar el release exacto en la arquitectura de destino. Tres intentos acotados de generación devolvieron 403; no habrá nuevos intentos sin evidencia nueva de acceso. La UI visual sigue pendiente por el bloqueo de automatización de Chrome.

El coste continúa desconocido: no hay tarifa aplicable ni saldo comprobados. Los US$100 del spec son una hipótesis, no permiso ni crédito. El JSON propone una ventana piloto de 30 minutos y límites de solicitudes/tokens; no son un techo monetario persistente ni una ventana automáticamente aplicada. La autorización de nuevos recursos y del gasto recurrente se resolverá sobre un paquete concreto cuando se cierren las dependencias técnicas.

## Reversión y siguiente paso

El JSON conserva la reversión por IDs propios: registrar recursos y ACL antes de aplicar; pausar el job; detener o restaurar la app; revocar solamente grants añadidos; retirar exclusivamente el espacio Genie creado; preservar originales y exportaciones. La eliminación de datos requiere alcance explícito y comprobación de identidad. No existe un release remoto anterior que pueda presentarse como backup.

No detener el warehouse compartido si hay trabajo ajeno. Detener una app no revierte sus datos. Antes de solicitar autorización integral: cerrar publicación y dependencias servidor, operación distribuida, configuración de destino y estimación; reconstruir y fijar el release; después ejecutar notebook, UI autenticada, conversación, Genie y recuperación reales. La misión sigue activa.
