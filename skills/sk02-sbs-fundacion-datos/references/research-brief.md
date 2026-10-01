# SK02 — Creator Z fases0/1/1.5

Fecha2026-09-27. Fuente creadora: /Users/macdenix/clawd/openclaw-codex/openclaw-workspace/skills/skill-creator-z/SKILL.md. Baseline previo: runs/sk02-baseline.json. Assertions escritas antes de SKILL.

Objetivo: corpus verificable de dosfamilias, captura idempotente e inmutable, extracción con páginas/offsets y calidad visible. Entradas: manifest de URLs autorizadas/familias, originales, extractorconfig. Salidas: SourceDocument/Provision, manifiesto cobertura, intentos, originales y derivados versionados; sin declarar vigencia automáticamente.

Investigación primaria incremental: context/foundation-source-notes.md; orígenes/transporte context/security-source-notes.md; estrategia-rag/span-limpio-contexto-v1. Todos existentes, no repetir descubrimiento. Pistas oficiales de bases504-2021/3274-2017 y modificatoria03240-2023, no cobertura completa. No noticias como gold jurídico.

Ecosistema local: pypdf y pdftotext instalados, inspect de PdfReader/PageObject.extract_text realizado hoy y guardado como decisión técnica de lectura PDF textual. Alternativas PyMuPDF no instalado, OCR no elegido. Empezar PDFs con texto; OCR/tablas complejas pendientes con estado explícito, nunca fallback silencioso como extracción confiable. La estrategia de citas se adapta, no hereda validación.

Riesgos: tabla linealizada, anexoausente, falsa versión por URL, reconstrucción no oficial, retryduplicado, SSRF y respuesta HTML200 confundida conPDF. Elegir persistencia contentaddressed y transacciones de metadata. Descargas con límite, timeout y validación cada salto; certificados verificados; noevadirlogin niwarning.

Eval:6casos, baseline existe sin fallo crítico aparente; RED/GREEN componente después de skill. Strictgeneralización/OCR y corpusreal adjudicado pendientes. No presentar fixtures como referencias reales. Toda frase normativa se conserva con fuenteexacta sin interpretación legal en estaetapa.
