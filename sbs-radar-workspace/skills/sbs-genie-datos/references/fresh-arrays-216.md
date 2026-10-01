# SK06 fresh216 — ndarray real del conector SQL

CreatorZ/SK06 0.1.17 provisional.215 completó SET y reservó primer DESCRIBE DETAIL antes de CONNECTOR_VALUE_TYPE_UNSUPPORTED. Traceback sin SQL nuevo: runs/sk06-fresh-215-types.json y detail-fixture.json. partitionColumns/clusteringColumns/tableFeatures son numpy.ndarray; timestamps datetime y properties/statistics listas de pares. Ningún numpy scalar standalone observado.

ArraySessionReader216 hereda SessionReader081 intacto y envuelve fetchmany: ndarray.tolist(), recursión sobre listas/tuplas/dict para arrays anidados. No convierte scalar standalone, nombres/tipos de columnas ni semántica de mapas. SessionReader original conserva canonicalJSON, ancho/esquema, bytecap/rowcap, queryID, hashes/proof, poisoning y ausencia de retry. connector-adapter216.json documenta la adaptación al mismo contrato JSONv1.

Detalle exige STRINGformat/id/location; perfilNamed añade STRINGname y location vacío o matchingUC. RestoARRAY/MAP se conserva JSON, sin gobernar identidad. HISTORY exige versionLONG/BIGINT; listas/tuplas/arrays adicionales se canonizan sin colapsar pares a dict. READBACK conserva STRING/BOOLEAN exactos y hashes/versiones.

Fixture DETAIL real reconstituido con ndarray reales/datetime reproduce fallo081 y pasa216 con esquema/proof/Namedidentity intactos. Prueba8tablas/33SQL sintéticos con arrays/mapas enDETAIL/HISTORY y32historyrecords valida certificado/hashes originales; cachedhistory sigue rechazado. Bytecap negativo y scalar standalone sin conversión probados. Seis tests PASS, sin acreditar cloud.

STATE216 nuevo exclusivo, cfg existente, cero start adicional. Original0810SQL,2131SET,2152SQL preservados con locks.216 máximo33 nuevos:36fresh acumulados, legacy99/112 sin reset. Pollhistory215 conservado. No modifica081/213/215 ni SDK.

Review: runs/sk09-fresh-216-review.json PASS_FRESH_RECOVERY_216 y freeze_sha256. Ejecutar module.execute(ROOT,review_path,cfg=cfgactual). Constructor sin auth/cloud/SQL.
