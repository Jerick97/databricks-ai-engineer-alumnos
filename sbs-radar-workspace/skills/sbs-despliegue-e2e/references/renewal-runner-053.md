# Runner de renovación053

Estado: implementación local provisional; revisión independiente del runner pendiente. Reutiliza PASS052 de biblioteca, no lo convierte en revisión del runner ni ejecución cloud. Autoridad humana existente: `runs/sk00-autonomy-053.json`; no requiere una nueva pregunta de consentimiento.

## Investigación y brecha

CreatorZ reutiliza código local phase017, resume/restart050, API052, configuración017 y ledger actual. Observaciones: scripts050 ejecutan al importarse; configuración017 tiene hashes previos a052; journal conserva binding original, presupuesto112 y3 reservas; intento recovery050b documenta RUNNING anterior. Nueva necesidad: preflight importable, aplicación explícita de configuración revisada, emisión fresca de ventana y renovación local antes del publisher. No se consultó web, SDK, autenticación ni cloud para construir.

El runner es `runs/sk12-phase-s-053.py`. Default:

```sh
PYTHONPATH=src .venv/bin/python runs/sk12-phase-s-053.py
```

No crea ni renueva capacidades. Expone hashes actuales/propuestos, delta de inputs de código, budget y `review_contract`. Sólo permite drift de los cuatro archivos publicación/writer/registry/renewal; otros inputs alterados bloquean. Comprueba PASS052 sobre hashes actuales, autoridad053 fijada, plan y binding/ledger originales. Ventana exacta30min; coste desconocido y límite SQL112 permanecen explícitos.

## Gate de revisión técnica

El evaluador independiente entrega un JSON cerrado igual a `report.review_contract` con `status` cambiado a `PASS`: `files_sha256`, `source_configuration_sha256`, `approved_configuration_sha256`, `status`. Los archivos incluyen runner, phase017, cuatro módulos de publicación, autoridad053, revisión052 y autorización previa050. La revisión evalúa comportamiento; copiar hashes sin revisión no constituye PASS.

Después de revisión, ejecución explícita por coordinador:

```sh
PYTHONPATH=src .venv/bin/python runs/sk12-phase-s-053.py --execute --review runs/REVIEW-ADMISSION.json --apply-reviewed-config
```

`--apply-reviewed-config` reconoce técnicamente el delta aprobado, no pide consentimiento humano nuevo. Antes de reemplazar configuración017, archiva bytes previos, posteriores y delta bajo `runs/sk12-phase-s-053-config-*`. Después vuelve a pasar `phase.load`; cualquier drift bloquea. No altera plan, roles, recursos, modelo ni límites.

## Admisión y persistencia

Sólo execute emite `deployment/phase-s-053-authorization.json` desde reloj actual, por30min, basado en autoridad persistente053. `renew_policy_window` recibe old/new WriterConfig y callback real `phase.authorize`, con presupuesto fijado; añade lineage sin reescribir binding/journal/ledger. Un runner-intent exclusivo y durable impide una segunda ejecución ambigua; fallos se registran y requieren reconciliación técnica, nunca reset automático.

Autenticación SDK comienza después de la migración local. AdmissionConfig vuelve a comprobar plazo tras autenticar y AdmissionStatements bloquea SQL vencido. El writer052 instala únicamente su propio CumulativeStatements bajo lock; el runner no reserva otra cuota. GET actual RUNNING permite seguir sin POST; GETSTOPPED permite unaPOST sólo con historialRUNNING confirmado y nuevo intent exclusivo. Si POST no se confirma, sólo GET hasta tres observaciones; no start/SQL retry, no stop/delete automático.

## Evidencia y límites

`tests/unit/test_phase_s_runner_053.py`: siete tests; preflight sin mutar config/binding/budget; autorización30min mediante authorize real; RUNNINGprevio/STOPPEDnuevo, POSTambigua y bloqueo de repetición; revisión obligatoria y apply explícito; vencimiento antes SQL y después de authenticate; execute en raíz temporal con authorize/renovación/persistencia reales y SDK/activity/writer falsos. Ese último verifica archives, lineage, ledger intacto y ausencia de wrapper doble, sin afirmar publicación real.

RED y GREEN en `runs/sk12-renewal-runner-053-*`. El preflight real es lectura local; sólo los fixtures ejecutaron la rama execute. No se modificaron configuración017, autorizaciones reales, journal ni presupuesto. No se ha ejecutado el runner cloud ni acredita permisos, publicación, Genie o app. Contención temporal no cancela solicitudes ya admitidas ni garantiza stop/coste cero.
