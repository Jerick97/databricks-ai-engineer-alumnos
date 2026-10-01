"""CP3: canary custom NeptunoVentas; agent/v1/responses no admite split."""
import argparse,json,os
from pathlib import Path
from mlflow import MlflowClient
import mlflow
from databricks.sdk import WorkspaceClient
from databricks.sdk.service import serving
from lab_deploy import CONFIG,save

def normalized_snapshot(endpoint,workspace_host,model_name,config):
    entities=sorted([serving.ServedEntityInput.from_dict(e.as_dict()).as_dict() for e in config.served_entities],key=lambda e:e['name'])
    traffic=config.traffic_config.as_dict()
    traffic['routes']=sorted(traffic['routes'],key=lambda r:r['served_model_name'])
    return {'endpoint':endpoint,'workspace_host':workspace_host,'model_name':model_name,'served_entities':entities,'traffic_config':traffic}

def validate_snapshot(snapshot,endpoint,workspace_host,model_name):
    if any(snapshot.get(k)!=v for k,v in {'endpoint':endpoint,'workspace_host':workspace_host,'model_name':model_name}.items()):
        raise ValueError('Snapshot pertenece a otro endpoint/workspace/modelo; no restaurar evidencia docente ni ajena')
    if not snapshot.get('served_entities') or any(e.get('entity_name')!=model_name for e in snapshot['served_entities']):
        raise ValueError('Snapshot contiene entidades de otro modelo')

def main():
    p=argparse.ArgumentParser();p.add_argument('--profile');p.add_argument('--challenger-version');p.add_argument('--percent',type=int,default=10);p.add_argument('--rollback',action='store_true');a=p.parse_args()
    if a.profile:os.environ['DATABRICKS_CONFIG_PROFILE']=a.profile
    if not 0<=a.percent<=100:raise ValueError('Porcentaje debe estar entre 0 y 100')
    w=WorkspaceClient();c=dict(CONFIG)
    c['endpoint']=CONFIG['endpoint']+'-rollout'
    c['model_name']=f"{CONFIG['catalog']}.{CONFIG['schema']}.ventas_rollout"
    mlflow.set_registry_uri('databricks-uc');client=MlflowClient()
    current=w.serving_endpoints.get(c['endpoint'])
    if current.task and current.task.startswith('agent/'):
        raise ValueError('Traffic splitting no soportado para agentes; usa lab_custom_rollout.py')
    if current.pending_config or current.state.ready.value!='READY':raise RuntimeError('Espera READY y NOT_UPDATING antes de otra actualización')
    assert c['endpoint'].startswith('ais08-')
    path=Path(__file__).resolve().parents[1]/'reports/lab-rollout-before.json'
    if a.rollback:
        old=json.loads(path.read_text())
        validate_snapshot(old,c['endpoint'],w.config.host,c['model_name'])
        w.serving_endpoints.update_config(c['endpoint'],served_entities=[serving.ServedEntityInput.from_dict(e) for e in old['served_entities']],traffic_config=serving.TrafficConfig.from_dict(old['traffic_config']))
        print('Rollback solicitado; verificar READY y consulta antes de afirmar recuperación');return
    if not a.challenger_version:raise ValueError('Especifica --challenger-version')
    before=normalized_snapshot(c['endpoint'],w.config.host,c['model_name'],current.config)
    if path.exists():
        old=json.loads(path.read_text());validate_snapshot(old,c['endpoint'],w.config.host,c['model_name'])
        if old!=before:raise ValueError('Ya existe snapshot de otro estado. Conservarlo; completar rollback o archivar explícitamente para nuevo ensayo')
    else:save('rollout-before',before)
    champion=client.get_model_version_by_alias(c['model_name'],'champion').version
    client.set_registered_model_alias(c['model_name'],'challenger',a.challenger_version)
    wanted={'champion':str(champion),'challenger':str(a.challenger_version)}
    existing={e.name:e for e in current.config.served_entities}
    # Preservar parámetros exactos si las versiones ya están desplegadas; no cambiar workload/env.
    entities=[serving.ServedEntityInput.from_dict(existing[name].as_dict()) if name in existing and existing[name].entity_version==version else serving.ServedEntityInput(name=name,entity_name=c['model_name'],entity_version=version,workload_size='Small',scale_to_zero_enabled=True) for name,version in wanted.items()]
    routes=[serving.Route(served_model_name='champion',traffic_percentage=100-a.percent),serving.Route(served_model_name='challenger',traffic_percentage=a.percent)]
    # REST exige entidades incluso para cambio de rutas (lab-rollout-api-limitation.json).
    w.serving_endpoints.update_config(c['endpoint'],served_entities=entities,traffic_config=serving.TrafficConfig(routes=routes))
    save('rollout',{'endpoint':c['endpoint'],'champion':champion,'challenger':a.challenger_version,'percent':a.percent,'submitted':True})
if __name__=='__main__':main()
