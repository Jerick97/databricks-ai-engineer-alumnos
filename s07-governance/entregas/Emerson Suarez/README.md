# Entrega S07 · Gobierno y seguridad de IA

Corrida personal en Databricks Free Edition. El notebook ejecutado está en `notebook.ipynb`; `notebook-ejecutado.py` conserva la exportación en Python.

## Resultados observados

| Indicador | Resultado |
| --- | --- |
| Casos del agente | 4/4; 0 errores de ejecución |
| Componentes deterministas | 4/4; 0 llamadas al modelo |
| Fuente autorizada | 1 documento aprobado |
| Linaje de Unity Catalog | 0 filas observadas en esta corrida; no se concluye ausencia de linaje |
| Vector Search | `not_configured` |
| Safety administrado | No verificado: `moderation_mode=disabled`, `status=not_configured`, 0 sondas |
| MLflow | Experimento `/Shared/S07-Neptuno-Governance`; Run ID `4e574b9fc60e44c985a8dbcff593234d` |
| Artefacto | `s07-governance-report.json` |
| Decisión | Práctica parcial; producción no aprobada |

## Evidencia

- `s07-governance-report.json`: reporte descargado del run MLflow.
- `capturas/CP1.png`: datos sintéticos y observación de permisos.
- `capturas/CP4.png`: intento de verificar Safety en AI Gateway. La corrida final conserva la moderación como no configurada.

Los 4/4 casos y 4/4 componentes corresponden a estas pruebas acotadas. No demuestran que el filtro Safety de AI Gateway funcione ni certifican seguridad para producción.
