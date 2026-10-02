"""Estado puntual; no espera ni considera READY con config pendiente como final."""
import argparse,os
from databricks.sdk import WorkspaceClient
from lab_deploy import CONFIG,save
p=argparse.ArgumentParser();p.add_argument('--profile');a=p.parse_args()
if a.profile:os.environ['DATABRICKS_CONFIG_PROFILE']=a.profile
w=WorkspaceClient();e=w.serving_endpoints.get(CONFIG['endpoint']);app=w.apps.get(CONFIG['app_name'])
r={'endpoint':e.name,'state':e.state.as_dict(),'versions':[{'name':x.name,'version':x.entity_version} for x in e.config.served_entities] if e.config else [],'pending_versions':[{'name':x.name,'version':x.entity_version} for x in e.pending_config.served_entities] if e.pending_config else [],'traffic':e.config.traffic_config.as_dict() if e.config and e.config.traffic_config else {},'app_state':app.app_status.as_dict() if app.app_status else {},'app_url':app.url}
save('status',r);print(r)
