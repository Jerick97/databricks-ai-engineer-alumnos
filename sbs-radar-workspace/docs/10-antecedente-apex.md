# Antecedente recuperado: arquitecta de datos de Apex

Se localizó el [one-pager Genie nativo en Teams vs. agente custom Foundry](/Users/macdenix/clawd/projects/agents-core-ai-databricks/docs/ONE-PAGER-genie-teams-decision.md:1), dirigido a la arquitecta de datos, fechado 18-jun-2026. Lo acompaña el [registro forense de la PoC](/Users/macdenix/clawd/projects/agents-core-ai-databricks/docs/poc-genie-teams/FORENSIC-build-log.md:1) y una [nota de coordinación con DataOps](/Users/macdenix/clawd/projects/agents-core-ai-databricks/docs/coordinacion-arquitectura-dataops.md:1).

## Qué comparó

Q&A gobernado en Genie/Teams frente al agente custom Foundry, considerando canal, curación/razonamiento, semántica, identidad, cómputo, telemetría y documentos. Separó capacidades disponibles, requisitos administrativos, costos confirmados y costos pendientes. Su conclusión histórica reservaba la solución custom para acciones y control específico que la solución nativa no cubría en esa PoC.

## Qué prueba y qué no

El log conserva verificación de Space, configuración, warehouse y permisos. También afirma que la instalación/activación en Teams estaba bloqueada por administradores, y varios costos seguían sin confirmar. Por eso **no demuestra por sí solo un benchmark pareado E2E con ambas plataformas ejecutando las mismas preguntas**, ni que Teams funcionara para usuarios finales. La ficha histórica del inventario que decía E2E cerrado requiere corroboración posterior.

Es el antecedente documental que coincide con la arquitecta y la comparación mencionadas. No se localizó en este barrido un dataset de resultados pareados Foundry vs. Databricks asociado a esa PoC. Si existe otra corrida, deberá vincularse sin inventar cifras ni adjudicarle las de otros benchmarks.

Las afirmaciones de producto, precios, beta y límites son de junio 2026: conservarlas como historia. Antes de elegir plataforma para SBS se verifica documentación vigente y disponibilidad real del entorno.

## Qué reutilizar en SBS

La ficha de comparación por capa: necesidad → opción nativa/custom → capacidad probada → costo/driver → limitación → dependencia/owner → evidencia. Comparar el mismo corpus, tareas, identidades y criterio experto. Separar calidad, permisos, latencia, costo, acción y operación; no declarar un ganador único a partir de una demo o un costo estimado.
