"""Genera la copia docente preconfigurada; el starter del alumno conserva su aislamiento."""
from pathlib import Path
import json
R=Path(__file__).resolve().parents[1]
c=json.loads((R/'lab/config.json').read_text());source=(R/'notebook.py').read_text()
defaults={'catalogo':c['catalog'],'warehouse_id':c['warehouse_id'],'sufijo':c['endpoint'].removeprefix('ais08-'),'esquema':c['schema'],'s07_schema':c['approved_schema']}
for key,value in defaults.items():
 old=f'dbutils.widgets.text("{key}", "",'
 assert source.count(old)==1,key
 source=source.replace(old,f'dbutils.widgets.text("{key}", {json.dumps(value)},')
source=source.replace('# MAGIC # S08 · Neptuno se despliega y se observa vivo','# MAGIC # S08 · Docente · Neptuno se despliega y se observa vivo\n# MAGIC **Copia docente preconfigurada para el workspace del curso.** Ejecuta Run all con `modo=verificar`: catálogo, warehouse, esquema y recursos ya tienen los valores del ensayo. No necesita parámetros de Job. El starter de alumnos sigue siendo `notebook.py`, con configuración propia por equipo.')
(R/'notebook-docente.py').write_text(source)
print('Copia docente generada; cinco widgets preconfigurados, modo verificar')
