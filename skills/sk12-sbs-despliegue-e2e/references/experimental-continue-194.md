# Continuación experimental194 — provisional, solo evaluación local

Invocación SK12 0.1.16 mediante Creator Z. Reutiliza investigación y decisión `runs/sk09-linux-next-experiment-190.md`, revisión191 y revisión del materializado191. No cambia archivos congelados191 ni gate153: equivalencia numérica188 permanece FAIL.

Fallo observado:191 hizo234 uploads verificados,1start y1deploy HTTP400 porque active_deployment estaba IN_PROGRESS aunque pending_deployment era null. Cleanup observó STOPPED.194 conserva source694605f5c11d9bcb82d75424db7e7cda83068ad07c64a8ec5318d9dd7f205f89 y deadline1790716194 (21:09:54UTC). Reutiliza los234 receipts de bytes exactos y manifiesto local, sin upload, mkdir, rematerialización ni nueva descarga. Sin evidencia de otro escritor al prefijo único.

Nueva admisión194 permite1start y1deploy adicionales, HTTP771 máximo: agregado191+194 upload234, mkdir42, start2, deploy2, HTTP1600. Identity y cleanup son transportes separados heredados191, no incluidos en ese contador de transporte SDK. Conserva límites de modelo4generation,2embedding,20000tokens y1worker; no renueva la ventana.

Antes de deploy requiere computeACTIVE/RUNNING, pending null y estado terminal explícito SUCCEEDED/FAILED/CANCELLED tanto en active_deployment como en get_deployment fresco, fijando id/source/owner/create_time. Restaura/adopta solo source previo exacto y dueño/tiempo del start. Fallos posteriores a start realizan cleanup del recurso conocido. CLI supervisado permanece hasta deadline y aplica cleanup194; el binding exitoso usa exactamente `experimental-app191/demo-ledger/binding.json` consumido por192.

Pruebas locales discriminan IN_PROGRESS+pendingnull, freshGET discordante, dueño cambiado, source/deadline fijo, caps adicionales, caducidad antes de autenticar y binding192. No acreditan cloud/UI. Revisar freeze y emitir `runs/sk09-experimental-194-review.json` con status PASS_EXPERIMENTAL_CONTINUE_194 y freeze_sha256 antes de ejecución por coordinador.

Comando autorizado por coordinador, tras revisión: `PYTHONPATH=src .venv/bin/python deployment/experimental_continue_194.py --execute`. No ejecutar191, rematerializar, editar ledger anterior ni extender deadline. Stop manual194: mismo comando con `--stop`.
