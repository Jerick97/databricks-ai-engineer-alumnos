"""Optional single-shot generator. No invocation occurs during construction."""
import json
import threading
import time
import re
from urllib.parse import urlsplit

ENDPOINT='databricks-gpt-6-sol'
_SAFE_CODES=frozenset({'INVALID_PARAMETER_VALUE','BAD_REQUEST','PERMISSION_DENIED','UNAUTHENTICATED','NOT_FOUND','RESOURCE_DOES_NOT_EXIST','REQUEST_LIMIT_EXCEEDED','TEMPORARILY_UNAVAILABLE','INTERNAL_ERROR','UNCLASSIFIED_ERROR'})


class SingleShotTransport:
    def __init__(self, workspace_client, *, endpoint=ENDPOINT):
        if not isinstance(endpoint,str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,150}",endpoint):raise ValueError("invalid_generation_endpoint")
        self.endpoint=endpoint
        self.config=workspace_client.config
        host=self.config.host.rstrip('/')
        u=urlsplit(host)
        if u.scheme!='https' or not u.hostname or u.path or u.query or u.fragment or u.username or u.password:
            raise ValueError('invalid_workspace_host')
        self.url=host+'/serving-endpoints/'+endpoint+'/invocations'
        self.last_attempt={}

    def __call__(self, body):
        import requests
        session=requests.Session()
        session.trust_env=False
        self.last_attempt={'stage':'authenticate','http_status':None,'error_code':None}
        started=time.perf_counter()
        try:
            headers={**self.config.authenticate(),'Content-Type':'application/json'}
            self.last_attempt['stage']='request'
            response=session.post(self.url,json=body,headers=headers,timeout=60,allow_redirects=False,stream=True)
            raw=response.raw.read(1048577,decode_content=True)
            if len(raw)>1048576:raise RuntimeError('generation_response_limit')
            self.last_attempt['http_status']=response.status_code
            if response.status_code!=200:
                self.last_attempt['stage']='http_error'
                code=None
                try:
                    payload=json.loads(raw)
                    if isinstance(payload,dict):
                        code=payload.get('error_code')
                        message=payload.get('message','')
                        if isinstance(message,str):
                            self.last_attempt['error_hints']=[term for term in ('max_tokens','max_completion_tokens','temperature','stream','messages','unsupported','not supported','context length','quota','rate limit','permission','not found') if term in message.casefold()]
                except Exception:pass
                self.last_attempt['error_code']=code if isinstance(code,str) and code in _SAFE_CODES else 'UNCLASSIFIED_ERROR'
                raise RuntimeError('generation_service_error')
            self.last_attempt['stage']='http_json'
            result=json.loads(raw)
            self.last_attempt['stage']='http_completed'
            return result
        except requests.Timeout:
            self.last_attempt['stage']='timeout'
            raise RuntimeError('generation_timeout') from None
        except Exception:
            raise RuntimeError('generation_transport_error') from None
        finally:
            self.last_attempt['latency_seconds']=time.perf_counter()-started
            session.close()


class DatabricksGenerator:
    """Finite process-local request quota; each failed request consumes one.

    Backend must retain this instance per authorized run. Reconstructing resets
    quotas. max_tokens bounds output per request, not billed input or cost.
    """
    def __init__(self, *, transport, max_requests, max_tokens, endpoint=ENDPOINT, expected_response_model=None, max_input_chars=120000):
        if any(type(v) is not int or v<=0 for v in (max_requests,max_tokens)):
            raise ValueError('invalid_quota')
        if type(max_input_chars) is not int or max_input_chars<=0:raise ValueError('invalid_input_limit')
        self.endpoint=endpoint;self.expected_response_model=expected_response_model;self.max_input_chars=max_input_chars
        self.transport=transport;self.max_requests=max_requests;self.max_tokens=max_tokens
        self.requests=0;self.lock=threading.Lock();self.last_attempt={}

    def __call__(self, request):
        messages=request['messages']
        if not isinstance(messages,list) or any(not isinstance(m,dict) or not isinstance(m.get('content'),str) for m in messages):raise ValueError('invalid_generation_messages')
        if sum(len(m['content']) for m in messages)>self.max_input_chars:raise ValueError('generation_input_limit')
        with self.lock:
            if self.requests>=self.max_requests:raise ValueError('request_quota_exceeded')
            self.requests+=1
        body={'messages':request['messages'],'max_tokens':self.max_tokens,'stream':False}
        self.last_attempt={'endpoint':self.endpoint,'requests':self.requests,'parameters':{'max_tokens':self.max_tokens,'stream':False},'usage':None}
        self.last_attempt['stage']='transport'
        try:
            response=self.transport(body)
        finally:
            # This transport owns a narrow diagnostics contract, never raw response.
            if isinstance(self.transport,SingleShotTransport):
                self.last_attempt.update(self.transport.last_attempt)
        self.last_attempt['stage']='response_envelope'
        if not isinstance(response,dict):raise ValueError('invalid_generation_response')
        usage=response.get('usage')
        self.last_attempt['usage']={k:v for k,v in usage.items() if k in ('prompt_tokens','completion_tokens','total_tokens') and type(v) is int and v>=0} if isinstance(usage,dict) else None
        model=response.get('model')
        self.last_attempt['response_model']=model if isinstance(model,str) and re.fullmatch(r'[A-Za-z0-9_.:/-]{1,150}',model) else None
        if self.expected_response_model is not None and model!=self.expected_response_model:
            self.last_attempt['stage']='model_identity'
            raise ValueError('generation_model_mismatch')
        choices=response.get('choices',[])
        self.last_attempt['choice_count']=len(choices) if isinstance(choices,list) else None
        if not isinstance(choices,list) or len(choices)!=1 or not isinstance(choices[0],dict):raise ValueError('invalid_generation_response')
        finish=choices[0].get('finish_reason')
        self.last_attempt['finish_reason']=finish if finish in ('stop','length','content_filter','tool_calls',None) else 'unknown'
        if finish=='length':
            self.last_attempt['stage']='truncated'
            raise ValueError('generation_truncated')
        self.last_attempt['stage']='message_content'
        message=choices[0].get('message')
        content=message.get('content') if isinstance(message,dict) else None
        if not isinstance(content,str):raise ValueError('invalid_generation_content')
        self.last_attempt['content_chars']=len(content)
        self.last_attempt['stage']='generated_json'
        answer=json.loads(content)
        if not isinstance(answer,dict):raise ValueError('invalid_generation_object')
        self.last_attempt['stage']='completed'
        return answer
