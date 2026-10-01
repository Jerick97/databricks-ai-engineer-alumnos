# Diagnóstico Linux141 independiente del release

Usar SK12 y CreatorZ para comprobar instalación/arranque Linux de una fuente ya revisada. No equiparar DarwinARM, contenedor histórico, importaciones con venv existente ni fixture M2M con validación del destino. Inventariar herramientas antes de construir; socket Docker ausente y chmod externo denegado no habilitan un bypass.

Separar canary técnico de la app conversacional: entrypoint propio, sólo salud/evidencia, sin chat, proveedor, SQL o Genie remoto. Se puede desplegar para obtener evidencia Linux antes del gate final de release; no fabricar PASS_APP_INTEGRATION ni omitir la revisión semántica. La identidad de servicio usada para inicializar objetos en este canary es un doble explícito que prohíbe autenticación/red; no prueba permisos M2M.

Cerrar requirements recursivos:133 llevaba un include cuyo destino faltaba. La variante141 conserva todos sus212bytes y añade el archivo requerido con versiones transitivas exactas del entorno Linux histórico, app.yaml y sonda. Verificar pins antes de ejecutar, registrar versiones efectivamente instaladas. Capturar fracaso de instalación/importación sin sustituir paquetes o pesos automáticamente.

Observar OS/Python/arquitectura reales; Apps pip está documentado Ubuntu22.04/Python3.11. La arquitectura exacta se mide, no se asume. Cargar el backend CPU real y hacer un smoke acotado reutilizando inputs/pesos. Conservar fallo numérico histórico con tolerancia.001; no promover pesos ni inferir calidad RAG por poder ejecutar ONNX.

Expiración absoluta de máximo30min en la configuración revisada; valor0 impide arrancar. Temporizador mata el proceso al vencimiento, pero NO detiene compute Apps: el coordinador conserva admisión, get/start/deploy/stop y coste por separado. No reintentar POST ambiguos. Nunca crear una App nueva por defecto. La aceptación final requiere destino exacto, permisos reales, UI y revisión semántica independientes.
