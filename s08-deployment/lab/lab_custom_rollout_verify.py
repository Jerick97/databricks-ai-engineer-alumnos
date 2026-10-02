"""CP3: evidencia cloud de rutas custom + muestras SQL, sin confundir ratio muestral y configuración."""
import argparse,os,collections,concurrent.futures,json
from databricks.sdk import WorkspaceClient
from lab_deploy import CONFIG,save
p=argparse.ArgumentParser();p.add_argument('--profile');p.add_argument('--requests',type=int,default=20);p.add_argument('--status-only',action='store_true');a=p.parse_args()
if a.profile:os.environ['DATABRICKS_CONFIG_PROFILE']=a.profile
if not 1<=a.requests<=100:raise ValueError('requests entre1y100')
w=WorkspaceClient();endpoint=CONFIG['endpoint']+'-rollout';e=w.serving_endpoints.get(endpoint)
r={'endpoint':endpoint,'state':e.state.as_dict(),'task':e.task,'traffic':e.config.traffic_config.as_dict() if e.config else {},'source':'UC ventas S05 real','served_entities':[{'name':x.name,'entity_name':x.entity_name,'entity_version':x.entity_version} for x in e.config.served_entities] if e.config else []}
if a.status_only:
    save('custom-rollout-status',r);print(r);raise SystemExit(0)
if e.state.ready.value!='READY' or e.pending_config:raise RuntimeError('Deployment pendiente; no es validación completada')
from lab_monitor import sql
expected=json.loads(sql(w,f"SELECT {CONFIG['catalog']}.{CONFIG['source_schema']}.ventas_categoria('Bebidas',2026)").result.data_array[0][0])
r['oracle_venta_neta']=expected['venta_neta']
def invoke(_):
    result=w.api_client.do('POST',f'/serving-endpoints/{endpoint}/invocations',body={'dataframe_records':[{'categoria':'Bebidas','anio':2026}]})
    return result['predictions'][0]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    outputs=list(pool.map(invoke,range(a.requests)))
r['counts_by_revision']=dict(collections.Counter(x['revision'] for x in outputs));r['requests']=len(outputs)
r['all_business_values_correct']=all(abs(float(x['venta_neta'])-float(expected['venta_neta']))<0.01 and x['fuente'].endswith('gold.ventas_por_categoria_mes') for x in outputs)
r['examples']=[next(x for x in outputs if x['revision']==revision) for revision in r['counts_by_revision']]
expected_revisions={route.served_model_name for route in e.config.traffic_config.routes if route.traffic_percentage>0}
r['all_active_routes_observed']=expected_revisions<=set(r['counts_by_revision'])
r['pass']=r['all_business_values_correct'] and r['all_active_routes_observed']
r['limitation']='Porcentajes configuran probabilidades; estos conteos no prueban una diferencia de calidad entre algoritmos.'
from pathlib import Path
from lab_rollout import normalized_snapshot,validate_snapshot
before_path=Path(__file__).resolve().parents[1]/'reports/lab-rollout-before.json'
if before_path.exists():
    before=json.loads(before_path.read_text())
    validate_snapshot(before,endpoint,w.config.host,f"{CONFIG['catalog']}.{CONFIG['schema']}.ventas_rollout")
    actual=normalized_snapshot(endpoint,w.config.host,before['model_name'],e.config)
    r['matches_saved_baseline']=actual==before
    r['comparison_note']='Debe ser true después del rollback; false durante el canary es esperado.'
save('custom-rollout-verified',r);print(r)
assert r['pass']
