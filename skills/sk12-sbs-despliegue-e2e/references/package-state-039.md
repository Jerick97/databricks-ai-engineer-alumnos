# Brief reutilizado039 — separación de estado operativo

Fecha: 2026-09-28. Fuentes primarias locales: `deployment/build_bundle.py` (ROOTS incluye deployment recursivamente) y `runs/sk12-phase-s-017.py` (state_root fijado a deployment/state/phase-s-017). No se consultó red ni se leyó el contenido de autorizaciones originales.

Hecho: el baseline empaqueta el archivo sintético de autorización y journals bajo deployment/state, en las variantes con/sin modelos. Inferencia: transplantarlos al destino mezcla evidencia de admisión/origen con estado operativo consumible. Decisión mínima: exclusión exacta de archivo y subárbol; no redacción genérica, eliminación ni modificación de configuración. Alternativa descartada: excluir deployment entero perdería planes/ejecutores; filtrar por substrings eliminaría nombres similares legítimos.

Prueba: tests/unit/test_bundle_state_039.py verifica miembros exactos, todos los hashes y bytes tar, near-misses stateful/state.json/authorization-template, evidencia en docs/runs y preservación byte a byte de entradas. Dos casos parametrizados fallan antes y pasan después. No acredita un release final, permisos de destino ni seguridad exhaustiva de todo archivo del repositorio. No hay benchmark conductual ni aceptación de skill por estos tests técnicos; revisión independiente pendiente.
