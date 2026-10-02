# Propuesta prospectiva de presupuesto de evidencia — 030

**Estado: proposed_not_effective · acceptance_not_run.** Documento revisable, sin aceptación ni sustitución del diseño018. [Propuesta estructurada](../context/evaluation-030/proposal.json). No ejecuta código, modelos ni otra evaluación. Los resultados028 permanecen medición de desarrollo expuesto con referencia IA Astra, sin aprobación humana ni holdout. Haber visto esos resultados impide presentar030 como preregistro de028.

## Problema y criterio de decisión

018 combina en el top5 dos objetivos diferentes: reunir90% de todos los pasajes positivos y ofrecer una primera vista breve y bien ordenada. Para una pregunta con N pasajes relevantes (grado>0), cualquier ranking de IDs únicos tiene techo `Recall@k ≤ min(k,N)/N`. Alcanzar0.90 en una pregunta requiere al menos `ceil(0.90*N)` plazas. Esta condición depende del inventario de referencia, no del recuperador, sus scores ni su orden.

Los N=13/16/13 de028 dan techos@5 de5/13,5/16,5/13 (38.46%,31.25%,38.46%). Sus presupuestos mínimos individuales serían12/15/12. Es un diagnóstico de factibilidad, no un recálculo de aceptación. No hace legítimo aplicar un gate nuevo favorable a los rankings ya observados.

**Recomendación propuesta:** separar cobertura del conjunto candidato de orden y sustento de la vista inicial, manteniendo todos los positivos.20 candidatos es una hipótesis de presupuesto heredada de018 que debe justificarse y fijarse antes del ensayo futuro; no es una cantidad óptima demostrada ni garantiza cobertura para toda pregunta futura.

## Matriz de criterios propuestos

Todos los estados de esta tabla son **proposed_not_effective / acceptance_not_run**. Las familias se evalúan por separado y todas las variantes del ensayo conservan corpus, filtros, referencia y presupuestos comunes.

| Criterio | Diseño018 preservado | Recomendación030 para un ensayo futuro | Denominador y alcance |
|---|---|---|---|
| Disponibilidad de evidencia candidata | Macro Recall≥0.90@5; @20 solo diagnóstico | Macro Recall≥0.90@20 por familia | Todos los pasajes elegibles con grado>0 de cada pregunta; conservar grados1 y2. Macro de preguntas, no micro ni promedio entre familias. |
| Orden de la primera vista | Macro nDCG≥0.80@5 | Sin cambio: macro nDCG≥0.80@5 | Ganancia lineal0/1/2; IDCG sobre la referencia completa elegible. Escala común en DCG/IDCG no cambia cociente. No normalizar contra solo el pool recuperado. |
| Sustento directo antes/después | Al menos un positivo de cada lado en top5, en cada comparación evaluable | Al menos un grado2 de cada lado en top5, en cada comparación recuperable | Cada par elegible debe tener ambos lados; gate por pregunta, no compensable por promedio. Es una propuesta más exigente que presencia de contexto, no prueba de entailment de cada afirmación. |
| Presencia de contexto de ambas versiones | Contraparte grado>0 es gate | Conservar medición grado>0, separada del nuevo gate grado2 | No confundir disponibilidad contextual con sustento directo. |
| Recall@5 y orden@20 | Gate y diagnóstico respectivamente | Conservar ambos como diagnósticos con numeradores/denominadores | No eliminarlos cuando revelen pérdidas; no convertir@20 en rescate retroactivo de018. |
| Factibilidad del presupuesto | Dificultad reportada sin recortar qrels | Techo por pregunta y macro por familia antes del ensayo | `Cq(k)=min(k,Nq)/Nq`; `Cf(k)=mean(Cq(k))`. Si `Cf<0.90`, el gate macro es matemáticamente inviable. Un techo individual bajo no basta por sí solo para probar inviabilidad del macro. |

Para N>22, ni20 plazas permiten0.90 por pregunta. Incluso N≤22 solo acredita factibilidad de cardinalidad, no que el sistema encontrará los positivos. El criterio recomendado sigue siendo macro por familia; reportar todos los techos individuales evita ocultar déficits por compensación. No ajustar k por pregunta después de ver resultados. Si el nuevo inventario hace inviable el presupuesto fijado, conservarlo y reportar el incumplimiento de diseño; cualquier cambio requiere una propuesta/protocolo futuro versionado, sin borrar el anterior ni excluir preguntas difíciles.

La falta de pasajes grado2 en un lado no autoriza inventarlos ni rebajar grados: conservar el caso como insuficiente/no recuperable y evaluarlo mediante el gate de insuficiencia. La elegibilidad y esa clasificación se fijan antes del ensayo. Si falta adjudicación para decidirlo, `not_evaluated`, nunca cumplimiento por conjunto vacío. Ausencias o errores de ejecución tampoco desaparecen del denominador esperado.

## Alternativa: conservar018 íntegro

Mantener macro Recall≥0.90@5, nDCG≥0.80@5 y contraparte grado>0@5, con20 diagnóstico. Reportar los techos y casos inviables como limitación del presupuesto/referencia, sin adjudicar todo el déficit al recuperador. Esta opción no requiere cambiar el diseño; tampoco autoriza declarar aceptación de028 ni eliminar positivos. El objetivo018 sigue intacto mientras030 no sea adoptado expresamente para un ensayo nuevo.

## Por qué no cambiar qrels para aprobar

Los pasajes automáticos y subspans anotados pueden solaparse; el denominador mide pasajes y no obligaciones independientes. Se conserva esa limitación visible. Deduplicar solo ahora los positivos solapados o retirar grado1/contexto reduciría el denominador tras observar resultados y cambiaría la pregunta evaluada. No constituye una corrección matemática de Recall. Una eventual evaluación por unidad de evidencia requeriría ontología, agrupación y adjudicación independientes, preregistradas en otro diseño; no se introduce aquí. Tampoco se puede fijar relevancia según lo que aparezca en el top20 del sistema.

## Gates de negocio que no cambian

Recall de detección≥0.95; precisión de detección≥0.90; cero críticos omitidos; todas las citas emitidas fieles/localizables; insuficiencias señaladas; ahorro mediano humano pareado≥0.30 incluyendo verificación y retrabajo. Reportar cada familia, errores y numeradores/denominadores. Críticos no representados, falta de citas verificadas o tiempos humanos ausentes implican no evaluado, no100%. Ninguna métrica de recuperación sustituye estos gates, la evaluación de cobertura de afirmaciones, ni requisitos operacionales/cloud/UI. Una revisión humana por pregunta no se añade como bloqueo para conversar.

## Condiciones de una evaluación futura

1. Resolver el diseño prospectivo y presupuesto antes de ejecutar rankings del nuevo ensayo. No aplicar030 a028 como aceptación ni seleccionar una variante ganadora retrospectiva.
2. Disponer de holdout real por componentes completos de pares/documentos/versiones, modificatorias y vecinos; registrar exposición y aristas.028 permanece desarrollo. La ausencia de hashes compartidos no prueba independencia.
3. Congelar corpus exacto, preguntas, qrels exhaustivos de todos los elegibles, grados directos/contextuales y contrapartes, criterios de insuficiencia/críticos y procedencia antes del trial; juez independiente sin rankings. Referencia IA permanece IA; no se inventa aprobación humana.
4. Fijar filtros, variantes efectivamente disponibles, modelos/backend, candidato20, presentación5, orden de operaciones y tratamiento de errores. Reportar variantes vector/híbrida no ejecutadas mientras falten vectores, sin sustituirlos por otra técnica.
5. Versionar un protocolo efectivo compatible con estas decisiones y verificar sus precondiciones, incluidas particiones reales. El harness actual no se modifica ni se invoca desde esta propuesta. Su compatibilidad con gates distintos por k y contrapartegrado2 debe revisarse antes de implementar/aplicar, no rellenarse con placeholders.
6. Conservar rankings y todas las combinaciones esperadas; medir una vez y revisar independientemente. Informar medición, factibilidad y aceptación por separado. Baseline humano requiere personas/tiempos reales; no se deriva de latencia CPU ni Astra.

**Decisión pendiente:** revisión independiente de030. No se adopta un nuevo gate, no se reejecuta028 y no se abre otra rama de modelos/ingeniería. El diagnóstico ya comprobado es que Recall90%@5 y13/16/13 positivos son incompatibles; la respuesta recomendada es explicitar presupuestos por función en un ensayo futuro, no reparar sus scores.
