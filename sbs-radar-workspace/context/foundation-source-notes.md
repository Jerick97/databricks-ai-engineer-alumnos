# SK02 — investigación incremental de fuentes

Fecha2026-09-27; búsqueda primaria limitada a brecha de corpus específico, sin repetir recuperación de marcos. Fuentes de descubrimiento, no manifiesto de ingesta completada ni vigencia adjudicada.

1. https://www.sbs.gob.pe/autorizacion-de-nuevas-empresas/marco-normativo-y-documentos-de-apoyo : lista 3274-2017 y enlace de descarga. También lista circulares antiguas de seguridad; no asumir lista actualizada/completa.
2. https://intranet2.sbs.gob.pe/dv_int_cn/1731/v7.0/Adjuntos/3274-2017.R.pdf : URL exacta de PDF oficial descubierta por búsqueda, v7.0 es versión del repositorio observada, no fecha de efecto. Aún no capturada localmente.
3. https://www.sbs.gob.pe/noticia/detallenoticia/idnoticia/2545 : noticia oficial sobre resolución504-2021 como pista de norma base, no sustituto del texto normativo.
4. https://www.sbs.gob.pe/boletin/detalleboletin/idbulletin/1177 : contiene enlace al acto publicado en ElPeruano; cualquier host adicional se revisará en política de fuentes antes de ingesta.
5. https://www.sbs.gob.pe/noticia/detallenoticia/idnoticia/3701 : pista de modificatoria03240-2023 que relaciona ambas familias. Buscar acto y anexos a partir de esta relación, no usar la noticia como gold jurídico ni como texto anterior/nuevo.

Decisiones: empezar con corpus real pequeño por ambas familias; cada par debe declarar si son versiones oficiales o reconstrucción derivada con actos fuente. No inventar 10pares si no están disponibles. Etiquetar proyectos normativos por separado; no considerarlos obligaciones vigentes.

Reusar context/security-source-notes.md (transporte/orígenes) y estrategia-rag/span-limpio-contexto-v1 (fidelidad/offsets). Pendiente: manifiesto de documentos capturados, cobertura de anexos, selección de extractor y corpus adjudicado.

Enlace de descarga seguido desde portaloficial, 29páginas observadas con web.run: https://www.sbs.gob.pe/Portals/0/jer/Auto_Nuevas_Empresas/Sistema_Financiero/7.%20Reg.%20de%20Gesti%C3%B3n%20de%20Conducta%20de%20Mercado_%20Res.%20SBS%20N%C2%B0%203274-2017.pdf . Original todavía no capturado por pipeline local.

Búsqueda dirigida adicional mismafecha resolvió dosURLs oficiales de ciberseguridad (númerosdeversiónderepositorio, noefecto): https://intranet2.sbs.gob.pe/dv_int_cn/2046/v4.0/Adjuntos/504-2021.R.pdf y https://intranet2.sbs.gob.pe/dv_int_cn/2046/v5.0/Adjuntos/504-2021.R%20.pdf . La misma búsqueda también devolvió preproyectos, deliberadamente excluidos de normasvigentes; no se sustituyen por actosfinales.

## Brecha resuelta 2026-09-27: actos modificatorios y segunda copia de mercado

Investigación SK02/SK09 localizada una vez: historial oficial https://www.sbs.gob.pe/app/pp/INT_CN/Paginas/Busqueda/VerHistorial.aspx?NormaId=1731 relaciona3274-2017v8 con2286-2024. URLsprimarias de2286y2220 capturadas en context/pilot-amendments-manifest.json; resultado y hashes en runs/sk02-amendments-capture.json. URLv8 fue hipótesis por patrón, contenido luegoverificado. No confundir procedencia de descubrimiento con linkobservado. La página dehistorial lista másmodificaciones posteriores: el corpus de6PDF no acredita vigenciaactualcompleta. Reusar estas fuentes; no repetirbúsqueda.

Brecha concreta0771-2026: búsqueda primaria acotada `site.intranet2.sbs.gob.pe "0771-2026"` y `site.sbs.gob.pe "0771-2026"` no produjo actoSBS pertinente el2026-09-27. Resultados deotrasentidades descartados. Referencia documentalcapturada siguependiente; no repetir estasmismasconsultas sin fuente nueva. No inferir vigencia/ausencia por faltadeindexación.
