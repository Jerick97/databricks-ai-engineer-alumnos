# Ejemplo resuelto docente · Neptuno S08

Corte de lectura: 2026-09-27T03:28:12.776576+00:00. Este ejemplo distingue resultados observados de pasos pendientes; no es aprobación global del paquete. Los reportes pueden actualizarse durante el ensayo: los hashes al final fijan exactamente qué archivos sustentan este corte. Para estado posterior leer `VALIDACION.md` y reportes nuevos.

## S08-CONTINUITY · CP0

Entrada real: catálogo `neptuno_manuel_arguelles`, funciones S05 `ventas_categoria` y `productos_reponer`, tabla S04 `rag.chunks_embeddings`. El preflight registró warehouse RUNNING y controles de moderación de entrada/salida. La secuencia conserva datos→tools/RAG→agente; no cambia de caso comercial.

Acción: inventario y smoke. Resultado: se pueden recuperar recursos del proyecto; `reports/lab-preflight.json` y `reports/lab-smoke-serving.json` lo sustentan. Límite: no demuestra por sí solo que una persona haya guardado valoración en Review App ni que esta versión herede todos los scores S06 sin reevaluación.

## S08-DEPLOY · CP1

Entrada: código de `lab/agent.py`, dependencias declaradas, recursos y prompt. Acción: empaquetar y registrar. Salida observada: `neptuno_manuel_arguelles.ais08_lab.agente_neptuno`, versión `4`, MLflow `3.16.1`, URI `models:/m-40c1877723fa4424a6035f8989f77c04`. `reports/lab-artifact-check.json` confirma correspondencia de código y prompt versión `4` en ese artefacto.

Lectura: el artefacto contiene código/configuración reproducibles; la App es otro despliegue de código. Registrar un modelo no prueba todavía servicio accesible. Recuperación: si cambia código/dependencias, crear nueva versión y repetir controles, sin editar silenciosamente el artefacto evaluado.

## S08-SERVING · CP2

Entrada: versión registrada y permisos de dependencias. Acción: invocar `ais08-neptuno` con `lab_smoke.py`. `reports/lab-smoke-serving.json` contiene **seis casos con `pass=true`**: ventas, aclaración, categoría ausente, reposición, RAG y costos. El artefacto UC es versión **4** y el prompt está fijado en **4**; `agent_revision="s08-v2"` es una etiqueta del código, **no la versión UC**. No mezclar esos identificadores.

Ventas respondió **116024.88** para Bebidas en 2026; petición sin año pidió aclaración; margen se abstuvo por falta de costos. El caso de categoría ausente registra `tool_errors=1`: es un fallo de herramienta esperado que la prueba exige manejar sin fabricar una cifra. Por ello 6/6 pruebas de contrato no significa cero errores de herramienta ni evaluación completa de calidad. Tiempos de pared en el orden de los seis casos: 3.73, 0.64, 1.99, 4.78, 3.53 y 0.52 segundos.

RAG devuelve fragmentos con referencias y advierte que no constituyen una política completa; aceptar citas no demuestra relevancia perfecta. Scale-to-zero puede cambiar la latencia de una llamada futura. Cada caso conserva un `client_request_id` para buscar su evento de inferencia.

## S08-ROLLOUT · CP3

El agente principal es `agent/v1/responses`: no admite traffic splitting. Su actualización/restauración fija una versión única. Alias de Registry y tráfico son objetos distintos.

El canary se ejecuta en otro endpoint: `ais08-neptuno-rollout`, custom, modelo `neptuno_manuel_arguelles.ais08_lab.ventas_rollout`, versiones **1** y **2**, fuente UC real. Ambas preservan la cifra; cambia la etiqueta de revisión para observar enrutamiento, no se afirma mejora de calidad.

`reports/lab-custom-canary-verified.json` acredita endpoint **READY / NOT_UPDATING**, rutas configuradas **90/10**, **50 solicitudes**, **42 champion y 8 challenger**, todas con venta neta **116024.88** y fuente `gold.ventas_por_categoria_mes`. Se observaron ambas rutas activas. El 16% muestral challenger no invalida la probabilidad configurada 10%; tampoco prueba calidad superior ni equivalencia estadística.

`reports/lab-custom-rollback-verified.json` acredita la reversión posterior: **READY / NOT_UPDATING**, configuración **100% champion / 0% challenger**, **5 de 5 respuestas champion** con la cifra esperada y **`matches_saved_baseline=true`**. La comparación valida rutas y versiones servidas contra el snapshot guardado. Esta evidencia posterior al canary acredita rollback; el 100/0 que había observado el notebook antes del canary no lo habría probado. Fuente: [matriz oficial de capacidades](https://docs.databricks.com/aws/en/ai-gateway/overview-serving-endpoints).

## S08-APPS · CP4

Entrada: `app/` y permiso CAN_QUERY de identidad de la App sobre el endpoint. `reports/lab-app-http.json` acredita health HTTP 200, POST autenticado HTTP 200 con respuesta comercial esperada y fuente, y entrada inválida HTTP 400 con formulario conservado y texto escapado. Esto verifica el backend real y su respuesta, más allá de health.

`reports/app-visual.json` verifica el HTML de esa respuesta a anchos 390 y 1280: formulario/respuesta presentes y sin overflow. Es renderizado de HTML obtenido por HTTP, no prueba del inicio de sesión interactivo.

**SSO en navegador sigue pendiente:** `reports/app-browser.json` registra `pending_manual_consent` y `live_browser_flow_pass=false`. Chrome encontró el control de automatización y requiere continuación manual en Permission Requested. No se evadió autenticación. HTTP y QA visual no acreditan ese paso; la clase no se presenta como 100% validada.

Decisión: credenciales administradas en backend; browser no recibe PAT. Autenticación corporativa no convierte automáticamente permisos del service principal en permisos individuales. Ante 403 revisar principal/recurso, no pegar tokens al frontend.

## S08-INFERENCE · CP5

Entrada: payload real del endpoint. `reports/lab-flatten.json` y `reports/notebook-observed.json` registran fuente `neptuno_manuel_arguelles.ais08_lab.ais08_neptuno_payload`, destino `neptuno_manuel_arguelles.ais08_lab.inference_flat`, **16 filas raw y 16 planas**, IDs únicos y **cero errores de parseo**. El reporte de flatten correlaciona **6 de 6** client request IDs del último smoke (`all_ingested=true`). No confundir esos seis casos con las 16 solicitudes acumuladas.

Ejemplo real del notebook: `client_request_id=ais08-costos-7a967e9479e74f9aab8db7308cb6866f` corresponde al request ID `046d13e7-e04f-45bb-bd95-069aa23cd86f`, recibido **2026-09-27 03:02:43.228 UTC**, HTTP **200**, `tool_calls=0`, `tool_errors=0` y `parse_status=ok`. El JSON interno registra latencia del agente **317 ms**; la columna plana de Serving registra **328 ms**: son mediciones en capas diferentes, no una contradicción. El caso se abstuvo de calcular margen por falta de costos.

El checkpoint verifica también `lab/lab_parse_contract.sql` mediante tres fixtures: válido→`ok`, texto movido→`parse_error`, error HTTP→`http_error`. `CP5_parser_fixture=true` acredita extracción y clasificación de esa entrada sintética. Está **separada del tráfico real**, no se inserta para aumentar filas ni acredita Logging de red.

Otro caso del smoke, categoría ausente, tiene `tool_errors=1` esperado y respuesta sin cifra inventada. Por eso error de herramienta, error HTTP, fallo de parseo y aceptación de la respuesta son campos distintos. Recuperación: revisar esquema/rutas JSON, mantener errores/nulos y esperar entrega asíncrona; no convertir ausencia en cero.

## S08-MONITOR · CP6

Entrada: tabla plana y baseline `neptuno_manuel_arguelles.ais08_lab.inference_baseline`. En su corte de las 03:16 UTC, el notebook observa monitor **ACTIVE**, refresh **312794834798968 SUCCESS**, **28 filas profile** y **14 filas drift**. Son filas de métricas, no 42 solicitudes. El monitor usa `event_time` y ventanas de una hora.

Ejemplo leído en `reports/notebook-observed.json`: la ventana **2026-09-27 02:00–03:00 UTC** contiene **9 eventos** en el perfil de `latency_ms`, media **2635.7778 ms**; baseline tiene **1 evento**, media **2614.0 ms**. El drift contra baseline tiene `avg_delta=21.7778 ms` y `count_delta=8`. Esta diferencia de medias describe el ensayo; con una baseline de una fila no se concluye estabilidad productiva ni significancia estadística.

La lectura directa de `inference_flat` del mismo notebook abarca **16 solicitudes** entre **02:42:50.054 y 03:02:43.228 UTC**, media **2523.3125 ms** y **0 errores HTTP**. No contradice el perfil de nueve: la ventana, el momento de llegada y el refresh son diferentes. El perfil es un resultado materializado de un refresh anterior al contenido más reciente de flat. Registrar siempre ventana, count y refresh antes de comparar.

El refresh posterior congelado en `reports/lab-freeze.json` a las **03:27:21 UTC** ya incluye dos ventanas: **42 filas profile y 42 filas drift**, con SUCCESS. `reports/lab-monitor-values.json` conserva la primera ventana de 9 eventos y agrega **03:00–04:00 UTC: 7 eventos**, media **2378.7143 ms**, delta contra baseline **−235.2857 ms** y delta contra ventana anterior **−257.0635 ms**. La media de `tool_errors` en la nueva ventana es **1/7 = 0.142857**, consistente con el caso negativo de categoría ausente; no equivale a una tasa de fallos HTTP ni a siete errores. Las 42/42 filas son resultados por métrica y comparación, no 84 solicitudes. Se conserva el 28/14 del notebook como corte anterior, sin reescribir su evidencia.

Que no haya errores HTTP en ese conjunto no acredita verdad factual. Revisar errores de tools, muestras humanas y evaluación S06 para calidad; drift numérico no sustituye esa revisión.

## S08-GATEWAY · CP6

Ejemplo de decisión: separar payloads de inferencia, consumo de llamadas y facturación. Los logs del agente incluyen tokens, pero no toda la factura de Serving/App/SQL/embeddings/moderación. `lab/lab_costs.sql` ofrece la consulta de referencia sujeta a permisos; `reports/lab-security-smoke.json` registra tres controles aprobados (inyección conocida, exceso de longitud y safety administrado).

Esos tres controles no acreditan rate limiting ni exactitud de factura. La [matriz oficial](https://docs.databricks.com/aws/en/ai-gateway/overview-serving-endpoints) distingue soporte por tipo: no atribuir al agente capacidades del custom o del endpoint de modelo subyacente. Medición de uso/costos y comprobación del límite configurado quedan pendientes si no hay reporte específico.

## S08-BUNDLES · CP7

Entrada: bundle y valores de catálogo/esquema/modelo/versión/endpoint/App/warehouse. Acción observada: `databricks bundle validate` con target dev y CLI 0.288.0. `reports/lab-bundle-validation.json` informa validación aprobada, `deployment_executed=false` y `ci_executed=false`.

Interpretación: configuración validada no es pipeline CI ejecutado ni despliegue vía bundle. Ejemplo de gate: pruebas→evaluación→revisión→deploy dev→smoke→promoción autorizada→monitoreo. Dev/prod deben apuntar a recursos y permisos separados. Recuperación: corregir variable faltante antes de desplegar.

## S08-PROMPTS · CP7

Entrada: prompt `neptuno_manuel_arguelles.ais08_lab.neptuno_system`. Acción observada: original **4**, challenger **5**, promoción y restauración a **4**; `reports/lab-prompts.json` conserva el recorrido y `affects_existing_model=false`.

Interpretación: mover alias del prompt no modifica el texto ya empaquetado en el modelo. `lab-artifact-check.json` confirma prompt **4** en artefacto UC versión **4**. La cadena `agent_revision=s08-v2` es otra etiqueta del código, no contador del Registry. Para cambiar el prompt usado en servicio hay que registrar/servir el artefacto correspondiente y verificar respuesta/configuración.

## S08-CLOUD · CP8

Ejemplo resuelto conceptual: la función «exponer una versión para inferencia administrada» tiene equivalentes en Vertex AI Endpoints, Azure ML Online Endpoints y SageMaker Endpoints. Para migrar Neptuno se deben resolver identidad del backend, permisos sobre datos, formato de inferencia, escalado y métricas del proveedor. Una configuración JSON de Databricks no se traslada directamente.

Resultado de este ejercicio: el componente es comparable; la integración y costos requieren verificación por nube. No se ejecutó despliegue en esas tres nubes como parte del laboratorio.

## S08-CERT · CP8

Ejemplo original del banco: Ventas pide margen sin datos de costo. La respuesta correcta de la pregunta 1 es C: acordar la métrica disponible y declarar datos faltantes. Razón: renombrar venta neta o inventar costos crea una respuesta no sustentada. `CERTIFICACION.md` entrega otros once casos, razones y mapa de seis dominios.

Es preparación y diagnóstico, no resultado de examen ni evidencia de aprendizaje de la cohorte. El plan del alumno debe identificar dos brechas con práctica/fecha.

## S08-FINAL · CP8

Manifiesto del corte: artefacto UC 4 con prompt 4 y código cotejado; seis casos Serving aprobados según su contrato; App autenticada por HTTP con respuesta comercial y validación de entrada; render visual a 390/1280; 16 inferencias aplanadas y correlación 6/6 del smoke; monitor ACTIVE con refresh SUCCESS y métricas interpretadas; prompt 4→5→4; bundle validado sin despliegue/CI; canary custom 90/10 observado en 50 consultas y rollback 100/0 verificado con snapshot y cinco respuestas posteriores. El refresh final del monitor amplía el corte a 42/42 filas de métricas para dos ventanas, sin cambiar los resultados históricos del notebook.

`reports/import-validation.json` acredita importación real de la copia de alumno a Workspace personal, exportación del source coincidente y recuperación de configuración. La ejecución final del notebook está documentada en `reports/notebook-observed.json`: Job **35725070281647 SUCCESS**, modo **verificar**, inicio **2026-09-27 03:16:02.505 UTC**, fin **03:16:33.342 UTC**, SHA-256 **4dbb89479b8d04d4e22de55110c9e47297e6e5f3d91e3d76339d9f9a4edf9510**. Se ejecutó el source completo en ese modo, que inspecciona recursos y hace consultas reales; no equivale a ejecutar todas las mutaciones del modo crear. Los scripts y reportes separados acreditan despliegue/canary/prompts.

El cierre técnico está congelado en `reports/lab-freeze.json`: código del notebook/modelo/App sin cambios después de sus pruebas, cero procesos escritores pendientes y estado final del agente **READY / NOT_UPDATING**, versión **4**, sin configuración pendiente (`reports/lab-status.json`).

El consentimiento/SSO interactivo sigue **sin verificar**; no es fallo probado del backend, cuyas pruebas HTTP y render sí están documentadas. Por ese límite no se afirma clase 100% validada. Este ejemplo conserva resultados y pendientes; los jueces emiten el dictamen final sobre artefactos y alcance.

## Identidad de la evidencia consultada

Hashes calculados después del freeze técnico; cada reporte conserva su alcance y momento de observación.

| Archivo | SHA-256 al corte |
|---|---|
| `reports/lab-preflight.json` | `cc94ee643c7f21601892a81d22ebd1c5009c4d0c4ef74bc71e1a7b07ec06c312` |
| `reports/lab-package.json` | `fa3a03a3417cfe31d0f789b07779b4bf31d11a7b91adbb09853a06750a6f8b12` |
| `reports/lab-artifact-check.json` | `2a4bfe991602e4e1df81453999c7a87d72cb4bb8011517d6439a4db7ee1bb39a` |
| `reports/lab-smoke-serving.json` | `a17e3d574ffe015c1c9f691cd6c8555a8592f4766f6c953823de7e07d9afba1a` |
| `reports/lab-custom-rollout-package.json` | `01d9a959b5e83e4d2370a1d5141bad27ff7dec0b8dbc7535b91073c1eb03e8a9` |
| `reports/lab-app-http.json` | `a6881fafb7090ae7249b453f8aa8f63508e52e3406c296d179d4bae5627e4a70` |
| `reports/app-visual.json` | `cdf9918c351777604e55c473e3d524420705103a57dd902d1d18767721454032` |
| `reports/app-browser.json` | `7f2ea6e7cbbea310c582a8cdd83bb723067481d9587865c2c1bfafe89e508c67` |
| `reports/lab-flatten.json` | `0aa2c1ba3fbc8dacd0b43b4adbd6987b21af1f7600d8f59abde88347ee697134` |
| `reports/lab-monitor-verified.json` | `8bf585d71519ed799e1c302f26e8d8adcc756169051657c5e4ac51f9c8fc570f` |
| `reports/lab-monitor-values.json` | `dae3617751266d784fdf5c09512f32118f6e900c237c208e404e273573001435` |
| `reports/lab-monitor-refresh.json` | `da6117d9c5af03e7f7de2d57c58494e608bbe74d19b093dbb2a0c003ebc900d2` |
| `reports/lab-bundle-validation.json` | `903285fc8ece1079df40961261c34295414156c30200bfe65b759c63745a6563` |
| `reports/lab-prompts.json` | `73aeba26b53c00cceb0bb72612908cd407e87381b3e881675586bd5c92d9f80c` |
| `reports/lab-security-smoke.json` | `6dd49056cbdeb70a096b457157d3b75e411d0052b533a31afe199a758bedb9fa` |
| `reports/lab-unit-tests.json` | `04cd05e363d38c8f57fb8144d906c9f51cd73429fef5c602ec44503484224f53` |
| `reports/import-validation.json` | `3cc995274189ce1143d36fe970af82dded9169793e5d9964cca09053205a59d9` |
| `reports/notebook-observed.json` | `711645f87a6c0c4ca6552abc9861fcee1a1dd9030cb1a40725cbfe44edfb4e4a` |
| `reports/lab-custom-canary-verified.json` | `4bdcaa4a3b1c37444f8865751e6abfd0207118a67aad91eed7ecf4b5616a002e` |
| `reports/lab-custom-rollback-verified.json` | `56e1c2f1900933969ceddd206f46992b59b79ed78d2af7bbc67f3dcdaed7d4ad` |
| `reports/lab-rollout-before.json` | `437aa537e13e9a970ab5ca7102f25bdcbbe8118c76c032ccaec3530c8309b443` |
| `reports/lab-freeze.json` | `2cd3661a6b4fc3511011c23cd46706ff3fe095bc5874e2c3ebbbf60b6d034213` |
| `reports/lab-status.json` | `b2ddd85a3c1f9d3853538a0f7c40c0fa3bb70cad908f2a74b19bcecbac284cd9` |
| `reports/lab-source-hashes.json` | `35d1e9101b406a0785c51e8576ee1600ab714ef3915488777cac6e9860fba0f3` |
