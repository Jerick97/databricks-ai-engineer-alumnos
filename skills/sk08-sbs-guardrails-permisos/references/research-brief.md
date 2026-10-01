# SK08 — Creator Z fases0/1/1.5

Fecha2026-09-27. Fuente: /Users/macdenix/clawd/openclaw-codex/openclaw-workspace/skills/skill-creator-z/SKILL.md.

Intención: diseñar controles que limitan autoridad de fuentes/herramientas y verifican evidencia. Entradas: spec aprobado, policy, principal de servidor, recursos y contratos. Salida: políticas versionadas, guardrails ejecutables y pruebas negativas; no identidad cloud ni autenticación inventada.

Fuentes recuperadas: context/security-source-notes.md (OWASP injection, SSRF, logging; fuentes primarias consultadas hoy), spec12 A07/A09; SK01 contratos. Confianza alta en decisiones de alcance, capacidades runtime aún no comprobadas.

Alternativas: confiar solo prompt/detector de palabras es insuficiente; escoger controles de servidor antes de tool/RAG, listas explícitas, corpus tratado como datos, citas/versiones comprobadas. Comparar bibliotecas por necesidad antes de sumar dependencias; primera implementación determinista stdlib y contratos existentes.

Riesgos: rol autodeclarado, URL engañosa/redirección, cita de versión ajena, chat bloqueado por reviewstatus, secretos en logs. Pruebas unitarias no demuestran prevención total de prompt injection ni SSRF real. Transporte seguro corresponde integraciónSK02; identidad a backendSK10.

Baseline ya ejecutado runs/sk08-baseline.json, sin acciones externas. Respuestas iniciales conservan límites; no inventar mejora. Eval set y assertions fijados antes de skill. Falta ejecuciónGREEN, generalización, microtests wording, repeticiones/varianza y revisión ciega strict; estado provisional.
