# Notas editoriales — Task3 / 020 provisional

Invocar SK02 para extraer notas de originales ya capturados; este helper no determina vigencia ni efecto jurídico. Investigación reutilizada: rawtext y bundles congelados019fix, contratos de citas, plan structural-evidence y hallazgo F3 del informe Astra019. No se consultó directamente referencia006 ni fuentes externas nuevas. Ajuste expuesto al feedback, no holdout.

API `sbs.foundation.structure_notes.extract_note_links(raw_bundle, structural_bundle)` devuelve `version`, `notes`, `links`, `unresolved`, procedencia por hashes y cobertura parcial. No importa el segmentador mutable ni modifica rawtext, artículos, IDs o offsets existentes. Valida identidad, hash crudo, coincidencia de fuentes, vínculo hash al padre, intervalos y mapa de páginas. Integra después mediante sidecar; este incremento no lo publica ni conecta al consumidor.

Cada nota conserva una cita independiente continua con documento/versión/páginas/offsets, marcador citado por separado y scope de sección explícita. Solo se detectan formas textuales soportadas (número + Artículo/Párrafo/Literal/Numeral + operación editorial). Los saltos de línea internos permanecen; una frontera no demostrada deja nota recuperable y estado unresolved. Blank line, nota siguiente o encabezado/furniture soportado son fronteras textuales heurísticas, no prueba visual universal. Los formatos no reconocidos permanecen en rawtext y no se cuentan como ausencia de notas.

Para vincular, requerir marcador terminal adherido a puntuación, coincidencia de número, sección/documento/versión y candidato único. Registrar el span exacto del marcador, la cita y provision_id del dueño textual y etiqueta subordinada cuando esté explícita. No usar el artículo que contiene físicamente la nota ni escoger el más cercano. Repetición de notas/marcadores, falta de marcador o frontera pendiente conservan nota y candidatos explicables en unresolved. `unique_textual_match` nunca significa certeza visual, adjudicación legal o aprobación humana.

Excluir decimales, fechas e importes con dígito antes del punto y abreviaturas soportadas art./num./núm./pág./etc. RED observado: art.8/num.8/núm.8 generaban falsos vínculos; v2 incorpora exclusión. No afirmar reconocimiento exhaustivo de todas las abreviaturas, tablas o numerales. Ante layout insuficiente, conservar evidencia y abstenerse.

Ensayo real sobre019fix: notas8/9 se vinculan a14.1/14.2 aunque físicamente estén dentro15; nota10 a15.2(h) aunque se encuentre después16. Nota11 queda unresolved porque su marcador no tiene dueño estructural disponible en019fix. No remover esas notas del artículo15/16 ni alterar la cita continua; una vista derivada futura requiere mapa reversible y motivo de exclusión. F1DCF e integración conTask2 no se dan por resueltos aquí.

Evidencia: runs/sk02-notes-020-record.json; primera salida conservada. Pruebas fixtures separadas del ensayo real: multilinea/cruce de página, números ordinarios, fechas/importes, abreviaturas, duplicados, secciones distintas, marcador ausente, frontera ausente, identidad y manipulación de texto. Skill sigue provisional; revisión independiente pendiente.

## Corrección NT20-01/02 — v3

La identidad de cada cita de nota, marcador y continuación incluye el hash completo del bundle crudo verificado; mismo texto con otra configuración/extractor no reutiliza citation_id. Mismo bundle conserva determinismo.

Una continuación con forma de artículo ordinal, numeral subordinado o literal puede ser cuerpo retomado o texto de la propia nota. No absorberla y declarar después la nota segura por encontrar una línea vacía. Conservar el prefijo citado como nota, el intervalo dudoso en `continuation_candidate` (cita exacta independiente), `boundary_status=unresolved` y candidatos de dueño explicables. No emitir vínculo único ni autorizar remoción de ese intervalo en vistas derivadas. Este tratamiento conserva la duda; no convierte reconocimiento de encabezado en certeza de propiedad.

Evidencia: runs/sk02-notes-020-fix-record.json, cuatro testsRED y probes originales de revisión reproducidos. Código/tests v2 y salidas anteriores congelados; revisión independiente de resolución pendiente. Task4 se detuvo en diseño hasta este retest.

Corrección NT20-02-R / v4: mantener consistente el vocabulario ordinal admitido por Task2, incluidas formas Sétimo/Séptimo, sin/con tilde y género. No usar un subconjunto ortográfico que convierta una variante soportada en continuación segura. Las28variantes del vocabulario se prueban;16fallaron en v3 antes de corregir. El texto39.11 de nota11 sigue ambiguo con decimal: nota recuperable, sin vínculo forzado ni autorización de remoción.
