# Refinamiento221 — conteo histórico explícito

Estado: código local probado; revisión independiente y App E2E pendientes. No es aceptación de producción. Diseño previo: [propuesta](immutable-snapshot-count-proposal.md), congelado antes de implementar mediante CreatorZ exacto y SK06/SK08.

Admitir exclusivamente desde configuración servidor fijada `immutable_snapshot_counts_v1`. Mantener generación219 exacta y perfil NAMED original,32 historiales y todas las comprobaciones históricas. No actualizar tiempos/TTL, no seguir current.json, no convertir readback antiguo en reciente. La política operativa nueva declara autorización hasta revocación, con invariantes originales y observaciones actuales≤60s; es una decisión explícita de alcance, no extensión silenciosa de política expirada.

Leer estado remoto exacto antes/después con GET no-cache; ausencia, revocación, desconocido, claves duplicadas o error deniegan. Conservar SQL/AST VERSION AS OF, Query History actual, identidad/SELECT-only pre/post, filas reales y comparación con corpus. Mantener límites ABA/continuidad y retención visibles. Un fallo no devuelve conteos verificados ni fallback latest.

Para pregunta documental explícita derivar contextos registrados de los pares ya validados, con ID distinto y selected_provision_id=null. No alterar export, mapping ni corpus; restringir catálogo nuevo a count. Restaurar el foco de artículo de la sesión al terminar, incluso con error. Etiquetar resultado y seguimiento como conteo del snapshot histórico, del par seleccionado, no total general de normas vigentes.

Implementación aislada: `runs/sk06-immutable-counts-221-overlay/source`. Incluye diagnóstico220 revisado más operación GET de vocabulario fijo, sin argumentos/excepciones arbitrarias. Regresión local:121PASS (40 nuevas+81legacy), UI221PASS. Fixtures no prueban permiso M2M ni disponibilidad real. Fallo Genie218 dentro de TTL sigue sin causa acreditada; diagnóstico sirve para observarlo después del único delta revisado.

SK09 debe revisar código/config/pins antes del deploy; SK12 prepara14archivos202110bytes, una actualización ACTIVE218, sin stop/start, misma identidad. Cuarta reserva explícita6gen5embed50000tokens/8h empieza al activar epoch listo;210/214/218 se preservan sin refund. No se implementó reposición del mismo epoch.

Aceptación aún requerida: pregunta real de conteos de ambas familias, consulta/filtros/versión/filas/historial verificados, seguimiento, etiqueta histórica visible y revocación fail-closed en ámbito controlado. Pasar5/30min por sí solo no renueva ninguna evidencia ni demuestra uptime. No declarar resuelto el fallo anterior por tests locales.
