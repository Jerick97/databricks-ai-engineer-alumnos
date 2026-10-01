# SK10 — respuestas HTTP ajenas al contrato JSON209

Estado: refinamiento provisional de SK10 0.1.5, implementación local; no desplegado, no aceptación E2E. Aplicado mediante skill-creator-z y ciclo RED/GREEN; revisión independiente del coordinador en `runs/sk09-api-response-209-review.json`.

## Investigación y alcance

Consulta2026-09-29: [Fetch Living Standard](https://fetch.spec.whatwg.org/), actualizado2026-09-21, secciones Body.json, Request.redirect y opaque-redirect filtered response. `json()` puede rechazar cuerpos inválidos; el manejo manual de redirects permite detener su seguimiento y el navegador puede entregar `opaqueredirect` sin estado legible. Confianza alta en contrato, cobertura local mediante Response de Node; no demuestra comportamiento del proxy real.

Hecho de código: `src/sbs/webapp/static/app.js` invocaba `r.json()` antes de verificar estado HTTP/tipo. La excepción del parser llegaba al chat. Baseline209 reproduce el defecto con HTML y JSON malformado. El productor de la respuesta original de `/api/ask` no fue capturado. El coordinador observó posteriormente HTML “Databricks App Not Available” en `/api/catalog`, compute Stopped y limpieza del ensayo207; evidencia separada: `runs/sk12-html-unavailable-209-observation.json`. Eso explica el estado observado actual, sin demostrar el cuerpo original del POST. El coordinador además halló deadline vencido en source199: reiniciar compute por sí solo no rehabilita el chat.

Alternativas: reutilizar Fetch nativo conserva dependencias y contrato; añadir una biblioteca HTTP no elimina la necesidad de validar tipo/estado. Analizar HTML o seguir enlaces de login expondría contenido no confiable y no resuelve disponibilidad. `redirect: manual` evita reenviar automáticamente un POST bajo307/308; no reintentar ni modificar autenticación.

## Instrucciones reutilizables

Activar ante errores JSON/HTML, redirecciones o mensajes HTTP crudos en UI; no ante calidad normativa de respuestas válidas. Verificar estado/redirección y Content-Type antes de JSON; aceptar JSON con parámetros y tipos application/*+json. Rechazar cuerpo vacío, JSON inválido, null, arrays y escalares en estos endpoints que exigen objetos. Mantener timeout distinguible, incluso durante consumo del cuerpo, y liberar el temporizador en todas las ramas.

Mostrar errores fijos accionables en español para sesión, permisos, cuota, indisponibilidad, red, formato y redirección. No reflejar HTML, detail no confiable, URL de redirección, errores del parser o tokens. Preservar método, body y CSRF; nunca repetir automáticamente POST. Mensajes de sesión deben hablar de comprobación, sin afirmar expiración por un HTML200. No declarar chat restaurado por robustecer el cliente.

## Requisitos, riesgos y evaluación

| Riesgo/requisito | Corrección | Prueba |
| --- | --- | --- |
| HTML200,502,503 y JSON inválido causan excepción cruda | Validar estado/tipo y capturar parseo | Response con HTML y JSON roto |
| Detail contiene token/HTML | Mensajes locales fijos | HTTP401/403/404/429/500 con detalle secreto |
| Redirección vuelve a enviar POST | Fetch manual, rechazar3xx/opaque/redirected | Opciones y una sola llamada |
| Rechazar JSON normal por parámetros/case | Normalizar tipo MIME | JSON charset, Application/JSON, problem+json |
| Lectura abortada confundida con formato | Conservar AbortError | Abort al fetch y al consumir JSON |
| Confundir fix local con restauración productiva | Separar evidencia | No despliegue, no nuevo deadline ni permisos |

Harness: `node --test tests/unit/test_api_response_209.cjs` evalúa declaraciones reales del helper de app.js, con Response reales y frontera fetch sintética sin red. RED: 5/25 pasan; GREEN: 25/25 pasan. Evidencia nueva `runs/sk10-api-response-209-{red,green}.txt`. Los fixtures no acreditan navegador, SSO, chat operativo ni recuperación de disponibilidad. Activación y presión (“despliega/reintenta aunque el ensayo venció”) se documentan como límites, no como benchmark conductual ejecutado. Tiempo/coste del agente no medido; latencias locales constan en salida Node. Revisión independiente del coordinador: 25 tests y sintaxis PASS, sin hallazgos bloqueantes; `runs/sk09-api-response-209-review.json`. Revisión humana y E2E productivo pendientes. Regresión Python pertinente: 12 tests de webapp/cloud webapp PASS, `runs/sk10-api-response-209-python-tests.txt`.
