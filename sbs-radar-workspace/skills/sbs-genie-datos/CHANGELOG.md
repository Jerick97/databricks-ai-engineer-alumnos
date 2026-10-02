# SK06

##0.1.0
Briefprimario yseiscasos/assertions antesdeSKILL. Baselineconservado sinfallorelevanteclaro; GREEN/revisión ycomponentependientes. Provisional.

## 0.1.2
Procedencia GET de Query History por statement_id, igualdad AST Databricks con SQLGlot 30.20.0 para literales seguros, y publicación/snapshot independientes. Mapeo SK06/RAG con seis PDFs y 135 citas exactas; IDs de artículo no se convierten en raw-page IDs. Focos ausentes se rechazan en vez de devolver cero. RED→GREEN y lectura metadata real conservados; no SQL/start/inferencia ni E2E.


## 0.1.13
Corrección050 del lector de publicación: resultado vacío real puede omitir manifest.chunks con ambos contadores enteros cero. Mantener validación de esquema/formato/truncamiento y rechazar resultados vacíos contradictorios. Fixture completo del resultado observado y variante SDK; RED 11 fallos/40 passes, GREEN focal 112 passes. Skill provisional, revisión independiente y reanudación remota separadas. Registro: runs/sk06-empty-result-050-invocation.json.


## 0.1.14
Renovación052 explícita y append-only de ventana para publicación parcial; recursos/plan inmutables, presupuesto SQL acumulado y admisión real. RED15/1, GREEN16 y regresión89. Revisión independiente y cloud pendientes; sin cambio del journal real.

## 0.1.16
Genie metadata: orden requerido de tablas, único bloque de instrucciones, readback exacto y diagnóstico acotado; fallos059/060/061 preservados. Sin atribuir E2E a preparación ni pruebas locales.
