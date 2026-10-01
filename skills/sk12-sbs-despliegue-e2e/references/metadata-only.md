# Creación de metadata sin cómputo — SK12 0.1.4

Regla derivada del intento `runs/sk12-app-metadata-001-result.json`, su reconciliación y `runs/sk12-app-metadata-001-observation-002.json`; propuesta revisada por SK09 en `runs/sk09-metadata-skill-refinement-review.json`. Alcance: instrucciones provisionales. No hay clasificador reutilizable ni mejora de comportamiento medida.

Separar cinco dimensiones: intención solicitada (`no_compute=true`), creación/identidad confirmadas, provisioning, estado de compute observado y coste. Confirmar mismo nombre/ID del recurso propio; una URL o SP asignados prueban metadata, no ejecución de la aplicación.

- STARTING con diagnóstico de provisioning de URL/SP/dependencias permite registrar `dependencies_observed`; no demuestra compute activo ni facturación. STARTING sin diagnóstico y UPDATING sin otra evidencia quedan como transición no resuelta.
- STOPPED permite afirmar detenido en el instante observado; no prueba ausencia histórica de consumo.
- ACTIVE o señales de actividad documentadas y observadas permiten clasificar actividad. No inventar campos del API ni interpretar ausencia como cero. Actividad tampoco determina tarifa/coste.
- Coste no observado permanece null. `no_compute` expresa el request, no reemplaza verificación posterior.

Observar mediante GET acotado al mismo recurso, con presupuesto operativo fijado antes del tramo (por ejemplo, hasta3 GET en5min). Agotarlo deja pending/unknown con última observación. Los límites no amplían permisos ni crean un requisito de nueva aprobación: seguir el alcance ya autorizado y la coordinación vigente. No usar Wait/poll oculto, recreación o arranque para resolver incertidumbre.

Contención: stop únicamente ante actividad sustentada, identidad propia confirmada, alcance autorizado y transición aplicable. STARTING solo no dispara stop. Un400 “actively starting” se registra como transición no aplicable; no repetir automáticamente al alcanzar20min. Esa restricción fue observada en este intento concreto, no es una regla universal demostrada. STOPPED posterior se observa por separado; no atribuirlo a stop exitoso cuando todos los stops fallaron.

Persistir estados, timestamps, IDs, códigos permitidos y un diagnóstico clasificado de provisioning, evitando mensajes arbitrarios/secretos en observabilidad. Mantener el intento inicial incomplete y ambos stop400. La observación002, a01:52:39UTC, mostró STOPPED sin deployment/resources; no modifica retrospectivamente aquellos resultados.

Antes de reutilizar un script de creación, corregir y probar con dobles: STARTING/provisioning, transición desconocida, STOPPED, ACTIVE propio, identidad distinta, stop400 y presupuesto agotado. Exigir cero mutaciones para transiciones ambiguas y ninguna afirmación de coste cero. No reejecutar el script histórico para validar instrucciones; implementación y prueba real quedan separadas.
