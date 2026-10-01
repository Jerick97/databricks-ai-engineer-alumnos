# Hallazgos que sustentan el framework

Fecha: 2026-09-27. Lectura forense de fuentes y artefactos; no nueva ejecución de los agentes. **Observación** describe lo localizado; **regla propuesta** es nuestra inferencia transferible. Los informes completos conservan paths y líneas en [casos](../evidence/sbs-forensic-cases.md), [Genie/SBS](../evidence/sbs-forensic-genie.md) y [marcos](../evidence/sbs-nine.md).

| ID | Evidencia observada | Qué obliga a preguntar en un caso nuevo | Decisiones del framework |
|---|---|---|---|
| F01 | N1 evaluador define universo en Jira incluyendo casos sin respuesta; campos objetivos, prelabel y humano separados | ¿Quién queda fuera del denominador? ¿Quién adjudica verdad? | A01, A05, A10 |
| F02 | N1 routing ubica errores en argumentos de herramientas, no solo en selección de dominio | ¿En qué eslabón se perdió la tarea? ¿Hay contratos por etapa? | A06, A09 |
| F03 | Benchmark N1 imprime cero diagnósticos legítimos rotos, pero el contador no se incrementa | ¿La métrica se midió realmente? ¿Tiene controles positivos independientes? | A10 |
| F04 | TYV conserva resultados separados de ejecución autónoma, replay y asistencia; el catálogo aún dice esqueleto | ¿Qué produjo el sistema y qué corrigió una persona? ¿Qué fecha manda? | A02, A10, A12 |
| F05 | PL00098 tiene extracción y offsets probados, pero citas de respuesta E2E pendientes en el reporte examinado | ¿La evidencia está disponible, recuperada, citada y sustenta la afirmación? | A04, A08, A10 |
| F06 | Research-citas maduro verifica cita completa y fronteras con mapa a texto crudo; el laboratorio antiguo solo verificaba un prefijo | ¿Cuál es la implementación vigente? ¿Qué normalización conserva significado? | A04, A05, A08 |
| F07 | SBS S05 usa fixtures, IDs/hashes ilustrativos, diff por artículo y supervisor definido como diccionario | ¿Se ejecuta la capacidad prometida o solo está descrita? | A03, A06, A12 |
| F08 | SBS S05 tiene documento objetivo fijo y overwrite; herramientas declaradas y funciones no coinciden totalmente | ¿La ingesta cubre el universo y es repetible sin perder histórico? | A04, A06, A11 |
| F09 | Ianbal IaC registra 17/20→18/20→20/20, pero dos referencias tenían defectos semánticos y faltaba revisión humana | ¿El gold es correcto? ¿Se conoce el conjunto de ajuste? | A05, A10 |
| F10 | Ianbal S&OP construye base sintética, mientras ocho agentes son candidatos | ¿Qué está construido y qué solo planeado? | A03, A12 |
| F11 | Webinar Genie expone trampas de fechas, precios, descuentos, fletes y joins | ¿Qué significan medidas, unidades y fechas antes de escribir instrucciones? | A05 |
| F12 | Template RAG catalogado con madurez5 resulta ser esqueleto comentado en la copia inspeccionada | ¿Existe código y ejecución o solo estructura de carpetas? | A06, A12 |
| F13 | El Chambas rechaza afirmaciones con citas que no puede verificar en el perfil | ¿Cuál es el contrato de evidencia por afirmación y qué salida se rechaza? | A08, A09 |
| F14 | LangGraph triage decide revisión humana mediante reglas de urgencia e intención fuera del modelo | ¿Qué umbral de autonomía se hace cumplir en código? | A07, A09 |
| F15 | S08 pasó un Job con parámetros, pero la copia abierta tenía widgets vacíos; después la App estaba detenida | ¿La prueba replica la entrega y el canal real? ¿Disponibilidad y aceptación están separadas? | A08, A11, A12 |
| F16 | Challenge Día2 analiza incidente y detiene prioridad indeterminada/revisión humana antes de crear ticket | ¿Qué condición permite actuar y qué se audita antes de la escritura? | A06, A07 |

## Anclas primarias adicionales

- F12: [README](/Users/macdenix/clawd/projects/production-rag-system/README.md:3) y [stub híbrido](/Users/macdenix/clawd/projects/production-rag-system/app/retrieval/hybrid_retriever.py:3).
- F13: [validación de citas del resultado](/Users/macdenix/clawd/projects/el-chambas-producto/chambas/agent.py:58).
- F14: [gate de revisión](/Users/macdenix/clawd/projects/langchain-agent-demos/06-support-triage-agent/src/agent.py:31).
- F15: [regresión entrega docente](/Users/macdenix/clawd/databricks-ai-engineer/s08-deployment/reports/teacher-delivery-regression.json), [Job sin parámetros](/Users/macdenix/clawd/databricks-ai-engineer/s08-deployment/reports/notebook-docente-observed.json), [recuperación HTTP de App](/Users/macdenix/clawd/databricks-ai-engineer/s08-deployment/reports/app-recovery-http.json). HTTP no reemplaza prueba browser→backend→endpoint.
- F16: [snapshot de código leído por GitHub](../evidence/challenge-dia2-source.py.txt), función `procesar_incidente` desde línea389; [repositorio](https://github.com/manuelarguelles/ai-engineer-challenge-dia2).

## Límites de lo que se puede afirmar

49 fichas no son 49 agentes productivos. La compilación incluye propuestas, plataformas y activos educativos; evita duplicar versiones como productos. Las métricas históricas se atribuyen a sus reportes y no se trasladan al nuevo caso. Un bug en un instrumento limita la afirmación afectada, no invalida automáticamente todo el proyecto.

Los commits de una cuenta de taller o un repo sin flag fork no bastan para afirmar autoría exclusiva. El catálogo conserva exclusiones previas y se verificaron contribuidores de los candidatos remotos nuevos; donde falta corroboración se conserva la incertidumbre. Los detalles de clientes permanecen locales.
