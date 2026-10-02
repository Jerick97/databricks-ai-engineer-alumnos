# Propuesta: conteos de un snapshot histórico con autorización actual

Estado: diseño provisional, pendiente de revisión independiente SK09. No implementado ni autorizado para cloud por este documento. Propietarios SK06/SK08; CreatorZ exacto del AGENTS. Fecha: 2026-09-29.

## Problema y evidencia reutilizada

El consumidor actual exige a la vez readback de antigüedad ≤5 minutos, registro vigente ≤5 minutos y política administrativa ≤30 minutos (`publication_rotation.py`). `219` publica una generación una sola vez; no existe renovador autónomo revisado. Leer `current.json` en cada pregunta no renueva esas pruebas. El análisis offline219 acredita aceptación con reloj histórico, no disponibilidad actual del App.

La consulta ya usa VERSION AS OF entero exacto, historial independiente de la ejecución Genie, ámbito cerrado de familia/par/disposición y comparación de columnas/filas con el snapshot local (`__init__.py`, `provenance.py`, `delta.py`). Reutilizar esos controles permite una modalidad histórica explícita, sin afirmar actualidad del contenido. Esta propuesta cambia el requisito temporal de admisión; NO constituye un arreglo inocuo de TTL ni mantiene idéntica la política anterior. Debe aprobarlo SK09 antes de implementar. Los perfiles anteriores y sus límites permanecen intactos.

## Decisión mínima

Añadir un modo servidor opt-in `immutable_snapshot_counts_v1`, separado del perfil de identidad del certificado. El certificado219 sigue siendo NAMED, con sus bytes, hashes, tiempos y 32 historiales originales. No convertirlo en REPLAY, no modificar valid_from/valid_until, no volver a fechar observaciones, no publicar una supuesta lectura reciente.

Este modo sólo admite las referencias cerradas de conteo documental/disposiciones ya existentes. No habilita SQL libre, listas nuevas, latest, vigencia jurídica, inferencias normativas ni nuevos snapshots. El catálogo determina las referencias elegibles; texto del usuario y payload nunca eligen el modo. El resultado debe decir «Conteo del snapshot publicado [identificador/fecha]», conservar sus filtros y distinguirlo de cambios materiales.

Seleccionar una generación histórica exacta por SHA256 fijado en configuración servidor, no seguir un puntero mutable a otra generación. Mantener el volumen protegido217 y su lectura mediante identidad M2M App. Validar integralmente certificado, export, mapping, ocho identidades/contenidos, publicador, warehouse, 32 IDs únicos, SQL/tipos/timestamps finales sin caché y hashes del historial. Mantener la comprobación original de que esas ejecuciones terminaron antes de valid_from histórico. No exigir que ese intervalo histórico cubra la pregunta actual, porque el resultado ya no afirma frescura del readback.

Separar una política operativa aprobada por servidor, vigente hasta revocación explícita, del documento administrativo de 30 minutos archivado en219. La nueva política es un archivo local fijado por hash en la configuración desplegada; contiene versión/mode, scope counts-only, snapshot/generation hash, namespace, administradores confiables, los mismos supuestos de mantenimiento/retención y ABAC, TTL de observaciones ≤60 segundos, y el identificador remoto exacto de revocación. No hereda autoridad de un documento expirado ni produce tiempos ficticios. Este cambio elimina deliberadamente el vencimiento automático de esa política para este ámbito limitado; no promete retención perpetua ni ausencia de ABA. La revisión acepta o rechaza explícitamente este supuesto operacional.

## Flujo por pregunta (sin publicador recurrente)

1. Autenticar usuario/origen/CSRF y validar contexto registrado como hoy. Comprobar que el plan es uno de los conteos permitidos antes de Genie.
2. Leer estado remoto exacto de revocación y bytes de la generación histórica fijada. Falta, acceso denegado, estado desconocido, `revoked`, bytes distintos o perfil inconsistente bloquean antes de Genie. Un estado `active` sólo indica no revocado; no demuestra frescura ni grants.
3. Ejecutar las observaciones reales actuales previas: identidad/grupos completos, SELECT-only, warehouse CAN_USE, UC ID/metastore/location del certificado, filtros/máscaras visibles y propietarios. Mantener límites y rechazo de paginación incompleta. No usar arrays vacíos sintéticos ni valores esperados como evidencia.
4. Genie ejecuta la consulta. Query History independiente debe confirmar statement final, executor/warehouse/espacio, SQL/AST exacto, VERSION AS OF y todos los filtros. Versión eliminada/no disponible, error, timeout o caché no verificable bloquean; no consultar latest como fallback.
5. Observaciones reales posteriores iguales a las previas y dentro del TTL original deben abarcar los tiempos reales de la ejecución. Releer revocación después; comparar columnas y filas reales con el resultado determinista del snapshot. Si falla un control, no devolver filas verificadas.
6. Conservar linaje y emitir `publication_evidence_temporality=historical`, fecha real del readback, fecha real de observaciones y `identity_continuity=not_proven`, `aba_prevented=false`. No utilizar `scope_verified=true` hasta completar TODOS los controles.

La revocación usa el estado protegido ya existente `<binding>.status.json`: operador propietario escribe `revoked`, App sólo lee. Relectura antes/después sin caché; no reactivar automáticamente ni sobrescribirlo al admitir el modo. Un estado ausente/ilegible es fail-closed. La administración puede retirar el modo mediante configuración; el usuario ordinario no necesita operar certificados. La prueba real de revocación se realiza al final, sobre binding aislado o con restauración explícita revisada, nunca dejando el App revocado accidentalmente.

## Riesgos que siguen abiertos

Identidades iguales antes/después no prueban continuidad: un cambio ABA entre observaciones puede escapar. El perfil NAMED tampoco acredita relación física UUID Delta/location por GET. Un conteo igual no demuestra identidad de todo el contenido actual. Son límites conocidos y visibles, no problemas resueltos por el nuevo modo; la afirmación se limita al conteo ejecutado con SQL exacto sobre la versión/identidad observadas bajo administradores confiables. Retención/VACUUM o sustitución de tablas puede romper disponibilidad y debe producir error claro. No se garantiza uptime del warehouse, proveedor o App. La autorización administrativa hasta revocación es un cambio de política material, sujeto a aceptación independiente.

## Archivos exactos previstos (no modificados por esta propuesta)

- `src/sbs/genie/publication_rotation.py`: selección explícita de generación histórica fijada, validación histórica completa y revocación; modo legacy por defecto intacto.
- `src/sbs/genie/server_rotation.py`: configurar capacidad histórica sólo desde archivos pinned, propagar scope count-only y política operativa. Integrar, sin sobrescribir, el overlay de diagnóstico220 si se aprueba.
- `src/sbs/genie/governance.py`: variante explícita de política hasta revocación; reutilizar collector y pre/post sin alterar los perfiles temporales existentes.
- `src/sbs/genie/delta.py`: distinguir prueba histórica de cobertura temporal vigente; preservar todas las validaciones restantes y linaje temporal explícito.
- `src/sbs/genie/__init__.py`: guard counts-only antes de despacho y etiqueta histórica en resultado, sin alterar SQL/AST/filas.
- `config/genie-rotation-098.json`, `config/genie-bootstrap-098.json`: nuevos pins/mode y propagación del hash; nuevo `config/genie-snapshot-count-policy.json` como política explícita. Chunks manifest actualiza sólo archivos realmente empaquetados.
- `tests/unit/test_immutable_snapshot_counts.py`: pruebas del contrato adjunto; regresión de perfiles existentes. SK06 y SK08 enlazarían este refinamiento sólo después de revisión/RED/GREEN, sin declarar validación E2E.

No necesita nuevo publicador33SQL, scheduler, nuevos grants, escritura de tablas ni reinicio periódico. Requiere una actualización revisada de App para habilitar la capacidad; después el mero paso de5/30 minutos no la invalida. Si219 no conserva toda la prueba exigida, parar y explicar la brecha, no fabricar evidencia.

## Reposición opcional de inferencia en el mismo epoch

Hoy NO está soportada: `activate` rechaza una segunda activación y SQLite fija epoch único. Genie de conteos no debe consumir generación/embedding; medir ese hecho antes de ampliar cuotas. Esta opción se implementaría sólo si el saldo real no permite entrega útil.

Preservar las tres reservas210/214/218 (22 generation,21 embedding,210000 tokens), además del baseline conservador y tentativa externa desconocida; no confundir reservas con consumo facturado. Añadir tabla append-only de extensiones al mismo ledger, sin migrar ni reescribir allocation. Cada extensión firmada contiene tipo/version, epoch exacto, activation_id inicial, hash/id de extensión anterior, sequence contiguo, extension_id único, issued_at, expiry IGUAL a la activación original, y deltas positivos de cuotas autorizados expresamente. No inventar ahora una cantidad adicional.

El coordinador, bajo transacción SQLite FULL, reserva durablemente todo el delta antes de entregar la firma. Runtime verifica firma, epoch, secuencia, padre y plazo; suma límites, conserva contadores usados y fecha de expiración original. Duplicado exacto devuelve acuse idempotente sin sumar; mismo ID con otros bytes, replay/out-of-order, epoch ajeno o expirado se rechaza. Si se pierde respuesta, reenviar el mismo sobre es seguro; ninguna nueva reserva ni refund. Reinicio genera epoch nuevo inactivo y exige nueva reserva explícita: las extensiones viejas no transfieren presupuesto. No prometer persistencia de contadores del proceso tras reinicio.

Archivos opcionales: `src/sbs/app133/lifecycle210.py`, webapp rutas/controles administrativos ya existentes (el POST activate puede discriminar un tipo explícito de extensión sin nuevo endpoint), adaptador de presupuesto de generación/embedding para que límites internos no bloqueen la cuota firmada, nuevo `deployment/allocation_extension.py`, `tests/unit/test_allocation_extension.py`. Usar el mismo private key local0600 y public key; nunca incluir key privada en paquete/logs. Revisar límites internos además del budget central: cambiar sólo status sería falso. La extensión no prolonga las8h; renovación del plazo es otro alcance, aún no diseñado/aprobado.

## Secuencia de decisión y aceptación

SK09 revisa esta especificación y matriz congelada antes del código; aceptar expresamente política hasta revocación y límites ABA. Luego tests RED sobre expiración original y guard scope; implementación mínima; regresiones locales. Preparar un único delta desplegable con baseline activo observado y revisión independiente, sin stop/start. No ejecutar cloud desde esta propuesta.

Aceptación real: contar ambas familias, seguimiento contextual, versión ejecutada/historial/filas verificados; repetir tras >5 y >30 minutos del readback original, con hora real y sin republicar/re-fechar; probar revocación y denegación fail-closed de forma aislada; conservar originales. En la entrega indicar saldo real y fecha de cierre de inferencia. No atribuir PASS operativo a fixtures ni a aceptación offline con reloj antiguo.
