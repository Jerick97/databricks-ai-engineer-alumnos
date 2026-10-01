# Mapa compacto 027

structural-comparison-v3 mantiene formato de segmento y citas exactas. Antes, cada espacio ordinario era replace aunque su texto permaneciera idéntico. Ahora, después de trim/collapse, ese caso es retain y se une a retains contiguos. raw_end/start y derived_end/start deben coincidir; cada longitud coincide con derived_text y rawslice. La reconstrucción raw exige fuente inmutable, como antes; vista derivada sigue citable=false.

No se unen omisiones, reemplazos de tabs/saltos/espacios múltiples, ni segmentos separados por omisiones. La representación se versiona; consumidores que reproducen wrappers deberán construir releases nuevos. No sobrescribir024/026 ni reinterpretar sus hashes.

RED5casos, primeraGREEN mostró tres expectativas de reducción excesivas: cuando todos los espacios cambian, retener la misma cantidad de segmentos es correcto. Prueba final exige no crecimiento y reducción a un segmento para frase de espacios literales. Preservados fallos y snapshotv2. Equivalencia real compara244vistas, todo payload no-mapping/version idéntico; true replacements y omits exactos. Recuperación original con Filesfixtures y PDFs reales pasa sin modificar default32MiB ni transporte. 42,226,207→12,006,047bytes sin gzip; no hay publicación remota, inferencia ni cambio de fuentes.

Pruebas dependen del snapshot `runs/sk03-map-compaction-027-before/structural.py`; empaquetarlo junto a test_mapping_027. Registro y hashes en runs/sk03-map-compaction-027-record.json. Revisión independiente pendiente.
