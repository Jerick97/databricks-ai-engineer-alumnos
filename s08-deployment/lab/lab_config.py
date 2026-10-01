"""Configura una copia de laboratorio por equipo, sin credenciales."""
import hashlib
import re

def build_config(base, catalog, warehouse, identity, suffix='', schema=''):
    suffix=suffix or hashlib.sha256(identity.encode()).hexdigest()[:10]
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,24}',suffix):
        raise ValueError('Sufijo: 1–25 letras minúsculas, números o guiones')
    schema=schema or 'ais08_'+suffix.replace('-','_')
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',catalog) or not re.fullmatch(r'ais08_[A-Za-z0-9_]+',schema):
        raise ValueError('Catálogo/schema inválido; schema debe comenzar ais08_')
    if not warehouse:raise ValueError('Completa warehouse_id')
    c=dict(base)
    c.update(catalog=catalog,warehouse_id=warehouse,schema=schema,
             endpoint='ais08-'+suffix,app_name='ais08-'+suffix+'-ui',model_name=f'{catalog}.{schema}.agente_neptuno')
    return c
