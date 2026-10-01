# SBS Genie E2E

Investigación y diseño de un agente que ayude a revisar cambios entre versiones de normativa SBS para el sector financiero peruano. Fecha de corte: 2026-09-27.

El encargo incluye levantar el E2E completo, usando las 12 decisiones, las 9 capas arquitectónicas y las 9 etapas de preparación. Se reutilizará material previo solo en lo que se compruebe adecuado. La fase actual recupera el método propio de nueve capas y nueve etapas, compila el laboratorio previo y reconstruye un framework de análisis de casos mediante evidencia. El E2E está pendiente de implementación y validación; la investigación no lo da por terminado.

Supuesto provisional: usuario de riesgos/cumplimiento de un banco peruano; corpus oficial público; especialista humano valida aplicabilidad e impacto. Entidad, familia normativa, periodo y presupuesto aún por confirmar.

Artefactos locales privados: contienen antecedentes corporativos. No publicar automáticamente. No se alteran repos fuente, catálogo canónico ni recursos cloud durante esta investigación.

## Lectura

1. [Nueve etapas de preparación](docs/01-nueve-capas.md).
2. [Escala auxiliar de madurez](docs/02-nueve-etapas.md).
3. [Compilación de iniciativas](docs/03-inventario-agentes.md) y [CSV](docs/03-inventario-agentes.csv).
4. [Hallazgos forenses](docs/04-hallazgos-forenses.md).
5. [Framework reconstruido](docs/05-framework-analisis-caso.md).
6. [Aplicación preliminar a SBS y Genie](docs/06-caso-sbs-genie.md).
7. [Plantilla para nuevos casos](docs/07-plantilla-caso.md).

Evidencias, límites y referencias primarias en `evidence/`. Estado de trabajo en [STATE.md](STATE.md).

8. [Nueve capas de arquitectura](docs/08-capas-arquitectura.md).
9. [Slide recuperada: capas × sesiones](docs/09-capas-vs-sesiones.md).
10. [Antecedente Apex Databricks–Foundry](docs/10-antecedente-apex.md).
11. [Contrato de construcción E2E](docs/11-contrato-e2e.md).

12. [Aula web interactiva](web/index.html): explorador, modo docente, matriz y taller SBS. [Uso y validación](web/README.md).

13. [Spec vigente v0.2](docs/12-spec-agente-v0.2.md): dos familias, conversación sin aprobación previa, RAG híbrido con RRF/reranking y listas permitidas. Estrategia base: `span-limpio-contexto-v1`, versión 1; adaptación SBS propuesta, ver skill `/Users/macdenix/.codex/skills/estrategia-rag/SKILL.md`.

14. [Plan de implementación por skills](docs/13-plan-implementacion-skills.md).
15. [Plan de creación de 13 skills con skill-creator-z](docs/14-plan-creacion-skills.md).
