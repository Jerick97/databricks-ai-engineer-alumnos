# Promoción local de release SK11

API servidor:

- `LocalService.from_release(state_root, pointer={release_id, sha256}, mode='local')` construye desde SK03/SK04/SK06 preparados, sin capturas ni inferencia.
- `service.promote_release(state_root, pointer=...)` verifica el candidato antes del swap bajo el mismo lock que consultas y lookups; fallo conserva estado anterior. Devuelve snapshot previo/actual. Sesiones se segregan por sujeto, ID y snapshot; no migra memoria.
- `materialize_release(store, receipt, destination)` en `sbs.operations.runtime_release` usa `VolumeArtifacts.recover/_read` (Files download) inyectado y el receipt confiable de `SnapshotWriter.current()`. Verifica manifiesto/hash/cierre, materializa en directorio aislado y devuelve `{state_root, pointer}`. No sube objetos. El servidor conserva ese directorio durante la vida de sus consumidores. Resolver directorios temporales canónicos del servidor (`Path(tempdir).resolve()`) antes de pasar al loader, que rechaza symlinks.
- `create_service()` lee opcional `config/runtime-release.json`: ausente o `{"enabled":false}` conserva piloto congelado; activo exige exactamente `enabled`, `state_root` relativo al proyecto y `pointer`. Config activa inválida falla, nunca vuelve silenciosamente al corpus anterior. Config/receipt son capacidades servidor, no inputs HTTP ni prueba de autorización por su hash.

Verificaciones: closure completo SK03/04/06, fuentes/PDF/rawtext/extractor/config, spans originales, input exacto del embedding, índice/modelo y recuración SK06 coherentes. Query embeddings previos se reutilizan por modelo exacto y pregunta sellada; no dependen del corpus. Promoción no llama modelos. Un nuevo modelo exige preparación y configuración compatibles, no mezclar por dimensión.

Catálogo y focos proceden de pares/provisiones actuales. Página física compartida es foco de lectura, no correspondencia semántica; comparación acotada SK03 mantiene candidatos/alineación incierta. Anotaciones reutilizadas conservan condición IA y materialidad no adjudicada. Cobertura parcial; páginas sin contraparte no se inventan como un par seleccionable, aunque sigan presentes en el índice del par. No se alteran fuentes/gold congelados.

Genie preparado localmente no equivale a publicación/binding: release promovido devuelve `GENIE_RELEASE_UNPUBLISHED` y no reutiliza el espacio/mapa del piloto anterior. Publicación, reconciliación de snapshot y conexión Genie del nuevo release son posteriores. Cierre técnico no acredita conversación de modelo, aplicación cloud ni Jobs reales; requiere SK09 independiente y ejecución autorizada posterior.


Perfil estructural049: [contrato explícito local](runtime-structural-049.md). `create_service(structural_config_path=...)` carga el índice231 en LocalService, pero no escribe `runtime-release.json` ni punteros. Es incompatible con bootstrap release/cloud concurrente; mantener separado hasta incorporar su preparación/cierre en SK11 y satisfacer el gate de promoción.
