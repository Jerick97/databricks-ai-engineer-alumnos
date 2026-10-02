# Framework de análisis de caso reconstruido de tu experiencia

**Propuesta v0.1, derivada por ingeniería inversa.** Las nueve etapas de preparación, las nueve capas de arquitectura y la escala auxiliar 0–8 son recuperadas; este instrumento de análisis es nuevo. No atribuirlo a Databricks ni presentarlo como validado comercialmente. Se deriva de comportamientos, defectos y mediciones en los casos del inventario, no solo de sus descripciones.

## Método de reconstrucción

Unidad de análisis: una decisión o tarea del usuario, no un repositorio. Una familia puede tener varios repos, versiones y canales. Se triangula declaración → código/contrato → prueba/reporte → límite de la evidencia. Lo no localizado se marca desconocido; no se concluye inexistencia global. La presencia de tests no significa tests ejecutados ni éxito operacional.

Niveles de evidencia: **D** declarado; **C** código inspeccionado; **T** reporte histórico de prueba; **O** operación observada en esta investigación; **H** aceptación del especialista. En esta auditoría se reúnen D/C/T; no se ejecutaron nuevamente los agentes para otorgar O/H. La revisión de GitHub verifica procedencia de algunos repos, no calidad ni autoría exclusiva del software contenido.

De cada incidente se extrae una pregunta preventiva, un artefacto y una condición de avance. La trazabilidad está en [hallazgos](04-hallazgos-forenses.md) y los informes de `evidence/`.

## Instrumento: doce decisiones antes de diseñar el agente

| ID | Decisión que hay que tomar | Qué pedir/observar | Artefacto verificable | Qué impide avanzar | Antecedente |
|---|---|---|---|---|---|
| A01 | Usuario, dueño y decisión | Quién hace qué hoy y quién acepta la salida | Mapa del proceso actual, dueño y entrevista con caso concreto | No hay responsable ni decisión identificable | N1 evaluador; TYV |
| A02 | Valor y alternativa simple | Tiempo, volumen, errores, revisión y costo actuales | Baseline medido y comparación reglas/búsqueda/SQL/LLM | Se promete ahorro sin medir proceso manual | TYV; Tesis Buscador |
| A03 | Alcance y unidad de trabajo | Qué entra/sale, entidades, excepciones, periodo | Contrato de alcance, preguntas ancla y exclusiones | “Todas las normas” o “todo el negocio” sin universo | Libun; webinar Genie |
| A04 | Fuentes y autoridad | Origen, acceso, licencia, cobertura, actualización | Inventario de fuentes y cadena original→derivación | Fuente no accesible, corpus incompleto sin advertencia | PL00098; SBS S05 |
| A05 | Verdad y semántica temporal | Qué cuenta como correcto, a qué fecha, con qué versión | Diccionario, relaciones, fechas y ejemplos resueltos por experto | Gold ambiguo, versión anterior desconocida, fechas mezcladas | Ianbal; N1 universo |
| A06 | Separación de responsabilidades | Qué es extracción, cálculo, recuperación, interpretación y acción | Flujo y contratos por etapa, alternativa sin agente | Se deja al modelo decidir reglas que deben ser deterministas | N1 routing; S05 SBS |
| A07 | Autonomía, permisos y autoridad humana | Qué puede leer, proponer, escribir y aprobar | Matriz actor×acción×recurso, estados HITL | No se sabe quién autoriza una consecuencia | Genie OBO; LangGraph triage |
| A08 | Contrato de respuesta y abstención | Qué necesita el usuario para confiar y actuar | Schema con evidencia, faltantes, límites y estados de error | HTTP200 se toma como respuesta correcta; no hay abstención | Research citas; El Chambas |
| A09 | Riesgos y errores costosos | Falsos positivos/negativos, inyección, acceso, omisiones | Taxonomía de fallos, escenarios adversariales, controles | Error crítico sin control ni responsable | Gemelo; TYV; N1 gate |
| A10 | Evaluación y oráculo | Gold experto, datos reservados, calibración de jueces | Protocolo congelado, métricas por error y regresiones | Oráculo defectuoso o evaluador ve respuestas de ajuste | Ianbal; TYV; research |
| A11 | Economía y operación | Costos de datos/modelo/humano, disponibilidad, soporte | Presupuesto por expediente y runbook con trazas | Costo de revisión omitido o nadie puede operar/recuperar | QhatuData; S08; Budgeted Supervisor |
| A12 | Prueba decisiva y criterio de parada | Qué resultado falsaría la hipótesis y cuándo | Piloto pequeño con umbrales, dueño, fecha y decisión | Demo sin aceptación, sin plan de abandono o sin límite | PersonaPlex; N1 alternativas refutadas |

Cada respuesta debe llevar **hecho / evidencia / inferencia / pendiente**, fecha, responsable y nivel D/C/T/O/H. No completar campos vacíos con supuestos invisibles. Un valor desconocido es parte del diagnóstico.

## Entrevista: ordenar preguntas por decisiones

1. Muéstrame el último caso real: entrada, pasos, resultado, quién lo aprobó y cuánto demoró.
2. ¿Qué decisión cambiaría si el agente funcionara? ¿Qué queda a cargo de una persona?
3. ¿Qué error es peor: omitir, inventar o tardar? Dame un ejemplo de cada uno.
4. ¿Qué fuentes y versiones usaste? ¿Dónde está la respuesta correcta y quién puede adjudicarla?
5. ¿Qué casos no debemos resolver? ¿Qué información falta o no podemos consultar?
6. ¿Cómo demostraríamos una mejora frente a reglas, SQL o el proceso manual?
7. ¿Quién lo usará, revisará, pagará, mantendrá y apagará si falla?

La entrevista produce A01–A12; no se exige al cliente hablar de embeddings, modelos o multiagentes.

## Selección de mecanismo

| Necesidad demostrada | Primera alternativa que probar | Escalar cuando… |
|---|---|---|
| Detectar cambios exactos entre textos/versiones | Hash, parsing y diff estructural | Renumeración o diferencias de significado requieren interpretación |
| Contar, filtrar y cruzar hechos definidos | SQL y consultas verificadas; Genie como interfaz | La pregunta necesita contenido no estructurado no extraído |
| Encontrar pasajes | Búsqueda lexical/estructural, luego híbrida si mejora | Evidencia de recuperación muestra ventaja sobre baseline |
| Explicar diferencias sustentadas | Síntesis LLM con contrato y citas | Su calidad adicional supera costo/latencia/revisión |
| Ejecutar acciones | Workflow determinista con validación | Solo si decisiones dinámicas de tool aportan valor medido |
| Resolver aplicabilidad normativa ambigua | Especialista con expediente y evidencia | No delegar autoridad por disponer de un modelo más potente |

No hacer obligatorio multiagente. “Agente Genie” describe una interfaz/capacidad deseada; A01–A12 determinan qué debe existir debajo para cumplir la tarea.

## Criterios de salida del análisis

**Listo para prototipo:** caso y dueño definidos; una muestra autorizada y verificable; criterio de verdad adjudicable; error crítico identificado; contrato de salida; prueba que puede refutar la propuesta.

**Investigar antes:** hay valor plausible, pero falta acceso a versiones, baseline, experto o viabilidad del mecanismo. Nombrar el bloqueo y la evidencia que lo levantaría.

**No construir todavía:** no existe decisión útil, una automatización simple cubre el caso, el riesgo residual no tiene dueño o no puede medirse el resultado. No sumar puntajes para compensar una falta de autoridad o de fuente.

## Relación con los otros marcos

El análisis decide **si y qué construir**. Las nueve etapas de preparación revisan **qué preparar para construir y operar**. Las nueve capas de arquitectura ubican **dónde se resuelve cada responsabilidad durante una solicitud**. La escala auxiliar 0–8 indica **hasta dónde llegó con evidencia**. Las pruebas por capa y tarea deciden si puede avanzar. Son cuatro instrumentos relacionados, no una única lista de nueve pasos.

## Cómo validar este framework nuevo

Aplicarlo retrospectivamente a N1, SBS, TYV e Ianbal: debe detectar los defectos observados sin usar su solución como pregunta. Después usarlo prospectivamente con un caso nuevo y registrar si anticipó bloqueos, qué preguntas sobraron y qué faltó. Que sea coherente con casos históricos no demuestra todavía eficacia predictiva ni retorno económico.
