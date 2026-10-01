---
name: sbs-contratos-gobierno
description: Define, valida o evoluciona contratos de documentos, versiones, evidencia, conversación y revisión de SBS Radar. Usar ante esquemas o estados incompatibles; no para descargar corpus, interpretar normas ni conceder permisos reales.
---

# SK01 — Contratos y gobierno

Versión 0.1.1. Estado provisional; strict pendiente de benchmark completo. Fuente creadora: skill-creator-z. No marcar producción por validación de JSON.

## Entrada y salida

Entrada: spec v0.2, tipo de entidad y payload, contexto autenticado cuando aplique y referencias de versiones/evidencias. Salida: schemas Draft2020-12 en contracts/, diccionario, validación estructural y semántica diferenciadas, errores localizables. Interfaz validate_contract(kind, payload) devuelve {valid, errors}; nunca autentica roles contenidos en el payload.

## Flujo

1. Recuperar spec y contratos existentes con SK00. Tratar fechas desconocidas como null con motivo/estado; nunca inferir publicación ni efecto de captured_at.
2. Modelar SourceDocument, Provision, VersionPair, ChangeSet, EvidencePack, QueryContext, Answer, ReviewDecision, RunRecord y ModelBundle. IDs inmutables, versiones y evidencia explícitas; conservar cambios de schema y no reinterpretar datos históricos silenciosamente.
3. Separar processing_status (detected/processing/ready/partial/error) y review_status (unreviewed/proposed/reviewed/approved/rejected). ready y partial permiten conversación con evidencia/límites; approved no es precondición del chat.
4. Validar tipos, campos requeridos y formatos explícitamente; JSON Schema no habilita por sí solo validación de formatos en todos los runtimes. Fijar dialecto e impedir carga remota arbitraria de referencias de schemas recibidos.
5. Validar vínculos: ambas versiones del par; cita ligada a documento/versión/offsets; publicación, captura y efecto separadas. Literalidad correcta de una versión ajena no sustenta la comparación. Datos sintéticos identificados; fuente normativa y proceso ficticio separados.
6. Para impacto approved exigir actor, rol, fecha y evidencia en el registro. Estos campos son requisitos estructurales, no prueba de autenticidad. El backend con SK08 comprueba identidad/rol de servidor y transiciones; rechaza reader y no confía en actor_role enviado por cliente.
7. Una nueva evidencia no hereda aprobación; conserva la revisión antigua referida a su versión. Contradicciones o faltantes producen errores/estado parcial, no valores inventados.
8. Escribir tests de rechazo y aceptación antes del validador. Guardar schema/version, payload no sensible, resultado y alcance de validación. Aplicar formatos para URI/fechas; la validación de URL no acredita fuente permitida.
9. Refinamientos de revisión real: rechazar IDs compuestos solo por espacios; para hashes combinar patrón y longitud exacta (el ancla `$` sola puede aceptar un salto final); ValidationResult debe concordar entre valid y lista de errores. Las reglas de revisión independiente e incrustada deben ser iguales: vínculos obligatorios para approved, y validar vínculos opcionales como un par cuando se suministren en otros estados. Probar formatos inválidos en el entorno instalado: FormatChecker sin extras puede omitir formatos; usar validación explícita y declarar el perfil admitido.

## Bajo presión

Se puede conversar antes de aprobación; se puede proponer implicancias. No falsear impacto aprobado para continuar. No confundir éxito de schema con exactitud jurídica, cita sustentada, permisos comprobados o ejecución E2E.

## Referencias

- [Brief](references/research-brief.md), [requisitos y riesgos](references/requirements-risks.md).
- [Casos](evals/cases.json), [assertions](evals/assertions.json).
- Implementación prevista: src/sbs/contracts.py; tests/unit/test_contracts.py. Contrato de autorización se implementa en SK08 y se prueba en integración; mantener boundary explícito.
