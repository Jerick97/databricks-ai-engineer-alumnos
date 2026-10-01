"""Fixed authorized canary; exclusive protocol file prevents quota reset."""
import json,hashlib,time,re
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[3]
ENDPOINT='databricks-gpt-6-luna'
def now():return datetime.now(timezone.utc).isoformat()
def sha(b):return hashlib.sha256(b).hexdigest()
def path(s):return ROOT/('runs/sk05-generation-alternative-'+s+'.json')
def write(s,d):path(s).write_text(json.dumps(d,indent=2)+'\n')
def safe(v):return v if isinstance(v,str) and re.fullmatch(r'[A-Za-z0-9_.:/-]{1,200}',v) else None
def main():
 import requests
 from requests.adapters import HTTPAdapter
 from databricks.sdk import WorkspaceClient
 assetpath=ROOT/'skills/sbs-modelos-configuracion/assets/generation-canary-v1.json'
 asset=json.loads(assetpath.read_text());body=asset['request'];assert body['max_tokens']==128 and body['stream'] is False
 wire=json.dumps(body,separators=(',',':')).encode();skill=ROOT/'skills/sbs-modelos-configuracion/SKILL.md'
 protocol={'registered_at':now(),'skill':'SK05','version':'0.1.3','skill_sha256':sha(skill.read_bytes()),'asset_version':asset['asset_version'],'asset_sha256':sha(assetpath.read_bytes()),'script_sha256':sha(Path(__file__).read_bytes()),'endpoint':ENDPOINT,'profile':'databricks-ai-engineer-aws','metadata_get_max':1,'alternative_post_max':1,'prior_sol_posts':2,'total_authorized_posts':3,'max_tokens':128,'stream':False,'timeout_seconds':60,'retries':0,'request_body_sha256':sha(wire),'cost':None,'scope':'canary_operability_not_SBS_quality','preparation_failure':'Initial runner write failed because scripts directory absent; no API called then.'}
 with path('protocol').open('x') as f:json.dump(protocol,f,indent=2)
 result={'stage':'authenticate','endpoint':ENDPOINT,'alternative_posts':0,'prior_sol_posts':2,'http_status':None,'usage':None,'response_model':None,'cost':None,'canary_pass':False};start=time.perf_counter();session=requests.Session();session.mount('https://',HTTPAdapter(max_retries=0))
 try:
  client=WorkspaceClient(profile='databricks-ai-engineer-aws');host=client.config.host.rstrip('/');u=urlsplit(host)
  assert u.scheme=='https' and u.hostname and not any([u.path,u.query,u.fragment,u.username,u.password])
  headers={**client.config.authenticate(),'Content-Type':'application/json'}
  result['stage']='metadata_get';response=session.get(host+'/api/2.0/serving-endpoints/'+ENDPOINT,headers=headers,timeout=60,allow_redirects=False)
  meta={'observed_at':now(),'http_status':response.status_code}
  if response.status_code!=200:write('metadata',meta);return
  d=response.json();config=d.get('config',{});entities=config.get('served_entities',config.get('served_models',[]));state=d.get('state',{})
  meta.update({'name':safe(d.get('name')),'task':safe(d.get('task')),'ready':safe(state.get('ready')),'config_update':safe(state.get('config_update')),'config_version':config.get('config_version'),'models':[safe(e.get('foundation_model',{}).get('name')) for e in entities]})
  meta['compatible']=meta['name']==ENDPOINT and meta['task']=='llm/v1/chat' and meta['ready']=='READY' and meta['config_update']=='NOT_UPDATING' and meta['models']==['system.ai.'+ENDPOINT]
  write('metadata',meta)
  if not meta['compatible']:result['stage']='metadata_incompatible';return
  write('before-post',{'at':now(),'protocol_sha256':sha(path('protocol').read_bytes()),'metadata_sha256':sha(path('metadata').read_bytes()),'request_body_sha256':sha(wire),'quota_consumed':True,'prior_sol_posts':2,'this_alternative_post':1,'total_posts':3})
  result['stage']='post';result['alternative_posts']=1
  response=session.post(host+'/serving-endpoints/'+ENDPOINT+'/invocations',data=wire,headers=headers,timeout=60,allow_redirects=False)
  result.update({'http_status':response.status_code,'response_body_sha256':sha(response.content),'response_body_bytes':len(response.content)})
  try:d=response.json()
  except Exception:result['stage']='invalid_response_json';return
  if response.status_code!=200:
   result['stage']='http_error';code=d.get('error_code') if isinstance(d,dict) else None
   result['error_code']=code if code in ('PERMISSION_DENIED','UNAUTHENTICATED','REQUEST_LIMIT_EXCEEDED','INVALID_PARAMETER_VALUE','BAD_REQUEST','NOT_FOUND','TEMPORARILY_UNAVAILABLE','INTERNAL_ERROR') else 'UNCLASSIFIED_ERROR'
   msg=d.get('message','') if isinstance(d,dict) else '';result['error_hints']=[s for s in ('permission','rate limit','quota','max_tokens','unsupported') if isinstance(msg,str) and s in msg.lower()];return
  result['stage']='response_validation';result['response_model']=safe(d.get('model'));usage=d.get('usage')
  result['usage']={k:v for k,v in usage.items() if k in ('prompt_tokens','completion_tokens','total_tokens') and type(v) is int and v>=0} if isinstance(usage,dict) else None
  choices=d.get('choices',[])
  if len(choices)!=1:return
  finish=choices[0].get('finish_reason');result['finish_reason']=finish if finish in ('stop','length','content_filter','tool_calls') else 'unknown';content=choices[0].get('message',{}).get('content')
  if not isinstance(content,str):return
  result['content_sha256']=sha(content.encode());result['canary_pass']=json.loads(content)==asset['expected_json'] and finish=='stop';result['stage']='completed'
 except requests.Timeout:result['stage']='timeout'
 except Exception:result['failure']='safe_unclassified_failure'
 finally:
  session.close();result.update({'elapsed_seconds':time.perf_counter()-start,'completed_at':now(),'total_posts_including_prior':2+result['alternative_posts']});write('result',result);print(json.dumps(result,indent=2))
if __name__=='__main__':main()
