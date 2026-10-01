# Capacidades temporales y cierre portable051

Fecha: 2026-09-28. Estado: implementación técnica local, revisión independiente pendiente; SK12 provisional. CreatorZ reutilizado de039. Sin web, SDK, autenticación, paquete real ni cambio a autorizaciones/journals.

## Investigación acotada

| Fuente primaria local | Hecho observado | Decisión |
| --- | --- | --- |
| `deployment/build_bundle.py` antes051 | ROOTS recorre deployment; filtro excluye sólo017 y state | Sustituir identidad de una corrida por namespace de capacidades |
| `tests/unit/test_bundle_state_039.py` | Conserva near-misses, plantillas y evidencia | Retener regresión; ampliar nombres sin excluir substrings arbitrarios |
| Nombres `deployment/phase-s-050-authorization.json` y `phase-s-050-corrected-authorization.json` | Nuevas capacidades top-level alcanzadas por ROOTS | Reproducir con contenido sintético, sin leer/modificar originales |
| `src/sbs/runtime_structural.py` y cierre de evidencia049 | Cargador consume archivos runs047/046/041 además de código/data | Auditar selección sin construir; no afirmar portabilidad por inclusión del módulo |

Alternativas: lista enumerada de nombres vuelve a fallar con la siguiente autorización; excluir todo deployment perdería planes/configuraciones; excluir toda aparición de `authorization` perdería plantillas/historia. Política elegida: archivos directamente bajo deployment cuyo basename termina exactamente `-authorization.json`. Mantener exclusión del árbol state. Las capacidades futuras se colocan en esa ubicación o exigen política explícita. Una copia histórica fuera de ese namespace conserva su identidad de evidencia; eso no la convierte en autorización vigente.

## RED → GREEN

`runs/sk12-package-capabilities-051-red.txt`: dos builds sintéticos temporales incluyen050 y corregida050. `red-v2.txt`: añade necesidad discriminante de selección no escritora; tres fallos. `green.txt`: cinco pruebas pasan (tres051 y dos039) después de cambio mínimo. No son builds del repositorio real.

Assertions: sin capacidades en tar/manifiesto; mismos miembros y SHA de bytes; originales sintéticos byte a byte intactos; con/sin modelos; preservación de planes, configs, template, example, history, stateful y state.json; helper de selección no abre tar ni escribe runs. `selected_paths` es la misma función que consume `build`, evitando un auditor con reglas distintas.

## Auditoría de perfil049

`runs/sk12-package-capabilities-051-profile049-dry-audit.json` compara35 rutas necesarias del cargador/config/código contra selección actual. Ambas variantes incluyen28, pero faltan:

- `runs/sk04-embeddings-041-vectors/vectors.json`
- `runs/sk04-structural-ranking-047-v2/index.json`
- `runs/sk04-structural-ranking-047-v2/record.json`
- `runs/sk04-structural-ranking-047-v2/records.json`
- `runs/sk05-query-compatibility-046.json`
- `runs/sk07-runtime-structural-049-config.json`
- `runs/sk09-query-compatibility-046-review.json`

Después del hallazgo se añadió una allowlist exacta de esos siete archivos mediante `include_structural_profile=True` (CLI `--include-structural-profile`); no se ampliaron ROOTS ni RUN_PATTERNS ni se construyó paquete real. El default conserva siete ausentes; ambas variantes opcionales tienen cero ausentes. Si falta un archivo de la allowlist, la selección falla antes del build. La opción incluye la configuración local049 habilitada pero no activa el runtime: el consumidor debe pasar explícitamente structural_config_path. El manifest registra la inclusión y el archivo tar usa sufijo `-structural` para distinguirlo del default. Antes de futura entrega portable, probar la app completa en raíz extraída sin acceso al origen. Esta auditoría acota el cierre del cargador049, no dependencias instaladas, runtime de generación ni cloud. El paquete040 existente no contiene estas mejoras y no se le atribuyen pruebas051.

Límites: filtro de ubicación/nombre, no detector universal de credenciales; archivo activo ubicado fuera del contrato exige revisión. Tests sintéticos prueban política/bytes, no permisos externos ni aceptación E2E o mejora conductual general de la skill. Evaluador distinto aún debe revisar código, casos y resultados.


Suplemento GREEN de cierre: `profile-red.txt` conserva tres fallos por falta de opción explícita. `profile-green.txt` registra ocho pruebas exitosas: se copian sólo las35 rutas seleccionadas del cierre049 a una raíz temporal y el loader real verifica el índice231 con sus pins; no se llama build sobre el repositorio. `profile049-green-audit.json` registra default7missing y opt-in0missing con/sin modelos, manteniendo cero autorizaciones050/state seleccionados. Esa prueba del cargador no ejecuta la app extraída ni sus dependencias instaladas.
