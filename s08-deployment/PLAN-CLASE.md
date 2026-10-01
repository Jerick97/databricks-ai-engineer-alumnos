# S08 · lunes 28 de septiembre de 2026

180 minutos reloj, incluidos 10 de pausa. Tiempos **estimados**; no equivalen al tiempo de aprovisionamiento asíncrono. Objetivo: operar el Copiloto Neptuno con endpoint, interfaz, observabilidad y una ruta de release reversible.

| Minuto | Trabajo | Evidencia que se pide |
|---|---|---|
|0–15|CP0 continuidad e inventario|Identidades y recursos de S05–07|
|15–40|CP1 empaquetar agente|URI/versionado y contrato de entrada|
|40–70|CP2 Model Serving|Invocación y estado del endpoint|
|70–85|CP3 rollout custom complementario|90/10 y rollback; agente con versión única|
|85–95|Pausa|10 min|
|95–120|CP4 Apps|Pregunta autenticada con backend|
|120–145|CP5–6 inferencias y monitoreo|JSON aplanado y métrica interpretada|
|145–163|CP7 bundles/prompts|Validación dev y prompt versionado|
|163–180|CP8 portfolio y certificación|Evidencia completa y diagnóstico|

La creación de servicios no se confunde con tiempo didáctico. Antes de clase el docente despliega y prueba una instancia aislada, preactiva el endpoint y comprueba que las tablas ya recibieron inferencias. En clase se muestra el proceso y cada alumno ejecuta checkpoints sobre su recurso asignado. Se conserva el procedimiento completo para repetir desde cero después. Si una operación queda pendiente, se registra; no se sustituye el entregable cloud por una simulación local.

En cierre se resuelven preguntas 1–4 del banco; las 8 restantes son práctica posterior con respuestas razonadas. La preparación de certificación acompaña la experiencia práctica y no garantiza aprobar.

El prewarm incluye **ambos** endpoints: agente principal y custom complementario de ventas. El split se demuestra en el segundo porque `agent/v1/responses` no lo admite. Apps sigue consultando el agente principal.

El ensayo del workspace mostró que cambiar rutas también puede iniciar una actualización prolongada: la API rechazó enviar sólo `traffic_config`, por lo que el script conserva las entidades requeridas. **No prometer que canary y rollback finalizan en 15 minutos.** Con el custom ya preparado, el docente solicita canary alrededor del minuto 40, mientras se trabaja CP2; en CP3 observa la configuración efectiva y solicita rollback. Comprueba la reversión después de la pausa o durante el cierre si sigue pendiente. Los 15 minutos son discusión/inspección, no un SLA de infraestructura. Usa los reportes fechados del ensayo para explicar resultados mientras la nueva ejecución continúa, identificándolos como evidencia previa. El alumno registra pendiente hasta verificar su propia reversión.
