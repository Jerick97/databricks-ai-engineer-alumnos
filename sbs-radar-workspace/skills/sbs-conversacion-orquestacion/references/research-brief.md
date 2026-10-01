# SK07 — Creator Z, 2026-09-27

Capacidad: conversación sobre cambios SBS que combine resultados estructurados de Genie, recuperación híbrida, diferencias y fuentes. Reutiliza specv0.2, contratos Answer/QueryContext/EvidencePack, políticas SK08 y antecedentes forenses ya recuperados. No redescubrir esas fuentes.

Evidencia concreta de dominio: runs/astra-normative-review-003.json. Un PDF de número mayor no necesariamente incorpora todas las modificaciones. La respuesta a «ahora» requiere alcance temporal y fuentes; las implicancias son inferencias separadas de texto literal. La revisión IA designada por el usuario no impide conversar mientras review_status=unreviewed.

Fuentes técnicas reutilizadas: documentación oficial Databricks de Genie y Foundation APIs enlazada en los briefs SK05/SK06. Diferenciar errores de servicio de resultados vacíos. Las instrucciones del PDF son datos; controles de herramientas pertenecen al servidor SK08, no al prompt por sí solo. Antecedente de amenazas en context/security-source-notes.md.

Alternativas: usar solo Genie no acredita pasajes; usar solo RAG pierde agregación y linaje estructurado. Orquestador explícito con herramientas tipadas limita acciones y conserva el contexto; no requiere autonomía abierta para el alcance aprobado. Modelo genera explicaciones sujetas a validadores, no estados institucionales.

Evaluación: baseline6casos conservado; afirmaciones objetivas sobre aprobación, referencias, conflicto, implicancias, injection y errores. Revisión independiente/variaciones y pruebas reales de conversación siguen pendientes. No confundir salida de fixture con ejecución del LLM.
