# Entrega local SBS Radar

Estado: canal y notebook locales; snapshot revisable. No equivale a despliegue Databricks ni aceptación E2E.

## Ejecutar

Con Python 3.11 o posterior, desde la raíz completa del proyecto:

```sh
python3 -m venv .venv
.venv/bin/pip install -r deployment/requirements-local.txt
.venv/bin/python deployment/execute_notebook.py
PYTHONPATH=src .venv/bin/python app.py
```

Abrir `http://127.0.0.1:8090`. La UI necesita `sbs.runtime` y su configuración real. La lista de dependencias corresponde a verificación offline y canal: no instala pesos, tokenizer ni proveedores para inferencia nueva. El notebook puede ejecutarse sin runtime conversacional y termina con gates remotos explícitos. No exige rellenar `warehouse_id` para verificar archivos locales.

El ejecutor inicia un kernel real con el mismo intérprete Python que lo invoca y comunicación local IPC. No requiere registrar ni sobrescribir kernels de otros proyectos. La evidencia conserva kernel, conteo de celdas y hashes; revisar también los outputs del notebook.

## Artefactos y portabilidad

- `notebooks/sbs-radar-local.ipynb`: notebook fuente, cuatro celdas de código independientes de estado previo.
- `runs/sk12-notebook-latest.json`: apunta al JSON y notebook del último intento, con estado explícito y archivos únicos. Los nombres fijos anteriores son históricos; no usarlos como aceptación actual.
- `deployment/offline.py`: hashes de seis PDFs y del piloto sellado, 135 pasajes, contratos, identidad de índice y métricas de tres consultas de ambas familias. Cero inferencias nuevas.
- `deployment/build_bundle.py`: construye `runs/sk12-review-bundle.tar.gz` y manifiesto de archivos SHA-256. Es snapshot completo para revisión; regenerarlo después de integrar cambios. No contiene credenciales ni modelos descargados.

Un notebook o wheel aislado no basta: conservar `src/`, `contracts/`, `context/`, `config/`, `skills/`, `runs/` y `data/` en la misma raíz. Los contratos se cargan relativos a `src`. La caché de corpus requerida sí entra al bundle; `data/raw` y modelos de cachés externas no. El verificador remapea las rutas históricas absolutas de capturas al snapshot, valida contención y no reescribe informes sellados. Otros scripts históricos pueden conservar rutas absolutas; usar el entrypoint de entrega para esta verificación. `SBS_RELEASE_ROOT` permite seleccionar explícitamente la raíz desde Jupyter.

## Gates remotos y operación

`deployment.offline.remote_preflight(root)` solo lee configuración. Warehouse observado `828756322bedff37`, STOPPED: candidato pendiente, no asignación ni permiso para iniciarlo. Faltan autorización concreta de gasto, catálogo/space dedicados, grants de backend, verificación independiente de consultas y adapter de identidad cloud. App rechaza modo cloud. No se creó ni inició recurso.

Operación objetivo: diario a las 08:00 America/Lima y bajo demanda. No hay scheduler habilitado ni job probado. Antes de programar: verificar idempotencia sobre snapshot, límites y coste, alertas y recuperación aislada. El presupuesto US$100 del spec es hipótesis y no autoriza recursos nuevos.

Recuperación local: conservar bundle y manifiesto anteriores, detener solo la instancia loopback del proyecto, extraer el snapshot previo en otra carpeta, verificar hashes y ejecutar su notebook antes de arrancar su app. No sobrescribir corpus ni tablas. Esto describe rollback de código/configuración; recuperación de datos y job remoto requieren ensayo separado. La prueba de portabilidad solo acredita extraer y verificar snapshot en otra raíz.

La aceptación pendiente incluye navegador real, teclado/móvil, seguimiento, pregunta cruzada, error recuperable, evaluación de respuestas, permisos y recuperación E2E. Integridad de hashes y métricas guardadas no demuestra verdad jurídica ni aprobación experta.

Para inferencia local, `deployment/requirements-inference-local.txt` fija las dependencias observadas adicionales. Requiere configuración normal Databricks y las cachés de modelos fijadas en los manifiestos; no equivale a instalación limpia validada ni portabilidad cloud. El endpoint generador observado rechazó la prueba con HTTP403; la interfaz puede consultar originales, pero no se acredita conversación operativa.
