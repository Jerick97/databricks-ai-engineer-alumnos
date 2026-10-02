# Databricks notebook source
# Diagnostic158: exactly five read-only requests; no pipeline/model/SQL/Files write.
import json,time,hashlib,re
import requests
from databricks.sdk.core import Config
HOST='https://dbc-0410b264-20c7.cloud.databricks.com'
JOB=989326861421503
PRINCIPAL='33b6f37c-7e6a-489f-b313-f886418b0319'
TARGETS=[('Me','/api/2.0/preview/scim/v2/Me',{}),('job','/api/2.2/jobs/get',{'job_id':JOB}),('job_acl','/api/2.0/permissions/jobs/'+str(JOB),{}),('table','/api/2.1/unity-catalog/tables/neptuno_manuel_arguelles.sbs_radar.refresh_control',{'include_browse':'false'}),('warehouse','/api/2.0/sql/warehouses/828756322bedff37',{})]
report={'version':'diagnostic158','cloud_calls':0,'mutations':0,'sql':0,'model_calls':0,'pipeline_executed':False,'cause_not_presumed':True,'observations':[]}
try:
 cfg=Config()
 if cfg.host.rstrip('/')!=HOST:raise ValueError('DIAGNOSTIC_HOST_INVALID')
 if int(dbutils.widgets.get('job_id'))!=JOB:raise ValueError('DIAGNOSTIC_JOB_CONTEXT_INVALID')
 report['job_id']=JOB;report['run_id']=int(dbutils.widgets.get('run_id'))
 session=requests.Session()
 if not all(a.max_retries.total==0 for a in session.adapters.values()):raise ValueError('DIAGNOSTIC_RETRIES_FORBIDDEN')
 try:
  for name,path,query in TARGETS:
   observation={'stage':name,'path':path};report['observations'].append(observation)
   try:
    # Normal runtime credentials; headers/tokens never persisted or printed.
    auth=cfg.authenticate();report['cloud_calls']+=1
    response=session.request('GET',HOST+path,params=query,headers=auth,timeout=(10,30),allow_redirects=False,stream=True)
    try:
     observation['http_status']=response.status_code
     observation['request_ids']={k:response.headers[k][:256] for k in ('x-request-id','x-databricks-request-id') if response.headers.get(k)}
     raw=response.raw.read(262145,decode_content=True)
     observation.update(body_bytes=len(raw),body_sha256=hashlib.sha256(raw).hexdigest())
     if len(raw)>262144:observation['body_status']='oversize_not_copied'
     else:
      try:body=json.loads(raw);observation['body']=body
      except Exception:observation['body_status']='not_json_not_copied'
    finally:response.close()
   except Exception as error:observation['local_error_type']=type(error).__name__
 finally:session.close()
except Exception as error:report['bootstrap_error_type']=type(error).__name__
# Result output retains raw JSON metadata, never request/authentication headers.
report['status']='diagnostic_only_not_pipeline_success'
dbutils.notebook.exit(json.dumps(report,sort_keys=True))
