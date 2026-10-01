# SK10 — Creator Z, 2026-09-27

Intención: implementar y verificar tres espacios conectados: novedades, comparación y conversación/revisión. Reutilizar spec v0.2 y el banco ficticio, sin sobrescribir web/index.html del aula. La nueva UI sirve al agente real; la web educativa existente no es prueba E2E del agente.

Fuentes: spec y contratos locales; https://www.w3.org/WAI/ARIA/apg/patterns/tabs/ consultada hoy para semántica de tablist/tab/tabpanel, foco y teclado. Preferir controles HTML nativos cuando no se necesite un widget complejo. https://docs.databricks.com/aws/en/dev-tools/databricks-apps/app-development y /deploy (Sep23,2026) para arquitectura Python/JS y ejecución; una app construida no queda probada por deploy HTTP200.

Alternativas: SPA introduce dependencias/build adicionales; HTML/CSS/JS con backend Python basta para tres espacios, conserva control de accesibilidad y facilita empaque notebook/app. Elegir diseño legible, responsivo y conectado a APIs tipadas; no necesita imágenes generadas para evidencias normativas.

Riesgos: XSS por texto normativo/LLM, selección de otra familia no propagada, estados fingidos, aprobación client-side, fuente inaccesible, foco perdido y bloqueo artificial del chat. Evaluar usuario/teclado/móvil y errores reales, no solo DOM o tests de API. Guías de amenazas reutilizadas en context/security-source-notes.md y SK08.

Baseline seis casos antes de SKILL. Estado provisional hasta implementación y recorridos reales en navegador.
