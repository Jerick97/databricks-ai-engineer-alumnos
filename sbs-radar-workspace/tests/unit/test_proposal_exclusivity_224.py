"""Transport isolation checks; synthetic model responses do not prove semantic repair."""
from pathlib import Path
import importlib.util,json
ROOT=Path(__file__).resolve().parents[2]
def load(path,name):
    s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
baseline=load('deployment/state/incremental-package214/delta/src/sbs/conversation/hybrid_125.py','sbs.conversation.baseline224')
candidate=load('deployment/overlay224/src/sbs/conversation/hybrid_125.py','sbs.conversation.candidate224')
f=load('tests/unit/test_hybrid_125.py','fixtures224')
r=load('tests/unit/test_qwen_trial_110.py','raw224')
def execute(kind,path,request):
    old,raw,capture=r.make(path,f.proposal_response());g=kind(old.delegate,path,ROOT);result=g(request);return result,raw.calls

def test_policy_is_only_change_in_real_transport_payload(tmp_path):
    request=f.source(3);source=json.dumps(request,sort_keys=True)
    old,old_calls=execute(baseline.HybridGenerator,tmp_path/'old',request)
    new,new_calls=execute(candidate.HybridGenerator,tmp_path/'new',request)
    assert json.dumps(request,sort_keys=True)==source and old==new
    assert len(old_calls)==len(new_calls)==1
    old_prompt=old_calls[0]['messages'][0]['content'];new_prompt=new_calls[0]['messages'][0]['content']
    assert new_prompt!=old_prompt
    assert 'No añadas una recapitulación' in new_prompt
    assert 'como concurrente con el mandato principal' in new_prompt
    new_calls[0]['messages'][0]['content']=old_prompt
    assert new_calls==old_calls

def test_extraction_stays_identical_without_model_calls(tmp_path):
    old,oc=execute(baseline.HybridGenerator,tmp_path/'old',f.source())
    new,nc=execute(candidate.HybridGenerator,tmp_path/'new',f.source())
    assert old==new and oc==nc==[]
