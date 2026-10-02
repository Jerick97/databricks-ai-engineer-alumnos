# SBS Radar — agente de seguimiento normativo

SBS Radar prepara documentos de la SBS, compara copias y permite conversar con evidencia mediante RAG y consultas estructuradas con Genie.

## Un repositorio, dos responsabilidades de infraestructura

El repositorio independiente propuesto se llama `sbs-radar-e2e`. Su historial vivirá en el proveedor Git elegido; Databricks Git folders será una copia conectada al **mismo repositorio**, no un segundo repositorio independiente.

**Estado actual:** esta carpeta contiene el proyecto del piloto. La estructura IaC que sigue es el diseño acordado; todavía no se ha implementado como un despliegue IaC completo; el código y este diseño se publican en el repositorio independiente. Documentarla no acredita un despliegue reproducible completo. Consulta el [estado de la entrega](ESTADO-ENTREGA.md).

## Qué carpetas son Terraform y cuáles son Databricks Asset Bundles

| Ubicación propuesta | Herramienta responsable | Qué contiene |
|---|---|---|
| `infra/terraform/` | **Terraform** | Infraestructura base: catálogo, esquema, almacenamiento y permisos base. Warehouse si el proyecto debe administrarlo. |
| `databricks.yml` | **Databricks Asset Bundles** (actualmente Declarative Automation Bundles) | Entrada del Bundle, archivos incluidos, variables y targets `dev`, `test` y `prod`. |
| `resources/` | **Databricks Bundles** | Declaraciones de los Jobs, la App y el espacio Genie propios de SBS Radar, y sus permisos específicos cuando estén soportados. |
| `src/`, `notebooks/`, `config/` | Código y configuración de la solución | Implementación consumida por los recursos desplegados; no son infraestructura por sí mismos. |
| `data/`, `skills/`, `tests/`, `docs/` | Datos, procedimientos, validación y documentación | PDF del piloto, manifiestos, skills, pruebas y material explicativo. |

```text
sbs-radar-e2e/                   # Estructura objetivo, pendiente de implementar
├── databricks.yml               # BUNDLES: configuración principal
├── resources/                  # BUNDLES: recursos de la solución
│   ├── jobs.yml
│   ├── app.yml
│   └── genie.yml
├── infra/
│   └── terraform/              # TERRAFORM: infraestructura base
│       ├── catalog.tf
│       ├── warehouse.tf
│       ├── permissions.tf
│       ├── variables.tf
│       └── outputs.tf
├── src/
├── notebooks/
├── config/
├── data/
├── skills/
├── tests/
└── docs/
```

Terraform usa archivos `.tf`. El Bundle de este proyecto usará YAML y declarará en `databricks.yml` qué archivos de `resources/` incluye. **La extensión por sí sola no define el responsable:** otros YAML pueden ser configuración de la aplicación.

## Un único responsable por recurso

Un mismo recurso no debe ser administrado simultáneamente por Terraform y Bundles. Por ejemplo: Terraform administra el esquema; el Bundle lo referencia para configurar los Jobs, la App o Genie.

Si Terraform crea un warehouse, publica su ID como output. El despliegue entrega ese ID como variable al Bundle. Si el warehouse ya existe y es compartido, se referencia: no se crea ni se adopta automáticamente.

Esta es una decisión de organización del proyecto, no una limitación universal de las herramientas: sus capacidades pueden solaparse. Los permisos también se separan por recurso para evitar que un despliegue sobrescriba los del otro.

Al implementar IaC, el inventario `docs/recursos.md` deberá registrar para cada recurso: entorno, responsable (Terraform o Bundle), archivo declarativo y tratamiento (**crear, adoptar o sólo referenciar**). Ese inventario todavía está pendiente.

## Cómo se desplegará

Estos comandos describen el flujo futuro; **todavía no son ejecutables como despliegue SBS completo en esta carpeta**:

```bash
# Infraestructura base, desde infra/terraform/
terraform init
terraform plan
terraform apply

# Recursos de SBS Radar, desde la raíz del repositorio
databricks bundle validate -t dev
databricks bundle deploy -t dev
```

Primero se prepara o referencia la infraestructura base. Después se pasan sus identificadores al Bundle y se despliegan los recursos de la solución. La carga de los seis PDF y de las tablas, la construcción del índice y las pruebas E2E son pasos adicionales: desplegar infraestructura no significa haber cargado ni validado los datos.

Los secretos se suministran por los mecanismos de autenticación y gestión de secretos del entorno. No se versionan tokens, valores de secretos ni estados locales de Terraform con información sensible.

## Recursos

- [Guía E2E y relación con SK00–SK12](teaching-guide/index.html).
- [Definiciones y configuraciones actuales del piloto](deployment/): no equivalen todavía a la estructura IaC objetivo.
- [Recursos soportados por Bundles](https://docs.databricks.com/aws/en/dev-tools/bundles/resources).
- [Integración Git de Databricks](https://docs.databricks.com/aws/en/repos/repos-setup).

## Repositorios públicos

- [Código SBS Radar y diseño IaC](https://github.com/manuelarguelles/sbs-radar-e2e).
- [Ejemplo implementado de Genie con IaC: ianbal-genie-iac](https://github.com/manuelarguelles/ianbal-genie-iac). Es otro proyecto; no despliega SBS Radar.
- [Material del curso para alumnos](https://github.com/manuelarguelles/databricks-ai-engineer-alumnos).

## Alcance de esta publicación

Se publica código, notebooks sin salidas, seis PDFs del piloto, índices y configuraciones, skills, guías y videos. Se excluyen credenciales, claves del tutor, cachés, pesos descargados y autorizaciones/estado operativo del workspace de origen. Las configuraciones de clase deben adaptarse al destino. Los scripts históricos conservan su contexto y no constituyen un instalador único. Las skills siguen siendo provisionales. No se ha reejecutado el despliegue cloud por publicar este repositorio.
