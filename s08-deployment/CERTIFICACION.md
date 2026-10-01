# Preparación de certificación · diagnóstico final

Guía oficial consultada el26 de septiembre de 2026: [Databricks Generative AI Engineer Associate, marzo de 2026](https://www.databricks.com/sites/default/files/2026-03/Databricks-Certified-Generative-AI-Engineer-Associate-Exam-Guide-Mar26.pdf), vigente desde el 18 de marzo de 2026. Informa 45 preguntas puntuables,90 min, USD200, vigencia 2 años y recomienda 6 meses de experiencia. Verifica la versión y condiciones antes de inscribirte. No extrapoles un puntaje de este diagnóstico a probabilidad de aprobar.

Los seis dominios de la guía y nuestro mapa pedagógico (el mapa es elaboración del curso):

| Dominio | Dónde lo practicamos | Evidencia para repasar |
|---|---|---|
|Design Applications|S03,S05,S08|Contrato de entrada/salida y elección de modelo/herramientas|
|Data Preparation|S01,S02,S04|Delta, limpieza, chunks y recuperación|
|Application Development|S03–S07|RAG, agente, evaluación y controles|
|Assembling and Deploying Applications|S04,S05,S08|Índice, tools, registro, endpoint y App|
|Governance|S01,S07,S08|ACL, datos/licencias e identidades de ejecución|
|Evaluation and Monitoring|S06,S08|Benchmark, trazas, métricas y monitoreo online|

Esto conecta el curso con los dominios; **no certifica que se haya dominado cada objetivo del examen**. Usa la guía oficial para detectar objetivos que necesiten estudio adicional.

## Doce preguntas originales de práctica

Redactadas para Neptuno; no son preguntas filtradas ni una reproducción del banco oficial. Una respuesta correcta por pregunta. En clase: 1–4. Después: 5–12, 20 min estimados. Antes de abrir las respuestas, anota letra, razón y por qué descartas una alternativa.

### 1 · Design Applications

Ventas pide «margen mensual» pero el modelo de datos contiene precio, cantidad y descuento, sin costo. ¿Qué contrato inicial es defendible?

A. Llamar margen a la venta neta. B. Estimar el costo con conocimiento del LLM. C. Acordar venta neta como métrica disponible y explicitar que margen necesita datos de costo. D. Aumentar la temperatura.

### 2 · Data Preparation

La comparación anual cae porque2026 tiene un último mes parcial. ¿Qué se debe corregir primero?

A. La ventana y completitud de datos de comparación. B. El color del dashboard. C. El modelo con más parámetros. D. El número de reintentos HTTP.

### 3 · Application Development

Un agente contesta precios correctamente, pero una instrucción en un documento le pide ejecutar una herramienta administrativa. ¿Qué control evita que ese texto amplíe privilegios?

A. Más tokens de contexto. B. Lista de herramientas y permisos mínimos aplicada por el backend. C. Solo una advertencia en la UI. D. Permitir cualquier función y auditar después.

### 4 · Assembling and Deploying Applications

El modelo servido apunta a la versión7. Se cambia el alias champion a8 y no cambia la respuesta del endpoint. ¿Cuál es la explicación más probable?

A. El alias obliga a reiniciar el catálogo. B. Las versiones desaparecen al mover el alias. C. El endpoint conserva la versión configurada y necesita una actualización explícita verificada. D. El tráfico cambia solo después de exactamente10 min.

### 5 · Governance

Una App autentica a cada vendedor pero su backend usa un service principal con acceso a todos los territorios. ¿Qué se puede afirmar?

A. El login garantiza filtro territorial. B. El browser debe recibir el token del principal. C. No necesita permisos porque está dentro de Databricks. D. Hay que diseñar autorización por usuario o restringir la identidad compartida; el login solo no prueba aislamiento.

### 6 · Evaluation and Monitoring

La latencia subió y cambió la distribución de longitud de preguntas, pero no hay respuestas etiquetadas recientes. ¿Cuál es la lectura válida?

A. El drift demuestra que todas las respuestas son incorrectas. B. Hay cambio operativo/de entrada que requiere investigación y evaluación de calidad. C. Hay que borrar la baseline. D. El endpoint está necesariamente caído.

### 7 · Design Applications

Para una consulta sobre ventas estructuradas y condiciones de devolución documentales, ¿qué diseño inicial permite explicar la procedencia?

A. Inventar todo en una llamada sin tools. B. Consultar solo el índice vectorial para sumar ventas. C. Separar herramienta SQL gobernada y recuperación documental, integrar resultados con fuentes. D. Consultar internet para todas las cifras internas.

### 8 · Data Preparation

Cada chunk de una política mezcla varias secciones inconexas y la búsqueda devuelve texto parcialmente relevante. ¿Qué experimento ayuda a decidir?

A. Dividir por límites semánticos y comparar recuperación sobre las mismas preguntas/referencias. B. Cambiar al azar el conjunto de preguntas en cada prueba. C. Quitar los identificadores de fuente. D. Medir solo si el notebook termina.

### 9 · Application Development

Dos modelos responden Neptuno con calidad comparable; uno cuesta más y supera la latencia máxima del caso. ¿Cómo escoger?

A. Elegir siempre el más grande. B. Seleccionar con métricas congeladas y restricciones de calidad, costo y latencia del caso. C. Elegir el que produzca más palabras. D. Escoger por nombre comercial.

### 10 · Assembling and Deploying Applications

El release de App cambió código y prompt. Para reconstruirlo la próxima semana, ¿qué información mínima se debe conservar?

A. Solo captura de la portada. B. El alias mutable actual. C. Commit, dependencias, configuración de entorno, versión del modelo y del prompt, pruebas y evidencia del despliegue. D. El nombre del último usuario.

### 11 · Governance

Se encuentra un documento comercial útil para RAG sin licencia ni permiso documentado. ¿Qué decisión corresponde?

A. Asumir permiso por estar en internet. B. Cambiar el nombre del archivo. C. Incorporarlo y borrar la fuente. D. Resolver permiso/uso antes de incorporarlo o usar una fuente autorizada.

### 12 · Evaluation and Monitoring

Inference Tables contiene respuestas, pero no el importe final facturado de cada solicitud. ¿Qué conviene hacer para controlar gasto?

A. Equiparar longitud en caracteres a dólares. B. Relacionar métricas de consumo y precios aplicables, revisar facturación real y fijar límites; mantener separados payload y uso. C. Desactivar los logs para que el LLM sea gratuito. D. Usar latencia como único costo.

## Respuestas razonadas

1. **C.** El contrato debe usar datos disponibles. A cambia el significado; B inventa una entrada faltante; D no añade costos.
2. **A.** Una ventana incompleta produce una comparación inválida aunque el código y el modelo funcionen. Los otros cambios no corrigen el denominador temporal.
3. **B.** El backend controla capacidad real de acción. Advertencias y contexto no sustituyen autorización; auditar después no previene daño.
4. **C.** Alias y configuración de tráfico son objetos distintos. Hay que inspeccionar la versión efectiva, actualizar y verificar; no existe espera fija que garantice promoción.
5. **D.** Autenticación identifica; autorización limita. La identidad de la App puede tener más permisos que el usuario. No se publican tokens para resolverlo.
6. **B.** Drift describe cambio, no verdad de la respuesta. Revisar segmentos, errores y casos con humanos/jueces permite decidir si hay degradación.
7. **C.** Cada fuente tiene su herramienta y control. El SQL calcula agregados; la recuperación trae políticas. Integrarlas no elimina la obligación de citar y abstenerse si falta evidencia.
8. **A.** Cambia una decisión manteniendo evaluación comparable. B confunde efecto del cambio y dificultad; C elimina trazabilidad; D solo mide ejecución.
9. **B.** La elección optimiza el caso de negocio con un piso de calidad. Tamaño y verbosidad no prueban utilidad.
10. **C.** Identificadores inmutables y configuración permiten reconstrucción. Un alias puede cambiar; captura y usuario no describen el artefacto.
11. **D.** Accesibilidad pública no acredita derecho de uso. Cambiar nombre o borrar procedencia empeora trazabilidad.
12. **B.** Payload, uso y facturación responden preguntas diferentes. Límites previenen exceso; ninguna de las otras opciones estima gasto con rigor.

## Plan personal de cierre

Para cada dominio marca: puedo explicar / puedo ejecutar / necesito ayuda. Elige dos brechas, un artefacto verificable por brecha y fecha de repetición. Reproduce el laboratorio sin mirar la solución, explica un fallo y su recuperación, luego contrasta con todos los objetivos de la guía oficial. Conserva dudas y contraejemplos; acertar doce letras sin razonar no demuestra preparación.
