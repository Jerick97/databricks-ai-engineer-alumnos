# Changelog

## 0.1.1 — 2026-09-27 — provisional

- Refinamiento de alcance solicitado antes de construir el componente: la skill habilita implementación local además de diseño y diagnóstico; la implementación todavía no se ejecutó en esta versión. No corresponde a un fallo observado de eval.
- Añadido flujo TDD para `src/sbs/observability/`, interfaz `record_event(run, event) -> str`, validación de allowlist/correlación y persistencia JSONL determinista con pruebas de contenido y ausencia de escritura ante datos inválidos.
- Integraciones SK08/SK07, GREEN y validación siguen pendientes. Se mantienen límites de no despliegue, no exportación externa y no gasto. Solo se editaron SKILL.md y este changelog; no se implementó código.

## 0.1.0 — 2026-09-27 — provisional

- Creator Z: fases 0/1/1.5 documentadas reutilizando notas primarias y spec/contrato existentes, sin búsqueda web duplicada.
- Leídas seis respuestas baseline reales. No se inventó fallo ni RED global: costo, frescura y triggering ya tienen respuestas correctas.
- Assertions y casos escritos antes de SKILL.md. Tres variantes nuevas pendientes de baseline separado.
- Definidos eventos con campos/tipos/enums cerrados, IDs autorizados sin URLs, errores estables y exclusión de excepciones/request/response libres. Motivo: baseline secret_log permitía URL y error sanitizados; el contrato pedido exige una proyección cerrada.
- Reutilizado RunRecord sin extenderlo; diferenciados último intento/último éxito y subtotal conocido/cobertura.
- GREEN, revisión independiente, resultados/benchmark y validación humana pendientes. No se implementó instrumentación, código del agente, infraestructura o acciones externas.

##0.1.2
Cuatro bugs de revisión reproducidos y corregidos: JSONLcorrupto/UTF8, orden deempates, registroUTF8 y overflowagregación.8fallosRED→40testsGREEN. Contrato refinado enSKILL; integración pendiente.

## 0.1.5 — 2026-09-27 — provisional

- OPS-01..04: no-follow state writes, plan/source membership invalidation, explicit commit/cleanup state, and real preparation separated from production acceptance.
- RED: 12 fixture tests failed against v0.1.4. GREEN: isolated regression suite; see runs/sk11-fixes-record.json. Independent review requested; original review retained.

## 0.1.21 provisional
Proyección display_label conserva labels internos, IDs y versiones; no nuevo embedding. CreatorZ037, baseline preservado; revisión y navegador después del cambio pendientes.
