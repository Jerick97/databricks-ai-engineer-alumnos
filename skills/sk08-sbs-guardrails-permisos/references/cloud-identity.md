# Identidad cloud del piloto

Fuente primaria consultada 2026-09-27: https://docs.databricks.com/aws/en/dev-tools/databricks-apps/auth . Databricks reenvía token de usuario y separa autorización de usuario y app. Se usan scopes de identidad; modelos/Genie se conceden al principal de la app solo dentro del namespace piloto. La política local asigna únicamente reader al usuario actual para ambas familias; no permite aprobar impactos.

El adaptador prueba GET current-user sin redirects/retries y obtiene id/active. Los demás campos no asignan roles. Workspace y origen público son configuración del servidor. create_app(mode=cloud) requiere adaptador y servicio con for_actor; ningún JSON del navegador construye esa autoridad.

Aún faltan prueba con token delegado real en Apps, grants mínimos y revisión independiente de despliegue. No se cambió permiso remoto ni inició recurso para construir el adaptador.
