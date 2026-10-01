"""CP0 read-only: no arranca compute, no imprime identidades/credenciales."""
import argparse,os
from databricks.sdk import WorkspaceClient
from lab_deploy import CONFIG,save

def main():
    p=argparse.ArgumentParser();p.add_argument('--profile');a=p.parse_args()
    if a.profile:os.environ['DATABRICKS_CONFIG_PROFILE']=a.profile
    w=WorkspaceClient();c=CONFIG
    r={'host':w.config.host,'warehouse':w.warehouses.get(c['warehouse_id']).state.value,
       'source_functions':[w.functions.get(f"{c['catalog']}.{c['source_schema']}.{n}").full_name for n in ['ventas_categoria','productos_reponer']],
       'rag_table':w.tables.get(f"{c['catalog']}.rag.chunks_embeddings").full_name}
    gate=w.serving_endpoints.get(c['moderation_endpoint']).ai_gateway
    r['safety_input_output']=bool(gate and gate.guardrails and gate.guardrails.input.safety and gate.guardrails.output.safety)
    if not r['safety_input_output']:raise RuntimeError('Moderación S07 sin configurar; no modificar endpoint compartido')
    save('preflight',r);print(r)
if __name__=='__main__':main()
