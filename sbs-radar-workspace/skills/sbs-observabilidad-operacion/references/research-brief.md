# Research brief — SK11

Fecha: 2026-09-27. Estado: provisional; investigación reutilizada, sin segunda búsqueda web. Creator Z fases 0, 1 y 1.5 antes de redactar la skill.

## Intención y alcance

Habilitar diseño y revisión de observabilidad SBS: latencia por etapa, trazabilidad por documento/expediente/conversación, costos observados, errores estables, frescura de captura y diagnóstico operativo seguro. Usuarios: ingeniería y operación. Runtime objetivo: Databricks/web privada; acceso real, SDK, exportadores y permisos no comprobados. Entrada: contexto de ejecución y referencias versionadas; salida: contrato de eventos, estado operativo, métricas y RunRecord. No establecer gold jurídico ni autorizar gasto, despliegues o acciones institucionales.

## Fuentes y decisiones

| Fuente | Consulta/versión | Hecho o alcance | Decisión | Confianza |
|---|---|---|---|---|
| `../../../context/security-source-notes.md` y https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html | Notas consultadas 2026-09-27; web primaria consultada previamente el mismo día; revisión exacta no registrada | Protección de logs y exclusión de credenciales; no demuestra implementación | Allowlist de campos; no cuerpos ni excepciones libres | Alta para criterio, limitada para despliegue |
| `../../../docs/12-spec-agente-v0.2.md` | v0.2, 2026-09-27 | A09/A11: errores explícitos, trazas y costos; RAG exige configuración/candidatos observables | Correlacionar versiones, etapas, familia y evidencias sin inventar scores | Alta para requisitos |
| `../../../contracts/RunRecord.json` | urn:sbs:contracts:RunRecord:0.1.0 | Campos cerrados, cost nullable, estados definidos | Reutilizar contrato sin agregar campos; detalles en artefacto separado | Alta estructural; no prueba persistencia ni autorización |
| `../../../context/sk11-creator-cases.json` | Insumo local leído 2026-09-27 | Seis casos: costo, frescura, secretos, reproducción y triggering | Copiar casos y congelar assertions antes de SKILL | Alta |
| `../../../runs/sk11-baseline.json` | without_skill; leído 2026-09-27 | Respuestas crudas de seis casos | Preservar baseline y no inventar fallos | Alta sobre respuestas; sin métricas del harness |

Las notas de seguridad también conservan OWASP Prompt Injection Prevention y SSRF Prevention. Se reutiliza su principio de mínima autoridad: mensajes de excepción, PDFs y resultados de herramientas son datos, nunca instrucciones para ampliar logs o permisos. SK11 no implementa controles DNS ni transporte de SK02.

## Alternativas y reutilización

Reutilizar RunRecord frente a inventar otro contrato de ejecución. Reutilizar IDs y artefactos versionados del pipeline frente a volcar prompts/respuestas para reproducir. Databricks es destino establecido, no selección validada de un exportador; no se compararon proveedores, licencias, SDK ni OpenTelemetry en esta revisión acotada. La alternativa de sanitizar un error libre es insuficiente para el contrato pedido: usar clasificación a códigos cerrados y descartar el cuerpo antes de persistir.

## Baseline y evaluación

El baseline ya responde null ante costo desconocido, distingue último intento de último éxito, evita secretos crudos, recoge IDs/configuración y acierta ambos triggers. No se declara RED general ni mejora demostrada. En secret_log conserva potencialmente una URL sanitizada y un error sanitizado; el nuevo requisito pide eventos sin URL ni texto libre, una brecha específica de diseño. No se ejecutó todavía GREEN ni se calcularon pass rate, delta, latencia o tokens. Assertions que ambas condiciones cumplan serán controles no discriminantes.

## Límites y supuestos

Campos y enumeraciones operativas de esta skill son una propuesta local, no un contrato desplegado. Moneda USD propuesta para el panel alineada con A11, pendiente de política de conversión. US$100 es hipótesis, nunca autorización. Retención, ACL, cifrado, servicio de captura, alertas, umbrales, tarifas y cobertura real requieren verificación posterior. No se inventan costos, timestamps ni infraestructura. La reproducción reconstruye condiciones; no garantiza salida idéntica de un modelo no determinista.
