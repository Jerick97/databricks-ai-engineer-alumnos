---
name: sk12-sbs-despliegue-e2e
description: Empaqueta, ejecuta y verifica notebooks, despliegue y recuperación E2E de SBS Radar. Usar para una entrega operativa, preflight de destino, release, rollback o aceptación completa; no para una comparación normativa aislada.
---

# SK12 — Despliegue y E2E

Versión 0.1.16 provisional. Creada mediante skill-creator-z tras baseline. [Brief](references/research-brief.md), [riesgos](references/requirements-risks.md), [casos](evals/cases.json).

## Contrato

Entrada: spec y matriz de requisitos, componentes/versiones probados, corpus, ModelBundle, referencias SK09, configuración de destino y alcance autorizado. Salida: paquete de release, notebook ejecutado, app probada, runbook/recuperación y veredicto por requisito. No reducir «terminado» al subconjunto que ya funciona.

## Preparar y ejecutar

1. Invocar SK00 para fijar hashes y capacidades observadas; verificar configuración actual, no asumir que el workspace conserva estado de clase. Usar namespace propio y conservar recursos ajenos.
2. Preparar notebook con parámetros explícitos, paths/configuración entregables y preflight accionable de warehouse, endpoints, credenciales normales y recursos. No escribir secretos. No depender de celdas ejecutadas fuera del notebook ni variables ocultas de otra sesión.
3. Fijar dependencias y entrypoint de app, esquema de configuración y manifiesto del release. Validar importaciones y ejecución en entorno limpio compatible. Registrar diferencias entre desarrollo local y runtime Databricks.
4. Antes de habilitar nuevos recursos facturables, resolver la autorización realmente faltante: el spec dice que US$100 es hipótesis, no permiso. Completar primero código, configuración revisable, recursos, estimación, límites y reversión. Reutilizar autorizaciones ya dadas; no volver a pedirlas ni extrapolarlas a recursos ajenos.
5. Ejecutar el notebook completo con la configuración que se entrega y corpus real de ambas familias. Conservar outputs, estado de jobs y errores; corregir y reejecutar celdas afectadas más dependencias. Un notebook generado o validado sintácticamente no cuenta como ejecutado.
6. Desplegar el paquete exacto autorizado y verificar estado, permisos y respuesta en UI real mediante SK10. La secuencia incluye fuentes, antes/después, implicancias propuestas, seguimiento y pregunta cruzada. Un status de API no reemplaza la interacción visible.
7. Ejecutar SK09 por familia para cambios, recuperación y conversación. Diferenciar referencia IA, tests técnicos, muestra real y gates no evaluados. No aprobar por promedio ni inventar ahorro humano, coste, cobertura o autenticación.
8. Probar recuperación en recursos/copia aislados: fijar release anterior, simular fallo controlado, restaurar referencias/configuración compatibles y comprobar consultas y datos. No borrar originales ni sobrescribir tablas compartidas. Separar rollback de código de recuperación de datos.
9. Entregar operación diaria a las 08:00 Lima y bajo demanda conforme spec, con idempotencia, trazas SK11, límites de consumo y procedimiento de fallo. Programación declarada no es job probado; no habilitar un gasto recurrente fuera de autorización.
10. Auditar requisito por requisito contra estado actual: artefactos, comandos, evidencia de runtime/UI, gates y límites. Mantener misión activa si falta evidencia; no declarar aceptación total por código local o modelos simulados.

## Refinamiento y entrega

Fallo reproducido→skill/componente propietario→corrección→prueba real. Publicar en el informe paths de notebook/app/configuración/evidencia y estado de cada gate. Mantener rollback verificable y conservar historia de pruebas fallidas.

## Refinamiento 0.1.1 — evidencia de intentos fallidos

Cada ejecución de notebook usa run_id nuevo y conserva notebook con outputs más JSON de estado, hashes y clase de error, incluso cuando una celda falla o el kernel lanza excepción. No sobrescribir una ejecución previa ni dejar su JSON exitoso como si describiera el intento nuevo. Publicar un puntero latest al intento actual, exitoso o fallido, y terminar CLI con código distinto de cero si falló. No imprimir mensajes de excepción completos en metadatos o consola; preservar la evidencia bruta en el notebook local.

Un hash_changed de SK00 tras editar un documento congelado es una detección esperada, no motivo para desactivar el gate. Restaurar el documento aprobado o realizar una revisión explícita del registro por su propietario; conservar el fallo y reejecutar después. Probar el ciclo éxito→fallo con historial intacto; los dobles de ejecución prueban persistencia, no notebook real ni aceptación E2E.

## Refinamiento 0.1.2 — portabilidad del runtime y modelos

No equiparar verificación offline de archivos con portabilidad de la aplicación. Extraer el snapshot completo en otra raíz y arrancar el backend real con endpoints deshabilitados; verificar catálogo, comparaciones y originales de ambas familias. Conservar hashes y rutas de la copia probada. Los informes sellados se mantienen intactos; resolver sus referencias históricas mediante una raíz explícita y contención, sin seguir symlinks fuera.

Empaquetar artefactos de modelos locales fijados por revisión y hash, reutilizando el caché existente solo desde una raíz explícita; no descargar pesos ni consultar credenciales para resolver rutas. Verificar bytes copiados y cargar el backend CPU real en el destino evaluado. Declarar arquitectura/SO/proveedor; éxito ARM64 local no acredita x86/cloud. Una sustitución de pesos o cuantización exige nueva identidad y evaluación, no corrección silenciosa de paths.

## Refinamiento 0.1.3 — dependencias del paquete

Al agregar un componente o configuración, incluir su cierre de archivos en el manifiesto de entrega: entrypoint, requirements y los datos referenciados por configuración. Probar desde el snapshot extraído con acceso al árbol original bloqueado; la mera presencia del módulo Python no prueba que sus tablas o configuración estén incluidas. Conservar manifiesto y hash exactos de la copia probada.


## Refinamiento 0.1.4 — metadata y estados transitorios

En creación con `no_compute=true`, separar intención, identidad creada, provisioning, estado de compute observado y coste. Aplicar [metadata-only](references/metadata-only.md). STARTING/UPDATING sin evidencia adicional no prueban compute activo ni justifican stop automático. Observar por GET acotados dentro del alcance vigente; el límite operativo no añade permisos ni impone una nueva aprobación. Stop exige actividad sustentada, identidad propia y transición aplicable; un400 no habilita reintentos automáticos. STOPPED solo acredita ese instante; coste desconocido=null.

Conservar intentos incomplete y errores aunque una observación posterior resuelva el estado. No atribuir detención a stops fallidos. Antes de reutilizar scripts de creación, exigir pruebas del tratamiento de transiciones y contención; este refinamiento documental no certifica un clasificador ni una mejora de comportamiento medida. Mantener estado provisional y límites E2E.


## Refinamiento 0.1.5 — comandos reproducibles dentro del paquete

ART14-01: incluir también los ejecutores referenciados por el runbook y sus dependencias de kernel; empaquetar solo notebook y outputs no hace ejecutable su comando documentado. Comprobar desde la copia extraída que ese mismo comando encuentra el runner, código y datos, y ejecutar el notebook allí. Conservar intentos y paquete anteriores. La app portable inicial y un notebook con runtime promovido son verificaciones distintas; no intercambiar su alcance ni afirmar UI/cloud por estos resultados.


## Refinamiento 0.1.6 — permisos observados no equivalen a HTTP200

MP01: en observaciones de grants conservar presencia de campos, assignments y existencia de paginación; HTTP200 solo acredita transporte exitoso. Una respuesta vacía no demuestra privacidad ni elimina accesos implícitos de propietario/administradores. Si un intento previo filtró esos campos, conservarlo y registrar un suplemento antes de repetir las GET necesarias. No convertir el suplemento en permiso para subir datos ni activar cómputo. Fijar identidad/parent/owner del recurso creado y separar creación de metadata, accesos verificados, publicación y coste. Ver `runs/sk09-metadata-post-015-review.json`; refinamiento por evidencia, sin mejora conductual medida.


## Refinamiento 0.1.7 — contratos por proveedor y diagnósticos útiles

Un campo opcional del SDK multiplataforma no acredita que el servicio AWS lo acepte en esa operación. Contrastar el request con la referencia oficial de proveedor/API concreto antes de crear identidades; el UUID devuelto no equivale siempre a un UUID que puede fijar el cliente. Guardar y revisar la propuesta corregida; nunca repetir una mutación ambigua ni adoptar por nombre.

Para requests limitados a metadata pública del proyecto, conservar código HTTP, código proveedor y detalle diagnóstico acotado/redactado cuando sea necesario para corregir el contrato. Nunca headers de autenticación, credenciales, excepciones crudas ni respuestas arbitrarias de documentos/modelos. Si un intento filtró el detalle, registrar esa limitación y no inventar la causa precisa. El400 de identidad016 se conserva; schema/name-onlyAWS016b es hipótesis fundada en documentación hasta ejecutar/readback, no arreglo confirmado.


## Refinamiento 0.1.8 — bytes del manifiesto y cierre del paquete

ART16-01: congelar entradas relacionadas antes del build. Leer cada archivo una sola vez y usar esos mismos bytes para hash y contenido tar; dos lecturas separadas permiten un manifiesto que no describe el archivo entregado. Verificar todos los miembros del tar contra su manifiesto después de construir. Una captura por archivo no equivale a una transacción entre varios archivos: mantener congelación y registrar drift. Incluir dependencia y consumidor juntos, o excluir explícitamente ambos del snapshot; no empaquetar un test cuyo helper queda fuera. Conservar intentos defectuosos y manifiestos previos como copias, no hardlinks.

Si el paquete final solo cambia documentación/estado, registrar el diff completo y distinguir el hash probado del hash final; no atribuir ejecuciones al tar nuevo. Repetir pruebas afectadas si cambia código/datos/dependencias. Prueba discriminante de carrera y verificación de cierre local no acreditan despliegue ni mejora conductual general de la skill.


## Refinamiento 0.1.9 — admisión, durabilidad y alcance

S17-01/02/03 ([revisión preservada](../../sbs-radar-workspace/runs/sk09-phase-s-017-review.json)): una autorización temporal se comprueba inmediatamente antes del efecto remoto, también después de autenticación que pueda consumir la ventana; no confundir ese gate con cancelar solicitudes en vuelo. Antes de POST dependiente de intención local, sincronizar archivo **y directorio**; sincronizar también creación/reemplazo de resultados. Un fallo de persistencia bloquea el efecto.

Separar la selección técnica del perfil de administradores confiables y sus supuestos no observados de la autorización humana real de gasto, start y ventana. No añadir una atestación del usuario sobre hechos administrativos hipotéticos ni presentarlos como observados. Preservar checks concretos de identidad, permisos, políticas visibles, contenido e historial. Referencia de alcance: [decisión SK00](../../sbs-radar-workspace/runs/sk00-phase-s-017-scope-decision.json). Tests locales de contrato no prueban durabilidad ante power loss ni mejora conductual general; revisión independiente y cloud permanecen separados.


## Refinamiento 0.1.10 — importación real antes de autenticar

SDK33-01: comprobar las importaciones reales del ejecutor contra la versión instalada y fijada, sin construir clientes ni autenticar. Los tests con config_factory inyectada no cubren ese camino. Para SDK0.102.0 usar Config exportado por databricks.sdk.core; el paquete raíz no lo exporta. Conservar el intento fallido y corregir solo la importación; mantener plan, autorización, ventana y journal. Una corrección local no prueba acceso cloud. Evidencia: runs/sk12-sdk-import-033-red.txt y runs/sk12-sdk-import-033-green.txt.


## Refinamiento 0.1.11 — estado de admisión no portable (histórico; política ampliada en 0.1.12)

PKG39-01: un snapshot de código/configuración no debe transplantar la autorización temporal ni los journals operativos del origen. Excluir exactamente `deployment/phase-s-017-authorization.json` y el árbol `deployment/state/` del builder; conservar planes, plantillas y evidencia histórica. No borrar originales ni generalizar la exclusión a cualquier nombre parecido. Probar ambas variantes del paquete en una raíz temporal, verificar miembros y SHA contra los mismos bytes del manifiesto, y comprobar conservación de near-misses/configuración. El paquete no renueva permisos ni demuestra ejecución cloud. [Brief acotado](references/package-state-039.md); evidencia RED/GREEN en `runs/sk12-package-state-039-*.txt`.


## Refinamiento 0.1.12 — capacidades temporales por namespace

PKG51-01: el filtro exacto039 dejó entrar nuevas autorizaciones050. Excluir los archivos del nivel raíz de `deployment/` cuyo nombre termina exactamente en `-authorization.json`, además de todo `deployment/state/`. Ese nivel es el namespace de admisión operacional; no fijar una sola fase/numeración ni leer contenido de capacidades para decidir. Conservar planes, configuración, plantillas `-authorization-template.json`, ejemplos `.json.example` y evidencia archivada en subdirectorios/history, docs y runs. Las capacidades futuras deben ubicarse en ese namespace o registrar explícitamente una política nueva; el filtro no acredita detección universal de secretos.

Usar `deployment/build_bundle.py:selected_paths()` para auditar cierre sin construir. Reproducir ambas variantes sobre árbol sintético temporal, verificando miembros/hashes y originales intactos. Los archivos del perfil049 no quedan incluidos por existir en runs: el audit051 detecta siete dependencias ausentes pese a incluir código/dataset. La opción `--include-structural-profile` incorpora sólo esos siete archivos fijados y falla si falta uno; no activa el runtime ni cambia el default. Probar desde copia extraída antes de llamar portable al perfil. No construir, publicar ni renovar autorización por este refinamiento. [Brief/evidencia051](references/package-capabilities-051.md).


## Refinamiento 0.1.13 — runner de renovación revisable

Para reanudar faseS con ventana expirada, usar [runner053](references/renewal-runner-053.md). Preflight local sin SDK ni writes, drift explícito y revisión técnica independiente separada de autorización humana persistente053. Emitir ventana30min sólo al ejecutar; archivar configuración antes/delta/después si se aplican hashes revisados. No silenciar drift de inputs ajenos ni cambiar plan/recursos/cupos.

Migrar con API052 y callback de authorize real, conservando binding original y ledger112/reserved3. Mantener AdmissionConfig tras autenticación y AdmissionStatements antes de SQL; CumulativeStatements052 reserva cuota pero no comprueba reloj. No añadir otro wrapper de presupuesto. Reiniciar sólo con GETSTOPPED nuevo y RUNNING previo confirmado, intent exclusivo durable y unaPOST; respuesta ambigua permite únicamente GET de reconciliación. No ejecutar el runner durante construcción/revisión; pruebas inyectadas no acreditan cloud.


## Refinamiento 0.1.14 — continuación posterior a readback fallido

No reutilizar un runner cuya admisión presupone journal virgen o reservas iniciales. El runner058 fija el último binding efectivo, el ledger acumulado51/112 y los ocho receipts, exige revisión056 y admisión058 de código/config exactos, e impide CREATE/INSERT antes de cualquier delegado. El perfil de identidad es capacidad explícita del servidor, no cambio de WriterConfig. Archivar config original, propuesta y delta de hashes; no silenciar divergencias.

Reutilizar timestamps de ventana vigente bajo la autonomía existente, con admisión actual antes de cada efecto. Validar autorización con hora actual; la reutilización no prolonga expires_at. Rechazar ventana activa con <=300000ms antes de escribir intent/config/auth/journal: el TTL mínimo del registro hace imposible publicarla. El margen mayor no garantiza completar antes del vencimiento; conserva admisión por efecto y límite TTL final. Si venció, emitir30min en execute y renovar append-only con policy efectiva y presupuesto intacto. Conservar una sola envoltura acumulativa052. GET actual del warehouse y sólo un POSTstart tras STOPPED y RUNNING histórico probado; un resultado ambiguo no se reintenta. Preflight no crea SDK/capacidad ni cambia estado. Evidencia local en runs/sk12-phase-s-058-record.json; no acredita certificado remoto ni Genie disponible.


## Refinamiento 0.1.15 — fuente reproducible y readiness por capacidad

Preparar la [entrega Apps070](references/app-release-070.md) reutilizando selector y configuración existentes, con modelos locales/pins y gzip reproducible. No transportar venv/macOS, secretos, autorización ni estado vivo. Source_code_path se deriva del hash bajo namespaceSBS; exactresources/env no otorgan permisos. Reconciliar069 y scopecurrentuser observado, sin claims SELECT-onlyM2M. Preservar evidenciaLinux fallida y defaultretrieval sin promover candidatos.

Una app puede servir fuentes/comparación sin inferencia, pero eso no acredita demo interpretativa. Respetar steering vigente: validar generación antes de start/deploy; Sol071rate0 es bloqueo real, no permiso para bypass. Genie necesita registro/política/pins actuales; TTL5min no se alarga para desplegar. Constructor070 produce plan revisable de un start/deploy máximo en App existente, sin ejecutarlo ni crear recursos.


## Refinamiento080 — selección Apps ligada a la muestra probada

Cuando la app necesita una selección de generación distinta del default, usar [contrato080](references/app-selection-080.md). La variable exclusiva del servidor tiene allowlist de archivos073/077; no recibir selección desde HTTP. Conservar runtime077 y default073. El entrypoint080 asigna la selección antes de inicializar modelos; el snapshot incorpora entrypoint, adaptador, selección y observación exacta. Un constructor sólo puede materializar paquete tras PASS_CONTROLLED_SAMPLE con cuatro respuestas reales, hashes, citas e identidad exacta; el preflight repite el gate antes de cualquier efecto.

Vincular plan→admisión→respuestas revisadas y todos los inputs de comportamiento del plan→bytes staged, incluidos prompt y observaciones. Rechazar mezcla073/075/077 y drift; las instrucciones de autoría pueden refinarse sin alterar bytes de comportamiento congelados. La revisión concreta de despliegue fija además manifiesto, plan operacional y código080 nuevo: no atribuir a la muestra077 la prueba de un entrypoint posterior. Tests sintéticos no son muestra real ni E2E; mantener gates UI, Linux, Genie, recuperación y operación diaria abiertos hasta evidencia propia.
