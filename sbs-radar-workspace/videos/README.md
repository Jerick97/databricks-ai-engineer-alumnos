# SBS Radar: dos videos docentes con Kokoro Dora

- **01 · Ingesta y publicación:** fuentes, hashes, extracción, pares, corpus, RAG, tablas, dos publicadores y límites de promoción.
- **02 · Consulta y aplicación:** selección, controles, ruteo, RRF y reranking, Genie, citas, implicancias, interfaz y evaluación.

## Estado

Los dos MP4 están exportados y se incluyen en esta entrega: 1920×1080, video H.264 y audio AAC. Duración: 3:15 y 3:29. Guiones revisados independientemente y voz española Kokoro `ef_dora`. La exportación se completó desde Terminal; los archivos `render-probe.json` conservan sus propiedades técnicas. Esto no acredita una revisión humana completa del montaje.
Para validar y exportar ambos desde Terminal:

```sh
zsh renderizar.command
```

El comando genera `01-ingesta-publicacion.mp4` y `02-consulta-aplicacion.mp4` en esta carpeta. No llama Databricks, no publica contenido y no modifica la App.

## Skills utilizadas

- `/Users/macdenix/.codex/skills/hyperframes/SKILL.md`: selección de flujo.
- `/Users/macdenix/.codex/skills/general-video/SKILL.md`: producción docente multiescena.
- `/Users/macdenix/.codex/skills/media-use/SKILL.md`, `audio/references/tts.md`: voz local Kokoro `ef_dora`.
- `hyperframes-core`, `hyperframes-animation`, `hyperframes-cli`: estructura, movimiento y comprobaciones.

No se crearon skills nuevas. Se invocaron las existentes; la actualización global tuvo errores EPERM. CLI fijado en 0.8.98.

## Fuentes reutilizadas

- [Guía docente](../teaching-guide/index.html)
- [Mapeo a skills](../teaching-guide/skills.json)
- [Estado real de la entrega](../ESTADO-ENTREGA.md)
- [Diagramas Archify](../../.archify/dataflow-sbs-e2e-20260930-082301/index.html)
- [Aplicación](https://sbs-radar-pilot-7474657121564806.aws.databricksapps.com/)

Cada proyecto incluye `script.json`, `guion.txt`, `BRIEF.md`, `STORYBOARD.md`, `timing.json`, composición HTML, seis WAV y narración completa WAV/M4A. `script-review.json` documenta la revisión independiente del contenido; `audio-validation.json` documenta propiedades técnicas, no una escucha humana completa.
