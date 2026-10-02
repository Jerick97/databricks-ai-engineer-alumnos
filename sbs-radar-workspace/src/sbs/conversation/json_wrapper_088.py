"""Opt-in whole JSON fence compatibility. No runtime or validator override."""
from copy import deepcopy
import json
import re
import math
from pathlib import Path
from .databricks import SingleShotTransport
from .generation_contract_086 import CapturingTransport,write_once,sha


def unwrap_json_object(content):
    if not isinstance(content,str):raise ValueError('GENERATED_CONTENT_NOT_TEXT')
    if len(content.encode())>1_048_576:raise ValueError('GENERATED_CONTENT_CAP')
    stripped=content.strip(' \t\r\n')
    wrapper='raw_json';body=content
    if stripped.startswith('```'):
        match=re.fullmatch(r'```json\r?\n(.*)\r?\n```',stripped,re.DOTALL)
        if not match:raise ValueError('GENERATED_JSON_WRAPPER_INVALID')
        body=match.group(1);wrapper='json_fence'
    def object_pairs(pairs):
        out={}
        for key,value in pairs:
            if key in out:raise ValueError('GENERATED_JSON_DUPLICATE_KEY')
            out[key]=value
        return out
    def constant(_):raise ValueError('GENERATED_JSON_NON_FINITE')
    def floating(value):
        number=float(value)
        if not math.isfinite(number):raise ValueError('GENERATED_JSON_NON_FINITE')
        return number
    try:decoded=json.loads(body,object_pairs_hook=object_pairs,parse_constant=constant,parse_float=floating)
    except json.JSONDecodeError:raise ValueError('GENERATED_JSON_SYNTAX') from None
    if not isinstance(decoded,dict):raise ValueError('GENERATED_JSON_NON_OBJECT')
    return body,dict(wrapper=wrapper,original_content_sha256=sha(content.encode()),normalized_content_sha256=sha(body.encode()),content_chars=len(content),normalization='whole_json_fence_only_no_content_repair',schema_validated=False,citations_validated=False)


class StrictCaptureTransport(SingleShotTransport):
    """One archive per attempted request, before optional envelope normalization."""
    def __init__(self,delegate,directory,*,max_requests,expected_response_model=None):
        if type(max_requests) is not int or not 1<=max_requests<=4:raise ValueError('WRAPPER_QUOTA_INVALID')
        self.delegate=delegate;self.directory=Path(directory);self.max_requests=max_requests
        self.expected_response_model=expected_response_model;self.calls=0;self.last_attempt={}
    def __call__(self,body):
        if self.calls>=self.max_requests:raise ValueError('WRAPPER_QUOTA_EXCEEDED')
        ordinal=self.calls;self.calls+=1
        capture=CapturingTransport(self.delegate,self.directory/f'generation-{ordinal}')
        try:response=capture(body)
        finally:self.last_attempt=dict(capture.last_attempt)
        # Let the existing generator validate failed/ambiguous envelopes first.
        choices=response.get('choices') if isinstance(response,dict) else None
        if not isinstance(choices,list) or len(choices)!=1 or not isinstance(choices[0],dict):return response
        choice=choices[0]
        if choice.get('finish_reason')!='stop':return response
        if self.expected_response_model is not None and response.get('model')!=self.expected_response_model:return response
        message=choice.get('message')
        if not isinstance(message,dict):return response
        self.last_attempt['stage']='content_wrapper'
        try:normalized,metadata=unwrap_json_object(message.get('content'))
        except ValueError as error:
            # All parser exceptions use closed codes, never model content.
            self.last_attempt['content_wrapper']={'status':'rejected','code':str(error)}
            write_once(self.directory/f'generation-{ordinal}','normalization.json',self.last_attempt['content_wrapper'])
            raise
        self.last_attempt['content_wrapper']=metadata
        write_once(self.directory/f'generation-{ordinal}','normalization.json',metadata)
        result=deepcopy(response);result['choices'][0]['message']['content']=normalized
        return result
