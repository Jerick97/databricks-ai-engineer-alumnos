# Binding 130 — SK11/SK12/SK08

Entrega local revisable, sin cloud ni nueva ventana emitida. Autorización053 persiste; revisión acotada interna.

El ejecutor exige autenticación SDK, host/owner/SP exactos, Job único observado con settings PAUSED originales, ACL confiables del Job y notebook privado118, tabla original, Volume y warehouse. Descarga y verifica bundle105 antes de emitir un NUEVO documento policy130.json que referencia la política106 histórica. La ventana real de 30 minutos sólo comienza durante execute tras estas observaciones. Supuestos administrativos heredados siguen siendo supuestos explícitos.

Construye DriverConfig con IDs GET, prueba igualdad de Job settings, sube configuración inmutable y enlaza su hash en el notebook privado existente. Preserva política106, intent desconocido y todos sus contadores. Presupuesto propio acumulativo:64 HTTP/2 escrituras (Files PUT sin overwrite y workspace import exacto). Intents durables y readbacks; reanudar conserva política/payloads y reconcilia sin reenviar efectos ambiguos. Política vencida requiere nueva versión explícita, jamás retimestamp. Sin Jobs write/run, SQL, ACL ni compute start.

Preflight sin auth ni ventana:

    PYTHONPATH=src .venv/bin/python -m sbs.operations.policy_binding_130

Después de revisión y login válido, completar approved/issued_at_ms/expires_at_ms del template deployment/policy-binding130-review-template.json con ventana vigente <=30min; conservar hashes, TTL y límites. Ejecutar inmediatamente:

    PYTHONPATH=src .venv/bin/python -m sbs.operations.policy_binding_130 --execute --review-file deployment/policy-binding130-authorization.json --journal deployment/state/policy-binding130

Siempre reusar ese journal separado de provision106; no reset ni nuevas ventanas mientras login pendiente.

Prueba local:

    PYTHONPATH=src .venv/bin/python -m unittest discover -s tests/unit -p 'test_policy_binding_130.py'

4 pruebas: ACL adversarias, auth fallida sin emitir política, flujo SDK con bytes bundle real y resume sin nuevas escrituras. Primera pasada32HTTP/2writes, resume57HTTP/2writes. HTTP simulado no acredita ejecución cloud/E2E.

Job queda PAUSED. Warehouse STOPPED permitido sólo para metadata; primer run requiere RUNNING. Notebook preparado para CloudDriver execute captura sellada105 pero no ejecutado. Pendientes primer run real, publicación, recuperación/rollback y operación diaria08Lima/on-demand. Política30min y certificadoGenie5min requieren renovaciones propias; Jobdiario no ofrece disponibilidad continua ni los renueva.
