# SK05

## 0.1.0
Brief, alternativas y assertions anteriores a SKILL; baseline6casos conservado. Conducta inicial mayormente correcta, delta no medido. GREEN/revisión/inferencia real pendientes. Provisional.

## 0.1.1
Revisión independiente detectó posible ampliación de alcance en consultas sin desarrollo. Implementación queda condicionada al encargo. Baseline y GREEN previos preservados; revalidación de este caso pendiente.

## 0.1.2
Fallo real confirmado por `runs/sk05-embedding-smoke-002.json`: el servicio devolvió
`qwen3-embedding-0-6b-112025`, dos vectores de dimensión 1024 y uso de 23 tokens,
pero el adaptador comparó el campo `model` con nombres de endpoint/configuración.
Fue un error local de identidad, no un rechazo de API. La ejecución 001 no
conservó granularidad suficiente; no se reconstruye ni se le atribuye la causa
observada después en 002.

Se separan identidad de endpoint, configuración y modelo de respuesta. El bundle
revisión 2 fija `expected_response_model` exacto; no acepta prefijos ni alias
imprevistos. Se conserva el bundle anterior. Se exige diagnóstico seguro antes
de validar (etapa, modelo, cantidad, dimensiones, índices, uso y latencia), con
separación de errores de servicio, validación y persistencia.

Regresión RED: 6 fallos y 29 pruebas existentes pasan. GREEN: 35 pasan; el nuevo
caso nominal acepta el ID observado, casos negativos rechazan cambios de revisión,
sufijos y alias de endpoint/configuración, y un pin ausente bloquea ejecución.
Smoke 003 se registra como nueva prueba expresamente autorizada (una solicitud,
dos textos públicos, 256 tokens de cuota); su evidencia queda separada del estado
general de la skill y de calidad semántica/E2E, todavía no acreditadas.

Resultado 003: una llamada, dos embeddings finitos de 1024 dimensiones,
modelo exacto esperado y 23 tokens reportados (39 reservados con margen).
`runs/sk05-embedding-smoke-003.json` y vectores con hash acreditan únicamente
esta inferencia documental breve. Coste monetario desconocido; calidad SBS,
query-role, reranking, generación y E2E no evaluados.


## 0.1.6 provisional — 080
Selección server-only073/077 y cierre de muestra probada→stage. RED cinco fallos; GREEN local y regresión070. Refinamiento documental con evidencia técnica, sin benchmark conductual ni validación cloud/E2E. Revisión independiente root pendiente.
