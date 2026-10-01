# SK12 Continuación204 — adopción explícita de App encendida por usuario

Creator Z / SK12 0.1.16 provisional.199 terminó después de unaGET, cero upload/mkdir/start/deploy, con FOREIGN_DEPLOYMENT. El usuario confirmó que encendió la App y pidió corregirHost. Root observó mediante nueva sesión OAuth204: mismo App/SP, ACTIVE/RUNNING, active_deployment01f1bc4ca1041e21be0f4795d63d7ebf, creado2026-09-29T21:27:53Z por propietario exacto, source191694605…, SUCCEEDED, sinpending. La respuesta SDK omite last_deployment_id; se tolera ausencia, pero active ID/source son obligatorios y cualquier last explícito debe estar permitido.

Reutiliza PACKAGE199 exacta24687d1435c9b7dbbd0a0689ff02328556031122a37b2fa4cf4b4cbfe789ec98 y deadline1790719123. No nueva materialización ni ventana. Revisión204 fija observación, package y fallo199; requiere `user_started_app_adoption_authorized:true` y status PASS_EXPERIMENTAL_CONTINUE_204. Conserva revisiones199/197 y numeric188 FAIL/final153 bloqueado.

Nuevo STATE204, adopción durable con executor_starts0. No llama start ni lo permite en ambos transportes. Upload234, mkdir50, deploy1 y HTTP1599 restantes del presupuesto SDK199; preserva acumulados191/194/199: upload234,mkdir42,start2,deploy2,HTTP905. Identidad/cleanup usan transportes heredados aparte. Paquete y234readbacks se verifican mediante shipping191. GET fresco exige identidad/fuente conocidas y computeactivo. Antesdeploy: pendingnull y terminal explícito en active.status más get_deployment fresco (corrección194), ID/source/owner/create_time ligados. No adopta otro ID no observado después de la revisión.

Errores después de adoptar computeactivado realizan cleanup de identidad conocida. Reconciliación usa adoption-intent.json, no inventa start-intent. Supervisor retiene MISMO cfg OAuth en memoria hasta deadline; `--ui-failed` del coordinador199 solicita stop204. No reconstruir perfil para ese flujo.

Handoff conserva ledger192 y usa migración199 sin refunds ni nuevasreservas. Crea archivos antes inexistentes deploy-receipt.json/demo-ledger/continuation204.json dentro deSTATE199 para mantener Coordinator199 y sus cuatroacciones exactas; result199,api199 y admission199 quedan intactos. Recibo204 y referenciahash dejan clara procedencia. No ejecutar nuevamente199.

Seis tests locales: adopciónactual/pins/window; rechazo owner/source/time/SP ajenos; start0/segundodeploybloqueado; gate terminal antesdeploy con no materialize; cleanup de candidatoambiguo basadoenadopción; expiryantesauth y cfg idéntico enstop. No validan cloud/UI. Prueba: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m unittest tests.unit.test_experimental_204 -v`.

Ejecución por root trasreview: importar experimental_continue_204 y llamar `supervised_execute(cfg=cfg204)` mientras sesión autorizada permanece viva. No emitirdeadline al revisar, ejecutar pruebas o consultarpreflight.
