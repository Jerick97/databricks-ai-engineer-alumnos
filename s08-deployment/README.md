# S08 · Deployment, monitoreo y certificación

**Última clase: lunes 28 de septiembre de 2026 · 180 min reloj, pausa de 10 minutos.** Continuamos el Copiloto Neptuno de S01–S07 hasta endpoint, interfaz Apps y monitoreo.

1. Docente: leer [plan de clase](PLAN-CLASE.md) y [guía](GUIA-DOCENTE.md); preparar recursos cloud antes de clase.
2. Alumno: abrir [consigna](CONSIGNA.md) e importar/sincronizar la carpeta completa en Databricks; ejecutar [notebook](notebook.py) por checkpoints 0–8.
3. Repaso final: [certificación](CERTIFICACION.md), mapa seis dominios y 12 preguntas originales con razones.
4. Contrato y cobertura: [requisitos](requirements.json), [agenda](agenda.json) y [contexto](course-context.json).

El paquete usa `lab/` para agente/despliegue/monitoreo/rollout, `app/` para UI con backend y `bundle/` para configuración declarativa. Los nombres de `lab/config.json` son configuración del entorno; cada alumno debe usar recursos propios o asignados. No ejecutar desde un notebook suelto sin sus carpetas.

El entregable es un manifiesto que enlaza código, versión, endpoint, App, evaluación, permisos, inferencias, monitor y rollback. Requiere evidencia de ejecución; recursos creados no equivalen a respuesta correcta. La latencia de provisión y de logs puede superar el bloque en vivo: hay prewarm docente y reproducción completa posterior.

La preparación se considera lista únicamente con evidencia funcional, QA visual y tres jueces independientes vigentes. Revisar `reports/` y `course-context.json` para el estado final; no inferir validación cloud por la existencia de estos archivos. El dictado y las entregas de alumnos se registran después de clase.

CP3 demuestra canary 90/10 en un custom complementario de ventas Neptuno (`ais08-neptuno-rollout`). El agente principal (`agent/v1/responses`) se actualiza con una versión única; no admite traffic splitting. Ambos se preparan antes de clase y sus evidencias se mantienen separadas.

## Acceso docente corregido

Para la demostración usa [S08-docente-validado](https://dbc-0410b264-20c7.cloud.databricks.com/editor/notebooks/3142549814418784?o=7474657121564806), preconfigurado. [Instrucciones y evidencia](ABRIR-NOTEBOOK-DOCENTE.md). `notebook.py` es el starter para alumnos y exige recursos propios.
