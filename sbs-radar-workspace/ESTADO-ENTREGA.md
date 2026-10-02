# Entrega vigente — 30 septiembre 2026

**SBS Radar funciona y pasó la validación controlada del piloto. El spec completo sigue abierto.**

[Abrir SBS Radar](https://sbs-radar-pilot-7474657121564806.aws.databricksapps.com/). La App246 quedó ACTIVE y abierta en Chrome, sin apagados en esta continuación. [Estado observado](runs/ui246/final-app-observation.json).

La muestra244 verificó cinco consultas: conteos de dos versiones documentales en cada familia, comparación de ciberseguridad, artículo27 y seguimiento29.1.4 de conducta de mercado. GPT-6 Astra high aprobó ocho citas y cinco propuestas. Se abrieron los cuatro PDF originales en sus páginas citadas. [Revisión244](runs/sk09-astra-actual244-review.json).

La versión246 conserva por hash la lógica anterior y añade renovación firmada finita. Se probaron dos consultas nuevas, cuatro citas, renovación sobre consumo existente y reenvío del mismo sobre sin duplicar crédito. El proceso mantuvo su identidad y contadores. [Revisión246](runs/sk09-astra-actual246-review.json) y [evidencia](runs/ui246/evidence-manifest.json).

**Saldo observado:** diez respuestas y ocho búsquedas; se consumieron dos de cada una. Tres búsquedas del tramo inicial vencen hoy12:13:24 Lima y cinco del tramo renovado12:17:46 Lima. Vencer el cupo no apaga la App; siguen disponibles catálogo, comparación y originales. Es una asignación finita de piloto, no operación continua. [Estado exacto](runs/ui246/status-after-renewal.json).

## Material y notebook

- [Guía docente S08](../s08-deployment/GUIA-DOCENTE.md), [web de clase](../s08-deployment/index.html) y [ZIP de alumnos](../s08-deployment/entregables/S08-material-alumnos.zip).
- [Notebook S08 en Databricks](https://dbc-0410b264-20c7.cloud.databricks.com/editor/notebooks/3142549814418784?o=7474657121564806). [Cierre S08](../s08-deployment/reports/closure.json): ejecución real y tres jueces PASS, evidencia propia conservada.
- [Web interactiva del framework](web/index.html): nueve capas, nueve etapas y doce decisiones.
- [Notebook/writer SBS ejecutados](runs/sk12-closure244-notebook-reuse.json): run817327291004649 y23artefactos leídos por hash. Es evidencia histórica de esos componentes, no una ejecución nueva del notebook con la configuración246.

## Capas y skills

Las trece skills SK00–SK12 existen y siguen provisionales. Sus componentes tienen evidencia acotada; no equivalen a trece skills certificadas para cualquier proyecto.

| Capa | Skills y estado del piloto |
|---|---|
| Canal y experiencia | SK10: novedades, comparación, conversación, seguimiento y fuentes probados. |
| Entrada y normalización | SK02: corpus real de ambas familias; cobertura completa y vigencia no acreditadas. |
| Borde, seguridad y gateway | SK01/SK08/SK12: identidad, límites y renovación probados en el alcance revisado. |
| Clasificación y ruteo | SK07: conteos, comparación y propuestas probados en las muestras. |
| Recuperación / grounding | SK04/SK05/SK06: RAG y Genie integrados; evaluación general y discrepancia numérica histórica del reranker pendientes. |
| Razonamiento y decisión | SK03/SK07: antes/después y propuestas sustentadas; no aprobación institucional. |
| Validación y guardrails | SK08/SK09: citas, alcance y rechazo de resultados no verificables; aprobación por muestra. |
| Acción y herramientas | SK03/SK06/SK10/SK11: consultas, originales y writer real; operación diaria pendiente. |
| Observabilidad, evaluación y mejora | SK00/SK09/SK11/SK12: trazas, hashes y jueces; falta aceptación completa. |

Refinamiento provisional: [renovación245/246 en SK12](skills/sbs-despliegue-e2e/references/renewal245-runtime246.md). No se reescribieron artefactos congelados ni se promovieron skills por el mero éxito del componente.

## Pendiente para cerrar todo el spec

Operación diaria08:00 Lima (Job todavía PAUSED), recuperación completa en nube aislada, evaluación independiente no expuesta y métricas por familia. La mejora de tiempo humano requiere mediciones humanas reales; no se infiere de latencia. Cuatro pruebas locales de recuperación pasaron, pero no sustituyen la recuperación cloud. Coste total desconocido. [Acciones y límites](runs/sk12-closure244-next-actions.json).

Los conteos describen el corpus publicado y contrastado con Genie; no acreditan vigencia normativa ni verificación independiente del SQL ejecutado. La conversación permite cambios pendientes de revisión, y mantiene separada la aprobación institucional.
