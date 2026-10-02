---
name: sbs-versiones-cambios
description: Alinea disposiciones, compara versiones o registra relaciones temporales de normativa SBS Radar. Usar ante renumeraciones, divisiones, fusiones o diferencias antes/después; no para configurar embeddings ni certificar implicancias jurídicas.
---

# SK03 — Versiones y cambios

Versión0.1.4 provisional, creada mediante skill-creator-z. [Brief](references/research-brief.md), [riesgos](references/requirements-risks.md), [casos](evals/cases.json).

## Contrato

Entrada: VersionPair, disposiciones/citas de SK02, cobertura, relaciones y alineamientos explícitos cuando estén disponibles. Salida: ChangeSet con cambios textuales/estructurales, evidence de ambas versiones, incertidumbre y provenance. No se infiere vigencia por URL/orden de archivo o captura.

## Flujo

1. Resolver contexto y validar contratos SK00/SK01. Comparar fuentes identificadas, no documentos elegidos únicamente por nombre similar. Original y bundle de extracción deben estar fijados; no mezclar offsets de bundles.
2. Trabajar por disposición estructural y conservar anexos/tablas. Matching de número ayuda, pero fullouterjoin por artículo no distingue renumeración de alta/baja.
3. Alinear texto exacto con contexto y detectar ambigüedades: si el mismo texto existe en varios lugares, no elegir arbitrariamente. Aceptar alineamientos explícitos1:1/1:n/n:1 con todas sus contrapartes; heurísticas de similitud producen candidatos a revisar, no certeza calibrada.
4. Clasificar adición, eliminación, modificación literal, renumeración/traslado y reorganización. Una renumeración con texto idéntico no es obligación nueva. Diferencia literal no implica cambio material; interpretación corresponde aSK07 y referencia expertaSK09.
5. Para cada afirmación recuperar citas relacionadas con el par correcto. Anexofaltante, texto no extraíble oalineamientoincierto impide “sin cambios” global; conservar resultados parciales de partes verificadas.
6. Registrar publicado/conocido/efectivo por separado con su fuente. Corrección retroactiva añade conocimiento nuevo sin borrar lo que el sistema sabía. Una consolidación reconstruida se etiqueta derivada, con actos fuente y transformaciones; no versión oficial.
7. Implementar src/sbs/comparison/ y tests/unit/test_comparison.py con RED/GREEN para renumeración, división/fusión, ambigüedad por texto duplicado, anexofaltante, historialtemporal y reconstrucción. Preservar IDs de fuentes/citas; reintentos idénticos producen mismo artefacto lógico.
8. Ejecutar sobre corpus real solo después de fijar manifest/versión de extracción. Reportar coverage, candidatos y límites. No aumentar score de aceptación editando alineamientos reservados del gold sin adjudicación/versionado.

## Refinamiento

Guardar fallo real y explicación → testRED → cambio de algoritmo y skill → regresión con casos nuevos. Un benchmark sintético no acredita precisión/recall jurídicos ni ambos frentes normativos reales.

## Refinamiento 0.1.1 — identidad de subpasajes

Conservar IDs de una cita solo si su identidad permanece igual. Al construir una disposición estructural desde una página o anotación, derivar citation_id propio de documento/versión/hash de extracción/disposición/rango y conservar la cita padre en provenance. Una página completa y un subpasaje distinto no pueden compartir ID. Verificar disjunción de IDs entre registros raw y estructurales y estabilidad en reejecución; no modificar los originales ni las revisiones históricas.


## Refinamiento 0.1.2 — evidencia derivada reversible

Usar [comparación estructural](references/structural-comparison.md) para separar candidatos del cuerpo y anotaciones editoriales sin reemplazar el resultado literal ni sus citas. Una vista derivada no es quote: conservar mapping reversible de todos los rangos, motivos de omisión y texto crudo. Correspondencias automáticas siguen heurísticas, no aprobación. Notas/exclusiones ambiguas conservan evidencia y estado inconclusive; propagar incertidumbre a candidatos de dueño incluso cuando la nota esté dentro de otra unidad. No interpretar igualdad normalizada como ausencia de cambios ni cobertura completa.

Ensayo021 de ambas familias y pruebas locales verifican mapas/citas/contratos; skill sigue provisional y revisión independiente pendiente. No promueve corpus, vectores ni consumidor.


## Refinamiento 0.1.3 — contenido no demuestra furniture

SC21-01: una dirección conocida puede ser texto prescrito. No omitir por regex de contenido. Sin evidencia suficiente de ubicación/recurrencia de encabezado o pie, conservar la línea y la incertidumbre; si cambia el cuerpo visible, mantener candidato textual. Ensayo114pruebas y probes locales no certifica reconocimiento de layout ni vigencia jurídica.

## Refinamiento 0.1.4 — mapa reversible compacto

Compactar representación solo después de todas las decisiones de normalización. Si un segmento no omitido conserva exactamente rawslice==derived_text, representarlo como retain; coalescer únicamente retains contiguos en ambos ejes y de igual longitud. No unir omisiones ni reemplazos reales, ni perder sus razones, citas o incertidumbre. Versionar el wrapper y exigir igualdad de todo contenido restante, reconstrucción completa raw/derived, offsets y categorías.

Evidencia027: recuperación local fallaba con42,226,207bytes frente al cap32MiB; mappingv3 produce12,006,047bytes y prueba original pasa sin elevar caps. Comparación244vistas de tres pares conserva todo salvo mapping/version. No garantiza tamaño acotado para toda historia futura; conservar rechazo ante caps y no confundir fixtures Files con publicacióncloud. [Contrato](references/map-compaction-027.md).
