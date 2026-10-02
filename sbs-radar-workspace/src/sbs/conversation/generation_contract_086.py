"""Opt-in diagnostics/capture; existing generator and validators are unchanged.

The captured envelope is the actual parsed HTTP JSON response, reserialized for
storage, not original wire bytes. Its message.content string is preserved exactly.
No fence removal, substring extraction, repair, retry, fallback, or prompt change.
"""
import hashlib
import json
import os
import time
from pathlib import Path
from .databricks import DatabricksGenerator,SingleShotTransport
from sbs.genie.publication_registry import _directory


def sha(raw):return hashlib.sha256(raw).hexdigest()


def write_once(directory,name,value):
    if '/' in name or not name.endswith('.json'):raise ValueError('DIAGNOSTIC_NAME_INVALID')
    raw=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    if len(raw)>1_048_576:raise ValueError('DIAGNOSTIC_ARTIFACT_CAP')
    fd=_directory(directory,True)
    try:
        out=os.open(name,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600,dir_fd=fd)
        with os.fdopen(out,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
        os.fsync(fd)
    finally:os.close(fd)
    return sha(raw)


def classify_content(content):
    if not isinstance(content,str):return {'code':'generated_content_missing'}
    diagnostic=dict(content_sha256=sha(content.encode()),content_chars=len(content),starts_with_code_fence=content.lstrip().startswith('```'))
    try:decoded=json.loads(content)
    except json.JSONDecodeError as error:
        return {**diagnostic,'code':'generated_json_syntax','json_error_position':error.pos,'json_error_line':error.lineno,'json_error_column':error.colno}
    return {**diagnostic,'code':'generated_json_object' if isinstance(decoded,dict) else 'generated_json_non_object','decoded_type':type(decoded).__name__}


class CapturingTransport(SingleShotTransport):
    """One request; durable received envelope before the generator parses content."""
    def __init__(self,delegate,directory):
        self.delegate=delegate;self.directory=Path(directory);self.calls=0;self.last_attempt={};self.content=None
    def __call__(self,body):
        if self.calls:raise ValueError('DIAGNOSTIC_POST_ALREADY_RESERVED')
        self.calls+=1
        write_once(self.directory,'request.json',body)
        try:
            response=self.delegate(body)
        finally:
            self.last_attempt=dict(getattr(self.delegate,'last_attempt',{}))
        if isinstance(response,dict):
            choices=response.get('choices')
            if isinstance(choices,list) and len(choices)==1 and isinstance(choices[0],dict):
                message=choices[0].get('message')
                if isinstance(message,dict):self.content=message.get('content')
        self.last_attempt['response_archive']='pending'
        try:
            response_sha=write_once(self.directory,'response.json',response)
            write_once(self.directory,'response-manifest.json',dict(artifact='response.json',file_sha256=response_sha,kind='actual_parsed_http_envelope_before_generated_content_parse',message_content_preserved=True,wire_bytes_preserved=False,credentials_or_http_headers_included=False,trust='untrusted_model_output_not_accepted_answer'))
        except Exception:
            self.last_attempt.update(stage='response_archive',response_archive='unconfirmed')
            raise RuntimeError('DIAGNOSTIC_RESPONSE_ARCHIVE_UNCONFIRMED') from None
        self.last_attempt.update(response_archive='durable',response_sha256=response_sha)
        return response


class DiagnosticGenerator(DatabricksGenerator):
    def __call__(self,request):
        try:result=super().__call__(request)
        except Exception:
            if isinstance(self.transport,CapturingTransport) and self.last_attempt.get('stage')=='generated_json':
                self.last_attempt['diagnostic']=classify_content(self.transport.content)
            else:self.last_attempt['diagnostic']={'code':'generation_failed_before_content_acceptance','stage':self.last_attempt.get('stage')}
            raise
        self.last_attempt['diagnostic']=classify_content(self.transport.content)
        return result


def reserve_continuation(directory,*,prior_reserved,total_limit,parent_sha256):
    if type(prior_reserved) is not int or type(total_limit) is not int or total_limit!=4 or not 0<=prior_reserved<total_limit:
        raise ValueError('DIAGNOSTIC_PARENT_BUDGET_EXHAUSTED')
    if not isinstance(parent_sha256,str) or len(parent_sha256)!=64:raise ValueError('DIAGNOSTIC_PARENT_PIN_REQUIRED')
    return write_once(directory,'admission.json',dict(phase='086',parent_phase='077',parent_plan_sha256=parent_sha256,prior_reserved=prior_reserved,additional_reserved=1,aggregate_reserved=prior_reserved+1,total_limit=total_limit,remaining_after_reservation=total_limit-prior_reserved-1,reserved_at_ms=int(time.time()*1000),scope='one exact archived request; no embeddings/retry/resource mutation; failed or ambiguous attempt stays reserved'))
