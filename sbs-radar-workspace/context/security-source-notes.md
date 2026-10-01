# Fuentes reutilizables de guardrails y observabilidad

Consultadas 2026-09-27 con web.run, fuentes primarias OWASP Cheat Sheet Series. Son guías técnicas, no prueba de que el sistema las aplique. No volver a buscar para redactar briefs SK08/SK11 salvo brecha concreta.

- https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html : separación de datos/instrucciones, mínima autoridad y validación de acciones. Decisión SBS: el corpus no otorga permisos; detección de palabras no prueba inmunidad a ataques.
- https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html : controles de destinos y redirecciones. Decisión SBS: hosts exactos HTTPS permitidos, control de cada salto y direcciones resueltas; validador sintáctico de URL no sustituye protección de transporte/DNS en SK02.
- https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html : proteger datos de logs y excluir credenciales. Decisión SBS: campos permitidos para eventos, sin cuerpos libres de request/response o excepciones; tokens/costos no observados son null, no cero.

Contexto de proyecto ya establecido: spec12, contratos SK01 y Creator Z. No infraestructura ni permiso cloud comprobados aquí.
