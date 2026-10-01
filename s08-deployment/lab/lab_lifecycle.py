"""Stop/start sólo App AIS08; endpoint scale-to-zero se verifica, no borra datos."""
import argparse,os
from databricks.sdk import WorkspaceClient
from lab_deploy import CONFIG,save
p=argparse.ArgumentParser();p.add_argument('action',choices=['status','stop-app','start-app']);p.add_argument('--profile');a=p.parse_args()
if a.profile:os.environ['DATABRICKS_CONFIG_PROFILE']=a.profile
w=WorkspaceClient();c=CONFIG
assert c['app_name'].startswith('ais08-') and c['endpoint'].startswith('ais08-')
if a.action=='stop-app':w.apps.stop(c['app_name'])
if a.action=='start-app':w.apps.start(c['app_name'])
endpoint=w.serving_endpoints.get(c['endpoint'])
r={'app':w.apps.get(c['app_name']).compute_status.as_dict(),'endpoint':endpoint.state.as_dict(),
   'scale_to_zero':[e.scale_to_zero_enabled for e in endpoint.config.served_entities] if endpoint.config else []}
save('lifecycle',r);print(r)
