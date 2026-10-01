"""CP3 complemento REAL si agent/v1/responses no permite traffic splits. No sustituye Neptuno UI."""
import argparse,os,json
from pathlib import Path
import mlflow
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound
from databricks.sdk.service import serving
from mlflow.models.resources import DatabricksSQLWarehouse,DatabricksFunction
from lab_deploy import CONFIG,save

def main():
    p=argparse.ArgumentParser();p.add_argument('--profile');p.add_argument('--deploy',action='store_true');a=p.parse_args()
    if a.profile:os.environ['DATABRICKS_CONFIG_PROFILE']=a.profile
    w=WorkspaceClient();c=CONFIG
    if a.deploy:
        try: w.serving_endpoints.get(c['endpoint']+'-rollout')
        except NotFound: pass
        else: raise RuntimeError('Endpoint custom ya existe; usa lab_rollout.py, no recrear ni mover aliases')
    mlflow.set_tracking_uri('databricks');mlflow.set_registry_uri('databricks-uc')
    mlflow.set_experiment(f"/Users/{w.current_user.me().user_name}/AIS08-Neptuno")
    name=f"{c['catalog']}.{c['schema']}.ventas_rollout";function=f"{c['catalog']}.{c['source_schema']}.ventas_categoria";versions=[]
    import pandas as pd
    for revision in ['champion','challenger']:
        with mlflow.start_run(run_name='AIS08-custom-rollout-'+revision):
            info=mlflow.pyfunc.log_model(name='ventas',python_model=str(Path(__file__).with_name('rollout_model.py')),
                model_config={'warehouse_id':c['warehouse_id'],'function_name':function,'revision':revision},
                resources=[DatabricksSQLWarehouse(warehouse_id=c['warehouse_id']),DatabricksFunction(function_name=function)],
                pip_requirements=['mlflow==3.16.1','databricks-sdk==0.143.0','pandas>=2,<4'],
                input_example=pd.DataFrame([{'categoria':'Bebidas','anio':2026}]))
            version=mlflow.register_model(info.model_uri,name).version;versions.append(version)
            mlflow.MlflowClient().set_registered_model_alias(name,revision,version)
    endpoint=c['endpoint']+'-rollout'
    save('custom-rollout-package',{'model':name,'versions':versions,'endpoint':endpoint,'source':'UC ventas S05 real','purpose':'Mecánica canary; ambas versiones preservan misma cifra y sólo etiqueta revision cambia'})
    if a.deploy:
        entities=[serving.ServedEntityInput(name=label,entity_name=name,entity_version=v,workload_size='Small',scale_to_zero_enabled=True) for label,v in zip(['champion','challenger'],versions)]
        w.serving_endpoints.create(name=endpoint,config=serving.EndpointCoreConfigInput(name=endpoint,served_entities=entities,traffic_config=serving.TrafficConfig(routes=[serving.Route(served_model_name='champion',traffic_percentage=100),serving.Route(served_model_name='challenger',traffic_percentage=0)])))
        print('Custom rollout endpoint submitted',endpoint)
if __name__=='__main__':main()
