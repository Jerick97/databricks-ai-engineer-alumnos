# Roadmap

- Completado: recuperación local de nueve capas y etapas; compilación de iniciativas; lectura forense; framework v0.1 y aplicación preliminar SBS.
- Pendiente de alcance: entidad/familia normativa, especialista, pares reales y baseline.
- Siguiente: manifiesto de corpus piloto con originales, versiones y fuentes; referencia adjudicada; comparación de alternativas.
- Después: prototipo E2E por disposición, benchmark reservado, revisión humana y prueba UI real.
- Posterior: despliegue, operación medida, mejora y regresiones. Sin fechas ni resultados prometidos antes de cerrar dependencias.

## Aclaración de alcance

El objetivo vigente es construir el E2E completo. La preparación tiene nueve ejes; el runtime tiene nueve capas de canal a observabilidad. La escala0–8 es auxiliar. Ver docs/11-contrato-e2e.md.

## Aula web

Material interactivo generado. Contenido y lógica comprobados; pendiente inspección visual en navegador cuando se cierre la ventana de extensión que bloquea Chrome. La implementación del agente conserva sus dependencias anteriores.

## Construcción por skills

Spec v0.2 aprobado. Plan E2E en docs/13 y plan de skills en docs/14. Secuencia: contexto/contratos → guardrails/observabilidad/fundación → referencia/comparación → modelos/RAG/Genie → conversación/UI → aceptación/despliegue. Cada skill se crea y evalúa con skill-creator-z antes de construir su componente; skills aún pendientes.
