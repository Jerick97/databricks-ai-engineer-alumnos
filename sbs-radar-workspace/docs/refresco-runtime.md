# Del refresco a la consulta

El refresco preparado puede cargarse en `LocalService`: catálogo, originales, comparaciones y registros vectoriales proceden del nuevo release. Las páginas sin alineamiento semántico se muestran como cobertura parcial. La publicación de un conjunto no aprueba sus implicancias ni lo declara vigente.

## Prueba reproducible local

Preparar un entorno Python compatible e instalar `deployment/requirements-notebooks.txt` en él (el entorno de la prueba es `.venv`). Desde la raíz del proyecto, ejecutar `.venv/bin/python runs/sk12-execute-runtime-notebook.py`. El runner conserva un notebook con outputs y JSON por intento, incluidos errores; `runs/sk12-runtime-notebook-latest.json` señala el último.

El notebook `notebooks/sbs-radar-runtime-promotion.ipynb` prepara los seis PDF de ambas familias con los 135 vectores existentes, promueve el runtime, abre comparaciones y originales por HTTP local y rechaza una promoción corrupta conservando el anterior. No llama al generador. HTTP no acredita interacción visual ni calidad semántica.

## Consumo del release

`LocalService.from_release(state_root, pointer=...)` construye el servicio desde SK03/SK04/SK06 verificados. `service.promote_release(...)` prepara un candidato antes de cambiarlo bajo lock; sesiones y evidencias quedan separadas por snapshot. Autorización y lectura deben compartir ese lock. Mantener originales/materializaciones anteriores mientras existan lectores.

`materialize_release(store, receipt, destination)` descarga mediante Files y comprueba el cierre del recibo confiable, sin subir ni publicar. El llamador suministra un recibo obtenido del control propio; un hash por sí solo no autoriza su origen. El consumidor cloud ya está conectado a la fábrica y a requests; la ejecución remota sigue pendiente. No presentar pruebas con adaptadores simulados como un refresco cloud desplegado.

`create_service()` admite `config/runtime-release.json` del servidor: ausente o `{ "enabled": false }` mantiene el piloto inicial. Activo requiere `enabled`, `state_root` relativo al proyecto y `pointer` con `release_id` y `sha256`. Configuración activa inválida falla; no vuelve silenciosamente al piloto. No recibir estos paths desde preguntas o parámetros HTTP.

## Escritor cloud preparado

`notebooks/sbs-radar-cloud-writer.ipynb` ejecuta por defecto preflight local sin crear SDK. La rama de escritura utiliza `execute_from_config`, configuración fijada, identidad del run, tabla de control, Files y publicación CAS. Su ejecución cloud sigue pendiente; la prueba integrada local usa SQL/Files/Jobs simulados junto a PDF y vectores reales.

`deployment/refresh-job.json` es un **plan de bindings**, no un request Jobs. El candidato serverless evita inventar un cluster; debe verificarse habilitación y coste antes de ejecutar. `deployment/refresh-control.sql` prepara la novena tabla de control, separada de las ocho tablas normativas; solo se ha comprobado su sintaxis. La tabla se inicializa una vez y el backend verifica exactamente una fila: Delta no impone unicidad de esa fila por este DDL.

Crear el manifiesto de código antes de la configuración externa que lo referencia, para evitar ciclos de hashes. Observar y fijar IDs/ACL reales; no copiar IDs de pruebas. Mantener horario 08:00 America/Lima en PAUSED hasta autorización de recurrencia.

El driver mantiene `capture_mode="sealed"` por defecto. El modo explícito `remote` captura las URLs oficiales permitidas y conserva originales anteriores cuando cambian los bytes en una misma URL. Requiere estado local persistente; no asumir que el disco efímero de serverless conserva el historial. Si el control compartido tiene publicación previa pero falta ese estado, rechazar la continuación hasta recuperar una base compatible. Nuevos textos sin vectores compatibles quedan pendientes; no se invoca automáticamente un modelo facturable.

Una captura real de SBS2220-2025 confirmó los mismos bytes del original sellado; esto acredita esa descarga concreta, no que todas las normas estén vigentes. El descubrimiento registra candidatos con procedencia y mantiene separada su incorporación al corpus. Un release RAG nuevo sin mapa/publicación Genie compatible responde indisponibilidad explícita en esa ruta.


## Consumo cloud por solicitud

`config/runtime-cloud.json` es configuración exclusiva del servidor. Ausente o desactivada no crea SDK. Activarla exige identidad OAuth M2M de app, IDs observados de tabla/warehouse/volumen, política administrativa explícita, hashes y cuotas. El consumidor comprueba warehouse RUNNING antes del SELECT; no lo inicia. Revisa el puntero con intervalo mínimo y cuotas por instancia, materializa Files y promueve bajo lock. No crea Jobs, no escribe la tabla ni sube archivos. La continuidad de administradores se declara como supuesto; no se demuestra con una GET.

Los estados públicos son `disabled`, `pending`, `current`, `unavailable` y `quota_exhausted`. `current` significa que se observó la publicación disponible; no acredita vigencia jurídica ni verificación completa de bytes en cada consulta. Ante fallo se conserva el corpus anterior. La primera descarga es síncrona y acotada; el middleware usa threadpool. Los originales anteriores se retienen y el límite de promociones acota crecimiento por instancia.

La UI permite actualizar el catálogo y conserva selecciones válidas. Separa historial por snapshot y no muestra como anterior una respuesta obtenida sobre otro snapshot: pide actualizar y repetir. Este comportamiento requiere todavía recorrido visual real; las pruebas de JavaScript y HTTP no lo sustituyen.
