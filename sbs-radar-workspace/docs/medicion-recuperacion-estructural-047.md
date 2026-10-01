# Recuperación estructural 047 — medición de desarrollo

Se midieron cuatro variantes sobre 231 vectores documentales reales y tres consultas cacheadas compatibles bajo el contrato operativo observado. La referencia Astra 028, los positivos 13/16/13 y los criterios 018 permanecen intactos. **No es holdout ni aceptación operacional.**

## Orden de los primeros cinco resultados (nDCG@5)

| Consulta | Léxico | Vector | RRF | RRF + reranker |
|---|---:|---:|---:|---:|
| cyber-art20-3 | 1.0000 | 0.9013 | 0.9218 | 0.9218 |
| market-art27 | 0.8106 | 0.8887 | 0.9795 | 0.8106 |
| market-art29-1-4 | 0.6622 | 0.7735 | 0.7735 | 0.7735 |

## Cobertura de pasajes relevantes (Recall@20)

| Consulta | Léxico | Vector | RRF | RRF + reranker |
|---|---:|---:|---:|---:|
| cyber-art20-3 | 9/13 (69.2%) | 10/13 (76.9%) | 11/13 (84.6%) | 11/13 (84.6%) |
| market-art27 | 8/16 (50.0%) | 9/16 (56.2%) | 7/16 (43.8%) | 7/16 (43.8%) |
| market-art29-1-4 | 11/13 (84.6%) | 3/13 (23.1%) | 5/13 (38.5%) | 5/13 (38.5%) |

## Interpretación y límites

- Todas las variantes recuperan sustento directo de ambas versiones en top 5 para estas tres consultas. Es un diagnóstico de contrapartes, no cobertura normativa completa ni verificación de respuestas generadas.
- El reranker reordena el mismo pool RRF de 20 resultados: Recall@20 permanece igual por construcción. En market-art27 nDCG@5 baja de 0.9795 a 0.8106; en las otras dos consultas queda igual a RRF. No hay evidencia de mejora universal.
- Los rankings léxicos top 20 coinciden exactamente con 028. Se conserva el primer intento fallido por diferencias de redondeo de 3.55e-15/7.11e-15; la segunda corrida comprueba IDs y orden exactos más una cota de error de suma flotante. No se ajustaron manualmente scores, umbrales ni qrels para mejorar métricas.
- La brecha de procedencia R47-01 se reprodujo, corrigió y revisó antes de la segunda corrida. Cada entrada consumida queda vinculada a los hashes revisados 046/026.
- ONNX CPU real evaluó 60 pasajes en 96 ventanas completas, sin recortar el texto y con pool RRF top 20 fijo. No comparar este efecto como si fuera el mismo pool del reranker léxico 028.
- La autorización 041 produjo 29 solicitudes de embeddings, 231 vectores de dimensión 1024 y 106278 tokens observados; no hubo nuevas inferencias remotas de embeddings ni generación durante 047; sí se ejecutó el reranker ONNX local. Coste monetario desconocido.
- Compatibilidad de endpoint/modelo/tokenizer/dimensión e inputs observada; no igualdad demostrada de pesos remotos inmutables. No se promocionó índice al runtime ni se habilitó generación, SQL, Genie o infraestructura.
- Recall del 90% en top 5 sigue siendo matemáticamente imposible con 13/16/13 positivos. La propuesta 030 de protocolo sigue propuesta: este informe no la adopta ni redefine los gates.
- Siguiente decisión técnica: diagnosticar los pasajes relevantes excluidos del pool antes de cambiar parámetros. Cualquier ajuste posterior sería desarrollo sobre muestra expuesta y necesitaría validación independiente antes de aceptación. No sustituir una solución requerida por la variante que casualmente gane aquí.

## Evidencia

- `runs/sk04-embeddings-045-result.json` y `runs/sk09-embeddings-045-review.json`.
- `runs/sk05-query-compatibility-046.json` y `runs/sk09-query-compatibility-046-review.json`.
- `runs/sk04-structural-ranking-047-record.json` y directorio `runs/sk04-structural-ranking-047-v2/`.
- `runs/sk09-measure-development-047-protocol.json`, script, invocation y result.
- Revisión final SK09 de artefactos y medición aprobada en alcance local: `runs/sk09-structural-ranking-047-final-review.json`. La precisión sobre inferencia local y remota se incorporó tras su observación documental.
