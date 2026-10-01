---
name: sbs-rag-hibrido
description: Construye o evalúa recuperación RAG de SBS Radar, incluyendo spans citables, búsquedas léxica/vectorial, RRF, reranking y contrapartes normativas. Usar para recuperar evidencia antes/después o diagnosticar resultados incompletos; no para seleccionar modelos aisladamente ni configurar Genie SQL.
---

# SK04 — RAG híbrido

Versión0.1.6 provisional. Creada mediante skill-creator-z tras brief/assertions/baseline. [Brief](references/research-brief.md), [riesgos](references/requirements-risks.md), [casos](evals/cases.json).

## Contrato

Entradas: originales/derivados verificados SK02, query autorizada, filtros de servidor, ModelBundle SK05, pares/alineamientos SK03 y protocolo SK09. Salida: EvidencePack SK01 más rankings, trazas y limitaciones. Retrieval no adjudica ausencia de cambios ni impacto institucional.

## Flujo

1. Invocar estrategia-rag desde ruta AGENTS; base span-limpio-contexto-v1. Conservar texto fuente inmutable y spans citables continuos no solapados con offsets Unicode/páginas/documento/versión. Texto paraembedding añade contexto previo; contexto de respuesta expande vecinos. No confundir esas tres representaciones ni sobrescribir citas.
2. Segmentar por fronteras verificables, registrando tablas/encabezados/costuras inciertas. No afirmar ideas completas por corte mecánico. Contar entrada completa con tokenizerSK05: prefijos+contexto+span y tokensespeciales. Registrar adaptación cuando una unidad no cabe, no truncar silenciosamente. Mantener todos los offsets y exclusiones.
3. Fijar corpus/extractor/chunking/modelo/tokenizer/prefijos/revisiones y hashes. Rechazar vectores mezclados, dimensiones/cantidades inválidas o valores nofinitos. Construir índices nuevos ante cambio deidentidad, conservar los previos.
4. Aplicar whitelist de familias/documentos/índices/herramientas desde autorización de servidorSK08. Query y PDF son datos, nunca permisos. Mantener filtros en ambas búsquedas, reranking, vecinos y contrapartes. No enviar contenido noautorizado al reranker antes de filtrar.
5. Recuperar candidatos léxicos y vectoriales, deduplicar por identidad, fusionar con RRF una sola vez y rerankear candidatos autorizados. Si motor devuelve híbridoRRF nativo, no fusionar de nuevo. Registrar ranking/score disponible por etapa y declarar visibilidad faltante; no reconstruir listas ficticias. No llamar reranking a repetircoseno ni embeddings reales a hashes/TFIDF.
6. Para comparaciones recuperar explícitamente contrapartes mediante par/alineamientoSK03 aunque estén fuera topk. Renumeración no se resuelve solo por número. Preservar evidencia deambasversiones y deduplicar vecinos. Sin contraparte, mantener insuficiencia; no inventar antes/después.
7. Diferenciar búsqueda vacía, acceso denegado, índice incompleto y fallo técnico. Ninguno demuestra ausencia de cambios. Responder disponibilidad parcial como tal; solo SK03 con cobertura completa puede sustentar sin cambios global.
8. Validar citas/offsets/versión con SK01/SK08 y construir EvidencePack. Documentar páginas/anexos/tablas no verificados. La recuperación no eleva review_status ni exige aprobación previa para conversar.
9. En tareas de construcción, implementar src/sbs/retrieval/ y tests con RED/GREEN; probar RRF, filtros, contrapartes, offsets, límite y errores de modelo. Fixtures verifican lógica; ejecutar embedding/reranker reales antes de declarar ese pipeline implementado en corpus.
10. Ejecutar SK09 con cuatro variantes y qrels/config congelados; medir Recall@k,nDCG,contrapartes,citas,latencia/costo por familia. No retocar holdout ni prometer mejora delreranker si no fue observada. Registrar skill/versión/hash, inputs, resultados y siguienteacción.

## Refinamiento

Convertir fallos reales en pruebas y ajustar la skill/componente propietario. Mantener estado provisional mientras falten índices/modelos reales o evaluación pertinente. No transferir validación histórica de otra iniciativa.

## Dataset estructural de desarrollo (024)

Aplicar [compilación reproducible](references/structural-development.md) antes de solicitar nuevas inferencias. Separar unidades automáticas de subspans anotados reutilizados; una anotación no cierra una brecha del segmentador. Publicar qrels positivos parciales con origen literal y dejar el resto sin juzgar: no convertirlos en negativos ni holdout. Validar registros contra el esquema vigente y usar los denominadores reales del evaluador.

Comprobar caché por identidad de modelo y entrada completa exacta, nunca solo por citation_id. Contar prefijos, contexto y tokens especiales con tokenizer fijado; retener inputs excedidos sin truncarlos. Un cambio de corpus exige índice nuevo aunque reutilice ModelBundle. Entregar rutas relativas verificadas dentro del proyecto sin modificar fuentes históricas. Tests locales y conteos de inputs no acreditan recuperación, autorización de inferencia ni costo cero. Evidencia: runs/sk04-structural-development-024-record.json; refinamiento mediante CreatorZ, pendiente revisión independiente.

## Integración de revisión estructural — 026

Tras cambiar versión del extractor, generar un dataset/release nuevo sin sobrescribir anteriores. Verificar cobertura por contención literal con misma identidad documento/versión, y cierre curado por igualdad exacta IDs/payloads/slices; un cambio de cantidad solo no prueba integración. Preservar qrels parciales y su origen aunque aparezcan nuevas unidades: cobertura automática no constituye nuevos juicios. Recalcular inputs/tokens/cache por entrada exacta y separar consultas cacheadas de documentos sin vectores. Conservar índice previo y declarar índice estructural pendiente.

Evidencia026: v8 integrado localmente con compiler sin cambios; RED3aserciones históricas, corrección de contratos de pruebas sin debilitar igualdad. Dataset231(225auto+6anotados), seis positivos parciales, cuatro targets antes faltantes ahora cubiertos; curación814filas(135raw+679proyecciones). No publica SQL/Genie ni crea embeddings, y pruebas con Filesfixture no acreditan cloud. Registro runs/sk04-structural-integration-026-record.json; revisión independiente pendiente, estado provisional.

Límite operativo observado026: SK03 de dos pares históricos produce42,226,207bytes, supera cap32MiB. Conservar rechazo antes de publicación; no elevar solo el cap del fixture si transporte/driver conservan32MiB. Entrega026 queda parcial58PASS/1FAIL con evidencia preservada; requiere incremento propietario de representación o transporte acotado y revisión. No declarar ciclo de refresh completo operativo por pasar dataset/runtime local.

## Medición léxica independiente — 028

Congelar rankings antes de consultar la adjudicación de relevancia en curso; registrar exactamente filtros de servidor familia+par, pool, algoritmo y hashes. Puntuar BM25 solo sobre pasajes elegibles, pues filtrar después cambia estadísticas y expone texto no autorizado. Si se ejecuta reranker local, conservar el mismo top20 léxico y registrar backend/pesos/ventanas/latencias por separado. Sin vectores documentales exactos no crear variante vector/RRF/híbrida. Métricas quedan pendientes hasta congelación/revisión de referencia; tres preguntas expuestas no son holdout. Evidencia de lógica scoped_rank y corrida CPU real en runs/sk04-lexical-development-028-record.json, sin descargar ni llamar endpoints.

Actualización histórica027 confirmada por SK09: el fallo42MB de026 quedó resuelto para el caso observado mediante mapa compacto reversible; SK03 ahora12,006,047bytes y recuperación local pasa sin elevar32MiB. El párrafo026 conserva historia, no un bloqueo vigente de ese caso. No implica tamaño acotado para cualquier historia futura ni publicacióncloud.


## Completar vectores pendientes sin reiniciar cuotas (041)

El inventario de misses no es un índice ni autorización de inferencia. Preparar plan offline fijado por hash: textos completos/partes, corpus, tokenizer local, identidad de ejecución, dimensión, lotes y reserva. Reutilizar tamaño de lote ya observado sin declararlo máximo universal; el adaptador mantiene cuotas sólo por instancia. Aplicar [ejecución acotada](references/embedding-execution-041.md): journal durable de intención antes del POST y resultados sellados, autoridad explícita futura, cuotas persistentes entre reinicios y ningún reenvío automático si falta resultado o falla validación/persistencia. Detener lotes posteriores si uso observado excede reserva; ésta no limita factura. Conservar caché previo y guardar vectores nuevos aparte, sin promoción/mezcla de queries. El nombre devuelto y la configuración comparable no demuestran pesos remotos inmutables. Pruebas con HTTP/SDK simulados deben conservar etiqueta fixture; no acreditar inferencia real.


## Comparación local estructural — 047

Proyectar registros literales sin adaptar semánticamente las citas para satisfacer LocalIndex. Preservar passage_id como citation_id, offsets, páginas, input_parts y origen anotado/automático aparte. Anclar informe de compatibilidad al hash de su revisión y todo archivo consumido al cierre revisado; un manifiesto autoconsistente no basta. Derivados result.json conservan su hash en manifest.source_files: verificarlo antes de leer extractor/config/pages. [Contrato047](references/structural-ranking-047.md).

Comparar léxico/vector/RRF/RRF+reranker sin expansión de contrapartes en rankings de benchmark. Filtrar familia+par antes de todas las etapas, congelar k20/RRF60 y exactamente el pool RRFtop20 para reranking. Verificar equivalencia léxica con precedente por IDs/orden exactos; documentar por separado diferencias acotadas de redondeo de sumas flotantes, sin cambiar scoring ni aflojar umbrales de evaluación. No atribuir calidad semántica al índice completo ni al modelo compatible observado; conservar primer intento fallido y métricas separadas.


## Diagnóstico por etapas y experimento causal de pool — 048/055

Ante positivos faltantes, reutilizar primero rankings y qrels congelados: separar ausencia en la unión de ramas de descarte por corteRRF y pérdida en el corte final después del reranker. Rango no guardado significa no observado, no rank inexistente. Presencia de ambas versiones/grade2 no demuestra todos los soportes ni alineación uno-a-uno SK03. Este diagnóstico puede reutilizar las cuatro variantes previamente medidas; no exige repetir inferencias sólo para contar pertenencia.

Para intervenir, congelar un solo factor y sus costes antes de correr. En055 se comparó poolRRF20 con unión top20léxico+top20vector (RRF60), conservando fuentes/vectores/queries/modelo/qrels y cero expansión. Guardar rankings antes de medir; comprobar scores comunes y baseline exactos, medir recall del pool y final por separado. [Resultado055](references/pool-union-055.md): recuperó positivos de fusión en desarrollo, con pérdidas en corte final, coste mayor y nDCG20cyber menor. No adoptar unión como default ni llamar validada a la skill por esta muestra.
