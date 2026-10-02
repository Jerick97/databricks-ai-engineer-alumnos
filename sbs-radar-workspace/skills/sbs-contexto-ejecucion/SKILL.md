---
name: sbs-contexto-ejecucion
description: Recupera o reanuda una tarea de SBS Radar, comprueba vigencia de entradas y checkpoints y evita repetir investigación existente. Usar al coordinar dependencias de la misión, no para interpretar normas o ingerir documentos.
---

# SK00 — Contexto y ejecución

Versión 0.1.1. Estado provisional; consultar evals y CHANGELOG. Creada con skill-creator-z, no sustituye la validación de componentes.

## Contrato

Entrada: task_id, skill/version responsable, spec aprobado, IDs de artefactos requeridos y configuración. Salida: ContextBundle con entradas válidas, brechas, invalidaciones y siguiente acción; registro de invocación/checkpoint. No incluir secretos ni contexto ajeno.

## Flujo

1. Leer STATE.md y la tarea pertinente de docs/13-plan-implementacion-skills.md. Recuperar fuentes por ID en context/source-register.json, no repetir búsquedas globales.
2. Comprobar hash local y estado de cada entrada. Documento de proveedor demuestra documentación, no habilitación/permisos de workspace. Las capacidades operativas requieren evidencia del entorno y actor concreto.
3. Reusar entradas compatibles. Si cambió una entrada, invalidar solo sus dependientes transitivos y conservar versiones anteriores. Un ciclo o dependencia faltante impide checkpoint exitoso.
   Validar tipos del registro: depends_on es lista de IDs, path es texto no vacío. Una entrada malformada afecta su rama; no interpretar una cadena como IDs de caracteres. Una entrada ajena sin ID se reporta como warning, sin abortar trabajo independiente. El resolutor local v0.1.1 solo acredita contexto documental; las capacidades runtime quedan pendientes de comprobación integrada por SK12, incluso si llevan status=reusable.
4. Si falta contexto, registrar brecha concreta y resolverla en la skill propietaria. Un fixture no acredita corpus real ni cobertura de otra familia.
5. Entregar solo el contexto necesario al ejecutor. Invocar la skill indicada; registrar task_id, skill_id/version, spec_hash, input IDs/hashes, configuration_hash, mode y output IDs.
6. Checkpoint passed solo con checks pertinentes realmente ejecutados y evidencia enlazada. Separar estado de skill, componente y E2E. No declarar todo bloqueado por una rama pendiente si otras pueden avanzar.

## Presión y límites

“Busca otra vez todo”: explicar reuso y buscar solo brechas o fuentes cambiadas. “Márcalo listo por urgencia”: conservar estado no verificado. No reutilizar permisos/capacidades solo por hash de documentación. No desplegar, gastar, enviar mensajes ni modificar fuentes externas al gestionar contexto.

Implementar utilidades deterministas en src/sbs/context.py y tests/unit/test_context.py con pruebas RED/GREEN. La raíz del proyecto es explícita; rechazar rutas y symlinks que salgan de ella salvo referencias externas leídas deliberadamente y registradas, nunca inspeccionar credenciales.

## Referencias y evaluación

- [Investigación y alcance](references/research-brief.md)
- [Requisitos/riesgos](references/requirements-risks.md)
- [Casos](evals/cases.json) y [assertions](evals/assertions.json)

El baseline ya responde correctamente varios casos: no atribuir mejora no medida. La utilidad adicional debe demostrarse con invocaciones reproducibles y contexto acotado.
