# Continuación privada118 — provisional SK08/SK11/SK12 + skill-creator-z

Evidencia: notebook Shared creado106/114 heredó usersCAN_MANAGE, diagnóstico runs/sk08-notebook-acl-118.json. Guard UNTRUSTED_NOTEBOOK_WRITER detuvo antes del grant/Job. Home existente observado118b: /Users/sociosdosmilveintiseis@gmail.com, directoryID2571826969054457; ownerCAN_MANAGE directo y adminsCAN_MANAGE heredado. No reducir el guard ni modificar Shared/globalACL.

provision_118.py reutiliza helpers/SDK/DriverConfig y orquestación106 copiada explícitamente con estos cambios: notebook exacto /Users/sociosdosmilveintiseis@gmail.com/sbs-radar-writer118-<archiveSHA16>; stages notebook_bootstrap118/notebook_acl118/notebook_bound118_* propios; home existente revalidado antes y al final; creaciónjob mediante private_settings que usa job_settings original. WriterConfig frozen sólo exige ruta absoluta: DriverConfig/path privado es compatible. Test compara hashes cloud_dispatch/cloud_driver con manifiesto105 para acreditar bytes frozen, sin relajar clases.

PrivateApi118 añade únicamente import privadoexacto y GETACL homeIDfijo. Rechaza mkdirs y cualquier import Shared/otra ruta, incluso con permit. Jobs create exige tasknotebook privadoexacto. Solicitud privada mantiene cuerpo fijado/permit de un uso, autorizar antes/después de auth, contador acumulativo, timeout, no retries/redirects y límite32MiB de106. Resto usa ScopedApi original. Files conserva normalizaciónHEAD114. No monkeypatch global ni cambios105/106/114.

La copia de run evita crear/revisitar carpetaShared; usa home yaobservado. Mismo journal106, policy106, tabla, seed, grants y bundle. Sharedbootstrap inocuo retenido y nunca enlazado al Job ni reemplazado por execute. Cinco mutaciones nuevas: bootstrap privado, CAN_READwriter notebook privado, createJobPAUSED, uploadconfig externo y notebookprivado final. Cuotas originales120HTTP/12mutaciones/12SQL; no reset, nueva tabla/SP/credencial/Volume/directorio, start ni run-now.

RED módulo ausente; GREEN tres casos, incluido pipeline concreto con serializadores SDK + HTTPfixture. Reproduce106HEAD404 y114SharedACL, llega45HTTP/7mutaciones/6SQL y continúa118 hasta88HTTP/12mutaciones/8SQL simulados. Previousreceipts/policy byte-idénticos, ceroPATCH SharednotebookACL y JobPAUSED ligado sólo al privado. No acredita cloud ni permiso efectivoSP;117 UC/warehouse separado.

Preflight sin auth/red/writes: PYTHONPATH=src .venv/bin/python -m sbs.operations.provision_118

Tras reviewroot y capability106 vigente más capability118 (template aprobadofalse, tiemposnull):

PYTHONPATH=src .venv/bin/python -m sbs.operations.provision_118 --execute --review-file deployment/provision106-authorization.json --patch-review-file deployment/provision118-authorization.json --journal deployment/state/provision106 --writer-mode execute

118 incluye hash wrapper114: no requiere capability114 adicional;106 sigue necesaria. Policy original no se renueva mediante review118; writer bloqueará tras vencer. DiarioPAUSED hasta permisos117, run real vía ledger/on-demand, readbacks, recuperación y aceptación independiente. GenieTTL5min independiente. Constructor sin nube ni cambiosjournal.
