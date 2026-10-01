# Refinamiento224 — no inventar exclusividad del régimen anterior

Estado provisional: corrección de instrucciones, no aceptación semántica. Invocación CreatorZ exacta: runs/sk07-proposal-exclusivity-224-invocation.json.

## Evidencia y decisión

SK09 Astra rechazó una respuesta real221 (N221-01): «solo permitía ... oficinas» contradice la cita anterior, que incluye otros canales adicionales. Se reutilizan ambas fuentes originales y capturas221; no se modifica el informe, corpus o referencia. Los PASS de muestras214/218 permanecen limitados a esas respuestas y no se trasladan a221.

Alternativas: conservar el prompt deja el fallo sin atender; sustituir palabras después de generar oculta la salida real; bloquear toda interpretación elimina una capacidad aprobada. Se elige refinar únicamente la política de propuesta: acciones sugeridas y sustento posterior, sin recapitular el régimen anterior ya expuesto literalmente por el servidor. Preservar listas abiertas y prohibir exclusividad no sustentada. Las condiciones, excepciones y concurrencia212 se conservan.

No se codifica una respuesta específica ni una lista de canales correcta para este artículo. No se cambia recuperación, modelo, temperatura, memoria, límites, citas o esquema. No hay reparación silenciosa de la respuesta. Un prompt no garantiza entailment: nueva generación y SK09 siguen obligatorios.

## Evaluación

RED: archivo candidato aún ausente (registro de colección fallida), no reproducción del defecto semántico. GREEN: dos pruebas del transporte demuestran cambio exclusivo de instrucciones y ruta extractiva idéntica sin inferencia; fixtures de respuesta no demuestran mejora del modelo. El AST, excluyendo PROPOSAL_POLICY, es idéntico al módulo desplegado214/221.

Casos semánticos que debe revisar SK09 en la respuesta nueva: listas abiertas no convertidas en exclusividad; mandatos/prohibiciones concurrentes conservados; propuesta ligada al proceso ficticio, sin vigencia actual ni aprobación inventada. La muestra es de desarrollo ya expuesta, no holdout ni fiabilidad de producción. Si vuelve a fallar, preservar salida y limitar el veredicto; no cambiar referencias o umbrales.

Artefacto: deployment/overlay224/src/sbs/conversation/hybrid_125.py. Integrar sólo después de revisión independiente y junto al próximo delta223 para evitar despliegue separado. El material normativo del usuario nunca se sobrescribe.
