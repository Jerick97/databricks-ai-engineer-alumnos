# Guía docente · operar Neptuno de punta a punta

Sesión final: lunes 28 de septiembre de 2026. Leer primero `PLAN-CLASE.md`. El notebook explica cada celda; esta guía explica qué demostrar, cómo acompañar y qué cuenta como evidencia. **Creado, desplegado, probado y listo son estados distintos.** La fuente de estado observado son los reportes de ejecución actuales, no las salidas esperadas descritas aquí.

## Antes de abrir la clase

El día anterior asigna catálogo/esquema y nombres aislados por alumno o equipo. Deben contar con acceso al workspace, cómputo permitido, lectura de datos Neptuno, funciones S05 y recursos RAG S04, creación/uso de modelos en UC, permisos de consulta y administración del endpoint según rol, Apps habilitada y permisos de tablas/monitoreo. La persona que solo consulta no necesita administración. No conceder administrador global para resolver un fallo específico.

Revisa `lab/config.json`; sus nombres corresponden a recursos del entorno del docente, **no** a recursos universales del alumno. Antes de ejecutar escrituras cada equipo usa nombres propios. Configura identidad humana para preparar recursos; identidad del endpoint para tools/modelos; identidad de la App para invocar. Esta separación retoma S07.

Desde el repo local se abre `s08-deployment/README.md`. Desde Databricks: Workspace → carpeta personal → crear/importar Git folder con el repo asignado, abrir `s08-deployment/notebook.py` y seleccionar el cómputo autorizado. Si se usa Import de notebook suelto, faltarán `lab/` y `app/`: importar/sincronizar la carpeta completa. El notebook usa Python source con separadores Databricks. No pegar todo el archivo en una única celda.

Si recibes el ZIP local y los cambios aún no están publicados en Git, descomprímelo. Desde Terminal, con el perfil del workspace configurado (`databricks auth login --profile s08`), ejecuta:

```bash
python -m pip install databricks-sdk==0.143.0
python s08-deployment/lab/lab_import_workspace.py --profile s08
```

El importador usa tu carpeta personal y conserva los módulos como archivos; el notebook se importa con sus celdas. Se niega a sobrescribir una carpeta existente: abre la copia anterior o usa `--folder S08-Neptuno-2`. `--dry-run` muestra el destino sin cargar archivos. Completa los widgets antes de crear recursos.


El docente debe ejecutar CP0–7 antes de clase en recursos aislados, guardar logs y comprobar una consulta real desde App. Provisionar endpoint puede tardar decenas de minutos; tablas de inferencia y métricas son asíncronas. No gastar los 30 min del bloque CP2 esperando que un servicio nuevo arranque: mostrar el proceso con una instancia ya preparada y dejar a cada equipo un recurso asignado disponible. El procedimiento desde cero queda en notebook/scripts. Si un alumno no tiene permiso, trabaja en pareja en un recurso autorizado y registra qué ejecutó; mirar una demo no acredita su despliegue.

Ensayar la solicitud canónica y una solicitud fuera de alcance; comprobar logs, monitor y rollback. Conservar request IDs y UTC. Ocultar secretos y payloads comerciales sensibles al proyectar o compartir. Una tabla con cero filas puede ser retraso; no demostrar drift sobre cero observaciones.

## CP0

**Pregunta inicial:** «¿Qué parte de Neptuno ya funciona y qué falta para que alguien lo use sin abrir un notebook?» Dibujar datos S01–02 → LLM/RAG/tools S03–05 → evaluación S06 → gobierno S07 → endpoint/App/monitor S08.

Entrada: código y configuración del repo completo. Acción: inventariar recursos e identidades con CP0 del notebook. Salida: nombres concretos y disponibilidad. Leer un permiso faltante como diagnóstico, no como fallo del LLM. No inferir que Review App ya tiene una valoración humana: pedir su referencia o anotarla como pendiente.

Practicar: cada equipo identifica su catálogo, modelo, endpoint, App y responsable. Si faltan fuentes Neptuno o funciones, resolverlos antes de empaquetar; no reemplazar silenciosamente el agente por un echo.

## CP1

Un artefacto de modelo contiene código ejecutable y dependencias; un modelo UC añade versión y permisos. `ResponsesAgent` define la interfaz de solicitud/respuesta. **Deploy model** publica una versión servible; **deploy code** publica código/configuración de App, Job o agente mediante un proceso reproducible. Empaquetar Python no significa entrenar pesos nuevos.

Entrada: `lab/agent.py`, `lab/config.json`, `lab/requirements.txt`. Ejecutar CP1: comprobar que el agente usa tools Neptuno y recuperación, registrar artefacto y leer URI/versión. Explicar input example y firma como contrato, no evaluación de calidad. Pedir al alumno localizar qué recurso necesita cada tool. Ante dependencia faltante, corregir/recrear el entorno declarado; no instalar paquetes a mano sin registrar la versión.

## CP2

Endpoint: dirección de servicio que recibe solicitudes y ejecuta el recurso configurado. Model Serving incluye modelos custom, Foundation Model APIs y modelos externos; comparten punto de consumo, difieren en alojamiento/configuración/costo. Serverless evita administrar un clúster, no elimina permisos, límites o gasto. Scale-to-zero puede reducir capacidad ociosa en configuraciones compatibles; el arranque en frío aumenta latencia. No prometer la misma opción en las tres categorías.

Entrada: versión UC y permisos de sus dependencias. Ejecutar CP2 usando `lab/lab_deploy.py`; mostrar estado listo e invocar. Comparar respuesta con la solicitud canónica y referencia S06. Una respuesta HTTP correcta no demuestra exactitud. Conservar endpoint, versión efectiva, request ID y tiempo. Si falla: leer estado/build logs y permisos; distinguir dependencia de Python, permiso de recurso y timeout. No repetir creación en bucle.

## CP3

El ensayo del workspace mostró que cambiar rutas también puede iniciar una actualización prolongada: la API rechazó enviar sólo `traffic_config`, por lo que el script conserva las entidades requeridas. **No prometer que canary y rollback finalizan en 15 minutos.** Con el custom ya preparado, el docente solicita canary alrededor del minuto 40, mientras se trabaja CP2; en CP3 observa la configuración efectiva y solicita rollback. Comprueba la reversión después de la pausa o durante el cierre si sigue pendiente. Los 15 minutos son discusión/inspección, no un SLA de infraestructura. Usa los reportes fechados del ensayo para explicar resultados mientras la nueva ejecución continúa, identificándolos como evidencia previa. El alumno registra pendiente hasta verificar su propia reversión.


Alias: nombre mutable que apunta a una versión; canary: exposición gradual; A/B: comparación de variantes bajo asignación definida; traffic split: porcentaje de solicitudes enrutadas. No confundir alias de modelo, alias de prompt y configuración del endpoint.

**Dos recursos distintos:** el agente principal `ais08-neptuno` tiene tarea `agent/v1/responses`, que no admite traffic splitting. Se actualiza una única versión, se verifica y, ante regresión, se restaura la versión anterior. El canary 90/10 se enseña y ejecuta en el endpoint custom complementario `ais08-neptuno-rollout`, con el modelo UC `ventas_rollout`: consulta ventas Neptuno reales y devuelve revisión y resultado. No es el agente principal ni sustituye su despliegue.

Entrada: versiones estables/candidatas del modelo custom y snapshot de configuración de ese endpoint. Preparar ambos endpoints antes de clase. Ejecutar CP3 usando `lab_custom_rollout.py`, `lab_rollout.py` y `lab_custom_rollout_verify.py`. Resolver aliases a versiones concretas, configurar 90/10 y verificar que suma 100. Discutir gate de errores/latencia/calidad, tamaño de muestra y dueño del rollback. Restaurar la configuración previa del custom y verificar respuesta de ventas/revisión y versión efectiva. Una muestra pequeña no demuestra exactamente 10% observado ni superioridad causal. Si el custom aún no está listo, registrar rollout pendiente; no atribuir el split al agente.

Referencia oficial: [Matriz oficial de capacidades por tipo de endpoint](https://docs.databricks.com/aws/en/ai-gateway/overview-serving-endpoints).

## CP4

La UI corre en browser; el backend de Databricks Apps recibe la pregunta y usa credenciales administradas del servidor. Autenticar a la persona no aplica automáticamente sus permisos de datos a llamadas realizadas por el service principal de la App. En este patrón explicar permisos de identidad compartida y alcance de datos; para permisos por usuario hace falta autorización explícita o flujo soportado de usuario.

Entrada: `app/app.py`, `app/app.yaml`, `app/requirements.txt`, endpoint disponible. CP4 despliega y muestra URL. Abrir sesión corporativa, enviar una pregunta y leer respuesta. Localizar endpoint en configuración del recurso y permisos de consulta del principal de App. Confirmar que no se colocó PAT en JS, HTML o navegador. Si hay 403 revisar identidad que llamó y recurso; no copiar un token personal al frontend. Si hay timeout comprobar primero endpoint y después backend.

## CP5

Inference Tables almacena solicitudes/respuestas y metadatos para análisis. El JSON anidado no es cómodo para agregación: **flatten** extrae campos tipados a columnas conservando clave de solicitud y timestamp. Una transformación no debe perder respuestas fallidas ni duplicar silenciosamente solicitudes.

Entrada: inferencias reales emitidas en CP2/4 y tabla configurada. Ejecutar CP5; inspeccionar esquema real antes de seleccionar rutas JSON. Comparar muestra cruda con fila plana, conteos, nulos y errores. Distinguir ausencia de datos, retraso de entrega y error de parseo. Si la tabla no llegó, conservar request IDs y reintentar la consulta más tarde; se puede explicar con fixture rotulado, pero no cerrar el requisito de logging real.

## CP6

Monitorear significa observar comportamiento después de desplegar. Baseline: período/dataset de referencia. Drift: cambio de distribución; no prueba por sí solo pérdida de calidad. Lakehouse Monitoring analiza tablas; los juicios de calidad/trazas complementan, no sustituyen, errores y latencia.

Entrada: tabla plana, baseline y columna temporal. Ejecutar CP6 con `lab/lab_monitor.py`; leer estado del monitor y refresco. Pedir interpretar una métrica con denominador y ventana. Umbrales pedagógicos se etiquetan como decisiones del ejercicio y requieren ajuste antes de producción.

AI Gateway añade controles de consumo: inference logging trata payloads; usage trata uso; rate limiting limita solicitudes/tokens según soporte. La factura requiere tarifas y dimensiones reales, no solo contar caracteres. Definir límite, destinatario de alerta y acción. Si no hay suficiente volumen/ventanas, registrar monitor creado o refrescado sin concluir «no hay drift». Ante calidad dudosa muestrear casos y reevaluar con S06; no revertir solo por una alarma sin investigar.

## CP7

Bundle: definición declarativa de recursos y configuración de despliegue. El temario lo llama Databricks Asset Bundles/DABs; la documentación actual también usa Declarative Automation Bundles. CI ejecuta pruebas al cambiar código; CD aplica un release aprobado. Targets dev/prod separan destino y permisos; no basta renombrar un endpoint compartido.

Entrada: `bundle/databricks.yml` y prompt de aplicación. CP7 valida bundle, identifica variables por entorno y versiona prompt. MLflow Prompt Registry conserva versiones y aliases; guardar versión resuelta para reconstrucción. Un alias mutable no es prueba de qué texto se utilizó. Mostrar gate test→evaluación S06→revisión→deploy→smoke test→observación/rollback. Una validación sintáctica no prueba despliegue ni conectividad. No desplegar prod como ejercicio sin recurso asignado y gate completo.

## CP8

Cierre del portfolio: unir código/commit, versiones, recursos, evaluación S06, controles S07, endpoint, App, logs, monitor y rollback. Pedir que otro equipo explique el recorrido sin ayuda del autor. Un eslabón pendiente se declara con causa y siguiente acción.

Cápsula multicloud: el componente «endpoint administrado» tiene equivalentes funcionales en Vertex AI Endpoints, Azure ML Online Endpoints y SageMaker Endpoints. No son APIs intercambiables: revisar IAM, formatos, escalado, costo y conectividad al migrar. Cada equipo elige un proveedor y anota una diferencia que verificaría.

Usar `CERTIFICACION.md`: mapa seis dominios, preguntas 1–4 con razones; 5–12 después. El cierre promete una ruta y evidencia de práctica, no aprobación garantizada del examen. Distinguir preparación del curso de aprendizaje observado por alumno.

## Ruta alternativa desde Terminal · comandos concretos

La ruta principal del alumno es el notebook; esta ruta permite preparar y repetir como instructor. Abre Terminal en la **raíz del repo**. Requiere Python3.11/3.12 disponible y Databricks CLI instalado según [instrucciones oficiales](https://docs.databricks.com/aws/en/dev-tools/cli/install). Sustituye `URL_WORKSPACE` por la URL asignada; `s08` es un perfil local nuevo, no una credencial compartida.

```bash
python3.11 -m venv .venv-s08
source .venv-s08/bin/activate
python -m pip install -r s08-deployment/lab/requirements.txt
databricks auth login --host URL_WORKSPACE --profile s08
databricks current-user me --profile s08
```

Leer salida de identidad antes de escribir recursos. Editar `s08-deployment/lab/config.json`: catálogo, esquema que empieza `ais08`, warehouse, endpoints de modelo/embedding, endpoint/App que empiezan `ais08-` y nombre de modelo UC de 3 partes. Conservar nombres aislados. La autenticación usa navegador; no imprime ni copia PAT.

Comprobar agente **local con dependencias remotas reales** (no es modo offline):

```bash
python s08-deployment/lab/lab_smoke.py --profile s08 --local
```

CP1–2, empaquetado y envío de despliegue. Se invoca una vez para una instancia nueva:

```bash
python s08-deployment/lab/lab_deploy.py --profile s08
```

`reports/lab-package.json` identifica la versión. `reports/lab-deployment.json` con `submitted` solo prueba envío. En UI abrir **Serving → nombre configurado → estado**; esperar Ready y revisar Build logs si falla. Luego:

```bash
python s08-deployment/lab/lab_smoke.py --profile s08
```

El script prueba ventas, aclaración, reposición, RAG y pregunta sobre costo; conserva resultados. Leer los casos además del exit code. Si el endpoint ya existe, `lab_deploy.py` se detiene tras empaquetar: no volver a lanzarlo en bucle para actualizar. El agente necesita actualización de una única versión; el script de rollout es solo para el custom complementario.

CP3 usa un **custom complementario**, nunca el endpoint `agent/v1/responses`. Desde la raíz del repo preparar y enviar su despliegue antes de clase:

```bash
python s08-deployment/lab/lab_custom_rollout.py --profile s08 --deploy
```

Leer `reports/lab-custom-rollout-package.json`: nombres del modelo/endpoint y versiones reales. Esperar READY sin update pendiente. `N` se sustituye por la versión challenger de **ventas_rollout**, no la del agente:

```bash
python s08-deployment/lab/lab_rollout.py --profile s08 --challenger-version N --percent 10
python s08-deployment/lab/lab_custom_rollout_verify.py --profile s08
```

El verificador comprueba el endpoint custom, su configuración, respuestas y revisiones. Por defecto envía 20 consultas SQL reales; no demuestra calidad comparativa entre las versiones. Antes del rollback, copiar `reports/lab-custom-rollout-verified.json` a `reports/lab-custom-canary-verified.json`, pues la siguiente verificación sobrescribe el primer archivo. Guardar `reports/lab-rollout-before.json` antes de otra promoción para no sobrescribir el estado a restaurar. Reversión del mismo ensayo:

```bash
python s08-deployment/lab/lab_rollout.py --profile s08 --rollback
python s08-deployment/lab/lab_custom_rollout_verify.py --profile s08
```

Esperar READY sin update pendiente después de enviar cada cambio; comprobarlo antes de invocar con `python s08-deployment/lab/lab_custom_rollout_verify.py --profile s08 --status-only`. Después del rollback, copiar el resultado a `reports/lab-custom-rollback-verified.json`. El verificador no convierte un envío en prueba de recuperación. El smoke del agente no prueba el custom. Para actualizar el agente principal se configura una versión única y se verifica con `lab_smoke.py`; su rollback consiste en reponer la versión estable conservada. Ningún alias mueve el tráfico automáticamente.

CP4, cargar y desplegar App:

```bash
python s08-deployment/lab/lab_app.py --profile s08
```

Abrir **Compute → Apps → nombre configurado**, revisar deployment y logs, abrir URL con sesión corporativa. `reports/lab-app.json` registra envío; probar pregunta en UI para acreditar uso real.

CP5–6, tras llegada de inferencias:

```bash
python s08-deployment/lab/lab_monitor.py --profile s08
python s08-deployment/lab/lab_monitor.py --profile s08 --create-monitor
```

Primero aplana registros reales; luego crea monitor. No repetir creación si ya existe: abrir tabla `inference_flat` en Catalog Explorer → Quality/monitoreo, inspeccionar estado y solicitar refresco mediante UI disponible. El monitor usa ventanas horarias y una baseline explícita de eventos exitosos iniciales, materializada una vez. Comparar contra esa muestra prueba el circuito, no calidad semántica ni generalización. Una creación recién enviada sin datos suficientes no demuestra drift calculado. Los nombres de pestañas pueden variar con disponibilidad del workspace.

CP7, bundle desde su carpeta para que la CLI encuentre `databricks.yml`:

```bash
cd s08-deployment/bundle
python - <<'PYBUNDLE'
import json, subprocess
from pathlib import Path
config = json.loads(Path('../lab/config.json').read_text())
package = json.loads(Path('../reports/lab-package.json').read_text())
values = {
    'catalog': config['catalog'], 'warehouse_id': config['warehouse_id'],
    'model_name': config['model_name'], 'model_version': package['version'],
    'schema': config['schema'], 'endpoint_name': config['endpoint'] + '-bundle',
    'app_name': config['endpoint'] + '-bundle-ui',
}
subprocess.run(['databricks', 'bundle', 'validate', '--target', 'dev', '--profile', 's08',
                '--var', ','.join(f'{k}={v}' for k, v in values.items())], check=True)
PYBUNDLE
```

Revisar variables requeridas y recursos resueltos en la salida. La creación/despliegue solo se hace en el entorno asignado siguiendo notebook; validación no crea el servicio. Volver a raíz del repo al finalizar. Para prompts usar CP7 del notebook, que registra y recupera la versión en MLflow. No escribir contraseñas ni tokens en archivos de bundle.

## Configuración unificada y modo de verificación

CP0 del notebook calcula un sufijo por equipo y persiste `lab/config.json` en **la copia del alumno**; los scripts en ese mismo filesystem leen esa configuración. El ZIP local y el Workspace importado son **copias distintas**. Después de CP0 y antes de ejecutar comandos en tu Terminal local, sincroniza:

```bash
python s08-deployment/lab/lab_import_workspace.py --profile s08 --pull-config
```

Usa el mismo `--folder` que al importar. Si trabajas con un Git folder creado por otra ruta, descarga su `lab/config.json` desde Workspace a `s08-deployment/lab/config.json` local. Compara catálogo, schema, endpoint y App con CP0 antes de continuar; el importador no sincroniza cambios automáticamente. No descargues una configuración de otro equipo.

 Se pueden completar sufijo/esquema explícitos, siempre AIS08. El docente usa sufijo `neptuno`, esquema `ais08_lab` y su catálogo sólo para repetir su ensayo. No compartir una copia editable entre equipos.

El modo predeterminado `verificar` inspecciona recursos existentes y hace consultas reales de prueba; no registra modelos ni cambia tráfico. El modo `crear` habilita las mutaciones descritas en cada celda; se ejecuta por checkpoints, esperando los estados de nube. En CP3 elegir canary/rollback y ejecutar sólo esa celda evita volver a crear el endpoint. La validación automatizada del notebook recorre el source exacto en modo verificar; las mutaciones de infraestructura se comprueban mediante scripts y reportes separados.

CP7 muestra el YAML en notebook; la validación oficial de Bundles se ejecuta desde Terminal con el CLI. El ejemplo de CI no es evidencia de una corrida remota. El ejercicio de alias del prompt mueve y restaura la referencia; el modelo ya empaquetado conserva su versión fija. Para cambiar su conducta, volver a empaquetar, actualizar la versión única del agente y repetir CP1–2; CP3 es el complemento custom.

La configuración docente probada habilita payload logging. Usage tracking/rate limiting administrados son una explicación con compatibilidad por tipo de endpoint; no se atribuye una usage table al agente si no fue configurada y observada. Los tokens de custom_outputs y el SQL de billing son señales diferentes.
