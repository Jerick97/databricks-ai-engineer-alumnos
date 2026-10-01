# Contrato Apps080 — investigación acotada CreatorZ

Fecha: 2026-09-29. Capacidad: llevar selección de ensayo077 a configuración revisable de Apps sin activar ni promover.

## Fuentes y decisiones

| Fuente primaria local consultada | Hecho | Decisión |
|---|---|---|
| deployment/app_release_070.py y app_deploy_070.py, freeze070 | El builder fija073; gate sólo admite073/075 y liga comportamiento075 | Capas080 separadas; preservar070 y su efecto remoto |
| src/sbs/runtime.py, hash de plan077 | LocalService acepta selección; create_service devuelve servicio con carga lazy | Adaptador externo asigna antes de initialize_models; prueba factory real sin inferencia |
| config/generation-selection-077.json y observation072 fijada | Endpoint/model de Llama e identidad exacta disponibles | Reusar load_selection y cierre por hash; no inventar identidad |
| deployment/generation-rag-077-plan.json y admission del ensayo | Plan fija runtime/prompt/config/datos de ensayo | Comparar todos inputs de comportamiento contra manifiesto staged |
| tests/unit/test_app_selection_080.py y runs/*080-red.txt | Cinco fallos iniciales: selector/módulos ausentes | Pruebas negativas y contrato integral sintético aislado |

No nueva consulta cloud/web, SQL ni inferencia: el cambio es conexión local de contratos existentes y congelados. Documentación externa histórica no se usa para afirmar permisos o estado actuales. Confianza alta en hechos por lectura/hash; calidad real, despliegue y UI fuera de estas pruebas. Alternativas: modificar070 rompería snapshot congelado; modificar runtime077 invalidaría plan probado. Capas080 mantienen ambos; deploy080 conserva copia del efecto070 y permite revisión del diff.

## Requisitos y riesgos

- Activar ante cambio explícito de modelo/configuración Apps; no ante comparación normativa aislada.
- Sólo073/077 desde entorno servidor, nunca request. Rechazar URLs, paths relativos escapados, vacío y selección075.
- Detener build sin muestra revisada; no crear directorio. Detener execute sin revisión exacta antes de cliente/efecto.
- Rechazar mezcla de familias de resultados, plan/admisión distinto, endpoint/model distinto, citas ausentes, hashes de respuestas o comportamiento alterados.
- Incluir entrypoint/adaptador y config en manifest. La muestra077 prueba comportamiento congelado, no los nuevos conectores080: revisión posterior del paquete exacto obligatoria.
- No inferir calidad/E2E por assertions sintéticas. Mantener estado provisional; costes/tokens de benchmark conductual no medidos.

## Evaluación y presión

Baseline080: cinco fallos preservados. GREEN: tests080 ampliados y regresión070; casos nominales sintéticos aislados, mutation de respuesta/runtime, selección divergente y review no aceptado. Factory real de servicio local con initialize_models prohibido prueba conexión y catálogo sin inferencia. Urgencia («despliega ya: smoke200 basta») no salta QUALITY_REQUIRED; coste hundido («no repitas muestra, cambia runtime») dispara IMPLEMENTATION_MISMATCH. Near-miss: documentación de autoría puede variar, prompt no. Las assertions distinguen nominal y mutation; no hay evaluación de agentes sin/con skill ni mejora conductual general medida. Revisión root separada requerida.
