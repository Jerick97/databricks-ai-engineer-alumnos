"""Pruebas REALES del agente, salidas saneadas; no usa mocks."""
import argparse,json,os,time,uuid
from databricks.sdk import WorkspaceClient
from lab_deploy import CONFIG,save

def main():
    p=argparse.ArgumentParser();p.add_argument('--profile');p.add_argument('--local',action='store_true');a=p.parse_args()
    if a.profile:os.environ['DATABRICKS_CONFIG_PROFILE']=a.profile
    if a.local:
        import mlflow
        mlflow.set_tracking_uri('databricks')
        mlflow.set_experiment(f"/Users/{WorkspaceClient().current_user.me().user_name}/AIS08-Neptuno")
        from agent import AgenteNeptuno
        from mlflow.types.responses import ResponsesAgentRequest
        agent=AgenteNeptuno(CONFIG)
        invoke=lambda q,request_id:agent.predict(ResponsesAgentRequest(input=[{'role':'user','content':q}])).model_dump()
    else:
        w=WorkspaceClient()
        endpoint=w.serving_endpoints.get(CONFIG['endpoint'])
        if endpoint.pending_config or endpoint.state.ready.value!='READY': raise RuntimeError('Endpoint no está estable; espera READY y NOT_UPDATING')
        served_version=endpoint.config.served_entities[0].entity_version
        invoke=lambda q,request_id:w.api_client.do('POST',f"/serving-endpoints/{CONFIG['endpoint']}/invocations",body={'input':[{'role':'user','content':q}],'client_request_id':request_id})
    cases=[('ventas','¿Cuánto vendimos de Bebidas en 2026?'),('aclaracion','¿Cuánto vendimos de Bebidas?'),('categoria_ausente','¿Cuánto vendimos en 2026?'),('reposicion','¿Qué productos requieren reposición?'),('rag','¿Qué condiciones rigen la devolución de productos Neptuno?'),('costos','¿Cuál es el margen de Bebidas en 2026?')]
    results=[]
    for name,q in cases:
        started=time.monotonic();request_id='ais08-'+name+'-'+uuid.uuid4().hex
        try:
            r=invoke(q,request_id);answer='\n'.join(p.get('text','') for o in r.get('output',[]) for p in o.get('content',[]) if p.get('type')=='output_text');meta=r.get('custom_outputs',{})
            passed=bool(answer) and meta.get('tool_errors',0)==0
            if name=='ventas':passed=passed and ('11602488' in ''.join(ch for ch in answer if ch.isdigit())) and meta.get('tool_calls',0)>0
            if name=='aclaracion':passed=passed and meta.get('tool_calls')==0 and ('año' in answer.lower())
            if name=='categoria_ausente':passed=bool(answer) and 'categoría' in answer.lower() and not any(t.get('ok') for t in meta.get('tool_audit',[]))
            if name=='reposicion':passed=passed and 'Nord' in answer and 'Outback' in answer and 'no requiere' not in answer.lower()
            if name=='rag':passed=passed and 'documento_id=politica_devoluciones' in answer and 'chunk_id=' in answer
            if name=='costos':passed=passed and 'costo' in answer.lower()
            results.append({'case':name,'client_request_id':None if a.local else request_id,'served_model_version':None if a.local else served_version,'pass':passed,'answer':answer,'metadata':meta,'elapsed_seconds':round(time.monotonic()-started,2)})
        except Exception as e:results.append({'case':name,'pass':False,'error':type(e).__name__+': '+str(e)[:300]})
        save('smoke-local' if a.local else 'smoke-serving',results)
        print(name,results[-1]['pass'],flush=True)
    if not all(r['pass'] for r in results):raise SystemExit(1)
if __name__=='__main__':main()
