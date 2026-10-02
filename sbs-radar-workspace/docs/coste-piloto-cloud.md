# Coste y alcance del piloto cloud — SK12

Estimación parcial del 28 de septiembre de 2026 UTC. No es una cotización de la cuenta, un límite monetario ni autorización. Registro y fuentes: `runs/sk12-cost-scope-001.json`.

La app Medium consume 0,5 DBU por hora, según la [configuración oficial](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/compute-size). La [FAQ pública de Apps](https://www.databricks.com/product/pricing/databricks-apps) da un ejemplo de AWS Premium en US-east Virginia a US$0,75/DBU. Con esos supuestos, **30 minutos de una app equivalen a 0,25 DBU y US$0,1875**. Es solamente el componente app: no incluye warehouse, Genie, modelos, job, almacenamiento ni red. La tarifa efectiva, región y nivel de esta cuenta siguen sin verificarse.

Genie usado por la identidad de servicio de la app tiene facturación de LLM; no recibe automáticamente la gratuidad de un usuario identificado. El warehouse se cobra por separado. Los datos de consumo pueden aparecer con demora en las tablas de facturación. Véase [monitorización de coste de Genie](https://docs.databricks.com/aws/en/genie/monitor-cost). No se ejecutó SQL para consultarlas ni se arrancó el warehouse. Tampoco se ha observado cuánto consume una pregunta SBS real: veinte preguntas no se convierten en una cifra de dólares sin ese dato.

Los presupuestos de Genie requieren administración de cuenta, cubren LLM y **no garantizan un techo absoluto de facturación**; el cómputo SQL queda fuera. No se modificarán presupuestos compartidos ni se enviarán alertas a terceros desde este trabajo. [Límites oficiales](https://docs.databricks.com/aws/en/genie/budgets).

## Escenario propuesto para revisión

| Componente | Alcance propuesto | Estado del coste |
|---|---|---|
| App propia | Una instancia Medium, ventana piloto de 30 minutos | Ejemplo público parcial arriba; tarifa de cuenta pendiente |
| SQL | Warehouse candidato existente, sin redimensionar; tamaño Small y un cluster observados históricamente | Consumo/tarifa AWS aplicable pendientes de verificación |
| Genie | Hasta 20 preguntas acotadas entre ambas familias y seguimiento | LLM separado de SQL; consumo por pregunta desconocido |
| RAG | Reutilizar los 135 vectores fijados; cero nuevos embeddings en esta corrida | Nueva inferencia excluida del escenario inicial |
| Generación | Cero nuevos intentos hasta resolver el acceso 403 | Tarifa de entrada/salida y ejecución exitosa pendientes |
| Refresco | Job diario inicialmente PAUSED | Cómputo e identidad por fijar y estimar antes de activación |
| Datos y red | Corpus/export propios y paquete fijado | Tarifas y duración de almacenamiento pendientes |

La fórmula total es `coste app + DBU SQL × tarifa SQL + DBU Genie × tarifa aplicable + tokens de modelos × sus tarifas + job + almacenamiento/red`. **El total sigue desconocido**. La tabla histórica de multiplicadores encontrada para GCP no se extrapoló a AWS. Las páginas públicas SQL exponen un selector dinámico; la extracción consultada no proporcionó la tarifa numérica aplicable.

## Control operativo antes de aplicar

El piloto necesita un inicio y cierre registrados, admisión de solicitudes limitada por servidor, IDs de los recursos propios y comprobación de parada. Los límites por proceso existentes no sobreviven por sí solos a un reinicio. Una ventana escrita en el plan tampoco detiene el cómputo automáticamente. La parada del warehouse compartido solo procede si esta ejecución lo arrancó, no hay trabajo ajeno y el alcance autorizado lo cubre; en caso contrario se registra exposición residual.

Después del piloto se reconcilian IDs y consumo observado con facturación disponible, sin poner cero donde falten datos. Antes de solicitar la autorización realmente faltante se terminarán la configuración ejecutable, los controles, la estimación aplicable y el rollback. Los US$100 del spec siguen siendo una hipótesis.

## Observación posterior de metadatos

La lectura autenticada de metadatos a las 01:41:46 UTC del 28/09/2026 informó metastore asignado `aws/us-west-2` y warehouse candidato STOPPED, Small, un cluster y auto-stop de 10 minutos. No se ejecutó SQL ni se arrancó cómputo. Evidencia: `runs/sk12-cost-metadata-001.json`. El ejemplo público de Virginia permanece meramente ilustrativo; no se ha acreditado que sea la tarifa aplicable a este destino. El nivel contractual y el saldo siguen desconocidos.
