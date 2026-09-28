# Sesión 06 · Registro de avance y límite de Free Edition

**Fecha:** 27 de septiembre de 2026. **Estado:** evaluación provisional; la entrega final sigue pendiente.

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
3. **CP3–CP4** calculan reglas, MLflow GenAI y el juez. **CP5** muestra BLEU/ROUGE y prepara
   tres trazas. Léelas, escribe veredicto y evidencia en los tres widgets de revisión, y
   vuelve a ejecutar solo **CP5.2b**. Los widgets empiezan vacíos para no simular juicios humanos.
4. **CP6** exporta `evaluacion_s06.json`, `dataset_s06.json`, `scores_s06.json`,
   `revision_humana.json` y `decision.md`. Descárgalos del run. La decisión declara el bloqueo
   Genie y no aprueba producción.

El notebook base del docente no se modificó. El notebook personal hace una evaluación nueva;
los resultados del replay histórico de S05 permanecen separados.

El replay encontró siete casos con selección de herramientas conforme a lo esperado;
los cuatro casos que usaron herramientas no registraron errores. Dos respuestas de
ventas coincidieron con el SQL previo. Las métricas documentales, calculadas por documento,
figuran por caso en las puntuaciones. Estos números describen **la corrida histórica de S05**,
no una evaluación nueva del agente en S06. Por eso el resumen declara
`mode=replay_historico_s05` y `complete=false`.

## Trabajo pendiente para cerrar S06

1. Ejecutar el notebook personal de CP0 a CP6 y revisar los errores observados.
2. Revisar al menos tres trazas como persona y registrar la decisión.
3. Completar el caso Genie con SQL independiente cuando vuelva el warehouse; recalcular el
   hash del dataset y repetir la evaluación de ese caso.
4. Descargar los artefactos del run. Los archivos de `provisional-local/` son fuentes del
   borrador y evidencia histórica, no sustituyen los artefactos nuevos.

Una API externa podría puntuar respuestas guardadas, pero cambiaría el entorno de evaluación
y no resolvería la consulta pendiente de Genie. Mantendré separadas las métricas históricas
de las que obtenga en una corrida nueva.
