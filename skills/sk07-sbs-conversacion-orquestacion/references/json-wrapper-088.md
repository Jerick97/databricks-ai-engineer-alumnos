# SK07 — envoltura no es calidad

Aplicar [compatibilidad088](../../sk05-sbs-modelos-configuracion/references/json-wrapper-088.md) junto con GeneratedClaims y los guardrails existentes. El servidor sólo retira una envoltura completa explícitamente admitida; no modifica material_claims ni citation_ids. Después se ejecutan sin cambios las validaciones de esquema, alcance, pertenencia y cita literal. Mostrar el texto exclusivamente derivado de claims validados.

El replay086 pasó validación técnica pero contiene un fallo semántico identificado por089. Una cita autorizada no acredita que «excepción», modalidad o condiciones estén correctamente interpretadas. Mantener revisión semántica independiente y `quality_accepted=false`; no promover por JSON correcto, HTTP200, quote exacto o replay. No reconstruir077retroactivamente ni aprobar cuatroturnos a partir de uno.
