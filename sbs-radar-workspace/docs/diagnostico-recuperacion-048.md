# Diagnóstico de recuperación 048

Diagnóstico SK04 mediante CreatorZ y estrategia-rag, sobre artefactos047 congelados. Sin nuevos rankings, inferencias, vectores ni cambios de parámetros/qrels. Estado: desarrollo expuesto; revisión independiente SK09 pendiente.

Las métricas se copian de SK09-047. Las cifras siguientes son particiones por pertenencia a listas guardadas, no una nueva evaluación ni un ranking contrafactual.

| Consulta | Positivos | En RRF20 | Perdidos en ambas ramas20 | Descartados en fusión20 | Positivos unión |
|---|---:|---:|---:|---:|---:|
| cyber-art20-3 | 13 | 11 | 2 | 0 | 11 |
| market-art27 | 16 | 7 | 5 | 4 | 11 |
| market-art29-1-4 | 13 | 5 | 2 | 6 | 11 |

## Interpretación

La presencia de soporte directo de ambas versiones en top5, medida por SK09, no implica recuperar todos los positivos. El benchmark047 no expande contrapartes SK03. Ningún pasaje aquí se identifica como contraparte uno-a-uno sólo por compartir artículo o versión. El reranker conserva exactamente los mismos 20 IDs de RRF: puede alterar el orden, pero no recuperar los excluidos.

Hallazgo concreto: market-art29-1-4 pierde en fusión seis positivos que sí estaban en el top20 léxico (rangos 13, 14, 17, 18, 19 y 20). Uno es grade2: structural-bfff74a43a1d99809eb8c2b2205d527ce49cb72cb46fd5ec3e08dec302184ecb. Por tanto, presencia de ambas versiones no significa conservar cada span de soporte directo.

La categoría «fusión» identifica positivos que sí entraron por alguna rama y quedaron fuera del pool RRF20. «Ambas» sólo significa ausencia en ambos top20 guardados; no ausencia en corpus ni rank exacto. El léxico puede omitir scores cero. No se reconstruyó la cola RRF ni se ejecutó el scorer.

## cyber-art20-3

¿Cómo cambió la responsabilidad por pérdidas en operaciones digitales sin autenticación reforzada en el artículo 20.3 entre las versiones 4 y 5?

| ID completo perdido | Grade | Léxico | Vector | RRF | Reranker | Pérdida | Documento / página |
|---|---:|---:|---:|---:|---:|---|---|
| `3cc6ddc7f484523a1bbc9c363bc34f0e93f19731963c53c4114446eee4032b2e` | 1 | no observado | no observado | no observado | no observado | ambas | sbs-504-2021 / 16 |
| `503d5e86397dfdc37d9f2ad545c6b615f64d598426db60b24ecaf52a7378b106` | 1 | no observado | no observado | no observado | no observado | ambas | sbs-504-2021 / 16 |

Los IDs de versión, offsets, origen, scores y todos los positivos retenidos están en el JSON048.

## market-art27

¿Qué cambió en el artículo 27 sobre seguros adicionales, contratación independiente y consentimiento del usuario entre las versiones 7 y 8?

| ID completo perdido | Grade | Léxico | Vector | RRF | Reranker | Pérdida | Documento / página |
|---|---:|---:|---:|---:|---:|---|---|
| `01ff8d3d480ef92038eae0f78a46cc8f70f1634d944b4682a2b843b6d9d93e1d` | 1 | no observado | no observado | no observado | no observado | ambas | sbs-3274-2017 / 13,14 |
| `028a102f532a15c94479e95fe945d9d0a197e50e1de6ec3203d6a2c65a5dc9bb` | 1 | 19 | no observado | no observado | no observado | fusión | sbs-3274-2017 / 22,23 |
| `21636cb9a0b7d48340f0d64615fe31bba0a7104caf5440dbc8c405dc25f805dd` | 1 | no observado | no observado | no observado | no observado | ambas | sbs-3274-2017 / 13,14 |
| `4f135517d6778a11863c2ab64901369368d272721062e621d1400a8509e6dcdd` | 1 | 18 | no observado | no observado | no observado | fusión | sbs-3274-2017 / 22,23 |
| `62520a29b5fa291c55f27d1ad1490abb28b31896d9ed477130aef32bbe9d9de2` | 1 | no observado | no observado | no observado | no observado | ambas | sbs-3274-2017 / 30 |
| `8a1fc0dccd7de2d3aa95e5176e8f40cab290f5158bc95342636378ada1317e4c` | 1 | no observado | no observado | no observado | no observado | ambas | sbs-3274-2017 / 15,16 |
| `a66df63864e92500034f65ac526ed548fc4f923109b8a31a274035598ef9f47a` | 1 | no observado | no observado | no observado | no observado | ambas | sbs-3274-2017 / 30 |
| `d6a3a7f13e8feaea6129973ec58649c98c116bbc6b035dce47ad4d467975ef6e` | 1 | no observado | 19 | no observado | no observado | fusión | sbs-3274-2017 / 20 |
| `d8a5307918aff8b059253299ddd2a4425032bcb193f3d025d21ec987cdde6ccd` | 1 | no observado | 18 | no observado | no observado | fusión | sbs-3274-2017 / 19,20 |

Los IDs de versión, offsets, origen, scores y todos los positivos retenidos están en el JSON048.

## market-art29-1-4

¿Qué cambió en el artículo 29.1 numeral 4 sobre canales para pagos anticipados y adelantos de cuotas entre las versiones 7 y 8?

| ID completo perdido | Grade | Léxico | Vector | RRF | Reranker | Pérdida | Documento / página |
|---|---:|---:|---:|---:|---:|---|---|
| `16b91c67ec2a71993a8198cc65985e20f1b1258309afe5561f6be100dcd02f01` | 1 | 18 | no observado | no observado | no observado | fusión | sbs-3274-2017 / 30 |
| `62520a29b5fa291c55f27d1ad1490abb28b31896d9ed477130aef32bbe9d9de2` | 1 | no observado | no observado | no observado | no observado | ambas | sbs-3274-2017 / 30 |
| `7d52ba1745aa940e619c0456c27e28bb13e7b801359630e65a14ca61f23ab432` | 1 | 13 | no observado | no observado | no observado | fusión | sbs-3274-2017 / 23 |
| `a5128e02dc6b978eb59eb5bca977bea1147158d58ab9787a695833d5c0404234` | 1 | 19 | no observado | no observado | no observado | fusión | sbs-3274-2017 / 30 |
| `a66df63864e92500034f65ac526ed548fc4f923109b8a31a274035598ef9f47a` | 1 | no observado | no observado | no observado | no observado | ambas | sbs-3274-2017 / 30 |
| `b868e12a415d3fa11fdabd03eb329e381b98f840f4b1a718e078e05c75cfafa4` | 1 | 17 | no observado | no observado | no observado | fusión | sbs-3274-2017 / 8,9 |
| `d6f32a8a06f736d4ca45636fee56e5c80e4066ecabd88d5b42e5d59862fb304e` | 1 | 14 | no observado | no observado | no observado | fusión | sbs-3274-2017 / 23,24 |
| `structural-bfff74a43a1d99809eb8c2b2205d527ce49cb72cb46fd5ec3e08dec302184ecb` | 2 | 20 | no observado | no observado | no observado | fusión | sbs-3274-2017 / 16 |

Los IDs de versión, offsets, origen, scores y todos los positivos retenidos están en el JSON048.

## Siguiente intervención causal propuesta, no implementada

En un experimento de desarrollo expuesto congelado por separado, variar sólo la política del pool: unión de los top20 de ambas ramas frente al RRFtop20. Mantener queries, vectores, qrels, filtros, RRF60 e identidad del modelo. Medir pérdida de cobertura en el corte del pool antes del reranker. La unión cambia la cardinalidad y el coste: declararlos por separado, sin prometer mejora en los 20 resultados finales. Los positivos ausentes de ambas ramas requieren otro experimento posterior de profundidad de candidatos, sin cambiar ambos factores simultáneamente.

## Refinamiento propuesto de skill

Añadir una ruta explícita de diagnóstico a SK04: reutilizar trazas/qrels congelados, separar ausencia en unión de descarte por fusión, declarar rangos no observados y distinguir presencia de ambas versiones de expansión de contrapartes SK03. El paso10 puede interpretarse como obligación de repetir las cuatro variantes en cada diagnóstico: precisar cuándo bastan métricas congeladas. Es una ambigüedad observada, no un fallo conductual reproducido ni validación del refinamiento. No se editó la skill compartida.

## Procedencia y verificación

Invocación previa: `runs/sk04-pool-diagnosis-048-invocation.json`. Script reproducible: `python3 runs/sk04-pool-diagnosis-048.py`. Salida: `runs/sk04-pool-diagnosis-048.json`. La investigación reutiliza el contrato047, código propietario, referencia028 y medición047; no se crea una nueva skill ni se declara validada. La estrategia base v1 se conserva con adaptación estructural047, sin transferencia de validación histórica.

Input hashes,047 metric/ranking anchors, qrels frozen anchor, trace order/score identity, pool equality, eligible scope, metric numerator reconciliation, exhaustive disjoint classification all passed. El script sólo usa biblioteca estándar y lee artefactos locales. No evalúa respuestas ni aceptación operacional.
