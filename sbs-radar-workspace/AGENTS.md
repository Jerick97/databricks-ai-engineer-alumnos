# Reglas de ejecución — SBS Radar

El usuario aprobó docs/12-spec-agente-v0.2.md y exige construir el agente mediante skills por responsabilidad. Consultar docs/13-plan-implementacion-skills.md y docs/14-plan-creacion-skills.md.

- Antes de construir un componente, crear/evaluar su skill con `/Users/macdenix/clawd/openclaw-codex/openclaw-workspace/skills/skill-creator-z/SKILL.md`. No sustituir por prompts sueltos ni por el skill-creator genérico.
- Mantener separados estado de skill, estado de componente y evidencia E2E. Las 13 skills del plan están planificadas; no asumir que existen o están validadas.
- Reutilizar contexto, fuentes y hallazgos existentes; investigar brechas o cambios concretos. No repetir recuperación de marcos ni auditoría completa de repos.
- Registrar invocación, skill/versión, entradas, hashes, pruebas, artefactos y veredicto. Evaluador distinto del constructor, con contexto mínimo pertinente.
- No alterar el requisito de conversación sin aprobación experta previa. La aprobación aplica al impacto institucional registrado.
- Aplicar `estrategia-rag`: `/Users/macdenix/.codex/skills/estrategia-rag/SKILL.md`; base `span-limpio-contexto-v1` v1. Adaptación SBS pendiente de evaluación.
- UI y notebook se prueban realmente con configuración entregada. Dobles, mocks, HTTP200 y contenido redactado no acreditan E2E.
- No leer credenciales ni memoria global para recuperar contexto del proyecto. Usar las configuraciones por mecanismos normales sin imprimir secretos.
