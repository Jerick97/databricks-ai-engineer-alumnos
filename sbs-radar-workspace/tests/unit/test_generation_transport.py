import json
from types import SimpleNamespace
import pytest
from sbs.conversation.databricks import SingleShotTransport, DatabricksGenerator


def transport(monkeypatch,status=400,payload=None,exception=None):
    calls=[]
    class Session:
        def post(self,*a,**kw):
            calls.append(kw)
            if exception:raise exception
            return SimpleNamespace(status_code=status,raw=SimpleNamespace(read=lambda *a,**kw:json.dumps(payload).encode()))
        def close(self):pass
    monkeypatch.setattr('requests.Session',Session)
    config=SimpleNamespace(host='https://example.test',authenticate=lambda:{'Authorization':'secret-token'})
    return SingleShotTransport(SimpleNamespace(config=config)),calls


def test_http_diagnostics_safe_and_single_shot(monkeypatch):
    t,calls=transport(monkeypatch,payload={'error_code':'INVALID_PARAMETER_VALUE','message':'secret-token raw prompt'})
    g=DatabricksGenerator(transport=t,max_requests=1,max_tokens=256)
    with pytest.raises(RuntimeError):g({'messages':[]})
    assert g.last_attempt['http_status']==400
    assert g.last_attempt['error_code']=='INVALID_PARAMETER_VALUE'
    assert g.last_attempt['stage']=='http_error'
    assert 'secret' not in json.dumps(g.last_attempt)
    assert len(calls)==1 and calls[0]['allow_redirects'] is False
    with pytest.raises(ValueError,match='quota'):g({'messages':[]})
    assert len(calls)==1


def test_unknown_error_code_and_timeout_sanitized(monkeypatch):
    t,_=transport(monkeypatch,payload={'error_code':'my-secret-token'})
    with pytest.raises(RuntimeError):t({})
    assert t.last_attempt['error_code']=='UNCLASSIFIED_ERROR'
    import requests
    t,_=transport(monkeypatch,exception=requests.Timeout('secret-token'))
    with pytest.raises(RuntimeError):t({})
    assert t.last_attempt['stage']=='timeout' and 'secret' not in json.dumps(t.last_attempt)


@pytest.mark.parametrize('finish,content,stage', [('length','{','truncated'),('stop','not-json','generated_json'),('stop',None,'message_content')])
def test_generation_envelope_diagnostics(finish,content,stage):
    g=DatabricksGenerator(transport=lambda body:{'choices':[{'finish_reason':finish,'message':{'content':content}}],'usage':{'prompt_tokens':3,'completion_tokens':2,'total_tokens':5,'secret':'redact'},'model':'observed-model'},max_requests=1,max_tokens=256)
    with pytest.raises((ValueError,RuntimeError)):g({'messages':[]})
    assert g.last_attempt['stage']==stage and g.last_attempt['finish_reason']==finish
    assert g.last_attempt['usage']=={'prompt_tokens':3,'completion_tokens':2,'total_tokens':5}


def test_service_message_classified_without_echo(monkeypatch):
    t,_=transport(monkeypatch,payload={'error_code':'BAD_REQUEST','message':'Parameter max_tokens is unsupported; secret-token'})
    with pytest.raises(RuntimeError):t({})
    assert t.last_attempt['error_hints']==['max_tokens','unsupported']
    assert 'secret' not in json.dumps(t.last_attempt)
