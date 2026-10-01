# SK12: candidato Linux191, admisión experimental separada

Estado provisional y pendiente de revisión independiente. Sigue el memo190 completo; no satisface ni cambia los gates153/168/186. Linux185 demostró runtime,188 demostró FAIL de equivalencia numérica con tolerancia0.001. Ambos hechos se conservan en manifest y ledger; no hay release final autorizado.

## Fuente y materialización

`PYTHONPATH=src .venv/bin/python deployment/experimental_app_191.py` es preflight local, sin autenticación. Con revisión de código fijada, `--materialize` crea deployment/state/experimental-materialized191 con deadline absoluto de30min. No se emite ventana durante preparación191.

Reutiliza directamente los234archivos de transporte/chunks168. Cambia exclusivamente deadline_unix en config/app-integration-133.json y su hash en chunks163-manifest.json. Código133, pesos, tokenizer, corpus, prompts, política privada del operador, selector098, dependencias y bootstrap de reconstrucción permanecen idénticos. No se resube un canary nuevo para buscar PASS. Cada archivo materializado y payload necesita revisión exacta antes del efecto remoto. El estado experimental se expone en coordinador192/ledger, sin modificar respuestas ni la interfaz normativa133.

Revisión código: runs/sk09-experimental-191-review.json con status=PASS_EXPERIMENTAL_191_CODE_ONLY y freeze_sha256. Revisión exacta: runs/sk09-experimental-materialized-191-review.json con status=PASS_EXACT_EXPERIMENTAL_191, manifest_sha256, payload_sha256, executor_freeze_sha256. El materializador no genera estos veredictos.

## Ejecutar y detener

Root ejecuta `PYTHONPATH=src .venv/bin/python deployment/experimental_app_191.py --execute`. Me debe ser owner76826984571984 y host exacto; App existente y SP App son los observados. No crea App, roles, secretos ni endpoints. Subida RAW y readback AUTO reutilizan168/154; antes de cada llamada hay reserva durable191. Estado deployment/state/experimental-app191 es exclusivo: no reintentar el ejecutor ni reiniciar para recargar cuotas. Un fallo requiere reconciliación, nunca resend automático.

Un start puede restaurar el deployment anterior expirado.191 sólo admite esa restauración por source exacta185, owner, ID observado y tiempo posterior al start. Espera compute activo y ausencia de pending; no exige que la App anterior esté sana. Después envía un único deployment candidato. Respuesta ambigua se reconcilia por GET, sin otro POST. Cleanup reconcilia restauración tardía o candidato ambiguo con fuente/owner/tiempo e intenciones; rechaza deployments ajenos.

Al desplegar, imprime el handoff pero **el proceso CLI permanece vivo** supervisando el deadline. Root debe conservar esa sesión mientras usa CUA/coordinador192. Al terminar antes, ejecutar `--stop`; de lo contrario el supervisor solicita stop al deadline y verifica STOPPED. En excepción después de start, intenta cleanup inmediatamente. Error de autenticación, interferencia ajena o stop no confirmado queda explícito; no se afirma STOPPED sin GET. No matar el supervisor como sustituto de stop. Una carpeta cleanup existente impide reenviar STOP.

Presupuesto propio:1600llamadasAPI máximas incluyendo hasta234uploads/50mkdir/1start/1deploy, más1GET identidad; limpieza separada≤13GET/1STOP. Polls acotados60para restauración y60para deployment. SDK0.102.0, transporte single-attempt sin retries. No hay llamadas a modelos ni SQL desde el ejecutor.

## Evaluación de la App

binding.json en demo-ledger incluye deployment/sourceSHA/deadline/caps y process_epoch=null. Caps por proceso133:4generaciones,2embeddings/20000tokens;1worker,8000tokens salida/120000caracteres por generación, sinfallback/retry. Coordinador192 preserva cuatro turnos170 y reservas acumuladas; no inventa cuota global ni epoch. T0–T2 son comparación extractiva; T3 propuesta. Publicación/reader Genie exige vigencia y presupuesto SQL separado: este deploy no lo certifica.

Acceso privado por política133 al operador; M2M, navegación visible, originales/citas y salidas Linux deben observarse realmente. Luego SK09/Astra high evalúa las cuatro salidas reales contra originales;139 es precedente de muestra, no aprobación heredada. Criterio190:4/4turnos adecuados, citas fieles/localizables y cero omisiones críticas observadas, con denominadores y pruebas no evaluadas. Incluso PASS de muestra deja equivalencia FAIL, holdout/generalización/producción pendientes. Conservar respuestas antes de juicio, sin ajustar prompts al resultado.

## Verificación local

Seis pruebas cubren cambios exactos del paquete, rechazo de drift, restauración source/owner/time, reserva previa a timeout y no resend,234subidas con readback y handoff, cleanup de restauración/deploy ambiguos con un STOP, rechazo de propietario ajeno y stop al deadline. Fixtures no acreditan nube, identidad efectiva ni M2M. Evidencia inicial fallida por path temporal symlink del fixture se conserva; corregida mediante resolve, sin cambio de política.
