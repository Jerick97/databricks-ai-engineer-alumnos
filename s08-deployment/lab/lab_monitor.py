"""CP5–CP6: payload real -> métricas sin texto/PII -> data profiling."""
import argparse,os,json,time
from pathlib import Path
from databricks.sdk import WorkspaceClient
from databricks.sdk.service import dataquality as dq
from lab_deploy import CONFIG,save

def sql(w,statement):
    r=w.statement_execution.execute_statement(warehouse_id=CONFIG['warehouse_id'],statement=statement,wait_timeout='50s')
    deadline=time.monotonic()+180
    while r.status.state.value in {'PENDING','RUNNING'} and time.monotonic()<deadline:
        time.sleep(2);r=w.statement_execution.get_statement(r.statement_id)
    if r.status.state.value!='SUCCEEDED':raise RuntimeError(str(r.status.error))
    return r

def main():
    p=argparse.ArgumentParser();p.add_argument('--profile');p.add_argument('--create-monitor',action='store_true');p.add_argument('--refresh',action='store_true');a=p.parse_args()
    if a.profile:os.environ['DATABRICKS_CONFIG_PROFILE']=a.profile
    w=WorkspaceClient();c=CONFIG;schema=f"{c['catalog']}.{c['schema']}";raw=schema+'.ais08_neptuno_payload';flat=schema+'.inference_flat'
    columns={x.name for x in w.tables.get(raw).columns}
    required={'databricks_request_id','request_time','status_code','execution_duration_ms','response','request','served_entity_id','client_request_id'}
    if not required<=columns:raise ValueError('Esquema diferente al contrato; inspecciona antes de flatten: '+str(columns))
    # No inventar logs: el monitor necesita eventos escritos por Serving, no fixtures.
    count=sql(w,f'SELECT count(*) FROM {raw}').result.data_array[0][0]
    if int(count)==0:raise RuntimeError('Inference table vacía: espera ingestión asíncrona (hasta una hora) y reintenta')
    sql(w,f'''CREATE TABLE IF NOT EXISTS {flat} (request_id STRING,served_entity_id STRING,event_time TIMESTAMP,status_code INT,latency_ms DOUBLE,input_chars BIGINT,output_chars BIGINT,input_tokens BIGINT,output_tokens BIGINT,tool_calls BIGINT,tool_errors BIGINT,agent_revision STRING,parse_status STRING) TBLPROPERTIES (delta.enableChangeDataFeed=true)''')
    # MERGE evita duplicar eventos al repetir el job. No modificar la tabla administrada raw.
    sql(w,f'''MERGE INTO {flat} t USING (
      SELECT databricks_request_id request_id, served_entity_id, request_time event_time,status_code,
      CAST(execution_duration_ms AS DOUBLE) latency_ms,
      length(get_json_object(request,'$.input[0].content')) input_chars,
      length(get_json_object(response,'$.output[0].content[0].text')) output_chars,
      CAST(get_json_object(response,'$.custom_outputs.input_tokens') AS BIGINT) input_tokens,
      CAST(get_json_object(response,'$.custom_outputs.output_tokens') AS BIGINT) output_tokens,
      CAST(get_json_object(response,'$.custom_outputs.tool_calls') AS BIGINT) tool_calls,
      CAST(get_json_object(response,'$.custom_outputs.tool_errors') AS BIGINT) tool_errors,
      get_json_object(response,'$.custom_outputs.agent_revision') agent_revision,
      CASE WHEN status_code>=400 THEN 'http_error' WHEN get_json_object(response,'$.output[0].content[0].text') IS NULL THEN 'parse_error' ELSE 'ok' END parse_status
      FROM {raw} QUALIFY row_number() OVER(PARTITION BY databricks_request_id ORDER BY request_time DESC)=1
    ) s ON t.request_id=s.request_id WHEN NOT MATCHED THEN INSERT *''')
    result=sql(w,f"SELECT count(*),sum(tool_errors),avg(latency_ms),sum(CASE WHEN parse_status='parse_error' THEN 1 ELSE 0 END),sum(CASE WHEN parse_status='http_error' THEN 1 ELSE 0 END) FROM {flat}").result.data_array
    report={'source':raw,'target':flat,'metrics':result,'raw_rows':count}
    smoke=Path(__file__).resolve().parents[1]/'reports/lab-smoke-serving.json'
    if smoke.exists():
        import re
        ids=[r.get('client_request_id') for r in json.loads(smoke.read_text()) if r.get('client_request_id')]
        if ids:
            assert all(re.fullmatch(r'[a-zA-Z0-9_-]+',i) for i in ids)
            quoted=','.join("'"+i+"'" for i in ids)
            matched=sql(w,f'SELECT count(DISTINCT client_request_id) FROM {raw} WHERE client_request_id IN ({quoted})').result.data_array[0][0]
            report['smoke_correlation']={'expected':len(ids),'observed':int(matched),'all_ingested':int(matched)==len(ids)}
    save('flatten',report)
    if a.create_monitor:
        sql(w,f'CREATE TABLE IF NOT EXISTS {schema}.inference_baseline AS SELECT * FROM {flat} WHERE parse_status=\'ok\'')
        table=w.tables.get(flat); output=w.schemas.get(schema)
        monitor=dq.Monitor(object_type='table',object_id=table.table_id,data_profiling_config=dq.DataProfilingConfig(
          output_schema_id=output.schema_id,baseline_table_name=schema+'.inference_baseline',assets_dir=f"/Shared/AIS08/{c['schema']}/monitor",time_series=dq.TimeSeriesConfig(timestamp_column='event_time',granularities=[dq.AggregationGranularity.AGGREGATION_GRANULARITY_1_HOUR]),warehouse_id=c['warehouse_id']))
        result=w.data_quality.create_monitor(monitor=monitor)
        save('monitor',result.as_dict())
    if a.refresh:
        table=w.tables.get(flat)
        refreshed=w.data_quality.create_refresh('table',table.table_id,dq.Refresh(object_type='table',object_id=table.table_id))
        save('monitor-refresh',refreshed.as_dict())
if __name__=='__main__':main()
