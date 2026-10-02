# Invariantes de interfaz y prueba

Referencia primaria consultada 2026-09-27: https://www.w3.org/WAI/ARIA/apg/patterns/tabs/

Si se usan tabs: contenedor tablist; botones tab con aria-controls y aria-selected; paneles tabpanel con aria-labelledby. Tab entra al seleccionado; flechas izquierda/derecha recorren el grupo; Enter/Espacio activan cuando la activación es manual. Mantener foco visible. Si el cambio requiere carga, preferir activación manual. No añadir roles de tabs a simples enlaces sin implementar su teclado.

Recorrido mínimo SBS: seleccionar familia y par → abrir comparación → abrir una cita → regresar manteniendo foco/selección → preguntar qué cambió → hacer seguimiento → cambiar familia → comprobar contexto nuevo. Repetir con teclado y viewport móvil.

El backend determina identidad y permisos. El navegador solo envía selecciones identificadas; no puede fabricar actor_role ni promociones de estado. En local, escuchar loopback y declarar sesión de operador local; en destino, usar identidad del proxy autenticado y autorización de servidor. CORS, cookies y protección de mutaciones se configuran conforme al modo real.

Mostrar estados útiles: cargando, evidencia parcial, consulta no disponible, pendiente de revisión y propuesta. «Revisión IA» no equivale a aprobación institucional. No mostrar éxito por tener una respuesta HTTP.
