# Ejecución propuesta — embeddings estructurales041

Estado: preparada y revisada técnicamente; autorización humana pendiente. No se ejecutó inferencia.

Objetivo: generar los231vectores documentales faltantes del dataset026 para continuar la evaluaciónRAG. Plan congelado: `runs/sk04-embeddings-041-plan-v2.json`, hash del payload `29b2909d6a050a3bc7e1210f1f0043fb6314689e50d058c3436f654a6165c87f`.

- Endpoint existente `databricks-qwen3-embedding-0-6b`, workspace `https://dbc-0410b264-20c7.cloud.databricks.com`, perfil normal del proyecto.
- Máximo29POST de embeddings:28lotes de8entradas y1de7, dimensión1024. Una GET metadata por invocación; máximo3intentosGET en todo el journal. Sin reintentosautomáticos. OAuthinterno no instrumentado.
-106278tokens locales de entrada;108126reservados con margen8porentrada. El margen no es un límite de facturación; se detiene después de un exceso observado. Uso no informado queda desconocido.
-Precio observado en metadata036:0.286DBU/millón de tokens; proyección aritmética para106278tokens≈0.030395508DBU. No es coste observado ni presupuesto monetario garantizado. ImporteUSD y facturaciónfinal desconocidos.
-Ventana propuesta:60minutos desde el inicio autorizado de la ejecución, con comprobación antes de admitir cada request. No cancela solicitudes ya en vuelo. La autorización sólo se materializará tras respuesta afirmativa y no renueva FaseS.
-Salida nueva `runs/sk04-embeddings-041-vectors/`. Preserva originales y cachés anteriores; no genera respuestas, no inicia warehouse, noSQL/Jobs/Apps, no cambia políticas ni configura recursos.
-No construye/promueve índice ni mezcla queriescacheadas: correspondencia del modelo remoto y evaluación de recuperación posterior siguen separadas. Corpus expuesto de desarrollo, noholdout.

Evidencia: preflight localreal231/29/108126;59tests delconstructor con dobles claramente etiquetados. SK09 detectó y cerró E41-01/02 con24tests y2probes independientes. Revisión final `runs/sk09-embeddings-041-resolution-review.json`; revisión fallida y snapshots anteriores preservados. El paquete040 anterior no incluye este componente041.

Autorización requerida por SK05: «La selección no autoriza por sí misma gasto o publicación.» Comando y contrato de autorización en `skills/sbs-rag-hibrido/references/embedding-execution-041.md`. La plantilla conserva approved=false; este documento no concede permiso.
