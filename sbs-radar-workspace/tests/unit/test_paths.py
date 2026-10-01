from pathlib import Path
import hashlib
import pytest
from sbs.paths import project_path,resolve_model_manifest

HISTORICAL='/Users/macdenix/clawd/projects/sbs-genie-e2e'

def test_only_known_historical_root_rebased_and_symlinks_contained(tmp_path):
    assert project_path(tmp_path,HISTORICAL+'/data/a.pdf')==tmp_path/'data/a.pdf'
    assert project_path(tmp_path,'data/a.pdf')==tmp_path/'data/a.pdf'
    with pytest.raises(ValueError): project_path(tmp_path,'/etc/passwd')
    with pytest.raises(ValueError): project_path(tmp_path,'../../passwd')
    (tmp_path/'escape').symlink_to('/tmp')
    with pytest.raises(ValueError): project_path(tmp_path,'escape/a.pdf')

def fixture(tmp_path):
    revision='a'*40; content=b'pinned model'; digest=hashlib.sha256(content).hexdigest()
    model=tmp_path/'data/models/acme--model'/revision/'onnx/model.onnx'
    model.parent.mkdir(parents=True); model.write_bytes(content)
    manifest={'repo_id':'acme/model','revision':revision,'files':{'onnx/model.onnx':{'path':'/old/home/weights','sha256':digest,'bytes':len(content)}}}
    return model,manifest

def test_portable_manifest_resolves_pinned_files_without_mutating_seals(tmp_path):
    model,manifest=fixture(tmp_path)
    result=resolve_model_manifest(manifest,root=tmp_path)
    assert result['files']['onnx/model.onnx']['path']==str(model)
    assert manifest['files']['onnx/model.onnx']['path']=='/old/home/weights'
    model.write_bytes(b'tampered')
    with pytest.raises(ValueError,match='hash'): resolve_model_manifest(manifest,root=tmp_path)

def test_explicit_hf_cache_only_and_reject_unpinned_or_traversal(tmp_path):
    model,manifest=fixture(tmp_path); content=model.read_bytes(); model.unlink()
    cache=tmp_path/'cache'; original=cache/'models--acme--model/snapshots'/manifest['revision']/'onnx/model.onnx'
    original.parent.mkdir(parents=True);original.write_bytes(content)
    with pytest.raises(FileNotFoundError):resolve_model_manifest(manifest,root=tmp_path)
    assert resolve_model_manifest(manifest,root=tmp_path,cache_root=cache)['files']['onnx/model.onnx']['path']==str(original)
    manifest['files']['../../secret']=manifest['files'].pop('onnx/model.onnx')
    with pytest.raises(ValueError):resolve_model_manifest(manifest,root=tmp_path,cache_root=cache)


def test_model_manifest_requires_revision_hash_and_cache_containment(tmp_path):
    model,manifest=fixture(tmp_path)
    manifest['revision']='main'
    with pytest.raises(ValueError,match='unpinned'):resolve_model_manifest(manifest,root=tmp_path)
    manifest['revision']='a'*40
    outside=tmp_path/'outside';outside.mkdir()
    root=tmp_path/'new-release';root.mkdir()
    cache=tmp_path/'hf';candidate=cache/'models--acme--model/snapshots'/manifest['revision']/'onnx/model.onnx'
    candidate.parent.mkdir(parents=True);candidate.symlink_to(model)
    with pytest.raises(ValueError,match='outside'):resolve_model_manifest(manifest,root=root,cache_root=cache)
