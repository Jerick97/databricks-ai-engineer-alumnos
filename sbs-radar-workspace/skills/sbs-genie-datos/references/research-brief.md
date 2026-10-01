# SK06 — Creator Z, 2026-09-27

Capacidad: configurar y consultar Genie sobre datos curados de normas/versiones/cambios/procesos/revisión; integrar resultados estructurados con orquestación. No sustituye RAG ni comparación determinista.

Fuentes reutilizadas: specv0.2, planes13/14, contracts y evidencia de claseS08 (warehouse_id ausente, UI noacreditada porAPI). Runtime actual: runs/sk05-workspace-preflight.json (1warehouseSTOPPED; información, no permisoCANUSE ni consultareal).

Fuente primaria nueva para brechaAPI: https://docs.databricks.com/aws/en/genie-agents/conversation-api (redirect desde/genie/conversation-api; actualizadaSep11,2026). Requiere entitlementSQL y CANUSE sobrewarehousepro/serverless. Gestión permite crear/configurar agentes; chatmantieneconversación. Recomienda almenos5SQLdeejemplo probados y5preguntasbenchmark. Nombreproducto cambió deGenieSpaces aGenieAgents; API mantiene /api/2.0/genie/spaces. Verificar SDKinstalado antesdeescribiradaptador, no asumirsimetríadocumentación/runtime.

Alternativas: adaptar patrones declase reducecódigo, pero no reusar datosficticiosdeclasecomoSBSreal. SQLlocal sirve para probar modelodatos/consultas, no reemplazaGenie. Selección: preparaciónlocalreproducible + adaptadorSDKconpreflight + pruebaremotaantesdeaceptación.

Riesgos: permisoslaterales, resultadosvacíosporfallo, consultasescritura, tablasdesactualizadas, respuestaSQLsinpasajes, parámetrooculto. Evaluación6casosantesdeSKILL, fixturetests separadosdeconsultareal. Estado provisional.
