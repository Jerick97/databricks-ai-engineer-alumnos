# Validación del aula · 2026-09-27

## Comprobado

- Build: 30 fichas únicas, grupos 9/9/12, campos requeridos, tres opciones por ficha y referencias cruzadas resueltas.
- JavaScript: `node --check web/check.js` sin errores.
- Ejecución estructural: `node web/verify.cjs` PASS. Render de las 30 fichas y cinco vistas; búsqueda, modo docente, notas con almacenamiento simulado, escape HTML y feedback correcto/incorrecto de los cuatro escenarios.
- Servidor local: HTTP 200 en `http://127.0.0.1:8876/`.
- Revisión cruzada: fichas de capas/preparación e interfaz revisadas por agente que no las redactó; contenido completo y sin referencias rotas. Se incorporó la aclaración de que las opciones pueden combinarse.
- Segunda revisión cruzada: las doce decisiones revisadas por un agente distinto del autor, PASS. Se ajustó la guía docente para permitir combinar opciones en lugar de exigir descartar una.
- Material explícitamente distingue ejercicios ficticios, diseño del futuro agente y evidencia de operación real.

## Pendiente, sin certificar

Chrome impidió abrir la página mediante automatización porque había otra interfaz de extensión abierta. Se solicitó cerrar/completar esa interfaz. Por ello no se certifican inspección visual, comportamiento responsive real, teclado, impresión ni descarga de notas en navegador. Los tests con doble del DOM no se presentan como pruebas de UI.

No se ejecutó ni desplegó el agente SBS. Los textos de los ejercicios son sintéticos; no se ha validado un corpus normativo real ni aplicabilidad jurídica.
