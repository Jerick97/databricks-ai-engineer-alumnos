# Decisión S06 · evaluación personal

Dataset SHA256: 40548383e256d082087e7be37843308b266abf811b313ae2942d4415d93e7591

Run de exportación: f898a403aec342bfbb6eca7e17eac486.

Casos planeados: 11; observados: 10; errores de ejecución: 0; bloqueados por entorno: 1 (Genie).

Run de reglas: e96fce04f31044cd9b43291f9529a43c; run de juez: f52fb5a3e8654e70a0baa775a60acc83.

Revisiones humanas: 3/3; sesión revisada: https://dbc-aa7e795a-12f2.cloud.databricks.com/ml/review-v2/daaa2395ab9d45e6b9937f3b81012770/tasks/labeling/91f9380a-ba7d-4e9d-87e4-2b759abfdf0a?o=7474645167834251.

## Métricas por tipo de caso

- Herramientas: 10/10 casos con selección esperada.
- Ventas: oracle SQL independiente=116024.88; comparación tool/SQL=True.
- Aclaraciones, límite de costos y acciones prohibidas: 5/5 casos con selección de herramientas esperada (ninguna); el juez y humano comprueban el texto final.
- documento: precision documental=1.0; recall documental=1.0.
- compuesto: precision documental=1.0; recall documental=1.0.
- sin_evidencia: precision documental=0.0; recall documental=N/A.
- lacteo_fuera_rango: precision documental=0.5; recall documental=1.0.
- Juez: {"juez_correctness/mean": 1.0, "juez_relevance/mean": 1.0, "juez_faithfulness/mean": 1.0}; mismo endpoint que el agente, con riesgo de auto preferencia.

## Fallo confirmado y regresión

- `sin_evidencia` (tr-4a046ba32f453a711c6099e16c073731) recuperó documentos irrelevantes (precision=0.0, recall=N/A porque no hay documentos relevantes): contrato_expreso_veloz, proveedor_exoticos. La respuesta final se abstuvo, pero citó esos documentos ajenos a descuentos; el fallo está en la recuperación y en citar contexto irrelevante.
- Corrección propuesta: filtrar fragmentos por relevancia antes de pasarlos al agente; si ninguno supera el umbral validado, devolver contexto vacío y abstenerse.
- Caso de regresión: repetir `sin_evidencia` con el mismo corpus y hash; exigir cero fragmentos ni citas irrelevantes y ninguna cifra o requisito inventado. Medir también la tasa de abstención correcta con nuevas preguntas sin respuesta documental.

Decisión: no aprobar producción. El caso Genie carece de oracle y ejecución actuales; completarlo cuando vuelva el SQL warehouse y repetir la evaluación. Conservar `complete=false` y separar fallos de recuperación de errores de ejecución.

Para S08: muestrear 10 % del tráfico y 100 % de errores, excluir datos sensibles, asignar revisión diaria a Emerson Suarez y alertar ante cualquier escritura prohibida o más de 5 % de respuestas sin fuente en el muestreo. No hay tráfico productivo aún.
