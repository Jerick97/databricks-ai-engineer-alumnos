# Diagnóstico025: referencia vs encabezado de anexo

Fuente: versiones locales selladas de SBS3274-2017 en seis fuentes del piloto. v6 trataba `Anexo N° 1-A del Reglamento.` como barrera y dejaba blocked=True hasta RESUELVE. La línea continúa el artículo13; artículos27/29 posteriores quedaban index_or_annex_region. Se reprodujeron cuatro faltantes reales y tres referencias partidas antes de corregir.

Cambio v7: solo etiqueta completa ANEXO, ANEXO A, ANEXO N°/Nº + identificador, guion-letra opcional y título con dos puntos inicia esa región. Conserva títulos en línea siguiente y bloqueo del índice. No usa números específicos del corpus. Los formatos de título en la misma línea sin delimitador explícito no están resueltos por esta regla; cobertura permanece parcial. No se modifica rawtext, anotaciones, notas, comparación ni compilador024.

110 pruebas pasan; ensayo de ocho bundles mantiene intervalos exactos en las dos versiones cyber504, actos2286/2220 y ambas4036. Market3274 pasa de12 a64/69 unidades; cuatro targets quedan contenidos literalmente en artículos automáticos27/29. No se atribuye validación jurídica a unidades recién recuperadas. Todos los IDs cambian al derivarse de VERSION/config; integración posterior pendiente. Ejecutor local: `PYTHONPATH=src .venv/bin/python runs/sk02-structure-025-corpus.py`; genera solo nuevos outputs025.

## Resolución ST25-01 (v8)

SK09 encontró que v7 adoptaba artículos posteriores a ANEXO II o títulos sin dos puntos. Se preservó exactamente v7 en runs/sk02-structure-025-v7-snapshot y sus salidas. La regla v7 de etiqueta completa queda sustituida por excepción positiva de prosa: solo frase de referencia soportada junto a oración anterior inconclusa permite continuar cuerpo. Todo otro candidato de anexo se acota como annex_heading_or_ambiguous_region y bloquea artículos posteriores. No se declara que sea anexo confirmado jurídicamente. El límite ahora conserva/excluye formatos desconocidos, no permite atribuirlos al cuerpo.

RED7fallos nuevos → GREEN117; cinco probes originales SK09 reutilizados sin cambiar assertions, omitiendo únicamente el bloque que exige igualdad con salidas históricasv7 (sustituido por ocho nuevos outputs/v6 interval regression). Cuatro targets27/29 siguen cubiertos; seis bundles no3274 conservan rangos. No hay regeneración024 ni promoción.
