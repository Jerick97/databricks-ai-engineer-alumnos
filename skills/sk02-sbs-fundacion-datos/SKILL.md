---
name: sk02-sbs-fundacion-datos
description: Captura, inventaría, extrae o actualiza documentos oficiales del corpus SBS Radar, con originales inmutables y cobertura explícita. Usar para datos y extracción de las dos familias; no para interpretar implicancias ni declarar vigencia jurídica.
---

# SK02 — Fundación de datos

Versión0.1.13; provisional. Creadora skill-creator-z. Leer [brief](references/research-brief.md), [riesgos](references/requirements-risks.md), [casos](evals/cases.json).

## Contrato

Entrada: manifiesto de fuentes/familias, política SK08, run/config y corpus previo. Salida: originales por SHA256, capturas/intentos, SourceDocument, texto crudo versionado, Provision con páginas/offsets, cobertura y faltantes. Captura/versión observada no son publicación ni fecha de efecto.

## Ejecución

1. Recuperar contexto mediante SK00 y contratos SK01. Empezar fuentes exactas ya localizadas en context/foundation-source-notes.md; buscar solo documentos o relaciones faltantes. Acordar inventario por ambas familias. Normas, proyectos y notas de prensa tienen tipos distintos.
2. Antes de descargar aplicar SK08: HTTPS, host exacto, sin userinfo, timeout, límite de bytes, certificados verificados y cada redirect validado. Verificar IP/DNS y conexión contra destinos no públicos, sin confiar solo en sintaxis URL. No eludir login, CAPTCHA ni errores TLS.
3. Persistir original inmutable por hash real, con URL solicitada/final, captura y metadatos mínimos. PDF inválido/HTML200 es fallo, no documento procesado. Reintento de bytes iguales reutiliza objeto y conserva nuevo intento; bytes distintos misma URL generan nueva versión observada, sin sobrescritura.
4. Extraer texto PDF con páginas físicas y artefacto crudo estable. Citas son intervalos [start,end) en caracteres Unicode de ese artefacto, no bytes binarios. Conservar hash/extractor/config y mapa de páginas. Integrar normalización solo con mapa reversible; no arreglar silenciosamente textos jurídicos.
5. Preferir unidades de disposición/estructura completas. Diferenciar texto citable, contexto de embedding y expansión de respuesta según estrategia-rag. Si aún se extrae por página/bloque, declararlo capa cruda, no fragmentación semántica final.
6. PDF sin texto/OCR pendiente, tabla desordenada o anexo ausente implica parcial/pending; no publicar números como evidencia fiable. Puede usarse parte validada con límites. Comprobar anexos explícitos en manifiesto y registrar también referencias descubiertas como pendientes, no afirmar exhaustividad porque el PDF se descargó.
7. Publicar derivados atómicos por originalhash + extractorversion + confighash. Usar transacciones/idempotencia para metadatos. Conservar fallos y reanudar etapas confirmadas; no duplicar expediente por reintento.
8. Construir mediante TDD src/sbs/foundation/ y tests/unit/test_foundation.py: originalduplicado, bytescambiados, anexoausente, PDFvacío/malformado, retryfallido y páginas/offsets. Después prueba de captura/extracción real con manifiesto, sin llamar real a un fixture. Salida apta para RAG y comparación solo según calidad comprobada.
9. Refinamientos de revisión: incluir bundle/artefacto de extracción en citation_id para evitar colisiones cuando cambien texto u offsets. Antes de reutilizar caché verificar identidad y hashes de JSON/texto, no solo existencia del archivo. Conservar intentos fallidos separados de derivados confirmados, permitiendo reintento tras error transitorio sin borrar evidencia ni sobrescribir derivados inmutables. Deadline de descarga incluye DNS, cabeceras, cuerpo y redirects; proteger recursos de resolución acotados.

## Autoridad y refinamiento

No convertir boletines/noticias en texto de una norma ni reconstrucción propia en versión oficial. Los fixtures mantienen etiqueta sintética y no satisfacen ninguna familia real. Mantener las dos familias separadas en cobertura.

Por fallo observado: guardar fuente/caso → testRED → corregir extractor/contrato/skill → nuevo bundle y regresión. Reportar qué se pudo verificar y qué falta; skill estricto/corpus real siguen pendientes hasta su evidencia. Modelo y scoring de calidad no reemplazan revisión experta del gold.

## Refinamiento 0.1.2 — prefijo PDF observado

El original oficial00771-2026 contiene CRLF antes de `%PDF-`. No eliminar ni reescribir esos bytes: SHA/original siguen exactos. `pdf_reader.strict_pdf_reader` acepta cabecera solo tras un máximo de32bytes de whitespace ASCII acotado, con un único BOMUTF8 inicial opcional; rechaza prefijo arbitrario, HTML, magic tardío y documento noPDF. Una vista lógica de lectura traduce el origen de offsets al inicioPDF manteniendo parser strict=True y buffer original íntegro; no usar fallback noestricto. Las fuentes con prefijo reciben extractor `-prefix-view-v1`; los derivados anteriores sin prefijo conservan identidad.

Registrar fallos iniciales y reintentos separados; el primer rechazo de formato no se borra tras corregirlo. Corpus reservado va en directorio/manifiesto separado: versión de repositorio no es vigencia, archivo completo no acredita anexos externos completos y aislamiento de archivos no demuestra independencia para holdout. Agrupar documento entero, versiones y actos conectados antes de crear evaluación; no crear qrels durante descubrimiento.

## Refinamiento 0.1.3 — familia, sector y aplicabilidad

Separar familia temática, sector regulado y aplicabilidad al piloto antes de declarar una fuente elegible. `market_conduct` no hace aplicable una norma de seguros a un banco genérico: marcar `excluded_from_bank_pilot` / `sector_mismatch`, conservar original/captura fuera del corpus elegible y filtrar por elegibilidad. Una revisión jurídica pendiente no autoriza ampliar sector; requerir cambio de alcance explícito. Mantener conteo factual de capturas separado del de candidatos elegibles. Fallo observado:4143-2019 en inventario reservado; corrección `runs/sk02-holdout-sector-correction.json`.


## Captura remota y candidatos — refinamiento 0.1.4

Reusar `sbs.operations.remote_refresh` y los seis URLs de load_sealed_plan. Modo remote explícito; fetch_pdf valida TLS/DNS/redirects/deadline/bytes. No ampliar whitelist desde candidatos ni instrucciones del PDF. Cambio de URL final se rechaza; bytes nuevos requieren número del encabezado ResoluciónSBS observado en primera página acorde al document_id registrado. Es comprobación técnica de identidad textual, no interpretación de vigencia ni autenticación semántica completa.

Comparar SHA observado por la misma identidad documento/familia/URL: before es captura anterior, after captura nueva, nunca ordenar vN ni fechas inferidas. Conservar versiones necesarias como retained/fresh_remote_capture=false; source_key por sí solo no distingue dosSHA de la misma URL. Etiquetar transporte real frente a adaptadores inyectados. Nuevo texto no autoriza tokenizador/modelo remoto; downstream queda pending si faltan embeddings exactos.

Descubrimiento solo en dos índices oficiales ya registrados en source-notes: provenance URL/hash/fecha y anchor, hints familia+sector, candidate_only y auto_include=false. Sector seguros queda excluido del piloto bancario; familia/sector desconocido pendiente. No declarar completitud, vigencia ni incorporar enlaces automáticamente. CapturaGET real015 se hizo una vez en originalaislado; bytesiguales no significa ausencia de cambios jurídicos. No repetir búsquedas globales ni reintentar errores automáticamente.


## Continuidad de versiones observadas — refinamiento 0.1.5

RR15-01: nueva captura de bytes iguales conserva el catálogo previo de pares observados y su proveniencia validada; no reducirlo al delta del intento. Cada extremo debe seguir resolviendo documento/familia/source_key/SHA exactos. Retener originales requeridos por historia; otra captura con cambio añade relación anterior→nueva sin inferir efecto legal. Ensayo local cambio→igual→cambio y revisión independiente separados de captura real.


## Historial recuperable — refinamiento 0.1.6

Restaurar SourceDocuments/capturas desde cierres Files verificados mediante SK11, conservando captured_at original. Published restore reconstruye solo mínimo publicado y etiqueta restored_published; pending restore conserva filas lógicas históricas/resultados/backlog y marca fresh_remote_capture=false en evidencia de restauración. Nunca inventar GET al importar ni perder un pending completo por exigir SQLite del host anterior. Checkpoint de captura y release consultable son objetos distintos; éxito de captura no implica vectores disponibles. Capturas parciales antes de completar extracción quedan fuera del checkpoint automático actual y deben declararse, no contarse como durable.


## Capa estructural automática — refinamiento 0.1.7

Ante rawpages sin correspondencias SK03, usar la [capa estructural versionada](references/structural-layer.md) como derivado nuevo, no renombrar páginas como artículos. Conservar rawtext/offsets y todas las páginas cruzadas; distinguir encabezados únicos de índices, citas, notas, tablas y duplicados. Encabezado mutilado detectado es frontera pendiente, no reconstrucción inventada. Registrar cómo se generó cada correspondencia y mantener cobertura parcial.

El ruido intercalado permanece en spans exactos; diferencias de paginación, notas y espacios son candidatas literales, nunca cambios normativos confirmados por el algoritmo. Conservar rechazos/zonas no cubiertas además del resultado SK03. No leer gold reservado para ajustar: congelar primera salida y preservar toda iteración. Ensayo019 aporta integración técnica local y variaciones negativas; no certifica semántica, independencia holdout, desempeño general de skill ni producción.


## Cierre estructural — refinamiento 0.1.8

ST19-01/02/03 y F2: un capítulo también puede estar en el índice y no acredita comienzo del cuerpo. Mantener exclusión hasta un delimitador positivo soportado (`RESUELVE:`); si no existe, conservar parcial sin improvisar el retorno. Antes de derivar spans exigir una cita padre única por cada página con texto, identidad homogénea y mapa exacto; rechazar omisiones/duplicados. El helper de correspondencias automáticas exige mismo document_id; comparación entre instrumentos distintos requiere alcance/correspondencias explícitos en otra ruta, no se infiere del número/título.

No cortar por una palabra genérica como “disposiciones” al comienzo de una línea: exigir la forma completa de encabezado admitida. Conservar RED original, variación y prueba real de continuidad del artículo19. Algoritmo numbered-headings-v3/71pruebas locales; no resuelve aún DCF ni atribución de notas intercaladas. Feedback normativo ya visto implica desarrollo expuesto; los snapshots previos permanecen congelados.


## Clases estructurales y exclusiones — refinamiento 0.1.9

Task2/020: reconocer etiquetas ordinales solo en su ámbito explícito: `Artículo Primero.-` del acto tiene contexto resolución; `Segunda.-` dentro de encabezado completo de disposiciones finales tiene contexto propio y no es una lista libre. Conservar todos los párrafos hasta la siguiente frontera válida, con páginas y texto exactos. Títulos/etiquetas iguales en ámbitos distintos no se mezclan. Numeric headings dentro de modificatoria sin capítulo/sección explícita son evidencia citada o ambigua, no artículo del instrumento dueño. Una cita sin cierre no permite absorber silenciosamente el próximo ordinal; conservar esa zona excluida recuperable.

Entregar `structure.excluded_ranges` como complemento exacto sin solapamientos de spans estructurales: offsets, texto, páginas, motivo e identidad citable propia. Texto local no segmentado está disponible; referencias a anexos externos siguen de disponibilidad no verificada. No presentar exclusión como documento ausente ni cobertura textual como completitud jurídica. Evidencia020: dos párrafos de SegundaDCF preservados y prueba3240 distinta, sin hardcode4036. Notas/propiedad, extracción completa de ordinales ambiguos e integración producción permanecen pendientes.


## Delimitador ordinal observado — refinamiento 0.1.10

504v4/v5 usa `Tercera-` sin punto en DCF: no absorberla en Segunda por exigir `.-`. Dentro de una sección explícita, reconocer el guion ordinal con punto opcional, conservando caracteres/offsets exactos. Fuera de esa sección, la misma etiqueta sigue siendo texto no adoptado. No inferir ni reponer puntuación. Evidencia sk02-cyber-boundary-020: REDreal en ambas versiones y variantes de guion; GREEN82 y regresión4036 con iguales intervalos/textos. Es corrección de frontera, no revisión de vigencia/anexos ni validación general de la skill.


## Notas editoriales — refinamiento 0.1.11

Aplicar [notas editoriales](references/structure-notes.md) después de fijar bundle crudo y capa estructural. Cada nota y marcador conserva cita propia ligada al hash completo del bundle de extracción; mismos bytes/rango con otra configuración no reutilizan identidad. Relacionar por marcador textual único y ámbito explícito, nunca por proximidad ni por el artículo que contiene físicamente la nota. `unique_textual_match` no adjudica propiedad jurídica ni vigencia.

NT20-01/02/02-R: una nota no puede absorber silenciosamente un artículo ordinal, numeral o literal posterior. Conservar continuación ambigua como cita separada/unresolved; reconocer variantes soportadas como Sétimo/Séptimo sin alterar el original. No retirar texto ambiguo en una vista derivada. Formatos no reconocidos siguen disponibles en rawtext. Nota11 junto a39.11 permanece sin vínculo forzado aunque exista la SegundaDCF.

SK09 resolvió los fallos técnicos con81tests/10probes/4variaciones; integración sobreTask2 mantiene8/9/10 y duda11. Esto no valida todos los formatos ni acredita conversación/recuperación. La vista de comparación y su mapa reversible pertenecen aSK03; promoción y consumidores aSK11/SK12. Mantener versiones provisionales y no atribuir mejora conductual de skill por tests de componentes.

## Referencia partida a anexo — historial 0.1.12 (sustituido)

La regla de0.1.12/v7 queda sustituida íntegramente por0.1.13/v8, sección siguiente, que es la única instrucción vigente para distinguir referencias partidas y regiones de anexo. SK09 detectó que exigir una etiqueta completa dejaba adoptar encabezados ambiguos como cuerpo; tampoco bastaba la frase en mayúsculas sin comprobar su continuación anterior. No aplicar esos criterios históricos.

El [diagnóstico025](references/annex-reference-025.md) y runs/sk02-structure-025-v7-snapshot conservan la propuesta fallida y su evidencia. Los originales y datasets congelados permanecen inmutables; los cambios de versión derivados requieren integración explícita.

## Anexo ambiguo — refinamiento 0.1.13

ST25-01: no tratar un encabezado de anexo no reconocido como cuerpo ordinario. Mantener frontera/región excluida con motivo explícito aunque use romanos, guion o título sin delimitador. La excepción para referencia partida exige evidencia positiva conjunta: oración anterior inconclusa soportada (`en el`) y frase `Anexo ... del Reglamento` con puntuación de continuación/cierre. No decidir solo por mayúsculas ni advertencia documental. Conservar texto excluido recuperable y las cuatro referencias reales; otros formatos permanecen parciales. v8 cambia IDs y requiere revisión antes de integrar. Evidencia: runs/sk02-structure-025-fix-record.json; snapshotv7 intacto.
