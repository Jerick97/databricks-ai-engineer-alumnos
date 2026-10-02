# Corrección aditiva114 — HEAD Files sin cuerpo

SK11/SK12 + skill-creator-z, provisional. Diagnóstico real de root `runs/sk11-files-head-114.json`: HEAD al directorio exacto bootstrap106 del archiveSHA respondió404/body_bytes0/content_typenull. El SDK106 interpretaba sólo error_codeJSON, incompatible con HEAD. Tabla dedicada, seed y grant ya estaban confirmados; journal106 tenía21HTTP/3mutaciones/5SQL. El HEAD diagnóstico adicional es evidencia separada, no se descuenta ni reinicia el contador106.

`provision_114.Head404Api` delega al adaptador106 original y sólo normaliza su RemoteError(404,UNCLASSIFIED) para **HEAD al directorio exacto** a la señal local de ausencia que ya entiende directory_observe. La señal no se presenta como error_code recibido del proveedor.403, otros estados/métodos/rutas conservan el error. No reintenta, crea clientes adicionales ni envía otra request. Sólo FilesAPI usa wrapper; original session/counter/permit/authorizer siguen compartidos.

`Provisioner114` exige journal106 existente con receipts de table/seed/control_acl y policy. Reutiliza run106 completo y sus readbacks, payloads y cuotas acumulativas; no cambia frozen105/106 ni escribe/migra journal durante construcción. Exige revisión106 válida más revisión114 exacta, ambas con ventanas<=30min; renovar revisión no cambia policy previamente persistida. Los gates de runtime/Genie/activación siguen los de106.

Pruebas: RED ausencia módulo; GREEN cuatro casos. HEAD404 vacío con una request incrementa sólo HTTP;403 bloquea; método/ruta diferente no se normaliza. Fixture HTTP con serializadores reales reproduce parada106 exactamente21HTTP/3mutaciones/5SQL, luego continúa114 hasta PAUSED con67HTTP/11mutaciones/7SQL acumulativos simulados. CREATE/INSERT sólo una vez; receipts/policy anteriores permanecen byte-idénticos. No es nueva evidencia cloud.

CLI default preflight sin auth/red/writes:

```bash
PYTHONPATH=src .venv/bin/python -m sbs.operations.provision_114
```

Después de revisión independiente root (template114 contiene approved=false):

```bash
PYTHONPATH=src .venv/bin/python -m sbs.operations.provision_114 --execute --review-file deployment/provision106-authorization.json --patch-review-file deployment/provision114-authorization.json --journal deployment/state/provision106 --writer-mode execute
```

No nuevo journal, no reset de contadores, no reenvío de un efecto ambiguo. Las dos capacidades se fijan por `review_inputs`106 y `patch_inputs`114, respectivamente. El constructor no aprobó ni ejecutó cloud. Source106 permanece intacto; revisión independiente y continuación remota son responsabilidad del coordinador.
