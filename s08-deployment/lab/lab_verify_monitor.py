"""Read-only: no basta crear monitor, exige métricas materializadas."""
import argparse,os
from databricks.sdk import WorkspaceClient
from lab_deploy import CONFIG,save
from lab_monitor import sql
p=argparse.ArgumentParser();p.add_argument('--profile');a=p.parse_args()
if a.profile:os.environ['DATABRICKS_CONFIG_PROFILE']=a.profile
w=WorkspaceClient();schema=f"{CONFIG['catalog']}.{CONFIG['schema']}";table=w.tables.get(schema+'.inference_flat')
monitor=w.data_quality.get_monitor('table',table.table_id)
r={'monitor':monitor.as_dict(),'refreshes':[x.as_dict() for x in w.data_quality.list_refresh('table',table.table_id)]}
cfg=monitor.data_profiling_config
for key,name in [('profile',cfg.profile_metrics_table_name),('drift',cfg.drift_metrics_table_name)]:
    r[key+'_table']=name
    try: r[key+'_rows']=int(sql(w,f'SELECT count(*) FROM {name}').result.data_array[0][0]) if name else 0
    except Exception as exc:
        r[key+'_rows']=0
        r[key+'_error']=type(exc).__name__+': '+str(exc)[:300]
r['pass']=r['profile_rows']>0 and r['drift_rows']>0
save('monitor-verified',r);print({k:v for k,v in r.items() if k!='monitor' and k!='refreshes'})
if not r['pass']:raise SystemExit('Métricas pendientes; revisa refresh y baseline, no afirmar monitor validado')
