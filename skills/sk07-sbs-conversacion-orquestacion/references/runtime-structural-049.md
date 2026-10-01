# Perfil local estructural049

Estado: implementación local provisional, evaluación independiente pendiente. Construida con CreatorZ, SK07, proyección SK04 y estrategia `span-limpio-contexto-v1` adaptación047. No amplía aceptación ni autorización del modelo.

```python
from sbs.runtime import create_service
service = create_service(structural_config_path='runs/sk07-runtime-structural-049-config.json')
```

La configuración de servidor debe ser exactamente `{"enabled":true,"profile":"structural-development-047-v2"}`. Nunca procede de HTTP/usuario del chat. Omitir el argumento devuelve el comportamiento anterior135; desactivar requiere una nueva instancia por la fábrica normal, preservando consumidores anteriores. No se crea configuración en `config/`, ni se escribe release/puntero. Cloud y configuración release simultáneas se rechazan. El objeto resultante es LocalService real y conserva `ask`, Conversation, GeneratedClaims, permisos, fuentes y comparación; únicamente cambia índice, caché verificada, contrapartes y snapshot. No se ha ejecutado generación ni conversación E2E049.

## Investigación y decisión

Fuentes locales consultadas el 2026-09-28: `src/sbs/runtime.py` (legacy135+expansión), `operations/preparers.py` (SK04 vuelve a formar raw-page chunks), `operations/runtime_release.py` (closure y swap), `retrieval/structural_ranking.py` y referencia047 (proyección231 literal), informe/revisión046 (compatibilidad observada), salida047v2 (índice, vectores, registros). No hubo búsqueda web, descarga, SDK, autenticación ni qrels para implementar/recuperar. No se reevaluaron métricas.

Alternativa descartada por brecha comprobada: sólo empaquetar con `build_real_hooks`; reconstruye raw pages y no consume proyección de unidades solapadas. Decisión mínima: perfil versionado en módulo `runtime_structural.py`, constructor separado antes de vincular a instancia nueva. SK11 permanece sin modificar. Procedencia e inputs se fijan en `runs/sk07-runtime-structural-049-invocation.json` y snapshot previo.

El perfil comprueba record047v2 contra hash fijo del código; report046 contra revisión046 fija; dataset y vectores contra pins de ambos; PDFs, rawtext y result.json contra manifiesto026 anclado; reproyecta registros para comparar identidad literal; valida modelo exacto y pregunta/embedding antes de construir LocalIndex231. Los archivos047 son sólo lectura. Devuelve cierre en metadata y nuevo snapshot que incluye identidad de índice y fuentes. Esto prueba bytes/contrato observado, no identidad inmutable de pesos remotos.

## Invariantes y pruebas

| Riesgo | Control | Evidencia049 |
| --- | --- | --- |
| Cambiar etiqueta sin usar vectores | LocalIndex231 y hash exacto047 | Vector/RRF/ONNX en `runtime-evidence.json` |
| Alterar fuente/caché/índice reseñado | Cierre antes construir índice | Ocho tamper de PDF/raw/result/query/model/records/index/record |
| Confundir foco/ranking o perder contrapartes | Mapa por doc/versión/start/end/text de citas SK03 anotadas | Runtime trace separa counterparts y selected_provision_expansion |
| Cruzar familia/par | Contexto igual al foco del servidor y whitelist de retrieve | Tres pares/focos y rechazo contexto alterado |
| Reusar memoria o Genie previo | Snapshot nuevo, session_key separado; Genie unpublished | Tests de aislamiento; consulta Genie no ejecutada |
| Inferir compatibilidad universal | Guard de preguntas exactas046 antes de modelos | Query nueva rechazada |
| Promover accidentalmente | Argumento explícito local, sin default ni write; rechaza mezcla | Default135/release regresiones y estado previo retenido |

La expansión conserva citas SK03 adicionales con IDs originales; los pasajes estructurales conservan `citation_id=passage_id`. No borrar una por tener el mismo texto: identidad/procedencia distintas no demuestran nueva evidencia independiente. Metadata de páginas/origen queda fuera del EvidencePack cerrado. Notas, mobiliario y solapamientos siguen limitaciones del dataset, no limpieza jurídica.

## Evidencia y gates

`runs/sk07-runtime-structural-049-probe.py` carga las tres preguntas046 y ONNX ya fijado047 (sin `initialize_models`), llama `LocalService.rag`, verifica EvidencePack y literales. Traza real de 20 candidatos por canal, reranking20, top5 con contrapartes y expansión; no contabiliza métricas de calidad ni reentrena nada. `rag_live` conserva inicialización existente para uso conversacional autorizado posterior; no fue ejecutado en049. No presentar el guard usado en la prueba como evidencia de autenticación cloud.

Antes de promover: revisión SK09 independiente de esta integración; criterios de calidad aprobados y evaluación separada de las tres preguntas expuestas; compatibilidad declarada para nuevas consultas sin asumir que046 la acredita; preparación SK11 del mismo índice/cierre y publicación/verificación SK06 de Genie para el nuevo snapshot; pruebas reales de conversación, contexto/seguimientos, UI, autorización y despliegue con configuración entregada. La ruta de recuperación LocalService/retrieve se reutiliza; falta el adaptador SK11 de preparación231 y su revisión. No quitar gates ni ajustar qrels/thresholds para conseguir aprobación.
