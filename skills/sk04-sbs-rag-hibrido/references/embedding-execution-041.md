# 041 — completar vectores documentales026, sin promover índice

Brief CreatorZ, 2026-09-28. Reutilización local: `data/retrieval/structural-development-026`, `VerifiedEmbeddingCache`, `src/sbs/models/databricks.py`, `skills/sbs-rag-hibrido/scripts/run_real_pilot.py` y preflight001. No búsqueda, descarga ni inferencia. Brecha comprobada:026 tiene231 misses; `DatabricksEmbeddingAdapter` reserva cuotas sólo en memoria y el piloto existente no es un ejecutor específico/durable para026. Alternativa descartada: reiniciar adapter tras fallo sin journal duplicaría intentos. No se reconstruye corpus ni se cambian criterios018/028.

## Artefactos y comandos

Desde raíz del repositorio, preflight sin SDK/autenticación (crear archivo NUEVO):

```sh
PYTHONPATH=src .venv/bin/python -m sbs.retrieval.embedding_execution preflight --plan runs/sk04-embeddings-041-plan-reviewed.json
```

El plan concreto congelado es `runs/sk04-embeddings-041-plan-v2.json`, envelope SHA256 del payload `29b2909d6a050a3bc7e1210f1f0043fb6314689e50d058c3436f654a6165c87f`. Se conserva el primer plan como historial; v2 añade límite durable total de GET. No ejecutar ahora el comando siguiente. Tras revisión independiente y autorización humana explícita, el operador proporcionará un archivo local de autorización (no credencial) con `approved=true`, hash exacto del payload, `requests=29`, `inputs=231`, `reserved_tokens=108126` y `expires_at` Unix finito en futuro. La plantilla entregada tiene approved=false/expiry=null y no concede permiso.

```sh
PYTHONPATH=src .venv/bin/python -m sbs.retrieval.embedding_execution execute --plan runs/sk04-embeddings-041-plan-v2.json --authorization runs/sk04-embeddings-041-authorization.json
```

Perfil normal `databricks-ai-engineer-aws`, host fijado `https://dbc-0410b264-20c7.cloud.databricks.com`; no secretos en plan/registro. Salida propia `runs/sk04-embeddings-041-vectors/`. La factory real es lazy: sólo construye WorkspaceClient después de validar autorización, cierre y journal. La importación/preflight no construye clientes. Cambio de host/plan/texto/cuotas/salida invalida hash autorizado.

## Presupuesto y observaciones

-231 entradas completas, dimensión1024,106278 tokens locales;8 reserva por entrada =>108126. Máximo2595tokens local por unidad; sin truncado.
-29POST:28 lotes de8 y uno de7. Reutiliza batching001 observado; no afirma techo universal del servicio.
-Una GET metadata por invocación de factory, máximo3 intentos por journal entre resumes. Cada GET tiene intención durable, timeout45s, sin redirects/retries y respuesta máxima1MiB. Los POST usan SingleShotTransport existente:45s por request sin retries/redirects; no ofrece límite de bytes de respuesta, declarado aquí. Deadline bloquea admisión tras autenticar; no cancela requests ya en vuelo ni garantiza duración total/costo de servidor.
-Coste monetario y hash de pesos remotos: null. Reserva local no cap de facturación; una respuesta cuyo uso observado supera reserva se conserva y bloquea siguientes lotes. Falta de usage no se rellena con cero.
-Modelo esperado exacto `qwen3-embedding-0-6b-112025`, endpoint `databricks-qwen3-embedding-0-6b`; bundle de ejecución histórico `242864ee8bbf14ac68fe6e27f3cb3d519eaf3d1d500c2b685610e17511c1202a`. Corpus estructural se identifica separadamente. No cambiar identidad para fabricar compatibilidad.
-La GET futura compara campos endpoint/task/config_version/modelos del método003/001. El hash config036 usa otra serialización, no se compara como prueba de drift. Los campos iguales tampoco prueban continuidad de pesos, ABAC o permisos de inferencia. Si difieren, detener y conservar observación; ninguna GET se ejecutó en041.

## Persistencia, errores y límites

Cada intento tiene intención exclusiva fsync archivo+directorio antes de inferir. Resultados sellados conservan input/batch/plan/modelo, vectores, usage y latencia del adapter. Lock local evita dos procesos cooperativos. No es journal distribuido ni prueba de durabilidad ante fallo físico. Sólo resultados validados se saltan al reanudar; intención sin resultado, resultado fallido/ambiguo, dimensión/modelo incorrectos o hash alterado bloquean antes de nuevos intentos. No reintento automático ni nueva carpeta para evadir cuotas. Autoridad y salida están fijadas en plan; un nuevo alcance tras ambigüedad exige decisión explícita, no aprobación inferida.

El documento/vector se valida por texto íntegro y modelo, no sólo citation_id. Entradas y caché históricos quedan intactos. El archivo final sólo reúne vectores en orden de passages; **no construye índice, no mezcla las tres queries cacheadas ni promueve runtime**. Continuidad remota y futura combinación se resolverán con SK05 separadamente. Dataset expuesto no es holdout y qrels no cambian.

Pruebas técnicas: autoridad ausente/expirada/caps, cierre alterado, intención no durable, fallo ambiguo y resume, resultado alterado/no finito, uso excedido y deadline después autenticación antes GET/POST. El transporte y SDK simulados se etiquetan fixture; el tokenizer/preflight real es local. RED import demuestra componente ausente, no fallo del servicio. No se atribuye mejora conductual general a SK04 ni disponibilidad cloud.


## Resolución técnica E41-01/02 (misma0.1.4 provisional)

SK09 reprodujo un journal con batch0 ausente y batch1 conservado: el ensamblaje por orden de llegada invertía vectores/IDs. Reanudar exige ahora un prefijo contiguo de recibos; cualquier intento posterior a un hueco bloquea antes de factory/inferencia. No intenta completar huecos automáticamente.

En fallo se conserva un subconjunto tipado de last_attempt: stage cerrado, HTTP100–599 entero exacto, código normalizado por EmbeddingServiceError, contadores/uso enteros no negativos (bool/float rechazados), latencia finita acotada, dimensiones/índices con máximo8 elementos. Sólo se conserva el nombre de modelo si coincide con el esperado; otro nombre se registra null, no se copia una cadena desconocida. Nunca se guardan mensajes de excepción, headers, cuerpos o claves adicionales. Esto mejora diagnóstico seguro sin atribuir resultado real a fixtures.

Evidencia: runs/sk04-embeddings-041-fix-red.txt (9 fallos) y fix-green.txt (59 tests). Plan/budget, dataset y revisión original intactos; no inferencia ni permisos nuevos.
