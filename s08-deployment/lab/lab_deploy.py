"""CP0–CP2: despliegue real, aislado. Ejecutar desde lab con auth unificada."""
import argparse
import json
import os
from pathlib import Path
import mlflow
from mlflow import MlflowClient
from mlflow.models.resources import DatabricksServingEndpoint, DatabricksSQLWarehouse, DatabricksFunction, DatabricksTable
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound
from databricks.sdk.service import serving

ROOT=Path(__file__).resolve().parent
CONFIG=json.loads((ROOT/'config.json').read_text())
REPORTS=ROOT.parent/'reports'

def save(name,data):
    REPORTS.mkdir(exist_ok=True)
    (REPORTS/f'lab-{name}.json').write_text(json.dumps(data,indent=2,default=str,ensure_ascii=False))

def main():
    p=argparse.ArgumentParser();p.add_argument('--profile');p.add_argument('--package-only',action='store_true');args=p.parse_args()
    if args.profile: os.environ['DATABRICKS_CONFIG_PROFILE']=args.profile
    w=WorkspaceClient(); c=CONFIG
    assert c['schema'].startswith('ais08') and c['endpoint'].startswith('ais08-')
    try:w.schemas.get(f"{c['catalog']}.{c['schema']}")
    except NotFound:w.schemas.create(name=c['schema'],catalog_name=c['catalog'],comment='Laboratorio aislado S08')
    mlflow.set_tracking_uri('databricks');mlflow.set_registry_uri('databricks-uc')
    mlflow.set_experiment(f"/Users/{w.current_user.me().user_name}/AIS08-Neptuno")
    from agent import SYSTEM
    prompt=mlflow.genai.register_prompt(name=f"{c['catalog']}.{c['schema']}.neptuno_system",template=SYSTEM,commit_message='S08 governed deployment')
    try: mlflow.genai.load_prompt(f'prompts:/{prompt.name}@champion')
    except Exception: mlflow.genai.set_prompt_alias(prompt.name,'champion',prompt.version)
    c['system_prompt']=prompt.template
    c['prompt_version']=str(prompt.version)
    resources=[DatabricksServingEndpoint(endpoint_name=c['llm_endpoint']),DatabricksServingEndpoint(endpoint_name=c['embedding_endpoint']),DatabricksSQLWarehouse(warehouse_id=c['warehouse_id']),DatabricksTable(table_name=f"{c['catalog']}.rag.chunks_embeddings")]
    resources += [DatabricksServingEndpoint(endpoint_name=c['moderation_endpoint'])]
    resources += [DatabricksFunction(function_name=f"{c['catalog']}.{c['source_schema']}.{f}") for f in ['ventas_categoria','productos_reponer']]
    with mlflow.start_run(run_name='AIS08-agent-as-code'):
        info=mlflow.pyfunc.log_model(name='agent',python_model=str(ROOT/'agent.py'),model_config=c,resources=resources,
            pip_requirements=['mlflow=='+mlflow.__version__,'databricks-sdk==0.143.0','openai==2.54.0','jsonschema==4.26.0'],
            input_example={'input':[{'role':'user','content':'¿Cuánto vendimos de Bebidas en 2026?'}]})
        model=mlflow.register_model(info.model_uri,c['model_name'])
    client=MlflowClient()
    try: client.get_model_version_by_alias(c['model_name'],'champion')
    except Exception: client.set_registered_model_alias(c['model_name'],'champion',model.version)
    save('package',{'model_name':c['model_name'],'version':model.version,'model_uri':info.model_uri,'mlflow_version':mlflow.__version__})
    if args.package_only:return
    # Un alias del Registry NO cambia el tráfico: Serving fija una versión numérica.
    entity=serving.ServedEntityInput(name='champion',entity_name=c['model_name'],entity_version=str(model.version),workload_size='Small',scale_to_zero_enabled=True)
    try:w.serving_endpoints.get(c['endpoint'])
    except NotFound:
        result=w.serving_endpoints.create(name=c['endpoint'],config=serving.EndpointCoreConfigInput(name=c['endpoint'],served_entities=[entity]),
            ai_gateway=serving.AiGatewayConfig(inference_table_config=serving.AiGatewayInferenceTableConfig(enabled=True,catalog_name=c['catalog'],schema_name=c['schema'],table_name_prefix='ais08_neptuno')))
        save('deployment',{'endpoint':c['endpoint'],'submitted':True,'version':model.version})
    else:
        raise RuntimeError('Endpoint ya existe: inspecciona y usa lab_rollout.py; no reemplazar silenciosamente')

if __name__=='__main__':main()
