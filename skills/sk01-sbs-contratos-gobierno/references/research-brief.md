# SK01 — Creator Z fases 0/1/1.5

Fecha: 2026-09-27. Fuente creadora: /Users/macdenix/clawd/openclaw-codex/openclaw-workspace/skills/skill-creator-z/SKILL.md. Estado investigación/diseño; baseline en ejecución antes de SKILL.md.

Capacidad: contratos verificables de datos, evidencia, conversación y revisión con autoridad separada.

Entradas: spec v0.2 aprobado, planes13/14, casos evals/cases.json. Salida: skill reutilizable, scripts y pruebas, registro de ejecución con evidencia. Runtime Codex/Python local; cloud no necesario para esta fase.

Fuentes recuperadas: docs/12-spec-agente-v0.2.md (decisiones, confianza alta como contrato de usuario); docs/13 y14 (plan); evidence/source-hashes.json (procedencia, no disponibilidad operativa); evidence/sbs-forensic-genie.md (fallos previos, evidencia histórica); skill estrategia-rag (solo referencias pertinentes). No se repitió búsqueda de marcos ni auditoría.

Fuente primaria adicional SK01: https://json-schema.org/draft/2020-12/json-schema-validation consultada hoy; draft2020-12, vocabulario de validación estructural. Decisión: usar Draft202012Validator y comprobación de formatos explícita. Un schema no autentica actores ni verifica que un PDF sea verdadero; esos controles pertenecen a políticas/servicios. No presentarlo como estándar jurídico.

Alternativas: relectura completa del historial (costosa y no reproducible) frente a registro con hashes; validación manual de dicts (frágil) frente a JSON Schema y reglas semánticas separadas. Reusar jsonschema ya instalado; sin instalar dependencias de producto en esta fase.

Riesgos: contexto obsoleto, secretos, estados aprobados falsos, fechas inventadas, citas de versión errónea. Ninguna métrica histórica o fixture acredita el nuevo E2E. No uso: respuesta jurídica de contenido, descarga masiva o despliegue fuera del contrato.

Evaluación: seis casos nominales/negativos/presión por skill, baseline y GREEN sobre mismo caso; pruebas nuevas para generalización; reviewers de activación/veracidad/permisos. Tokens/latencia no instrumentados se marcarán no medidos. SK01 strict quedará provisional hasta completar sus repeticiones, wording y revisión ciega; no inventar mejora si baseline ya pasa.
