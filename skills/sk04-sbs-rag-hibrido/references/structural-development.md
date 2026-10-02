# Compilador estructural de desarrollo 024

API: `sbs.retrieval.development.build_dataset(root)` y `write_dataset(root, destination)`. El destino debe ser nuevo; no sobrescribe resultados. CLI empaquetable:

```sh
PYTHONPATH=src .venv/bin/python -m sbs.retrieval.development --root . --output data/retrieval/structural-development-next
```

Salida congelada: `data/retrieval/structural-development-024-v3/`; v1 y v2 se conservan. Reutiliza seis fuentes selladas, structure v6, notes v4, wrapper021 y tres preguntas expuestas de SK04real001. Los registros questions/passages/pairs/judgments cumplen el esquema018. Los seis positivos son un mapeo compilado de referencias literales anotadas existentes, no una adjudicación nueva de Astra, revisión humana, negativos exhaustivos ni holdout. No cambia umbrales ni llama freeze_protocol.

122 pasajes:116 automáticos y6 subspans anotados con origen separado. Cuatro brechas automáticas permanecen: artículos27 y29.1.4 de market_conduct en ambas versiones. No se sustituyen silenciosamente por páginas. Notas/exclusiones y contexto conservan sidecars; el texto automático exacto puede contener notas intercaladas y mobiliario, sin afirmar limpieza completa. Los wrappers conservan original_comparison, mapas y limitaciones.

Cada input conserva texto completo, partes exactas, hashes, identidad del modelo, conteo y estado de caché. Caché documental:0hits/122misses;51410tokens, máximo2595, límite32760, sin excedidos. Caché de consultas:3hits verificados por archivo, envelope, input y modelo. No se emiten vectores nuevos ni índice; candidate_strategy declara new_index_required/indexed=false. Coste futuro desconocido y autorización de inferencia pendiente.

Pruebas discriminantes: mismo ID con texto cambiado no reutiliza vector; identidad tokenizer/modelo incompatible falla; input sobre límite permanece íntegro; citas exactas y esquema018; denominador de contraparte2; destino existente no se sobreescribe; metadatos anotados portables sin alterar fuente. RED originales, error de harness recall(dict) y RED de rutas históricas están preservados. Las rutas se proyectan a relativas solo en metadata entregada, usando resolver con contención existente.
