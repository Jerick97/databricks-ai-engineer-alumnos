"""Explicit candidate identity; no model inference in unit tests."""
import pytest
from sbs.models.reranker import execution_identity, WEIGHTS


def spec():
    return {'weights':'onnx/model_quint8_avx2.onnx','engine':'onnxruntime',
            'provider':'CPUExecutionProvider','system':'Linux','architecture':'x86_64'}


def test_candidate_selects_explicit_weights_and_records_actual_backend():
    got=execution_identity({'execution':spec()},system='Linux',machine='AMD64',ort_version='1.26.0')
    assert got['weights']==spec()['weights']
    assert got['architecture']=='x86_64'
    assert got['onnxruntime_version']=='1.26.0'
    assert got['selection']=='explicit'


def test_legacy_preserves_selection_but_records_actual_platform():
    got=execution_identity({},system='Linux',machine='x86_64',ort_version='1.26.0')
    assert got['weights']==WEIGHTS
    assert got['selection']=='legacy_default'
    assert got['system']=='Linux'


@pytest.mark.parametrize('key,value',[('architecture','arm64'),('system','Darwin'),('provider','CUDAExecutionProvider'),('engine','pytorch'),('weights','../model.onnx')])
def test_explicit_candidate_rejects_runtime_or_weight_mismatch(key,value):
    s=spec();s[key]=value
    with pytest.raises(ValueError,match='unsupported_execution_identity|execution_target_mismatch'):
        execution_identity({'execution':s},system='Linux',machine='x86_64',ort_version='1.26.0')


def test_partial_execution_is_not_silently_defaulted():
    with pytest.raises(ValueError,match='unsupported_execution_identity'):
        execution_identity({'execution':{'architecture':'x86_64'}},system='Linux',machine='x86_64',ort_version='1.26.0')


def test_from_manifest_passes_selected_file_to_session_and_exposes_identity(tmp_path, monkeypatch):
    import hashlib, json
    import onnxruntime as ort
    import platform
    from tokenizers import Tokenizer, models
    from sbs.models.reranker import LocalOnnxReranker, REPO_ID
    token=Tokenizer(models.WordLevel({'[UNK]':0},unk_token='[UNK]'))
    contents={'config.json':json.dumps({'max_position_embeddings':512,'num_labels':1}),
              'tokenizer_config.json':json.dumps({'model_max_length':512}),
              'tokenizer.json':token.to_str(), spec()['weights']:'fake weights'}
    files={}
    for name,data in contents.items():
        path=tmp_path/name;path.parent.mkdir(exist_ok=True);path.write_text(data)
        files[name]={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    calls=[]
    monkeypatch.setattr(platform,'system',lambda:'Linux')
    monkeypatch.setattr(platform,'machine',lambda:'x86_64')
    monkeypatch.setattr(ort,'InferenceSession',lambda path,**kw:calls.append((path,kw)) or object())
    manifest={'repo_id':REPO_ID,'revision':'a'*40,'files':files,'execution':spec()}
    model=LocalOnnxReranker.from_manifest(manifest)
    assert calls[0][0]==files[spec()['weights']]['path']
    assert calls[0][1]['providers']==['CPUExecutionProvider']
    assert model.execution_identity['weights_sha256']==files[spec()['weights']]['sha256']
    calls.clear();manifest['execution']['architecture']='arm64'
    with pytest.raises(ValueError,match='execution_target_mismatch'):
        LocalOnnxReranker.from_manifest(manifest)
    assert calls==[]
