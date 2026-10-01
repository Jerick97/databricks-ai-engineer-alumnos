import copy,json,hashlib
from types import SimpleNamespace
import pytest
from sbs.models.generation_selection import load_selection
from sbs.conversation.databricks import DatabricksGenerator,SingleShotTransport

def fixture(tmp_path):
    obs={'endpoint':'databricks-qwen3-next-80b-a3b-instruct','http_status':200,'model':'qwen3-next-instruct-091725'}
    p=tmp_path/'observation.json';p.write_text(json.dumps(obs))
    config={'status':'selected_for_controlled_trial','endpoint':obs['endpoint'],'expected_response_model':obs['model'],'observation_path':'observation.json','observation_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'max_requests':4,'max_output_tokens':5000,'max_input_chars':120000}
    (tmp_path/'selection.json').write_text(json.dumps(config));return config

def test_selection_verified(tmp_path):
    c=fixture(tmp_path);assert load_selection(tmp_path,'selection.json')==c
@pytest.mark.parametrize('change',[{'status':'pending'},{'expected_response_model':'other'},{'endpoint':'other'},{'observation_sha256':'0'*64},{'max_requests':5},{'max_input_chars':0}])
def test_selection_rejects(tmp_path,change):
    c=fixture(tmp_path);c.update(change);(tmp_path/'selection.json').write_text(json.dumps(c))
    with pytest.raises(ValueError):load_selection(tmp_path,'selection.json')
def test_missing_config_does_not_choose_legacy(tmp_path):
    with pytest.raises(ValueError,match='generation_unconfigured'):load_selection(tmp_path,'missing.json')
def test_transport_selected_endpoint():
    t=SingleShotTransport(SimpleNamespace(config=SimpleNamespace(host='https://example.com')),endpoint='databricks-qwen3-next-80b-a3b-instruct');assert t.url.endswith('/databricks-qwen3-next-80b-a3b-instruct/invocations')
    with pytest.raises(ValueError):SingleShotTransport(SimpleNamespace(config=SimpleNamespace(host='https://example.com')),endpoint='../escape')
def test_model_identity_and_input_bound_before_transport():
    calls=[]
    def t(body):calls.append(body);return {'model':'wrong','choices':[{'finish_reason':'stop','message':{'content':'{}'}}]}
    g=DatabricksGenerator(transport=t,max_requests=4,max_tokens=5000,endpoint='selected',expected_response_model='expected',max_input_chars=10)
    with pytest.raises(ValueError,match='input_limit'):g({'messages':[{'role':'user','content':'x'*11}]})
    assert not calls
    with pytest.raises(ValueError,match='model_mismatch'):g({'messages':[{'role':'user','content':'ok'}]})
    assert len(calls)==1
