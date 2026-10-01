# Refinamiento provisional SK12 — renovación245 / runtime246

Aplicación mediante skill-creator-z y SK11/SK12. El cupo de pruebas de un proceso no debe forzar a detener la App ni a desplegar código para cada renovación admitida. Separar disponibilidad de la interfaz, vigencia del cupo y aceptación de respuestas.

Mantener asignaciones finitas firmadas, consumo acumulado y vencimiento propio de cada tramo. El mismo sobre debe ser idempotente; no devolver intentos fallidos ni extender créditos anteriores. Verificar todos los límites que realmente ejecutan el consumo: lifecycle y adaptador embedding. El firmante y su clave quedan fuera del paquete cloud.

Antes de entregar, probar una consulta, observar contadores reales, aplicar la renovación, reenviar el mismo sobre y consultar de nuevo. Registrar mismo epoch, saldo, expiraciones y ledger, además de la respuesta visible. La prueba de código y el estado ACTIVE no sustituyen este recorrido. Dejar la App encendida.

Evidencia: [diseño245](../../../sbs-radar-workspace/runs/sk12-renewal245-design.md), [revisión245](../../../sbs-radar-workspace/runs/sk09-astra-renewal245-review.json), [gate246](../../../sbs-radar-workspace/runs/sk09-incremental-246-review.json), [observaciónUI](../../../sbs-radar-workspace/runs/ui246/renewal-ui-observations.json), [estadofinal](../../../sbs-radar-workspace/runs/ui246/status-after-renewal.json). 34pruebas del componente y3del despliegue; evidencia conductual de esta ejecución. No demuestra reutilización general de la skill, operación continua ni aceptación completa del spec. Se conserva la skill canónica provisional; este anexo no reescribe artefactos congelados.
