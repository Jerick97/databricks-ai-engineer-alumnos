# Sesión 06 · Registro de avance y límite de Free Edition

**Fecha:** 27 de septiembre de 2026. **Estado:** diez casos evaluados, tres revisiones
humanas aprobadas y cinco artefactos del run de entrega validados. Genie sigue pendiente
por la cuota de SQL warehouse de Free Edition; la decisión es no aprobar producción.

El objetivo de S06 es evaluar el `ResponsesAgent` construido en S05 con casos nuevos,
referencias independientes, trazas, métricas y revisión humana. Mi [entrega de S05](../../../s05-agentes/entregas/Emerson%20Suarez/evidencia.md)
documenta el agente, sus herramientas y una ejecución previa de Genie.

## Bloqueo observado

Configuré el catálogo y el Genie Space de mi workspace. La cadena `%run` de S06 avanzó
hasta la llamada `consultar_genie`, pero esta terminó después de tres minutos en
`MessageStatus.PENDING_WAREHOUSE`. La [captura de la traza](capturas/Captura%20de%20pantalla%202026-09-27%20185022.png)
muestra el timeout.

El [estado del SQL warehouse](capturas/Captura%20de%20pantalla%202026-09-27%20185139.png)
muestra `Failing to start` y `RESOURCE_EXHAUSTED`, con el mensaje de Databricks:
`You've hit the limit for serverless compute for free usage`. Por tanto, la consulta de
Genie no llegó a ejecutar SQL en este intento. La documentación de
[Databricks Free Edition](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations)
confirma límites de uso del cómputo serverless; las capturas no permiten determinar la hora
de restablecimiento de la cuota.

## Continuación local

Para avanzar sin simular una respuesta nueva, ejecuté el
[evaluador local](../../scripts/evaluar-historico-local.py) sobre el notebook **ya ejecutado**
de S05. El script lee siete respuestas históricas, sus llamadas a herramientas y sus IDs de
traza. Para ventas compara contra el SQL de referencia que S05 ejecutó antes de inferir.
No usa SQL warehouse, credenciales, red ni una API LLM externa.

Los artefactos provisionales son:

- [Dataset histórico](provisional-local/dataset_s06_historico.json).
- [Puntuaciones deterministas](provisional-local/scores_s06_historico.json).
- [Resumen y límites](provisional-local/evaluacion_s06_historica.json).

Para continuar **CP0–CP6** sin modificar el notebook del docente preparé el
[notebook personal de S06](notebook-s06-personal.py), el
[borrador de once casos](provisional-local/dataset_s06_cp1_borrador.json) y sus
[referencias y pendientes](provisional-local/referencias_s06_cp1.json). El caso adicional
pregunta por un lote lácteo recibido a 8 °C y usa la ficha fuente de S04. El notebook personal
reutiliza el agente Python de S05 con `%run` hasta CP3, sin pasar por el notebook de Genie.
Valida las referencias, ejecuta los diez casos accesibles, calcula métricas, invoca MLflow,
prepara tres revisiones humanas y exporta la evidencia. El caso Genie permanece `pending`:
una cifra obtenida anteriormente por Genie no serviría como oracle independiente.

### Cómo continuar S06 en Databricks

Conservo localmente `original/notebook-incompleto.ipynb`, el intento que se detuvo en `%run`.
Abre **solo** `notebook-s06-personal` en este mismo Git Folder y ejecútalo por bloques:

1. **CP0** carga el agente S05 hasta CP3. **CP1** verifica los once casos, el SHA256,
   recalcula la cifra de ventas con SQL independiente y contrasta los documentos S04.
2. **CP2** infiere diez casos nuevos; el undécimo (`genie`) queda bloqueado por la cuota del
   warehouse. Revisa trazas y errores antes de seguir.
3. **CP3–CP4** calculan reglas, MLflow GenAI y el juez. **CP5** muestra BLEU/ROUGE;
   **CP5.2** crea la sesión de Review App. Tras guardar allí tres respuestas esperadas,
   registra veredictos y evidencia en los widgets y ejecuta **CP5.2b**.
4. **CP6** exporta `evaluacion_s06.json`, `dataset_s06.json`, `scores_s06.json`,
   `revision_humana.json` y `decision.md`. Descárgalos del run. La decisión declara el bloqueo
   Genie y no aprueba producción.

#### Revisión humana: dos lugares distintos

1. **CP5.2** crea una sesión de Review App para `sin_costos`, `documento` y `compuesto`.
   Abre el enlace que imprime esa celda. En **Expected response** escribe una respuesta
   correcta en **texto normal**, sin JSON, para cada pregunta y pulsa **Save**. Comprueba que
   Review App marque **100 % Reviewed**. Esto guarda referencias humanas en Review App.
2. Vuelve al notebook. Los campos superiores `revision_sin_costos`, `revision_documento` y
   `revision_compuesto` siguen vacíos aunque Review App marque 100 %. Cada uno necesita un
   **JSON de veredicto y evidencia**, escrito tras comparar respuesta, fuente y herramientas:

   ```json
   {"veredicto":"correcto","evidencia":"La respuesta coincide con la fuente consultada y no inventa datos."}
   ```

   Cambia el veredicto a `parcial`, `incorrecto` o `no_evaluable` cuando corresponda. La
   evidencia debe tener al menos 20 caracteres y describir lo que observaste, no una frase
   genérica. Confirma cada widget con Enter o saliendo del campo.
3. Ejecuta **solo CP5.2b**. La salida esperada es `Revisiones registradas: 3 / 3`; si muestra
   `0 / 3`, comprueba que los tres widgets superiores contengan JSON válido. **No repitas CP5.2**
   al rellenarlos: esa celda crea otra sesión de Review App, nueva y pendiente. Tampoco repitas
   CP2, porque produciría otra corrida y otras trazas.
4. Ejecuta **CP6 una vez después del 3 / 3**. Descarga los cinco artefactos del run de
   exportación; comprueba que `revision_humana.json` tenga tres entradas `approved` o `rejected` y que
   `evaluacion_s06.json` conserve `genie` como bloqueado, sin puntuarlo como fallo.

#### Artefactos finales validados

El run de exportación es `f898a403aec342bfbb6eca7e17eac486`. Sus cinco archivos están en
[`logged/`](logged/): `dataset_s06.json`, `evaluacion_s06.json`, `scores_s06.json`,
`revision_humana.json` y `decision.md`. El SHA256 del dataset coincide con el reporte:
`40548383e256d082087e7be37843308b266abf811b313ae2942d4415d93e7591`.
Hay 11 casos planeados, 10 observados, 0 errores de ejecución y 1 caso (`genie`) bloqueado
por el entorno. Los diez casos tienen puntuaciones de reglas y juez. Review App llegó a
**100 % Reviewed**; las tres revisiones del JSON tienen responsable, evidencia concreta,
respuesta corregida y `trace_id` asociado al caso correcto. El reporte marca
`review_status: completa` y enlaza esa sesión revisada.

La cifra de ventas fue **116024.88** y coincidió con el SQL independiente. La selección de
herramientas fue correcta en **10/10** casos. `decision.md` registra el defecto confirmado en
`sin_evidencia`: recuperó contexto ajeno a descuentos (`context_precision=0`) y citó un
documento irrelevante pese a abstenerse. Incluye corrección, prueba de regresión y plan de
muestreo online. Las métricas del juez son 1.0, pero agente y juez usaron el mismo endpoint;
esa limitación figura en el reporte. La decisión conserva `complete=false` y **no aprueba
producción** mientras Genie no pueda ejecutarse y el defecto documental siga abierto.

#### Si Git Pull reinició Python

Abre de nuevo `notebook-s06-personal` después del Pull y busca **Recuperación después de Git Pull**
entre CP5.1 y CP5.2. Si esa sección no aparece, recarga la pestaña del notebook. Ejecuta su
celda Python: recupera del run `f898a403aec342bfbb6eca7e17eac486` los diez casos, las
puntuaciones y el enlace de la Review App ya completada; también verifica el hash del dataset.
Después comprueba los tres widgets de revisión y ejecuta **CP5.2b → CP6**. La salida de CP5.2b
debe ser `3 / 3`. No hace falta volver a ejecutar CP0–CP4 ni CP5.2; esta última crearía otra
sesión de Review App. Si generas una nueva exportación, valida sus cinco artefactos antes de
reemplazar la copia de `logged/`.

El notebook base del docente no se modificó. El notebook personal hace una evaluación nueva;
los resultados del replay histórico de S05 permanecen separados.

El replay encontró siete casos con selección de herramientas conforme a lo esperado;
los cuatro casos que usaron herramientas no registraron errores. Dos respuestas de
ventas coincidieron con el SQL previo. Las métricas documentales, calculadas por documento,
figuran por caso en las puntuaciones. Estos números describen **la corrida histórica de S05**,
no una evaluación nueva del agente en S06. Por eso el resumen declara
`mode=replay_historico_s05` y `complete=false`.

## Trabajo pendiente para cerrar S06

1. Completar el caso Genie con SQL independiente cuando vuelva el warehouse; recalcular el
   hash del dataset y repetir la evaluación de ese caso.
2. Aplicar el filtro de relevancia documental y comprobar que `sin_evidencia` no cite
   documentos ajenos a descuentos; luego repetir la regresión.
3. Los archivos de `provisional-local/` son fuentes del
   borrador y evidencia histórica, no sustituyen los artefactos nuevos.

Una API externa podría puntuar respuestas guardadas, pero cambiaría el entorno de evaluación
y no resolvería la consulta pendiente de Genie. Mantendré separadas las métricas históricas
de las que obtenga en una corrida nueva.
