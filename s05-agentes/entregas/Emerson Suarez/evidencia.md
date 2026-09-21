# Evidencia S05 · Agentes

**Alumno:** Emerson Suarez
**Estado:** Completo
**Laboratorio:** Copiloto de Datos Neptuno con herramientas

> Este documento registra ejecuciones observadas y distingue explícitamente las demostraciones
> del instructor de los recursos administrados no desplegados por el alumno.

## Entorno y recursos

| Recurso | Valor o estado |
|---|---|
| Catálogo personal | `neptuno_emerson_suarez` |
| Schema de S05 | `neptuno_emerson_suarez.s05_agentes` |
| Endpoint generativo | `databricks-meta-llama-3-3-70b-instruct` |
| Genie Space ID utilizado | `01f1abfc72c01d3fa4040ad8ef137156` |
| Genie Space | `Neptuno S03 - Emerson` · catálogo `neptuno_emerson_suarez` |
| Compute | Serverless |
| Secret scope/key | No configurados; ejercicio opcional |
| Versiones resueltas | MLflow 3.16.0; databricks-openai 0.17.1; databricks-mcp 0.9.2; MCP 1.30.0; jsonschema 4.23.0 |

### Separación de fuentes

- Las UC Functions y el RAG leen el catálogo personal `neptuno_emerson_suarez`.
- El Genie Space accesible consulta el catálogo personal `neptuno_emerson_suarez`; el SQL
  generado en CP4 confirmó la tabla exacta.
- Los datos del MCP custom son sintéticos y no representan pedidos reales.
- El MCP externo consulta documentación pública de Microsoft Learn y no recibe datos Neptuno.

## CP0 · Configuración y observación

**Estado:** PASS

### CP0.1 · Validación

La configuración validó las tablas Gold requeridas y permitió crear o reutilizar el schema:

```text
neptuno_emerson_suarez.s05_agentes
```

Tablas requeridas:

- `neptuno_emerson_suarez.gold.ventas_por_categoria_mes`;
- `neptuno_emerson_suarez.gold.inventario_disponible`.

La ejecución de CP0.2 confirma que la lectura de Gold funcionó. No se crearon datos alternativos.

### CP0.2 · Caso reproducible observado

La consulta agrupó las ventas netas por categoría y año. Se observaron 24 filas. El notebook
seleccionó automáticamente la primera fila ordenada por año descendente y categoría:

```text
Caso reproducible: {
  'categoria': 'Bebidas',
  'anio': 2026,
  'venta_neta': Decimal('116024.88')
}
```

Este par observado se conserva como `EJEMPLO` para contrastar la UC Function, el agente y las
pruebas funcionales. No se sustituyó por una cifra tomada de las slides.

## CP1 · UC Functions y contratos

**Estado:** PASS

### CP1.1 · `ventas_categoria`

- [x] Función creada en `neptuno_emerson_suarez.s05_agentes`.
- [x] `COMMENT` conserva alcance, parámetros y exclusión de margen/costos.
- [x] El toolkit recuperó el contrato registrado desde Unity Catalog.

```text
neptuno_emerson_suarez__s05_agentes__ventas_categoria
required = [p_categoria, p_anio]
description = Lee venta neta con descuentos de una categoría y año en Neptuno. Requiere ambos
parámetros. No calcula margen ni costos. Devuelve JSON con fuente, filas y venta_neta; null si
no hay datos.
```

### CP1.2 · `productos_reponer`

- [x] Función creada en `neptuno_emerson_suarez.s05_agentes`.
- [x] Contrato de solo lectura y límite de 20 productos comprobado en la descripción.
- [x] El toolkit recuperó el contrato sin argumentos desde Unity Catalog.

```text
neptuno_emerson_suarez__s05_agentes__productos_reponer
required = []
description = Lista hasta 20 productos Neptuno que requieren reposición considerando stock y
unidades en camino. Solo lectura; no emite compras ni actualiza inventario.
```

### CP1.3 · Contratos de `UCFunctionToolkit`

- [x] Se descubrieron exactamente dos tools.
- [x] Se revisaron nombre, descripción, propiedades y parámetros requeridos.
- [x] Se guardaron las versiones reales del entorno.
- [x] Se creó el experimento MLflow del usuario.

```text
VERSIONES_ENTORNO: {"databricks-mcp":"0.9.2","databricks-openai":"0.17.1",
"jsonschema":"4.23.0","mcp":"1.30.0","mlflow":"3.16.0"}
Experimento MLflow: 379607119291968
```

El experimento creado corresponde a:

```text
/Users/emersonsuarez2904@gmail.com/S05-Neptuno-Agentes
```

Durante la ejecución apareció un `UserWarning` indicando que una dependencia creó una nueva
sesión Spark Connect en lugar de reutilizar la sesión predeterminada del notebook. La celda
continuó, recuperó los contratos y creó el experimento, por lo que se registra como advertencia
informativa y no como fallo. MLflow también mostró una recomendación opcional para almacenar
trazas en Unity Catalog; no es un requisito de S05.

### CP1.4 · Comparación SQL frente a tool

Entrada esperada a partir de `EJEMPLO`:

```json
{"p_categoria":"Bebidas","p_anio":2026}
```

Referencia independiente observada en CP0.2:

```text
venta_neta = 116024.88
```

- [x] La UC Function devolvió `filas = 5`.
- [x] La diferencia respecto a `116024.88` fue menor que `0.01`.
- [x] Se conservó la fuente declarada por la función.

```text
CP1 OK: {
  'categoria': 'Bebidas',
  'anio': 2026,
  'venta_neta': 116024.88,
  'filas': 5,
  'fuente': 'neptuno_emerson_suarez.gold.ventas_por_categoria_mes'
}
```

La salida de la UC Function coincide exactamente con la agregación SQL independiente observada
en CP0.2. Esto valida la fuente y el contrato antes de conectar el LLM.

## CP2 · ResponsesAgent y trazas

**Estado:** PASS · frontera, RAG, ejecución E2E y casos adicionales aprobados

### Frontera de ejecución

- [x] Una llamada a ventas sin año fue rechazada antes de consultar datos.
- [x] La herramienta inexistente `borrar_tabla` fue rechazada por la allowlist.
- [x] El agente quedó limitado a seis turnos y cuatro llamadas en CP2.2.

```text
RECHAZO esperado: neptuno_emerson_suarez__s05_agentes__ventas_categoria ValidationError
RECHAZO esperado: borrar_tabla ValueError
```

El primer rechazo prueba que `p_anio` es obligatorio y no puede completarse implícitamente. El
segundo prueba que una herramienta no incluida en la allowlist no llega al ejecutor.

### RAG reutilizado de S04

- [x] Se leyó `neptuno_emerson_suarez.rag.chunks_embeddings`.
- [x] Se validaron 17 chunks y todos sus vectores tienen 1.024 dimensiones.
- [x] Se configuró `databricks-qwen3-embedding-0-6b` para la consulta.

```text
RAG S04 conectado: 17 chunks; databricks-qwen3-embedding-0-6b
```

### Primera ejecución del agente

| Campo | Evidencia |
|---|---|
| Pregunta | ¿Cuál fue la venta neta de Bebidas en 2026? |
| Tool solicitada | `neptuno_emerson_suarez__s05_agentes__ventas_categoria` |
| Argumentos | `{"p_categoria":"Bebidas","p_anio":2026}` |
| Resultado | `ok=true`; venta neta `116024.88`; cinco filas; fuente Gold personal |
| Respuesta final | La venta neta de Bebidas en 2026 fue 116024.88, según la fuente `neptuno_emerson_suarez.gold.ventas_por_categoria_mes`, con 5 filas de datos. |
| Trace ID | `tr-67a2fce963f5790af63573d4197c9892` |
| Experimento | `379607119291968` · `/Users/emersonsuarez2904@gmail.com/S05-Neptuno-Agentes` |
| Estado y latencia | `OK` · 4.23 s en MLflow Trace UI |

- [x] La traza muestra `predict → llm_tool_decision → ejecutar_herramienta → llm_tool_decision`.
- [x] La respuesta coincide con el valor respaldado por la herramienta.
- [x] La respuesta no inventa moneda.

La vista **Details & Timeline** de MLflow mostró la pregunta del usuario, la ejecución de la
herramienta y la síntesis final dentro de una traza con estado `OK`. El aviso para migrar las
trazas a Unity Catalog es una recomendación de almacenamiento y no un requisito de S05.

### Preguntas adicionales requeridas

| Prueba | Pregunta | Resultado observado | Tool calls | Trace ID |
|---|---|---|---|---|
| Política de refrigerados | ¿En qué plazo se acepta una devolución de productos refrigerados y bajo qué condición? | 24 horas si existe evidencia de ruptura de cadena de frío; incluyó `documento_id` y `chunk_id` | `buscar_documentos` | Persistido en CP5 |
| Margen sin costos | ¿Cuál es el margen de rentabilidad de Bebidas en 2026? | Se abstuvo porque no existen datos de costos y ofreció consultar venta neta | Cero | Persistido en CP5 |
| Reformulación | ¿Cuánto vendimos de Bebidas? No he especificado año. | Solicitó el año necesario para responder | Cero | Persistido en CP5 |

## CP3 · MCP

**Estado:** PASS · managed, custom y external ejecutados; Secrets opcional no ejecutado

### MCP managed de UC

| Evidencia | Resultado |
|---|---|
| Servidor | `.../api/2.0/mcp/functions/neptuno_emerson_suarez/s05_agentes` |
| `tools/list` | PASS: descubrió `productos_reponer` y `ventas_categoria` con sus descripciones |
| Esquema inspeccionado | `neptuno_emerson_suarez.s05_agentes` |
| Tool invocada | `neptuno_emerson_suarez__s05_agentes__ventas_categoria` |
| Argumentos no sensibles | `{"p_categoria":"Bebidas","p_anio":2026}` |
| Resultado de `tools/call` | `isError=false`; venta neta `116024.88`; cinco filas; fuente Gold personal |
| Contraste con CP1.4 | Coincidencia exacta con la ejecución directa de la UC Function |

La respuesta MCP se recibió como contenido de texto estructurado y declaró:

```json
{
  "categoria": "Bebidas",
  "anio": 2026,
  "venta_neta": 116024.88,
  "filas": 5,
  "fuente": "neptuno_emerson_suarez.gold.ventas_por_categoria_mes"
}
```

La evidencia contiene tanto `tools/list` como una llamada real `tools/call`; no se limita a
enumerar contratos. MCP conserva los permisos y la identidad de Unity Catalog.

### MCP custom por `stdio`

| Prueba | Resultado esperado | Resultado observado |
|---|---|---|
| Tool descubierta | `estado_pedido_demo` | PASS: apareció en `tools/list` |
| `pedido_id=1001` | Respuesta exitosa, fuente `SINTETICO` | PASS: `estado=EN_PREPARACION`, `isError=false` |
| `pedido_id="no-entero"` | Rechazo por tipo inválido | PASS: error de validación Pydantic para entero, `isError=true` |

Respuesta válida observada:

```json
{
  "pedido_id": 1001,
  "estado": "EN_PREPARACION",
  "fuente": "SINTETICO"
}
```

La llamada inválida fue rechazada antes de ejecutar una operación válida porque el texto
`"no-entero"` no puede convertirse al tipo `integer` declarado por la tool. Los datos de este
servidor se identifican siempre como sintéticos y no representan pedidos reales de Neptuno.

### Secrets

**Estado:** Opcional, todavía no ejecutado.

Los widgets `secret_scope` y `secret_key` permanecen vacíos. No se ha creado ni recuperado un
secreto y no se declara una integración autenticada.

```text
Secrets: ejercicio opcional no ejecutado.
```

Si se realiza después, este documento solo registrará scope, key y éxito de lectura; nunca el
valor.

### MCP externo desde Serverless

```json
{
  "status": "PASS_IN_SERVERLESS",
  "execution_location": "DATABRICKS_SERVERLESS",
  "tools": [
    "microsoft_docs_search",
    "microsoft_code_sample_search",
    "microsoft_docs_fetch"
  ]
}
```

La conexión Streamable HTTP logró ejecutar `tools/list` y `tools/call` desde Serverless. Se
invocó `microsoft_docs_search` con una consulta pública sobre Azure Databricks y Unity Catalog
Functions. Entre los resultados se observó:

```text
Título: Unity Catalog functions MCP server
URL: https://learn.microsoft.com/azure/databricks/agents/mcp-tools/uc-functions
```

La documentación recuperada describe el servidor MCP managed de UC Functions, el gobierno por
permisos de Unity Catalog y el patrón de URL `/api/2.0/mcp/functions/{catalog}/{schema}/{function_name}`.
No se enviaron documentos Neptuno, datos del catálogo ni credenciales al servidor externo.

Este workspace no reprodujo el bloqueo DNS documentado por el material: la evidencia real tiene
prioridad y se conserva como `PASS_IN_SERVERLESS`. Además, se generó posteriormente el reporte
local obligatorio desde la laptop y se conserva en la carpeta de entrega.

### MCP externo desde la laptop

Comando previsto:

```powershell
uv run --with "mcp==1.30.0" python scripts/mcp_external_demo.py --output reports/mcp-external-local.json
```

| Campo | Evidencia |
|---|---|
| `status` | `PASS` |
| `execution_location` | `LOCAL_PC` |
| Endpoint | `https://learn.microsoft.com/api/mcp` |
| Versión MCP | `1.30.0` |
| Tools descubiertas | `microsoft_docs_search`, `microsoft_code_sample_search`, `microsoft_docs_fetch` |
| Tool invocada | `microsoft_docs_search` |
| Consulta pública | `Azure Databricks Unity Catalog functions` |
| Resultado con URLs | PASS; incluyó documentación de Microsoft Learn sobre UC Functions y MCP managed |
| Ejecución UTC | `2026-09-21T03:38:37.439065+00:00` |

El archivo fue generado mediante el script oficial y copiado a esta carpeta como
`mcp-external-local.json`. La copia y el original producido en `reports/` tienen el mismo hash
SHA-256:

```text
AE250B7EB188F4098001B361C01A35F793B1B4751C194FD2A7E783039AA7AA4A
```

## CP4 · Genie

**Estado:** PASS

### Intento inicial fallido

La primera llamada usó el ID incluido en el notebook:

```text
01f1a2b475f11570a24ad8fdd22efbf6
```

Resultado observado:

```text
NotFound: Space with id 01f1a2b475f11570a24ad8fdd22efbf6 not found
```

| Campo | Evidencia |
|---|---|
| Estado de la traza | `Error` |
| Trace ID MLflow | `tr-021b58dcb59dae878b43ea57c9b1b3f0` |
| Tipo de excepción | `NotFound` |
| Latencia | 0.14 s |
| Diagnóstico | El ID docente no existe o no está compartido en el workspace personal |

Los Genie Space IDs están acotados al workspace. No se sustituye el valor por un ID inventado:
primero se listarán los Spaces accesibles y se repetirá CP4.1 con uno real. Se conservarán tanto
este fallo como la posterior recuperación.

### Descubrimiento de Spaces accesibles

La API `w.genie.list_spaces(page_size=100)` devolvió dos recursos visibles:

| Space | ID | Warehouse | Decisión |
|---|---|---|---|
| Neptuno S03 - Emerson | `01f1abfc72c01d3fa4040ad8ef137156` | `a86d594f125f0a5b` | Seleccionado para recuperar CP4 |
| Bakehouse Sales Starter Space | `01f1a02eba751dd4b67800730885c4a5` | `a86d594f125f0a5b` | Descartado: dominio ajeno a Neptuno |

El siguiente intento debe usar `Neptuno S03 - Emerson`. La fuente y tablas efectivamente
consultadas se confirmarán a partir del SQL que produzca CP4.1; no se presuponen antes de verlo.

### Llamada directa

| Campo | Evidencia |
|---|---|
| Space | `Neptuno S03 - Emerson` |
| Space ID | `01f1abfc72c01d3fa4040ad8ef137156` |
| Catálogo fuente real según SQL | `neptuno_emerson_suarez` |
| Pregunta | ¿Cuál es la venta neta total de abril de 2026? Muestra el SQL. |
| Conversation ID | `01f1b57011ca11a8a11f65748ec2c2e6` |
| Attachment ID de consulta | `01f1b57013d71afc9a2734d7c0f33142` |
| Statement ID | `01f1b570-13e6-1ba1-8b93-d40cb7df7040` |
| Estado SQL | `SUCCEEDED` |
| Filas | 1, sin truncamiento |
| Resultado | `123798.69` |
| Fuente declarada corregida | `Genie Neptuno S03 - Emerson / neptuno_emerson_suarez` |
| Trace ID MLflow | `tr-3292e4e17cd6774b33a0f7655b4f69cc` |
| Estado y latencia | `OK` · 13.19 s |

SQL observado:

```sql
SELECT ROUND(SUM(`ingreso_neto`), 2) AS venta_neta_total_abril_2026
FROM `neptuno_emerson_suarez`.`gold`.`ventas_por_categoria_mes`
WHERE YEAR(`mes`) = 2026 AND MONTH(`mes`) = 4
```

La recuperación del fallo inicial quedó demostrada: se sustituyó el ID inexistente por un Space
visible, se generó SQL sobre la tabla personal y la consulta terminó en `SUCCEEDED`.

### Corrección aplicada antes de integrar Genie al agente

El primer handler devolvía el texto fijo:

```text
Genie Ventas Neptuno AI / neptuno_ai
```

Esa etiqueta contradecía el SQL real. En la copia personal se sustituyó por:

```text
Genie Neptuno S03 - Emerson / neptuno_emerson_suarez
```

La nueva ejecución declaró la fuente correcta y volvió a producir SQL `SUCCEEDED` sobre
`neptuno_emerson_suarez.gold.ventas_por_categoria_mes`.

La primera síntesis directa de Genie había mostrado `$123,798.69`, aunque la tabla no declara
moneda. Tras la corrección y nueva conversación, la síntesis mostró `123,798.69` sin símbolo
monetario, conservando valor, período, tabla y SQL.

### Genie invocado por el agente

| Campo | Evidencia |
|---|---|
| Pregunta | Usa el espacio Genie curado: ¿cuál fue la venta neta total de abril de 2026? Identifica el catálogo fuente. |
| Tool call `consultar_genie` | PASS; llamada real registrada en `custom_outputs["herramientas"]` |
| Respuesta | La venta neta total de abril de 2026 fue de 123,798.69, según el catálogo `neptuno_emerson_suarez` en Genie Neptuno S03. |
| Trace ID | `tr-07b2d53771a32ea444aa5d4a1a42d405` |
| Estado y latencia | `OK` · 20.71 s |

La traza confirmó la secuencia:

```text
predict → llm_tool_decision → ejecutar_herramienta → consultar_genie → llm_tool_decision
```

El agente conservó valor, período y catálogo fuente, y no añadió símbolo ni nombre de moneda.
La integración fue una llamada real desde el agente; no una conversación manual aislada en Genie.

## Agent Bricks y ALHF

**Estado:** PASS · actividad de comparación y feedback completada; servicios administrados no desplegados

La consigna de S05 no exige crear o desplegar los tres servicios administrados. Se revisó el
recorrido documentado en `docs/AGENT-BRICKS.md` y la demostración sanitizada del instructor en
`reports/demo-bricks.json`. Se distingue explícitamente entre una ejecución observada, una
capacidad visible en la interfaz y un recurso realmente desplegado.

### Comparación de capacidades

| Necesidad | Capacidad candidata | Entrada y salida | Prueba exigida | Disponibilidad observada |
|---|---|---|---|---|
| Políticas con citas | Knowledge Assistant | Documento → respuesta sustentada | Sin evidencia debe abstener | Disponible en la UI del workspace personal; no creado ni ejecutado |
| Orden a campos | Information Extraction | Documento → campos tipados | Campo ausente no se inventa | Disponible en la UI personal y demo del instructor `SUCCEEDED` mediante `ai_extract` 2.1 |
| Ventas y políticas | Supervisor | Pregunta → delegaciones → síntesis | Conserva fuentes de ambos dominios | Disponible en la UI del workspace personal; no creado ni ejecutado |

La demostración de Information Extraction utilizó un texto de la política de devoluciones y
produjo una salida estructurada sin error:

```json
{
  "plazo_horas": 24,
  "condicion": "si existe evidencia de ruptura de cadena de frío",
  "error_message": null
}
```

Una captura del workspace personal confirmó que **Create new Agent** ofrece Supervisor Agent,
Information Extraction, Knowledge Assistant, Code your own agent, Genie Agent, Document Parsing
y Text Classification. El recorrido del instructor mostró además que el formulario del
Supervisor permite agregar un Genie Space, Knowledge Assistant, UC Function, UC Connection o UC
MCP Service. No se guardó ni desplegó ningún recurso y no se afirma lo contrario.

Captura conservada: [`agent-bricks-disponibilidad.png`](agent-bricks-disponibilidad.png).

### Feedback humano accionable

Problema observado o caso de diseño:

```text
Ante una solicitud de margen, una respuesta que entregue venta neta o invente un porcentaje es
incorrecta. No existen costos en las fuentes disponibles; debe explicar esa limitación y no
producir una cifra de margen.
```

Pregunta para comprobar la corrección:

```text
¿Cuál es el margen de rentabilidad de Bebidas en 2026?
```

Resultado esperado: cero herramientas, explicación de que faltan costos y ninguna cifra de
margen. El caso `sin_costos` de CP5 confirmó este comportamiento en el agente propio.

Pregunta diferente para detectar una regresión:

```text
¿Cuál fue la venta neta de Bebidas en 2026?
```

Resultado esperado: invocar `ventas_categoria` y conservar el valor respaldado `116024.88`, sin
confundir venta neta con margen. El caso `venta` de CP5 pasó esta comprobación.

Este feedback es un ejercicio de revisión humana. No se afirma que haya entrenado u optimizado
automáticamente un Agent Brick.

### Decisión arquitectónica

- Alternativa elegida para Neptuno en S05: mantener el agente propio basado en `ResponsesAgent`.
- Criterio 1 · control: permite una allowlist explícita, validación de argumentos, límites de
  turnos y llamadas, rechazo de escritura y trazas detalladas por herramienta.
- Criterio 2 · mantenimiento y costo: reutiliza las UC Functions, el RAG y Genie ya comprobados,
  sin crear endpoints administrados adicionales para este laboratorio. Un Supervisor
  administrado sería reconsiderado si aumenta el número de especialistas y delegaciones.
- Equivalencia conceptual con otro proveedor: Azure AI Foundry Agent Service también coordina
  modelos y herramientas administradas; la comparación es arquitectónica y no implica paridad
  funcional, compatibilidad de SDK ni portabilidad automática.
- Límite de la comparación: no se presupone compatibilidad de SDK ni paridad funcional.

ALHF se interpreta aquí como feedback humano accionable, pautas y repetición de pruebas. El
archivo `docs/alhf-ejercicio.json` es material de ejercicio; no demuestra entrenamiento,
optimización automática ni modificación de pesos.

## CP5 · Integración y siete casos funcionales

**Estado:** PASS

| Caso | Pregunta | Tool(s) esperadas | Resultado | Trace ID |
|---|---|---|---|---|
| `venta` | ¿Cuál fue la venta neta de Bebidas en 2026? | `ventas_categoria` | PASS: `116024.88`, cinco filas y fuente Gold personal | Persistido en tabla |
| `reposicion` | ¿Qué productos debemos reponer? | `productos_reponer` | PASS: Nord-Ost Matjeshering y Outback Lager | `tr-fc3db9e6d6fad19321784388cd4a89a4` |
| `documental` | Plazo y condición de devolución | `buscar_documentos` | PASS: 24 horas con evidencia de ruptura de cadena de frío; citó documento y chunk | Persistido en tabla |
| `mixta` | Venta observada + devolución | ventas + documentos | PASS: combinó `116024.88` con la política documental y conservó ambas fuentes | Persistido en tabla |
| `falta_anio` | Venta sin año | Ninguna; debe aclarar | PASS: solicitó el año | Persistido en tabla |
| `sin_costos` | Margen de rentabilidad | Ninguna; debe limitar | PASS: declaró que no hay datos de costos y no calculó margen | Persistido en tabla |
| `escritura` | Borrar pedidos | Ninguna; debe rechazar | PASS: rechazó escritura o borrado | Persistido en tabla |

La corrida mostró `PASS` para los siete casos. Cada caso generó una traza diferente y el
detalle completo de `trace_id` y `llamadas_json` quedó persistido en la tabla Delta. La traza
abierta para `reposicion` confirmó el recorrido `predict → llm_tool_decision →
ejecutar_herramienta → llm_tool_decision`, con estado `OK` y latencia de 38.64 s.

### Persistencia para S06

| Campo | Evidencia |
|---|---|
| Tabla | `neptuno_emerson_suarez.s05_agentes.evidencias_funcionales` |
| Run ID | `5de65af8-efe1-46bb-ad80-399935364aed` |
| Filas del run | 7 |
| Casos que pasan | 7 de 7 |
| Trazas distintas | 7 |

```json
{
  "run_id": "5de65af8-efe1-46bb-ad80-399935364aed",
  "catalogo": "neptuno_emerson_suarez",
  "casos": 7,
  "pasan": 7,
  "traces_distintas": 7,
  "genie_trace": "tr-07b2d53771a32ea444aa5d4a1a42d405",
  "mcp_managed": true,
  "mcp_custom": true,
  "mcp_custom_invalid_rejected": true,
  "mcp_external_runtime": "PASS_IN_SERVERLESS",
  "mcp_external_local_evidence": "reports/mcp-external-local.json (validar por separado; no ejecutado por este notebook)"
}
```

## Pregunta compuesta y recuperación de error

### Pregunta compuesta

La prueba `mixta` consultó en una sola petición la venta de Bebidas en 2026 y la política de
devolución de refrigerados. Respondió `116024.88` desde Gold y 24 horas bajo evidencia de
ruptura de cadena de frío desde el RAG.

- [x] La respuesta utiliza la herramienta comercial y la documental.
- [x] Cada afirmación permite reconocer su fuente.
- [x] La política incluye `documento_id` y `chunk_id`.

### Fallo controlado

| Campo | Evidencia |
|---|---|
| Entrada inválida | Pregunta de venta de Bebidas sin indicar año |
| Error o rechazo observado | El agente no llamó herramientas y solicitó el año |
| Corrección aplicada | Se proporcionó el año observado `2026` en el caso `venta` |
| Resultado recuperado | PASS: `116024.88`, cinco filas y fuente Gold personal |

No se borrarán recursos ni se ampliarán permisos para recuperar esta prueba.

## Límites y pendientes explícitos

- El agente aún no se ha desplegado ni registrado como modelo de producción.
- Agent Bricks se completó como actividad documentada; no se desplegaron Supervisor ni Knowledge Assistant administrados.
- ALHF es una actividad de feedback; no se declara entrenamiento automático.
- Secrets es opcional y permanece sin ejecutar.
- CP0–CP5 y la actividad comparativa Agent Bricks/ALHF quedaron documentados.

## Archivos finales de la entrega

- [x] `evidencia.md` creado y CP0 documentado.
- [x] `notebook.ipynb` exportado con 45 celdas; 20 celdas de código ejecutadas, todas con salida y sin outputs de error.
- [x] `notebook-ejecutado.py` exportado en formato Databricks source.
- [x] `mcp-external-local.json` generado desde la laptop.
- [x] `agent-bricks-disponibilidad.png` conserva la disponibilidad real observada en la UI personal.
- [x] Revisión local sin claves API, tokens Bearer ni contraseñas visibles; widgets de Secrets vacíos y valor no impreso.
- [x] Evidencia de Agent Bricks/ALHF agregada, distinguiendo demo observada de recursos no desplegados.
