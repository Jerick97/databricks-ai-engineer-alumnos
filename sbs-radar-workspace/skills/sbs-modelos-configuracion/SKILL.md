---
name: sbs-modelos-configuracion
description: Selecciona, fija o comprueba modelos y límites de embedding, reranking y generación de SBS Radar. Usar ante cambios de modelo, incompatibilidad, presupuesto de tokens o configuración de endpoints; no para comparar disposiciones ya extraídas ni diseñar toda la recuperación.
---

# SK05 — Modelos y configuración

Versión 0.1.6 provisional, creada mediante skill-creator-z tras baseline. [Brief](references/research-brief.md), [riesgos](references/requirements-risks.md), [casos](evals/cases.json).

## Contrato

Entrada: caso/spec, corpus y estrategia RAG, candidatos con procedencia, capacidades observadas y límites. Salida: ModelBundle SK01 más informe de preflight, mediciones, hashes y pendientes. Separar selección documentada, acceso real e inferencia verificada.

## Ejecución

1. Reutilizar fuentes y estrategia-rag indicada en AGENTS. Congelar identidad de corpus, extractor, chunking, modelo/revisión, tokenizer/revisión, dimensión, prefijos/roles y normalización. Un endpoint mutable requiere configuración observada y fecha; no inventar hash de pesos remotos. Separar nombre de endpoint, identidad de configuración observada e identificador `model` devuelto por inferencia. Fijar este último como `expected_response_model` exacto en el bundle a partir de evidencia: no deducirlo del endpoint, aceptar prefijos amplios ni cambiarlo silenciosamente cuando falla la validación.
2. Seleccionar candidatos por español, span completo, recursos, licencia y privacidad. La oferta del proveedor o una preferencia histórica no demuestra disponibilidad ni calidad SBS. Comparación normativa literal corresponde SK03.
3. Contar la entrada total con tokenizer compatible, incluidos contexto, prefijos y tokens especiales. Comprobar límite antes de inferir; no truncar silenciosamente. Si excede, comparar candidato alternativo o adaptar explícitamente los límites de spans con continuidad/offsets y nueva versión. Registrar también exclusiones. Aplicar límite de pares query+passage al reranker y reservar salida en generación.
4. No mezclar vectores de modelos/revisiones/prefijos diferentes por tener igual dimensión. Un cambio de identidad requiere bundle/índice distinto. Reutilizar artefactos solamente con hashes verificados.
5. Inspeccionar capacidades existentes con cliente normal y permisos mínimos: estado/configuración del endpoint y runtime. No imprimir tokens, variables secretas ni excepciones arbitrarias. Distinguir documentado, observado y probado. No crear recursos cloud a partir de un presupuesto meramente propuesto.
6. Medir muestras controladas con identidad del modelo y coste/uso observables dentro del alcance autorizado. Validar cantidad, dimensión y valores finitos de embeddings y scores; error de servicio no equivale a vector cero o respuesta vacía. Antes de validar respuestas, conservar diagnóstico con etapa, modelo reportado/esperado, cantidad, dimensiones, índices, uso y latencia mediante campos permitidos; nunca cuerpos arbitrarios ni secretos. Distinguir rechazo del servicio de fallo local de validación y de fallo de persistencia. Una nueva prueba tras un fallo requiere alcance explícito y no debe exceder la cuota original mediante reintentos ocultos. No sustituir modelo real por hash, TF-IDF ni fixtures sin etiqueta.
7. Separar precio publicado, estimación y coste observado; desconocido=null, nunca cero. Guardar fuente/fecha/moneda/unidad y límites de ejecución. La selección no autoriza por sí misma gasto o publicación.
8. Comparar con corpus/consultas/qrels congelados (SK09). Si cambia corpus/chunking/prefijos junto con modelo, reportar paquete; no atribuir causalidad a un factor. La fidelidad del índice no demuestra relevancia semántica.
9. Si el encargo incluye construcción de código, implementar preflight/manifest en src/sbs/models/ con pruebas RED/GREEN de presupuesto, identidad y resultados inválidos. Probar adaptadores reales antes de declarar integración. Guardar runs con skill/versión/hash y entradas; no modificar bundles previos.

10. En ejecución local, fijar archivo de pesos/hash, backend/proveedor, versión del runtime, sistema y arquitectura observados además del modelo/revisión/tokenizer. Los nombres de archivos orientados a CPU no demuestran pesos distintos: comparar hashes. Un candidato explícito rechaza un target incompatible; no sustituir selección legacy silenciosamente. Distinguir smoke de equivalencia numérica, estabilidad de ranking y calidad en holdout. Conservar el gate numérico fallido con su tolerancia original aunque mejore otro gate; no convertir tolerancia arbitraria de smoke en requisito de calidad ni atribuir diferencias a instrucciones CPU sin prueba. Una muestra reutilizada de tres consultas sirve como regresión, no como aceptación independiente.

## Refinamiento

Un fallo real produce caso de regresión y cambio en esta skill. Preservar baseline, salidas y coste no medido. Estado provisional hasta prueba real del bundle seleccionado; aprobación técnica no es certificación jurídica.

## Refinamiento073 — selección independiente de generación

Una observación HTTP200/JSON-smoke sólo acredita acceso y formato de ese ensayo. Seleccionar generación en configuración exclusiva del servidor, separada del bundle de embeddings para conservar identidad de vectores/índice. Fijar endpoint, expected_response_model exacto y archivo/hash de observación; rechazar pendiente, ausente, identidad distinta o límites inválidos sin fallback al endpoint anterior. No aceptar selección desde mensajes o parámetros del cliente.

La configuración073 selected_for_controlled_trial pasa a initialize_models por defecto; esto habilita un candidato para ensayo, no promoción de calidad ni aceptación del producto. Contar entrada en caracteres explícitamente si no hay tokenizer compatible; ese guard no se presenta como medición de tokens del proveedor. Cuotas4requests/5000outputtokens/120000inputchars se aplican por instancia; el runner añade admisión durable para impedir reiniciar cuota.

## Refinamiento077 — timeout no es indisponibilidad ni prueba causal de tamaño

Un timeout sin HTTPstatus/usage sólo demuestra que el cliente no recibió la respuesta en su ventana. Conservar presupuesto consumido y petición real; no inferir endpoint deshabilitado, fallo de autenticación o causalidad por tamaño. Comparar con observaciones previas:073Qwen respondió entradas mayores en8.8–15.3s,075menor agotó60s; variabilidad backend/cola/salida siguen siendo hipótesis sin telemetría.

Para discriminar con mínimo cambio, preparar selección alternativa explícita con endpoint/model/hash de observación y presupuesto nuevo revisado, sin fallback automático.077 conserva paquete075/preguntas/prompt/output5000/timeout60 y prueba Llama observado072; default073Qwen permanece intacto. Una muestra de latencia o calidad no demuestra superioridad general. El parámetro de ruta de selección es dependenciaPython del servidor, no entradaHTTP/cliente.


## Refinamiento080 — transportar la selección sin promoverla

La selección de ensayo077 sólo llega a Apps por configuración del servidor con allowlist073/077, entrada `app080.py` y adaptador que fija `generation_selection_path` antes de la inicialización lazy. Conservar `app.py`, default073 y runtime077; no convertir un resultado favorable en fallback ni promoción global. Incluir en el snapshot selección y observación por hash, manteniendo la identidad del bundle de embeddings.

Para empaquetar/desplegar exigir muestra real revisada PASS_CONTROLLED_SAMPLE, cuatro respuestas del mismo plan/admisión077 e identidad endpoint/model exacta; ligar todos los bytes probados al stage. HTTP200, prueba sintética, selección explícita o smoke072 no sustituyen calidad SBS ni aprobación del paquete. El código de conexión080 posterior requiere revisión de despliegue independiente. [Contrato compartido](../sbs-despliegue-e2e/references/app-selection-080.md).
