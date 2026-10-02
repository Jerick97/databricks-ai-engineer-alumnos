# Notebook docente S08 corregido

[Abrir S08-docente-validado](https://dbc-0410b264-20c7.cloud.databricks.com/editor/notebooks/3142549814418784?o=7474657121564806)

Usar esta copia para la demostración docente. Ejecutar Run all con modo=verificar y rollout=inspeccionar. Los cinco valores de configuración vienen completos. El notebook genérico de alumnos requiere los recursos propios de cada equipo.

Corrección del 27/09/2026: el enlace anterior abría el starter con widgets vacíos. La validación previa había inyectado parámetros desde un Job y no demostraba que esa copia arrancara sin configuración. Se reprodujo ValueError: Completa warehouse_id y se añadió una prueba de regresión.

Nueva validación: Job 439573581964505, TERMINATED/SUCCESS, base_parameters={}, seis controles PASS. Se ejecutaron las 30 celdas de la copia docente mediante Jobs API, sin parámetros externos. El export remoto coincide con notebook-docente.py, SHA256 53f0e331e04e18766bdfe1ef5f22593e8639ca58e119c60800986a4037a73e4c. La apertura en Chrome fue comprobada; no se automatizó el botón Run all del navegador. Juez independiente: reports/teacher-delivery-judge.json.

Limitación histórica observada durante el Job del 27/09: la App ais08-neptuno-ui figura STOPPED/UNAVAILABLE con el mensaje «App compute was stopped due to workspace or account status». El 28/09 se arrancó de nuevo y se observó ACTIVE/RUNNING. El estado de la prueba de navegador de hoy está en [class-day-browser.json](reports/class-day-browser.json). El éxito del Job valida el recorrido del notebook y sus seis controles; no certifica que la App esté operativa ahora. El reporte conserva ese estado sin ocultarlo.

Evidencias: reports/teacher-delivery-regression.json, reports/notebook-docente-submit.json, reports/notebook-docente-observed.json y reports/teacher-delivery-judge.json. Esta corrección docente se entrega como addendum al paquete de alumnos previamente validado.
