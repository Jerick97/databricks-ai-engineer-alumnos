# Laboratorio S08 · tu Copiloto Neptuno operable

Abre `README.md` y sigue la preparación de `GUIA-DOCENTE.md`. Trabaja con el repo completo, `notebook.py` y recursos asignados a tu equipo. No reutilices nombres del docente sin indicación. Entrega archivos Markdown o JSON en `entregas/` con fecha, identidad/rol, entrada, acción, resultado y evidencia sin secretos. Cada requisito de `requirements.json` indica el nombre de entrega esperado. Un resultado bloqueado se documenta; no se marca aprobado.

## CP0

Abre notebook, revisa `lab/config.json` y ejecuta inventario. Identifica agente S05, benchmark S06 y control S07. **Salida:** `cont-neptuno.md` con recursos concretos y faltantes. **Aceptación:** puedes explicar quién consulta datos y quién administra el endpoint. Si falta acceso, registra recurso/permiso y consulta al docente antes de crear alternativas.

## CP1

Lee el contrato del agente en `lab/agent.py`, ejecuta empaquetado del notebook y registra URI/versión/dependencias. **Salida:** `s08-deploy.md`. **Aceptación:** una solicitud con formato esperado produce respuesta válida y diferencias deploy code/model están explicadas. Conservar error si falla; cambiar dependencias mediante archivo versionado.

## CP2

Ejecuta Serving sobre tu versión asignada. Espera estado listo antes de invocar. **Salida:** `s08-serving.md` con endpoint, versión, request ID, latencia y respuesta saneada. **Aceptación:** invocación real y explicación de 3 categorías, serverless y cold start. HTTP 200 no acredita exactitud: compara un dato con referencia del curso.

## CP3

Distingue los dos servicios: el agente principal `ais08-neptuno` (`agent/v1/responses`) admite una versión servida; el custom complementario `ais08-neptuno-rollout` permite demostrar canary. No configures un split en el agente.

En el custom de ventas asignado, guarda configuración previa, resuelve aliases, prepara distribución 90/10 y ejecuta/verifica rollback con los comandos de la guía. **Salida:** `s08-rollout.md` con ambos nombres, versiones del modelo `ventas_rollout`, estado antes/después, consulta de ventas y revisión observada. **Aceptación:** porcentajes suman 100, configuración restaurada y respuesta verificadas. Explica aparte cómo actualizar/restaurar la versión única del agente. Si solo calculaste plan, marca «diseñado, no ejecutado». No inferir promoción por mover un alias.

## CP4

Despliega `app/` desde CP4 del notebook. Abre URL con identidad corporativa y consulta Neptuno. **Salida:** `s08-apps.md` con URL, identidad de backend, permiso de endpoint y respuesta saneada. **Aceptación:** browser→backend→endpoint funciona; explica por qué autenticación no demuestra aislamiento de datos por usuario. Nunca copiar PAT al browser para resolver 403.

## CP5

Busca la inferencia de CP2/4 y ejecuta aplanado del notebook. **Salida:** `s08-inference.md` con request ID, muestra cruda saneada, fila plana y conteos. **Aceptación:** correspondencia observable; distingue nulo de parseo y fila ausente por retraso. Fixture local es práctica de transformación, no logging real.

## CP6

Crea/refresca monitor con tabla plana y baseline; interpreta una métrica. **Salidas:** `s08-monitor.md` y `s08-gateway.md`. **Aceptación:** estado/refresh y métrica con ventana, número de observaciones y limitación. Añade una regla de rate limit y cómo verificar consumo frente a factura. Drift requiere investigación, no equivale automáticamente a error de respuesta.

## CP7

Valida `bundle/databricks.yml` con target dev desde Terminal según GUIA-DOCENTE (el notebook muestra su configuración); identifica variables de prod. Registra prompt y alias, conserva versión resuelta y explica reversión. **Salidas:** `s08-bundles.md` y `s08-prompts.md`. **Aceptación:** evidencia de validación y prompt versionado; enumera gates y separación de entornos. Sintaxis válida no prueba deploy.

## CP8

**Salidas:** `s08-final.md`, `s08-cloud.md`, `s08-cert.md`. Enlaza cada entrega anterior y evaluación/gobierno S06–07. Agrega commit, recursos, versiones, pruebas, fecha y costos observados si están disponibles. Compara un equivalente endpoint de otro proveedor. Responde 12 preguntas originales de `CERTIFICACION.md` antes de leer las razones y escribe dos brechas con plan de práctica.

**Aceptación final:** endpoint consultable, App usable, evaluación y gobierno trazables, inferencia real y monitor interpretable, ruta de rollback. Un archivo de configuración o una captura de creación no sustituyen ejecución. Si falta un eslabón, el portfolio queda parcial con acción y responsable. No incluir credenciales ni datos privados en repos públicos.
