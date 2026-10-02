# SK12 — Creator Z, 2026-09-27

Intención: empaquetar notebooks/configuración/app y demostrar ejecución, despliegue, recuperación y operación de SBS Radar. No redefine terminado alrededor de los módulos que ya pasan tests.

Fuentes reutilizadas: spec v0.2 A11/A12, planes13/14, lecciones S08 (warehouse_id vacío y app detenida), contratos, registros SK00/SK05/SK11. Presupuesto US$100 es hipótesis explícitamente no autorizada para habilitar nuevos recursos facturables. Preparar paquete concreto antes de pedir la autorización que falte.

Fuente primaria consultada: https://docs.databricks.com/aws/en/dev-tools/databricks-apps/deploy (Sep23,2026). App requiere entrypoint, dependencias y comando/configuración; despliegue instala paquetes y ejecuta app, pero no acredita respuesta correcta. Servicio debe acceder al código/recursos. No subir secretos ni cache/modelos innecesarios mediante sync indiscriminado.

Alternativas: local ayuda a probar la integración y empaquetado; destino Databricks sigue siendo requisito. Notebooks con fixtures solo son ejemplos técnicos; entregar ejecución sobre corpus real y configuración reproducible. No modificar ni restaurar ciegamente recursos de clase/otros proyectos.

Evaluación: arranque limpio del notebook, UI real con ambas familias y seguimiento/pregunta cruzada, errores, permisos, rollback y persistencia. Referencias IA provienen SK09; no llamarlas humanas. Mantener matriz requisito→evidencia y gates parciales visibles.

Baseline seis casos antes de SKILL; integración completa y despliegue pendientes.
