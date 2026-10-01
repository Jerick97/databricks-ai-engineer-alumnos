import inspect,json
from pathlib import Path
import pytest
from sbs.runtime import LocalService
from sbs.models.generation_selection import load_selection

def test_runtime_explicit_server_path_before_any_sdk(monkeypatch):
    assert 'generation_selection_path' in inspect.signature(LocalService).parameters
    service=LocalService.__new__(LocalService);service.generator=None;service.generation_selection_path='config/generation-selection-077.json'
    calls=[]
    def selection(root,path):calls.append(path);raise ValueError('stop_before_sdk')
    monkeypatch.setattr('sbs.models.generation_selection.load_selection',selection)
    with pytest.raises(ValueError,match='stop_before_sdk'):service.initialize_models()
    assert calls==['config/generation-selection-077.json']

def test_default_073_unchanged_and_candidate077_pinned():
    root=Path(__file__).resolve().parents[2]
    assert load_selection(root)['endpoint']=='databricks-qwen3-next-80b-a3b-instruct'
    candidate=load_selection(root,'config/generation-selection-077.json')
    assert candidate['endpoint']=='databricks-meta-llama-3-3-70b-instruct'
    assert candidate['expected_response_model']=='meta-llama-3.3-70b-instruct-121024'
    assert candidate['max_output_tokens']==5000 and candidate['max_requests']==4
