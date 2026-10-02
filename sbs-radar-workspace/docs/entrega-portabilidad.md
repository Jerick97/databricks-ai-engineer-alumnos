# Portabilidad local: corpus y modelos

El paquete completo conserva los seis PDFs, derivados, informes sellados, contratos y recursos de skills. `sbs.paths.project_path` reubica exclusivamente rutas del proyecto histórico conocido dentro de la nueva raíz; rechaza rutas ajenas, traversal y symlinks externos. Los informes originales no se reescriben para moverlos.

Para materializar modelos ya disponibles localmente, indicar explícitamente la raíz del caché HF:

```sh
python3 deployment/materialize_models.py --cache-root /ruta/explicita/huggingface/hub
```

Para crear el paquete autocontenido después de materializar, ejecutar `python3 deployment/build_bundle.py --include-models`. Produce `runs/sk12-review-bundle-models.tar.gz` y `runs/sk12-release-manifest-models.json`; no agregar los pesos a Git. Sin ese flag, el bundle conserva su variante ligera.

Este comando no descarga archivos, no abre credenciales ni consulta endpoints. Copia siete artefactos fijados por revisión y SHA-256 a `data/models/<repo>/<revision>/`. Incluye el tokenizer Qwen y el cross-encoder ONNX qint8 ARM64; no incluye pesos Qwen porque la generación de embeddings del piloto usa un endpoint remoto. `data/models/manifest.json` documenta archivos, tamaños y manifiestos de procedencia. Un archivo presente con hash distinto provoca error; no se oculta con un fallback al caché.

`resolve_model_manifest(manifest, root=raiz)` devuelve una copia con rutas verificadas bajo esa raíz. Su argumento opcional `cache_root` permite un caché explícito, pero un snapshot autocontenido debe funcionar sin él. El runtime usa este mapa; el manifiesto histórico y su hash permanecen intactos.

Las dependencias exactas observadas están en `deployment/requirements-models-arm64.txt`. La prueba real cargó el peso ONNX fijado en `CPUExecutionProvider` sobre Darwin ARM64 desde otra raíz, sin inferencias nuevas ni descargas. No certifica Linux/x86 ni Databricks. No se sustituyeron pesos por otra cuantización ni se generaron embeddings nuevos. Antes de otro destino, verificar disponibilidad de sus wheels y cargar/probar el artefacto exacto; cualquier cambio de peso requiere manifiesto, índice/model bundle compatible y evaluación propia.

La comprobación de arranque trasladado lee catálogo, tres comparaciones y fuentes reales mediante HTTP local con endpoints de modelos deshabilitados. Demuestra portabilidad de lectura del backend; no equivale a conversación remota, recorrido visual, autenticación cloud ni E2E. La configuración normal no debe activarse para probar portabilidad offline.

Evidencia de esta iteración: `runs/sk12-portable-app-check.json` registra 317 archivos, tres comparaciones y seis PDFs verificados por HTTP, con lecturas del proyecto original/caché HF y conexiones remotas bloqueadas durante la prueba. El archivo incluye SHA-256 del bundle exacto probado; posteriores cambios de runtime/auth requieren regenerar y repetir. `runs/sk12-portable-model-check.json` conserva la carga CPU separada. No se probó instalación de dependencias en un entorno Python limpio.
