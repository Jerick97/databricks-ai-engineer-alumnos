# SK06 fresh213 — continuación tras fallo anterior al primer SQL

Creator Z, SK06 0.1.17 provisional. Intento205/081 inició warehouse y conservó gobernanza, luego fallóimportaciónSQL. Repetirlo chocó con warehouse.json append-only distinto. Ambos hechos no autorizan borrar el journal ni repetir start.

213 conserva205 intacto y utiliza exclusivamente deployment/state/fresh-readback-213. Antes de cualquier efecto exige original081 sin intent/submission/result ni publicación. Valida binding exacto plan/cap33, startintent del warehouse correcto, observación históricaRUNNING/start_requested y gobernanza. Retiene lock exclusivo del original durante toda nuevaejecución para impedir una reserva205 concurrente; no escribe original. Estado213 nuevo con mkdir exclusivo impide reabrirlo incluso si vuelve a fallar antesSQL. CualquierSQL yareservado exige reconciliaciónGET, no213.

La importaciónreal Connection y versión4.2.6 preceden creación213. cfg oficialenmemoria se conserva. FreshGET warehouse mediante ensure_running allow_start=False: siSTOPPED bloquea y jamásPOSTstart. RUNNINGhistórico no se presenta como actual. Se reobservan identidad y gobernanza en nueva carpeta de evidencia.

Cuerpo de33SQL sigueidéntico205: SETuse_cached_result=false +32lecturas en una sesión,8tablas, historial independiente sincache, governanceantes/después, certificado, registry, publicaciónprotegida y TTLsin ampliar. Historiallegacy112/99 se preserva y referencia porhash, sinreset/refund; lectura fresca33 es fase081 separada ya revisada, no ampliación del cap112original. recovery213.json conserva hashesoriginales, ceroSQLprevios y1startprevio; éxito expone33máximoacumuladofresh y0startnuevo.

9testsPASS: zeroSQL/legacy/startpreservados, cincoevidenciasprevias bloqueantes, stateexclusivo/cfgidéntico, STOPPEDnoPOST y diff exactodelcuerpo205. No cloud/auth/SQL duranteconstrucción. El entorno local.venv informa connectorausente; root poseeprocesoactual con4.2.6 importado y debe reutilizarlo, no sustituir un testdoblepor evidenciaSDK.

Revisiónindependiente: runs/sk09-fresh-213-review.json status PASS_FRESH_RECOVERY_213 y freeze_sha256 de runs/sk06-fresh-213-freeze.json. Ejecutar módulo.execute(ROOT, review_path, cfg=cfgactual). Reconcile213 sóloGET sobrejournal213. No tocar081 ni copiapreservadaattempt1.
