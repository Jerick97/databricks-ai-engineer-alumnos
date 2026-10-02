# Diagnóstico048 y experimento055

CreatorZ,2026-09-28. Fuentes primarias locales reutilizadas: contrato047, diagnóstico048, revisiónSK09-048, loader049 (pins046/047/cierrePDF), reranker CPU fijado047 y evaluador018/047. No hubo búsqueda web ni descarga.

Brecha causal: diagnóstico048 identifica4 y6 positivos descartados alrecortarRRF20 en las consultas de conducta de mercado. Reranker sobre ese mismo pool no puede recuperarlos. Alternativas: aumentar ramas o cambiar embeddings alteraría otro factor; expansiónSK03 no mide recuperación del ranking. Intervención acotada: unión de ambas ramas20, mismoRRF60/modelo/queries/filtros/qrels, sin expansión.

[Informe completo](../../../sbs-radar-workspace/docs/experimento-pool-union-055.md) y evidencia `runs/sk04-pool-union-055/`. Scores comunes y baseline047 exactos; pools30/29/35. Rankings congelados antes de medir referencia. Dos tests de mecánica antes delscript; seis llamadasONNX reales. Coste monetario desconocido, repeticiones1, desarrollo expuesto.

Riesgo→control: contaminación por qrels→no usados para scoring; cambio silencioso modelo→identidad/sha/exactscore; confundir pool confinal→métricas ambas; ocultar familia peor→tabla porconsulta y macrosporfamilia; aumentar coste→ventanas/tokens/timing separados; aceptación falsa→no promoción ni gate. Skill permaneceprovisional y revisión independiente pendiente. No se observó ni afirmó mejora conductualgeneral por wording.
