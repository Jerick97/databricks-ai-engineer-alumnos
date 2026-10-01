# Escala auxiliar de madurez 0–8 — no las etapas de preparación

**Corrección:** mi entrega anterior interpretó “etapas” como madurez. Tras la aclaración del usuario, la escala queda como referencia auxiliar; no sustituye las nueve etapas de preparación ni las nueve capas runtime.

La fuente las llama explícitamente **etapa**: [tabla original del laboratorio](/Users/macdenix/clawd/agent-lab/README.md:34), corroborada en [PROJECT del índice](/Users/macdenix/clawd/projects-index/personal/agent-lab/PROJECT.md:34). Es la interpretación con mayor respaldo encontrada para “las nueve etapas”. No se encontró otra secuencia general inequívoca; si te referías a otro pipeline, debe conservarse como marco distinto.

| Nº original | Etapa | Significado original | Evidencia que exigiría al caso SBS — propuesta |
|---|---|---|---|
| 0 | Idea | Spec o arquitectura, sin código | Caso definido, especialista, corpus y criterio de éxito identificados |
| 1 | Esqueleto | Scaffold, no corre end-to-end | Tablas/contratos/tools definidos; componentes pendientes explícitos |
| 2 | Corre local | Camino feliz en la máquina | Un par documental procesado hasta una salida verificable |
| 3 | Demo e2e | Mostrable de punta a punta | Analista consulta, compara versiones, abre ambas citas y revisa resultado |
| 4 | Desplegado | Vive en una URL o servicio | Mismo recorrido sobre despliegue real, identidad/permisos y configuración entregada |
| 5 | Usuarios reales | Alguien más que yo lo usa | Piloto con especialistas, tareas reales y evidencia de uso |
| 6 | Producción operada | Corre solo, con dueño y guardias | Detección programada, recuperación de fallos, responsable y rollback |
| 7 | Medido | Evaluación + monitoreo sobre datos reales | Calidad y costo en operación con denominadores y revisión independiente |
| 8 | Iterado | Se mejora sobre métricas, no intuición | Cambio de versión mejora la métrica acordada sin regresiones prohibidas |

La numeración original empieza en **0**; no renumerarla oculta la relación con tu catálogo. Madurez y número de capas son ejes independientes. Evaluación no se aplaza hasta 7: se diseña desde 0 y se prueba durante el desarrollo; 7 exige además medición en datos/uso reales.

## Cómo evitar inflar la madurez

- Reportar por separado: existencia, implementación, ejecución observada, aceptación humana, despliegue y disponibilidad actual.
- Una URL que existe no demuestra usuarios ni operación autónoma.
- Un benchmark con fixtures no acredita comportamiento sobre normas reales.
- Un Job exitoso no acredita UI, SSO o recorrido interactivo; el incidente de S08 lo demuestra.
- Registrar fecha y versión de la evidencia. Madurez histórica no garantiza disponibilidad hoy.
- Capas no aplicables requieren explicación; no construir nueve componentes por cumplir un número.

El antecedente S05 SBS contiene código pero no prueba del agente completo: no se eleva a demo E2E por tener un notebook. El nuevo E2E está **en análisis**, no desplegado.
