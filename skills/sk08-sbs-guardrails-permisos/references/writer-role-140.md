# Rol writer140

126 observó403 PERMISSION_DENIED explícito: creador del Job requiere servicePrincipal.user. No inferencia histórica: evidencia deployment/state/job-recovery126/http-005-error.json.140 añade sólo ese rol al OWNER sobre SPwriter exacto; preserva todos los grants frescos y etag con serializer AccountAccessControlProxyAPI SDK0.102.0. Preflight no cloud; fresh identity/SP/rulesetGET antes de máximo1PUT. Presupuesto acumulativo12HTTP/1PUT, sin retries. GET final verifica conjunto exacto de principal/rol esperado. Intent existente sólo reconcilia; conflicto/fallo no se reenvía. No cambia ownership, tokens, grupos, ACL global ni Job.

CLI: PYTHONPATH=src .venv/bin/python -m sbs.operations.writer_role_140. Para ejecutar después de revisión usar --execute --review-file deployment/writer-role140-authorization.json --journal deployment/state/writer-role140. Template aprobadofalse; ventana de admisión interna vigente <=30min, alcance053 ya autorizado. Journal no puede solapar106/126. Frozen126 e intento agotado preservados.

Cuatro pruebas con transporte simulado, no E2E cloud. PUT+readback primera5HTTP/1PUT, resume4GET sinPUT. Posterior create necesita nuevo intento explícito separado tras cambio de estado, únicoPOST y freshGETlist0, sin reutilizar126 agotado. JobPAUSED y137 binding/firstrun siguen pendientes. Coste desconocido.
