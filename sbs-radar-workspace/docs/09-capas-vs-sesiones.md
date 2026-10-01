# Matriz original: capas de arquitectura × sesiones

Recuperada sin alterar celdas de la **slide 4** del [apéndice S03](/Users/macdenix/clawd/databricks-ai-engineer/s03-genai/S03-append.html:12). La slide 3 contiene las capas; la slide 7 el comparativo Foundry/Databricks. La matriz empieza en S02, no inventar una columna S01.

| Capa | S02 Datos | S03 GenAI | S04 RAG | S05 Agentes | S06 Eval. | S07 Gob. | S08 Oper. |
|---|---|---|---|---|---|---|---|
| Canal y experiencia | — | Contexto | — | Aplicación | UX eval. | Riesgo | Producción |
| Entrada / normalización | Base | Prompt | Documentos | Eventos | Casos | PII | Logs |
| Borde / gateway | — | — | — | API/tools | — | Acceso | Operar |
| Clasificación / ruteo | — | — | Query | Profundiza | Segmentos | Política | Alertas |
| Recuperación / grounding | Gold | Introducción | Centro | Tools | Recall | Fuentes | Frescura |
| Razonamiento / decisión | Reglas | Prompt | Contexto | Plan | Calidad | Riesgo | Fallback |
| Validación / guardrails | Calidad | Formato | Grounded. | Permisos | Evalúa | Centro | Incidentes |
| Acción / herramientas | Jobs | — | — | Centro | Tool eval. | HITL | Runbook |
| Observabilidad / mejora | Runs | Tokens | Retrieval | Traces | Centro | Auditoría | Centro |

Se reutiliza como mapa pedagógico. Cobertura de una sesión no demuestra que el componente del nuevo agente SBS esté implementado o probado.
