# S05 · Vigía de vigencia normativa SBS

Entregable full stack de Databricks para el contexto regulatorio peruano.

## Archivos

- `SDD.md`: diseño técnico, arquitectura, modelo de datos, contratos y criterios de aceptación.
- `notebook.py`: corpus didáctico versionado, diff por artículo, embeddings, recuperación,
  herramientas read-only, router/agente, trazas y abstención.
- `slides/S05-vigencia-deck.html`: material visual de la sesión.

## Caso

Resolución SBS N.° 272-2017, Reglamento de Gobierno Corporativo y de la Gestión Integral de
Riesgos. El notebook usa fixtures didácticos marcados; la fuente oficial y el historial están
enlazados en el SDD. La siguiente iteración sustituirá fixtures por PDFs oficiales descargados,
hasheados y procesados con `ai_parse_document`.

## Ejecución

1. Importar `notebook.py` a Databricks.
2. Ejecutar la primera celda y escribir el catálogo de S01–S02.
3. Confirmar que existe `databricks-qwen3-embedding-0-6b` o elegir otro endpoint de embeddings.
4. Ejecutar las celdas en orden.

El agente es de solo lectura: el modelo puede proponer una herramienta, pero la allowlist,
los argumentos, la evidencia y la traza se validan antes de responder.
