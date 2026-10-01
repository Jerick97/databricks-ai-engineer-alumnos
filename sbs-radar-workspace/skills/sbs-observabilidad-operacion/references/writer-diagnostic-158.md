# Diagnóstico158 — sin inferir causa del fallo146

Run418932841079948/task472124888759957 falló en CloudDispatcher.verify112. Captura156 contiene JOB_VERIFICATION_UNAVAILABLE pero no identifica cuál llamada agrupada falló. No es prueba de permisos Jobs insuficientes. Ver análisis158. No cambiar guards ni dar grants por hipótesis.

Notebook diagnóstico standalone usa Config normal en contexto mismoJob/SP, valida host/jobcontext, hace exactamente hasta5GET independientes: Me,Job,JobACL,UCtable,warehouse. Cada respuesta guarda status/requestID/rawJSON hasta256KiB; no authheaders/tokens. JSON no parseable/sobredimensionado sólo hash/tamaño. Excepción local registra tipo, nunca texto sensible. Reporte final dbutils.notebook.exit conserva output aunque haya403; no ejecuta pipeline/SQL/modelos/Files writes.

Runner tras revisión: PYTHONPATH=src .venv/bin/python -m sbs.operations.writer_diagnostic_158 --execute --review-file deployment/writer-diagnostic158-authorization.json --profile databricks-ai-engineer-aws. Nuevojournal writer-diagnostic158. Ownerauth y GETfresh Jobnormalized/trustedACL/privateNotebookID/ACL/exporthash antes efecto. Máximo16GETouter+1import+1run; ejecución notebook añade hasta5GETreadonly. Import exacto overwritenotebookprivate existente, sin cambiarJobsettings. Preserva payload146 en restore146-payload.json; restauración es paso posterior revisado (no segundoimport automático). Intents ambiguos no se reenvían; readbackconfirma notebook antesrun. Resultado run_id_candidate requiere GETobservado posterior, no IDactivo asumido.

Capreview ventana vigente<=30min independiente de política146, pues diagnóstico no usa pipeline ni toca datos. JobPAUSED sigue; ejecución puntual diagnóstica. No reinicia ledger146/156; source146/invocations/errores preservados. Después de report: localizar primera falla transporte/guard y corregir mínimo demostrado; taskruntime incompleto detectado localmente es dependencia separada, no causa establecida deverify.

2tests PASS: notebook5GETcon403raw sinsecret y runnerfixture import/run/readback/resume sin segundaescritura, restorepayload igual146. No nube porconstructor ni causa cloud probada.
