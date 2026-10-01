# Plan de creación de skills — Skill Creator Z

Fuente obligatoria: [skill-creator-z](/Users/macdenix/clawd/openclaw-codex/openclaw-workspace/skills/skill-creator-z/SKILL.md), localizada y leída el 2026-09-27 mediante búsqueda local. Usar esta misma fuente por cada skill; no sustituirla por el skill-creator genérico. El índice antiguo no la encontraba y su ruta de reconstrucción estaba obsoleta; no se interpretó eso como ausencia.

Estado: trece skills planificadas, ninguna creada ni validada. Esta entrega prepara sus contratos y expedientes; la ejecución de RED/GREEN/REFACTOR pertenece a su construcción, antes de implementar cada parte del agente.

## Expediente obligatorio por skill

1. Fase 0: capacidad, triggers positivos/negativos, entradas, salidas, runtime, límites, criterios y supuestos específicos.
2. Fase 1: brief de dominio con fuentes primarias y alternativas. Reutilizar IDs del registro compartido; investigar solo brechas. Separar hechos/inferencias/decisiones y registrar fuente, fecha, versión y confianza.
3. Fase 1.5: requisitos/riesgos, dependencias, no aplicación y plan de evaluación. Documentar por qué se crea una skill separada y qué reutiliza.
4. RED: ejecutar casos sin la nueva skill, conservando salida bruta y fallos. No inventar un baseline a posteriori. La misma configuración y fixtures sirven en GREEN.
5. GREEN: escribir SKILL.md conciso, referencias enlazadas y scripts deterministas que resuelvan los fallos observados. Los prompts del agente/jueces son recursos versionados de la skill responsable, no instrucciones sueltas fuera del proyecto.
6. REFACTOR: ejecutar casos nuevos y presión; corregir sin sobreajustar. Un cambio sustantivo requiere repetir evaluación afectada.
7. Revisión paralela: activación, veracidad y permisos con revisores independientes y contexto mínimo. Registrar alcance → hallazgo → evidencia → severidad → acción; no convertir tres revisiones parciales en auditoría total.
8. Benchmark: assertions por caso, pass rate, delta, tiempo, herramientas y tokens cuando estén disponibles; datos ausentes como no medidos. En nivel strict incluir pressure testing, microtests de wording, triggering, comparación ciega y repeticiones para varianza; no calcular varianza de una sola muestra.
9. Hardening: tabla fallo → causa → corrección → prueba; revisar licencias, privacidad, fuentes no verificadas, prompt injection, acciones externas y efectos irreversibles.
10. Entrega: SKILL.md, brief, matriz, evals, baseline, resultados, benchmark, changelog y estado provisional/validada-en-alcance/producción. Solo el alcance probado puede llamarse validado. Instalar o registrar sin sobrescribir skills ajenas.

Conjunto mínimo por skill: dos casos nominales distintos, uno de entrada insuficiente, uno adversarial/de presión y un par de activación/no activación. Separar los ejemplos utilizados al redactar de los nuevos casos de generalización. Establecer assertions antes de GREEN. Evidencia de un baseline ya correcto también se conserva; no inflar mejoras.

## Contratos individuales para ejecutar /skill-creator-z

Cada fila es un encargo de creación distinto, no una skill ya escrita. La fuente y secuencia anteriores se aplican por separado a las trece.

| ID / nombre | Activación y salida | Contexto a reutilizar / brecha concreta | Eval que debe discriminar / nivel |
|---|---|---|---|
| SK00 `sbs-contexto-ejecucion` | Retomar/encadenar tarea SBS; produce ContextBundle y registro de dependencias. No responde preguntas jurídicas. | Spec, STATE, source-hashes, inventario y fuentes existentes. Brecha: resolver hashes y capacidades reales sin recopilar secretos. | Solicitud “busca otra vez todo” con fuente vigente: reutiliza; fuente cambiada: invalida descendientes. Standard. |
| SK01 `sbs-contratos-gobierno` | Crear/evolucionar contratos SBS; produce schemas, diccionario, roles y estados. | Spec A01/A05/A07/A08, docs06/11. Brecha: contratos ejecutables y migración compatible. | “Apruébalo sin revisor para seguir”: permite conversación, rechaza estado institucional aprobado. Strict. |
| SK02 `sbs-fundacion-datos` | Incorporar/actualizar corpus oficial; entrega manifiesto, originales, spans y cobertura. | Portal SBS, auditoría del laboratorio de curso S05 (evidence/sbs-forensic-genie.md), estrategia de spans. Brecha: corpus real de ambas familias y calidad de tablas/OCR. | Anexo ausente, PDF modificado en misma URL, reintento y redirección externa; no rellena con fixtures. Strict. |
| SK03 `sbs-versiones-cambios` | Alinear/comparar versiones completas; produce relaciones, diferencias y temporalidad sustentada. | Laboratorio de curso S05 como patrón (evidence/sbs-forensic-genie.md), spec A05, contratos. Brecha: 1:n/n:1, correcciones y reconstrucciones. | Renumeración idéntica y efecto diferido; evita alta/baja o vigencia inventadas. Strict. |
| SK04 `sbs-rag-hibrido` | Construir/evaluar recuperación citable; produce índice/config y EvidencePack. | estrategia-rag, documentación híbrida/RRF/reranking ya localizada. Brecha: adaptación SBS, qrels y controles observables. | Artículo exacto vs paráfrasis; versión anterior de menor ranking; no doble RRF, no “sin cambios” por top-k vacío. Strict. |
| SK05 `sbs-modelos-configuracion` | Seleccionar/versionar modelos; produce ModelBundle y comparación medida. | estrategia-rag y su evidencia fechada, requisitos de español/citas. Brecha: oferta/limites/precios actuales y capacidades del workspace. | Modelo no cabe en presupuesto/tokenizer: registra adaptación o candidato alternativo, no recorta silenciosamente. Standard. |
| SK06 `sbs-genie-datos` | Configurar Genie sobre tablas curadas; produce configuración, consultas de referencia y pruebas. | Documentación Genie, antecedentes Ianbal y clase de curso S08 y spec. Brecha: API/permisos y warehouse real del proyecto. | Resultado SQL vacío por acceso no se afirma “no hay normas”; warehouse_id faltante detectado en preflight. Strict. |
| SK07 `sbs-conversacion-orquestacion` | Construir rutas y memoria contextual; entrega orquestador y contrato Answer. | Spec consultas 1–16; patrones forenses, contratos y packs Genie/RAG. Brecha: resolución de referencias y conflicto entre fuentes. | “Ese punto” tras cambio de familia, pregunta antes de revisión experta, conflicto SQL/RAG; responde o aclara con evidencia. Strict. |
| SK08 `sbs-guardrails-permisos` | Diseñar/aplicar controles SBS; entrega políticas, validadores y pruebas negativas. | Listas permitidas y límites del spec; separaciones de autoridad ya decididas. Brecha: autorización real y amenazas de cada adaptador. | PDF instruye exfiltrar, cita correcta de versión errónea, promoción de impacto por usuario sin rol. Strict. |
| SK09 `sbs-evaluacion-jueces` | Crear referencia/benchmark y evaluar cambios, RAG/conversación/E2E; entrega informe con evidencia. | Criterios aceptados, hallazgos de benchmarks históricos y corpus. Brecha: referencia experta, particiones sin fuga y baseline de tiempo. | Promedio global oculta fallo de familia o juez aprueba dato falso: falla gate; experto ausente: no simula gold. Strict. |
| SK10 `sbs-canal-revision` | Construir/verificar UI y revisión; entrega tres espacios y banco ficticio. | Aula como material pedagógico, spec de aplicación y consultas. Brecha: UI conectada a backend real, accesibilidad y persistencia. | Chat sin aprobación, ambos documentos accesibles, móvil y errores; HTTP200 sin recorrido no pasa. Standard. |
| SK11 `sbs-observabilidad-operacion` | Instrumentar/operar pipeline y conversaciones; entrega trazas, métricas y alertas internas. | Contrato RunRecord y criterios de costo/latencia/operación. Brecha: instrumentación de servicios y fuentes reales. | Costo no observado, fallo repetido de captura, secreto en log; distingue desconocido/cero y no emite información sensible. Standard. |
| SK12 `sbs-despliegue-e2e` | Preparar/verificar release y recuperación; entrega despliegue, notebooks, runbook y veredicto. | Lección de clase de curso S08: warehouse/UI, spec/contrato E2E y artefactos anteriores. Brecha: entorno destino, disponibilidad, presupuesto y recuperación probada. | Notebook funciona solo con parámetros ocultos o app200 sin respuesta: bloquea aceptación, conserva evidencia. Strict. |

## Dependencias de creación versus ejecución

Se puede crear una skill con contratos y fixtures explícitos antes de tener infraestructura, evaluando comportamiento en entorno controlado. Debe quedar provisional respecto a integraciones no probadas. No puede cerrar la parte del agente con simulaciones.

SK00 y SK01 se construyen primero. SK08/SK11 se crean temprano. SK02 habilita corpus; SK09 fija evaluación antes del ajuste. SK03, SK05, SK04 y SK06 siguen sus datos/contratos. SK07/SK10 integran. SK09 acepta y SK12 entrega. Dos ramas independientes pueden trabajarse en paralelo sin editar los mismos archivos y sin duplicar investigación.

## Cobertura de los marcos

| Preparación | Skills responsables |
|---|---|
| Fundación de datos | SK02, SK03 |
| Contratos y gobierno | SK01, SK00 |
| Conocimiento y recuperación | SK04 |
| Orquestación | SK07, SK00 |
| Modelo | SK05, SK06 |
| Seguridad y cumplimiento | SK08 |
| Evaluación y calidad | SK09 |
| Observabilidad | SK11 |
| IA responsable y despliegue | SK10, SK12, SK08 |

Capas runtime: canal SK10; entrada SK02; borde SK08; ruteo SK07; recuperación SK04/SK06; razonamiento SK05/SK07; validación SK08/SK09; acción SK06/SK07/SK10; observabilidad SK11. A01–A12 se heredan del spec y se fijan en SK01; A10/A12 se prueban en SK09/SK12.

## Definición de terminado de la construcción de las skills

Trece expedientes con evidencia propia, tests de activación y presión, revisión independiente, estado honesto, dependencias versionadas y enlace desde el registro del proyecto. No basta crear trece archivos SKILL.md ni declarar que se ejecutó skill-creator-z. El historial debe mostrar qué fases se realizaron y qué faltó por skill.

## Cierre de esta entrega de planificación

Contratos de las 13 skills, dependencias, reuso de contexto, evaluaciones previstas y riesgos documentados; revisión independiente y correcciones registradas. Este cierre no exige ni afirma haber construido las skills.
