# S08 · Preparar el lunes y recuperar un fallo

Este laboratorio crea consumo real. Todos los comandos usan la copia y configuración del equipo; `s08` es un perfil local de ejemplo, nunca una credencial compartida. El recurso docente se identifica en EJEMPLO-RESUELTO.md. No aplicar estos comandos a un servicio productivo.

## Antes de clase

1. Abrir el repo completo y revisar `VALIDACION.md`: los IDs allí son evidencia del ensayo, no garantía de disponibilidad futura.
2. En Terminal, activar el entorno de `lab/requirements.txt`, autenticar el perfil y confirmar `lab/config.json` propio.
3. Consultar estado y activar la App si quedó detenida:

```bash
python s08-deployment/lab/lab_lifecycle.py status --profile s08
python s08-deployment/lab/lab_lifecycle.py start-app --profile s08
python s08-deployment/lab/lab_status.py --profile s08
```

4. Esperar App RUNNING y ambos endpoints READY **sin configuración pendiente**. Scale-to-zero puede requerir una primera inferencia para despertar el servicio. El warehouse también puede arrancar al ejecutar SQL. Reservar tiempo suficiente antes de entrar; no se garantiza un número de minutos.
5. Ejecutar `lab_smoke.py --profile s08`, revisar cada caso y guardar el reporte. Si la moderación rechaza una consulta benigna, conservar el error; investigar el framing/criterio sin deshabilitar el filtro para conseguir una aprobación.
6. Abrir App con identidad autorizada; hacer una pregunta de ventas y una ambigua. Correlacionar evidencia del backend con el servicio. Las personas necesitan acceso propio: el perfil CLI del docente no inicia sesión en su navegador.
7. Consultar tablas raw/flat y última actualización del monitor. Preparar evidencia real anterior identificada por fecha para explicar retrasos asíncronos sin presentarla como tráfico recién llegado.

## Si algo falla

| Síntoma | Diagnóstico | Recuperación y criterio |
|---|---|---|
| 401/403 | Identidad que llama y recurso que rechaza | Corregir el permiso específico con el responsable. No pegar un PAT en el frontend. Repetir la llamada. |
| READY con update pendiente | Configuración activa versus candidata | Esperar NOT_UPDATING; comparar versión servida y repetir smoke. |
| Error de dependencias | Build logs y versiones declaradas | Corregir archivo de dependencias y registrar una versión nueva; no modificar el artefacto ya evaluado. |
| Consulta ambigua devuelve cifra | Traza, argumentos y regla de periodo | Detener promoción; reproducir con benchmark S06 y corregir el contrato. |
| Safety rechaza una consulta benigna | Control administrado, contenido y contexto | Guardar evidencia del falso positivo; revisar diseño antes de repetir. Un fallo se mantiene fallo. |
| Tabla raw vacía | Configuración de logging, permisos y tiempo desde solicitud | Esperar entrega asíncrona dentro de ventana documentada. Sin fila real no se aprueba logging. |
| parse_error | Schema observado y rutas JSON | Preservar filas fallidas, corregir transformación y repetir; no convertir null en cero. |
| Monitor sin métricas | Estado de refresh, tabla fuente y baseline | Corregir causa y refrescar. Create exitoso no demuestra métrica calculada. |
| Regresión en canary custom | Snapshot del endpoint `ais08-neptuno-rollout` y gates | Restaurar con `lab_rollout.py --rollback`; esperar y ejecutar `lab_custom_rollout_verify.py`. |
| Regresión del agente principal | Versión única actual frente a estable | Restaurar la versión estable en configuración; esperar sin update pendiente y ejecutar `lab_smoke.py`. No usar split. |

## Después del ensayo

```bash
python s08-deployment/lab/lab_lifecycle.py stop-app --profile s08
python s08-deployment/lab/lab_lifecycle.py status --profile s08
```

Detener App es reversible y conserva el código/configuración. Los endpoints del laboratorio tienen scale-to-zero; su estado se revisa por separado. No borrar modelos, tablas de inferencia ni snapshots para ahorrar durante una prueba: eso destruye evidencia y puede romper logging. El warehouse respeta su política de auto-stop; es compartido, no detenerlo indiscriminadamente.

Costos: `lab/lab_costs.sql` es una consulta de referencia sujeta a permisos de system tables. Tokens del agente no incluyen toda la factura: contar también llamadas de moderación/embeddings, Serving, App, SQL y monitor. No asumir costo cero por terminar una consulta.

## Preparación del complemento canary

`agent/v1/responses` no admite traffic splitting. Preparar el custom antes de clase y verificarlo por separado:

```bash
python s08-deployment/lab/lab_custom_rollout.py --profile s08 --deploy
python s08-deployment/lab/lab_custom_rollout_verify.py --profile s08
```

Leer las versiones reales en `reports/lab-custom-rollout-package.json`; no ejecutar `--deploy` en bucle si ya existe. El estado del agente y el de la App no prueban disponibilidad del custom. Después de cada cambio esperar READY sin configuración pendiente. Conservar evidencia separada del agente y del custom.
