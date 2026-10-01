# Requisitos/riesgos

| Requisito | Error a detectar |
|---|---|
| Híbrido+RRF+reranking observable | Doble RRF o etiqueta de reranker sin ejecutarlo |
| Span literal con offsets | Contexto embedding insertado en cita |
| Autorización por familia/versión | Filtro del cliente o documento amplía acceso |
| Ambas versiones | Contraparte necesaria queda fuera topk |
| Resultados vacíos diferenciados | Fallo/ausencia equivale a sin cambios |
| Identidad índice/modelo | Mismo dimension mezcla espacios incompatibles |
| Calidad honesta | Fixtures o benchmark genérico presentado como SBS validado |

Salida EvidencePack más trazas/rankings/config. Expandir contrapartes por alineamiento explícito, no por mismo número en casos renumerados. Indicar cobertura e insuficiencia.
