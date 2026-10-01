# SK05 — brief Creator Z (2026-09-27)

Intención: seleccionar, fijar y comprobar bundles de embedding/reranking/generación para SBS. Activa ante selección, cambio, presupuesto o compatibilidad de modelos; comparación normativa literal pertenece SK03.

Fuentes reutilizadas: spec v0.2, contracts/ModelBundle.json y estrategia-rag/strategies/span-limpio-contexto-v1.md (ruta exacta en AGENTS). Preferencia histórica no demuestra desempeño SBS. Separar span citable, entrada embedding y contexto de respuesta.

Brecha consultada hoy en fuentes primarias:
- https://docs.databricks.com/aws/en/machine-learning/foundation-model-apis/api-reference (actualización visible Sep11,2026): endpoints por tarea; respuesta incluye usage. Disponibilidad documental no comprueba permiso ni actividad del workspace.
- https://huggingface.co/intfloat/multilingual-e5-small/raw/main/README.md : candidato local multilingüe, licencia MIT; verificar revisión/tokenizer/límites en artefactos antes de ejecutar. La página HTML no pudo abrirse por tamaño; raw sí. No asumir benchmark externo válido para normativa SBS.
- https://huggingface.co/cross-encoder/mmarco-mMiniLMv2-L12-H384-v1 : crossencoder multilingüe sobre MMARCO, Apache2.0. Alternativa de reranking local; la tarjeta no acredita calidad normativa. El ejemplo del proveedor usa truncation=True: no copiarlo sin preflight de entrada completa.

Alternativas: endpoint administrado existente reduce instalación y permite integración Databricks; requiere autenticación/costo observables. Embedding+crossencoder local ofrece pruebas reproducibles sin crear cloudcompute, requiere recursos/librerías y evaluación equivalente. No elegir ganador aún. Crear adaptadores separados evita confundir selección de modelo con recuperación.

Decisión: SK05 produce manifest inmutable + informe de preflight/medición. Lectura de capacidades existentes autorizada por misión, sin imprimir credenciales. Un presupuesto propuesto no autoriza automáticamente recursos cloud nuevos. Precio desconocido se mantiene null. ModelBundle registra configuración; evidencia real adicional registra revisión verificable, prefijos, límites, runtime y hashes.

Evaluación: seis casos baseline/green; checks de identidad, límite de tokens, no mezcla, permisos y coste. Revisión independiente y casos nuevos antes de afirmar validación. Estado provisional: no medición SBS de candidatos ni endpoint comprobado todavía.
