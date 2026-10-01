# SK05 — modelos y adaptador Qwen Databricks

`ModelManifest` valida el contrato SK01, congela configuración como JSON canónico,
calcula `bundle_hash` y rechaza sobrescribir un manifiesto existente. El hash es
de configuración, nunca de pesos remotos. Un corpus, prefijo, tokenizer, modelo
u otra configuración nuevos requieren un bundle nuevo.

## API para SK04

```python
from databricks.sdk import WorkspaceClient
from sbs.models import ModelManifest
from sbs.models.databricks import (
    PinnedQwenTokenizer, SingleShotTransport, DatabricksEmbeddingAdapter,
)

# bundle: configuración completa SK01; pin: revisión y hashes ya aprobados.
manifest = ModelManifest.from_bundle(bundle)
tokenizer = PinnedQwenTokenizer(
    pin['files']['tokenizer.json']['path'],
    revision=pin['revision'], sha256=pin['files']['tokenizer.json']['sha256'],
)
client = WorkspaceClient(profile='databricks-ai-engineer-aws')
adapter = DatabricksEmbeddingAdapter(
    manifest, tokenizer, transport=SingleShotTransport(client),
    max_calls=authorized_call_limit, max_tokens=authorized_token_limit,
)
# Las operaciones siguientes hacen inferencia y consumen el alcance autorizado:
# vectors = adapter.embed_documents([('prefijo explícito: ', 'contexto y span íntegro')])
# vector = adapter.embed_query('consulta')
```

- `identity`: `manifest.bundle_hash`; `dimension`: dimensión del bundle.
- `embed_documents(list[tuple[str,...]]) -> list[list[float]]`: concatena cada
  tupla sin insertar separadores, conserva todos sus caracteres y no envía
  `instruction` al endpoint. El llamador proporciona separadores en sus partes.
- `embed_query(str) -> list[float]`: envía una consulta y la `query_instruction`
  congelada en `parameters`; devuelve un único vector.
- `embed(texts, role='document'|'query')`: API base con vectores, uso observado,
  identidad, preflight, latencia y coste desconocido `null`.
- `token_counter`: `TokenCounter` para documentos, cuenta las partes completas
  concatenadas incluyendo tokens especiales del tokenizer.
- `query_token_counter`: añade `Instruct: {query_instruction}\nQuery:{query}`
  antes de contar. El texto y la instrucción se mandan separados a Databricks;
  la plantilla de conteo viene del autor Qwen y no acredita la serialización
  interna exacta del servicio.
- `preflight(texts, role=...)`: conteos por entrada y reserva de 8 tokens por
  entrada por defecto. `embed` verifica además cuota acumulada de tokens y
  llamadas antes del transporte. No hay truncado ni fallback.
- `last_attempt`: diagnóstico separado de uso y configuración; guarda etapa,
  modelo de respuesta, cantidad, dimensiones, índices, uso y latencia con lista
  permitida de campos. Nunca guarda cuerpo arbitrario, secretos o vectores.

El adaptador solo acepta `databricks-qwen3-embedding-0-6b` y dimensiones potencia
de dos entre 32 y 1024. `parameters` debe incluir `tokenizer_sha256`, la revisión
congelada, `document_prefix=''`, `query_prefix='Instruct: '` y
`query_instruction` no vacía y `expected_response_model` exacto, además de la
identidad requerida por el manifiesto. Un pin ausente bloquea el adaptador. El
nombre del endpoint (`databricks-qwen3-embedding-0-6b`), la identidad de su
configuración (`system.ai.qwen3-embedding-0-6b`) y el modelo reportado
(`qwen3-embedding-0-6b-112025`) son campos distintos. No se aceptan prefijos
arbitrarios ni alias del endpoint como sustituto del modelo esperado.
Las variantes de prefijo suministradas en los inputs requieren identidad de
chunking/corpus coherente en el bundle y el índice del llamador.

Las cuotas son por instancia/proceso. No restauran automáticamente un presupuesto
entre procesos y no conceden autorización monetaria. Una llamada fallida consume
la cuota de intento; no hay reintentos automáticos ni redirecciones HTTP. Se usan
credenciales por el mecanismo normal `WorkspaceClient.config.authenticate()`.
El transporte Requests evita los reintentos POST automáticos del cliente API SDK.

## Evidencia y límites

`runs/sk05-qwen-tokenizer.json` fija el repositorio público y sus tres archivos:
revisión `97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3`. La configuración del tokenizer
anuncia un máximo diferente del contexto del modelo: se usa el límite documentado
de 32768, no ese máximo genérico. Los archivos se leen del cache local después de
verificar su hash. No se descargaron pesos ni se atribuyó su hash al endpoint.

`runs/sk05-qwen-smoke-bundle.json` es configuración serializable y sin
credenciales, exclusiva del corpus de dos textos públicos de prueba. Sus modelos
de generación/reranking están explícitamente sin seleccionar; no representa un
bundle SBS de producción.

Los intentos se conservan por separado. El 001 perdió la granularidad del fallo;
no se reconstruyó su respuesta. El diagnóstico 002 identificó `response_model`:
el adaptador confundía el nombre del endpoint con el modelo de respuesta. El
bundle `runs/sk05-qwen-smoke-bundle-v2.json` fija el modelo exacto observado y
conserva la configuración, fecha y procedencia de cada identidad por separado.

La prueba 003, expresamente autorizada después de la corrección, realizó una
sola solicitud con los mismos dos documentos públicos: 23 tokens locales y 23
reportados por el servicio, 39 tokens reservados contando el margen, dos vectores
válidos de 1024 dimensiones. Se conservan en
`runs/sk05-embedding-smoke-003-vectors.json`; el hash y la latencia están en
`runs/sk05-embedding-smoke-003.json`. El coste monetario sigue desconocido. Esto
acredita esa inferencia documental breve; no acredita consultas, calidad de
recuperación SBS, límites máximos del modelo, generación, reranking o E2E.
Los intentos 001/002 y el bundle revisión 1 permanecen intactos.

Fuentes verificadas para esta implementación:
- https://docs.databricks.com/aws/en/machine-learning/foundation-model-apis/api-reference#embeddings-api
- https://docs.databricks.com/aws/en/machine-learning/foundation-model-apis/supported-models
- https://huggingface.co/Qwen/Qwen3-Embedding-0.6B
