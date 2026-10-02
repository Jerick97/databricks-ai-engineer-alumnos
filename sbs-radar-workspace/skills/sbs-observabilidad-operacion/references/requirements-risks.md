# Requisitos, riesgos y evaluación — SK11

Estado provisional, 2026-09-27. Fase 1.5 de Creator Z.

| Capacidad/requisito | Riesgo | Regla y evidencia | Prueba |
|---|---|---|---|
| Costo observable | null convertido a cero o presupuesto autorizado | null/no_reportado; A11 y RunRecord | unknown_cost |
| Frescura | fallo reciente aparenta datos nuevos | last_attempt_at independiente de last_success_at; A09 | capture_failure |
| Diagnóstico seguro | secretos en excepciones/URLs/configuración | allowlist cerrada e IDs opacos; notas OWASP | secret_log, free_text_pressure |
| Reproducción | mezclar versiones o prometer determinismo | IDs de ambas versiones, dirección y bundle/config hash; spec RAG | trace |
| Métricas | ocultar fallos de familia o costos incompletos | denominadores, cobertura y grupos; A10/A11 | partial_costs |
| Activación | apropiarse del gold jurídico | activar operación, derivar gold a evaluación/experto; A10 | trigger_yes, trigger_no |
| RunRecord | campos extra/status ambiguo | contrato cerrado 0.1.0; observabilidad en artefacto referenciado | runrecord_boundary |
| Acciones | gastar/desplegar/enviar logs sin autorización | producir diseño local; no ejecutar acciones externas | free_text_pressure |

Dependencias: contratos SK01, artefactos inmutables del pipeline, identidad/autorización, bundle de modelos y configuración, consumidor del panel. No se asume que estén implementadas. Permisos de lectura y retención deben comprobarse antes de conectar exportación; sin ellos producir únicamente el diseño y registrar el bloqueo de integración.

## Plan de validación

Conservar los seis casos y respuestas baseline existentes; ejecutar GREEN con mismos insumos/configuración y conservar salida bruta en artefactos gestionados por el coordinador. Evaluar los casos nuevos por separado: aún no tienen baseline y no entran en un delta pareado. Las assertions son criterios semánticos de revisión, no un runner ejecutado. Registrar evidencia, tiempo/tokens/herramientas cuando disponibles y null cuando ausentes. Marcar no discriminantes las assertions que pasen en ambas condiciones. Comparar triggering positivo y negativo sin atribuir propiedad del gold a SK11.

Revisiones independientes de activación, veracidad y permisos: pendientes de coordinación; esta entrega no afirma ejecución paralela de esas revisiones. No hay benchmark, revisión humana o comprobación de infraestructura. No declarar validada ni producción antes de GREEN, regresiones y revisión con evidencia.
