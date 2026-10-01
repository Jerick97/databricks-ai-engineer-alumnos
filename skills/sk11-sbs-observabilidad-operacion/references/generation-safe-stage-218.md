# SK11 / CreatorZ — diagnóstico seguro del generador218

Baseline real: primerturn3 UI214 devolvió generator:error tras HTTP200; contador reservó1generation. Logs sólo mostraron request/avisosONNX; causa no observable. Segundoenvío explícito respondió y Astra verificó concurrencia correcta. Conservar1fallo/2intentos: éxito posterior no explica el primero ni prueba fiabilidad.

Parche acotado al punto propietario de captura de generación `src/sbs/app133/runtime.py` (overlay218), sin cambiar RunRecord ni crear otro backend. En excepción, emitir una única línea SBS_GENERATION_FAILURE con clase y3etapas/código de vocabulario cerrado. Nunca serializar str(error), datos del documento, prompt, respuesta, headers, claves o mapas arbitrarios. Campos desconocidos y tipos inesperados se reducen a unknown; no se intenta inferir una causa. Si el logger falla, se preserva y propaga la excepción original. No cambia salidas, reintentos, cuota ni conducta modelo.

Tests: sentinel secreto en excepción/headers/stage/code no aparece; valoresdeetapa list/dict reducidos; código tipado permitido conservado; fallo artificialdel logger no sustituye error original. Pruebas locales acreditan proyección y control de error, no aparición de logs reales ni diagnóstico retrospectivo214. Se añade en el siguiente deploy autorizado por raíz por el aislamientoGenie217, no se despliega sólo para instrumentación. SKU/expansión de gasto quedan fuera de este refinamiento; tasa/costos no se inventan.

CreatorZ exacto exigido porAGENTS; propietarioSK11, constructor deployment_lifecycle210, revisiónroot independiente. Estado provisional. No registros ni evidenciahistórica modificados; no lograw remoto capturado durante preparación.
