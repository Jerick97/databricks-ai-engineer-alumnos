# SK03 — comparación estructural derivada021

Versión v2. Adaptación provisional de span-limpio-contexto-v1 v1. Reutiliza SK02 estructura v6/notas v4 y el comparador literal SK03 sin editarlo. Entradas: VersionPair y dos RAW bundles fijados. API `sbs.comparison.structural.compare_structural(pair,before,after)`. No calcula embeddings ni expansión RAG; la expansión aquí es evidencia cruda contextual.

Salida:
- `original_comparison`: resultado SK03 completo, ChangeSet/citas/candidatos/limitaciones intactos.
- `alignment_provenance`: correspondencias heurísticas del segmentador; `explicit` interno sigue significando caller-supplied, no aprobación.
- `evidence_context`: provisiones exactas, todas las páginas, notas/marcadores/vínculos/unresolved, estructura y excluded_ranges. Cada unidad tiene contexto crudo expandido con cita propia y relación `contextual_not_legal_ownership`; ninguna unidad se declara completa por esa expansión.
- `derived_comparison`: vistas no citables, comparación editorial por vínculos textuales únicos, categoría candidata y materialidad no evaluada.

Las categorías son `body_text_candidate`, `editorial_only_candidate`, `no_supported_body_difference` y `unresolved`. No son cambios jurídicos/materiales ni métricas de aceptación. Diferencia del cuerpo puede contener ruido todavía no reconocido. Igualdad derivada con incertidumbre se marca inconclusive/unresolved; nunca implica ausencia global de cambios. Los cambios fuera de correspondencias siguen disponibles en el resultado original y exclusiones, no se rellenan correspondencias inventadas.

Cada vista conserva mapping ordenado: raw_start/end, derived_start/end, derived_text, operación y razón. Concatenar los slices crudos de mapping reconstruye exactamente la cita original; concatenar derived_text reconstruye la vista. Conservar también los segmentos de reemplazo por whitespace aunque produzcan texto vacío tras el trim. Omisiones completas llevan su rango/texto/páginas/razón e identidad de nota/marcador si aplica. La vista soldada es `citable=false`, jamás quote continua.

Solo omitir notas bounded con vínculo único y sus marcadores exactos; las notas pendientes y sus continuaciones ambiguas quedan en evidencia y bloquean igualdad concluyente del candidato a dueño aunque estén físicamente en otra unidad. ContraejemploRED021: nota ambigua situada en artículo15 con marcadores candidatos en14 antes no propagaba incertidumbre a14. La corrección consulta candidate_owners, no proximidad.

Whitespace se transforma a espacio, sin eliminar separaciones entre tokens ni puntuación; 1 000 no se vuelve1000. En v2 la línea completa de dirección SBS es solo candidato incierto de furniture: se conserva, sin omisión por contenido. Números aislados/paginación no demostrada, otros encabezados/tablas o abreviaturas quedan visibles. No agregar eliminación por apariencia sin nuevo RED y evidencia explícita.

Ordinales de actos que anteceden texto citado externo pueden estar incompletos: excluded_ranges adyacentes/interiores se entregan con contexto original ampliado. Esto no adjudica esos pasajes al instrumento ni los convierte en unidad normativa completa. La nota11 de4036 sigue unresolved ante39.11; no forzar vínculo ni eliminarla por este wrapper.

Evidencia: runs/sk03-structural-021-record.json y dos primeras salidas de ambas familias. Desarrollo expuesto al feedback Astra; no nueva prueba holdout ni evaluación normativa. Preparers/consumidores/RAG/producción no conectados en este incremento. Una modificación de los inputs requiere nuevas derivaciones y sus embeddings exactos antes de promoción.


## SC21-01 — dirección normativa no es pie por su contenido

El patrón de dirección exacta puede formar parte de una obligación. En v1 se omitía sin prueba de ubicación: RED sintético sede obligatoria y variante real4036 preservados. V2 retiene la dirección, registra unverified_page_furniture_retained y la diferencia observable permanece body_text_candidate, no editorial_only. Los bundles actuales solo ofrecen rawtext/mapa de páginas, sin evidencia visual suficiente para certificar header/footer. Una futura omisión requiere evidencia de ubicación/recurrencia justificada y evaluación; no basta añadir una advertencia de materialidad. Originales, mapas y primera salida v1 permanecen intactos.
