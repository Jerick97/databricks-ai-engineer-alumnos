# Identidad escritora — investigación puntual reutilizable

Consultado: 2026-09-28 UTC. Brecha: creación de una identidad dedicada para Jobs, separada del lector de Apps. No crear secretos ni asignar administración.

La [guía oficial de administración](https://docs.databricks.com/aws/en/admin/users-groups/manage-service-principals), actualizada el11/09/2026, distingue principal de cuenta y asignación a workspace. Documenta para administradores del workspace el proxy `/api/2.0/account/scim/v2/`. La creación legacy mediante SCIM del workspace no es una alternativa equivalente en un entorno con federación. Crear la identidad no prueba acceso a Jobs, datos o warehouse.

El [Account SCIM2.1 oficial](https://docs.databricks.com/aws/en/assets/files/account-scim-2_1-da24f7cb52abfee4646aff48adb4307f.pdf), páginas13–16, documenta filtro exacto `applicationId`, respuesta con ID/UUID y creación. Su ejemplo de creación contiene una discrepancia de schema `User`; el objeto de respuesta y el enum del SDK identifican `ServicePrincipal`. No copiar ese ejemplo incongruente.

El SDK instalado0.102.0 `AccountServicePrincipalsAPI.create` serializa `application_id`, `display_name`, `active` y `schemas`; el endpoint del SDK para AccountClient no se ejecutó. La propuesta utiliza el proxy documentado con UUID fijado para reconciliar una respuesta ambigua sin reenviar POST. Ausencia de campos de roles/grupos no demuestra ausencia de permisos heredados. No usar creación o readback como autorización de gasto ni prueba de ejecución.

La API Identityv2 también documenta creación de un principal local de cuenta por workspace, pero está marcada Beta; no se añadirá como fallback automático. Fuente: [Workspace Service Principal](https://docs.databricks.com/api/iam/v2/create-service-principal-proxy).

Evidencia observada: `runs/sk12-metadata-preflight-016.json`: búsqueda de nombre en workspace sin resultados; app y warehouse detenidos. Esto no demuestra ausencia en toda la cuenta. `deployment/writer-metadata-proposal-016.json` fija un applicationId propio para la comprobación exacta antes de crear. Ninguna mutación ejecutada por esta investigación.

## Evidencia posterior y corrección propuesta

Primer request016 con UUID/active/schema/name recibió400invalidSyntax; GET antes/después del UUID dio0. El detalle fue filtrado, por lo que no se conoce la causa exacta. La [referencia SCIMv2 por proveedor](https://api-docs.databricks.com/rest/latest/account-scim-api.html) distingue creación AWS (schema+name, UUID en respuesta) de Azure (UUID en request). Propone016b usa el ejemploAWS y filtro prefix displayName documentado para v2; no vuelve a enviar016 ni emplea el nuevoAPIbeta como fallback. Una respuesta ambigua se observa y se detiene, sinadopción por nombre.
