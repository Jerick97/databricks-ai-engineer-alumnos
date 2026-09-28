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

Para continuar con **CP1** sin modificar el notebook del docente preparé el
[notebook personal de CP1](notebook-cp1-personal.py), el
[borrador de once casos](provisional-local/dataset_s06_cp1_borrador.json) y sus
[referencias y pendientes](provisional-local/referencias_s06_cp1.json). El caso adicional
pregunta por un lote lácteo recibido a 8 °C y usa la ficha fuente de S04. El notebook personal
permite revisar el dataset y comprobar su hash en Databricks sin llamar a Genie ni a `%run`.
La referencia de Genie permanece `pending`: una cifra obtenida anteriormente por Genie no
serviría como oracle independiente.

### Cómo continuar CP1 en Databricks

Conservo localmente `original/notebook-incompleto.ipynb`, el intento que se detuvo en `%run`.
Para avanzar, abre `notebook-cp1-personal` en este mismo Git Folder:

1. La primera celda verifica los once casos y el SHA256 del borrador. En la ejecución del
   27 de septiembre mostró `Referencia Genie: pending`.
2. Ejecuta **CP1.1** para revisar preguntas, herramientas y fuentes. El undécimo caso es
   `lacteo_fuera_rango` y su referencia procede de la ficha de Lácteos de S04.
3. Ejecuta **CP1.2** para leer el oracle previo de ventas y los textos de la política de
   devoluciones y de la ficha de Lácteos. Confirma manualmente las etiquetas documentales.
4. Conserva el hash impreso. El caso Genie seguirá pendiente hasta calcular su referencia
   con SQL independiente sobre el catálogo personal; después habrá que actualizar el dataset
   y congelar un hash nuevo antes de CP2.

Este notebook prepara CP1 y no vuelve a ejecutar `%run`. El notebook base del docente no se
modificó. Los resultados del replay histórico de S05 siguen separados de los once casos nuevos
de S06.

El replay encontró siete casos con selección de herramientas conforme a lo esperado;
los cuatro casos que usaron herramientas no registraron errores. Dos respuestas de
ventas coincidieron con el SQL previo. Las métricas documentales, calculadas por documento,
figuran por caso en las puntuaciones. Estos números describen **la corrida histórica de S05**,
no una evaluación nueva del agente en S06. Por eso el resumen declara
`mode=replay_historico_s05` y `complete=false`.

## Trabajo pendiente para cerrar S06

1. Confirmar las etiquetas del borrador de CP1 contra el corpus actual y calcular un oracle
   SQL independiente para Genie cuando haya cómputo disponible.
2. Ejecutar el dataset nuevo de S06, incluido el caso propio, cuando haya cómputo disponible.
3. Alinear el oracle y la fuente declarada de Genie con el espacio personal: el notebook base
   de S06 aún usa referencias al espacio y catálogo docentes.
4. Ejecutar el juez de MLflow, revisar al menos tres casos como persona y registrar la decisión.
5. Exportar los artefactos finales pedidos por la consigna. Los archivos de `provisional-local/`
   quedan como evidencia del avance y no sustituyen esos artefactos.

Una API externa podría puntuar respuestas guardadas, pero cambiaría el entorno de evaluación
y no resolvería la consulta pendiente de Genie. Mantendré separadas las métricas históricas
de las que obtenga en una corrida nueva.
