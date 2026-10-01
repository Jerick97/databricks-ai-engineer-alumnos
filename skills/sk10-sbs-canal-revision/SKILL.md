---
name: sk10-sbs-canal-revision
description: Construye o verifica la interfaz de SBS Radar: novedades, comparación antes/después, conversación y revisión. Usar ante navegación, citas, accesibilidad, errores o recorridos de usuario; no para reconstruir índices sin cambios del canal.
---

# SK10 — Canal y revisión

Versión 0.1.5 provisional. Creada mediante skill-creator-z tras baseline. [Brief](references/research-brief.md), [riesgos](references/requirements-risks.md), [casos](evals/cases.json), [invariantes UI](references/ui-invariants.md).

## Contrato

Entrada: APIs y contratos reales de SK03/SK07, fuentes originales, actores verificados SK08, estados y diseño aprobado. Salida: UI y backend conectados con evidencia de recorridos. Mantener separada la web educativa existente; no sobrescribirla ni presentarla como agente operativo.

## Construcción y verificación

1. Diseñar tres espacios que compartan selección de familia, norma, par y disposición: bandeja de novedades, comparación con fuentes y chat/revisión. Explicar los estados con lenguaje claro; mostrar vigencia desconocida, evidencia parcial y revisión IA cuando corresponda.
2. Conservar contexto al navegar y abrir una cita; ofrecer acceso a ambos originales y al pasaje localizado. No representar número de carpeta como vigencia actual. Diferenciar texto de cambio, inferencia y propuesta institucional.
3. Permitir conversar sobre cambios no aprobados cuando el acceso y los datos lo permitan. Separar disponibilidad técnica de aprobación. Acciones de aprobación requieren autenticación y autorización del backend; esconder un botón no es control de permisos.
4. Conectar datos reales a endpoints tipados. Fixture o modo sin backend se etiqueta explícitamente y no cuenta como E2E. Carga, vacío, parcial, error y timeout deben ser distintos; nunca inventar respuestas para mantener una demo verde.
5. Renderizar contenido normativo/modelo como texto, o Markdown con sanitización explícita. Prohibir ejecución de HTML y enlaces de protocolos arbitrarios. Servir originales mediante IDs permitidos, no rutas de archivo aportadas por el cliente. Aplicar SK08 también a sesiones y mutaciones.
6. Usar controles semánticos, etiquetas, foco visible y navegación por teclado. Si se eligen tabs ARIA, implementar el patrón resumido en ui-invariants.md y su fuente primaria. Adaptar comparación a móvil sin desbordamiento general ni perder fuentes; no depender solo de color para estados.
7. Mantener mensajes útiles para el usuario y detalles técnicos en diagnóstico aparte. Preservar historial de chat por sesión autorizada; no compartir conversaciones entre usuarios. Las preferencias locales no son un registro institucional.
8. En construcción, implementar app propia con dependencias reproducibles y pruebas pertinentes de rutas, sesiones, permisos, contenido no confiable y errores. Conectar SK11 sin loguear documentos completos ni secretos.
9. Ejecutar recorridos reales en navegador: novedades→comparación→fuente→pregunta→seguimiento, ambas familias, pregunta cruzada, estado unreviewed, error recuperable, teclado y viewport móvil. Registrar resultado visible y evidencia. DOM, screenshot aislado, API200 y tests unitarios no bastan por sí solos.
10. Si navegador o infraestructura bloquean una prueba, registrar el bloqueo concreto y continuar trabajo independiente. No simular la aceptación. SK09 evalúa respuestas y SK12 valida la entrega/configuración completa.

## Refinamiento

Convertir problemas de recorrido en correcciones de UI/backend o de la skill propietaria. Mantener límites de validación visual, accesibilidad y funcionalidad explícitos.

## Refinamiento 0.1.2 — canal con identidad cloud

La fábrica cloud exige identidad SK08 verificable, origen HTTPS exacto y runtime cloud; denegar mezcla con perfil local. Usar vista de servicio limitada al actor antes de catálogo, selección, fuente o pregunta. Vincular sesión y CSRF al sujeto; cambio de sujeto renueva cookie y token. Cookie Secure en cloud y comprobación de Origin en mutaciones. Error de identidad no degrada a operador local.

La verificación real del recurso current-user y las pruebas de rutas con identidades sintéticas son evidencias distintas. No acreditar SSO, scopes, permisos del principal de app ni flujo visual hasta probar el despliegue real. La identidad delegada no implica autorización UC del usuario cuando datos se leen con el principal de app; mostrar y documentar ese límite.

## Refinamiento 0.1.3 — conteos visibles y trazables

Mostrar los estados de conteo verificado, indisponibilidad y alcance no respondido en lenguaje de usuario. Conservar unidad y significado del wrapper SK07; no convertir filas documentales en cambios materiales. Ofrecer en un detalle desplegable la consulta ejecutada/ID, alcance, filas y enlaces a los originales del par; identificarlos como fuentes del conteo, no como citas que prueban una interpretación normativa. Renderizar todos los valores como texto y servir fuentes por IDs permitidos. La inspección de código/sintaxis no acredita el recorrido visible; probarlo en navegador cuando esté disponible.


## Refinamiento 0.1.4 — catálogo y respuesta coherentes

Mostrar comprobación de publicación, indisponibilidad y cuota agotada sin atribuir vigencia jurídica. Actualizar catálogo conserva selecciones todavía válidas y separa historial por snapshot. Si comparación o respuesta devuelve un snapshot distinto del seleccionado, no mostrarla como evidencia de la versión anterior: pedir actualizar catálogo y repetir la acción. El control de actualización lee publicaciones; no dispara el Job. Mantener I/O de refresco fuera del event loop HTTP. Validar estados y carreras con SK09; pruebas de código no acreditan recorrido visual.


## Refinamiento 0.1.5 — etiquetas, ancho móvil y alcance del ensayo

UI36-01/02: presentar norma y disposición mediante metadatos documentales verificados; separar `display_label` del `label` interno que alimenta recuperación. Mostrar copias A/B con identificación corta; conservar IDs y hashes completos en detalle desplegable y enlaces originales intactos. No deducir vigencia o fechas de carpetas, hashes o identidad documental. Disposiciones finales/resolutivas no se renombran artículos numerados; páginas físicas siguen explícitas.

Medir scrollWidth frente al viewport móvil en ambas familias, con el contenido normativo real. Corregir anchos mínimos de grid/hijos y permitir ajuste de palabras largas; ocultar overflow no demuestra accesibilidad del contenido. Conservar capturas antes/después y repetir fuentes, teclado y contexto.

UI36-MODE: `adapter=None` no significa red deshabilitada cuando existe inicialización diferida. Antes de enviar preguntas de un ensayo sin inferencias, bloquear explícitamente los inicializadores remotos y comprobar el bloqueo; denominarlo fallo inyectado para UI, no chat operativo. Si el primer ensayo pudo inicializar remotos, conservar el intento y reportar tráfico desconocido cuando no haya trazas suficientes.

Baseline real: runs/sk10-036-ui-record.json y revisión de etiquetas runs/sk09-ui-labels-036-baseline.json. Refinamiento CreatorZ037; provisional, no aceptación cloud ni mejora de recuperación atribuida.

Expediente037: [fuentes, alternativas y matriz de riesgos](references/display-labels-037.md).

Refinamiento local209 (provisional): [errores HTTP/JSON y redirecciones](references/api-response-209.md). Aplicar ante respuestas HTML o fallos de parseo del canal; no acredita restauración del servicio ni autoriza reinicios/despliegues.
