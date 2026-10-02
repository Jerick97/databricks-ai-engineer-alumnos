# S08 · Estado de entrega

Última clase: lunes 28 de septiembre de 2026. Material validado en el ensayo del 27/09. El cierre histórico `reports/closure.json` omitió el gate CP4 de navegador y no certifica disponibilidad hoy. La validación del día en `reports/class-day-browser.json` acredita ahora CP4 con dos consultas reales. Consultar el cierre regenerado para el resultado de los jueces actuales.

- 52 slides con notas/fuentes, QA de 18 escenarios y nueve controles.
- 13 requisitos del temario cubiertos; jueces independientes de currículo, pedagogía y ejecución PASS, cobertura PASS sin huérfanos.
- Notebook de 30 celdas, Python/IPYNB equivalentes. Run Databricks 35725070281647 SUCCESS; SHA-256 4dbb89479b8d04d4e22de55110c9e47297e6e5f3d91e3d76339d9f9a4edf9510.
- Agente UC v4/prompt v4: seis casos reales, tres controles de seguridad; 14 pruebas locales.
- Custom complementario: canary 90/10 con 50 consultas (42/8); rollback 100/0 con cinco consultas y snapshot coincidente. El endpoint del agente no admite split.
- App autenticada por HTTP y render en móvil/escritorio comprobados. Primer consentimiento SSO interactivo de Chrome no ensayado; requiere acción humana, sin bypass.
- Inference Tables reales: correlación seis de seis; monitor final 42 filas profile y 42 drift, dos ventanas reales, refresh SUCCESS. Baseline pequeña; no inferir calidad universal.
- Bundle validado; CI remoto y deploy mediante bundle no ejecutados ni afirmados.
- Entrega local: índice, guías, ejemplo, plantilla, banco de certificación, ZIP y copia en repositorio de alumnos. 88 archivos con paridad por hash. Sin commit/push remoto.

Abrir `index.html`. Antes del lunes seguir `RUNBOOK.md`: comprobar permisos, App y ambos endpoints, prewarm e inferencias/monitor. El estado cloud observado durante el ensayo no garantiza disponibilidad futura. Los recursos permanecieron desplegados; Serving tiene scale-to-zero. No se borraron modelos, tablas ni recursos del curso.


## Corrección entrega docente — 2026-09-27

El usuario detectó warehouse_id vacío al ejecutar el starter abierto. La validación anterior usó parámetros externos: no cubría esa apertura. Nueva copia docente preconfigurada, path /Shared/curso-databricks-ai-engineer/s08-docente/S08-docente-validado, Job439573581964505 SUCCESS sin parámetros externos y seis controles true; export remoto idéntico. Véase ABRIR-NOTEBOOK-DOCENTE.md. App observada STOPPED por estado workspace/account: no ratificar disponibilidad actual con el éxito de este Job.


### Recuperación App — 2026-09-27 12:43 UTC

Tras aviso del usuario sobre celda 20 se ejecutó apps.start sobre despliegue existente. Estado final ACTIVE/RUNNING; health HTTP200 y POST formulario HTTP200 con respuesta 116024.88 y fuente gold.ventas_por_categoria_mes. Evidencia reports/app-recovery-http.json. CP4 navegador sigue PENDIENTE: Chrome bloqueó automatización por interfaz de otra extensión abierta; se solicitó cerrar el panel. No confundir prueba HTTP con aceptación browser→backend→endpoint.

## Validación del día — 28/09/2026

App existente recuperada a ACTIVE/RUNNING, endpoint READY sin configuración pendiente. CP4 probado en Chrome con SSO autorizado: consulta de ventas devuelve 116024.88 con fuente; pregunta sin año solicita aclaración. Evidencia `reports/class-day-browser.json`. Seis casos del endpoint PASS y 14 pruebas locales PASS (`class-day-smoke-serving.json`, `class-day-local-tests.json`). Notebook docente mantiene las 30 celdas ejecutadas en el Job del 27/09; no se afirma una nueva ejecución integral hoy. Acceso docente destacado en el índice. Jueces actuales y paridad se actualizan después de estas correcciones.
