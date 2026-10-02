"""Contained project rebasing and pinned model resolution. No network or credential access."""
from copy import deepcopy
import hashlib
from pathlib import Path
import re

HISTORICAL_ROOT=Path('/Users/macdenix/clawd/projects/sbs-genie-e2e')

def project_path(root, path):
    root=Path(root).resolve(); path=Path(path)
    if path.is_absolute():
        if path.is_relative_to(root): pass
        elif path.is_relative_to(HISTORICAL_ROOT):path=root/path.relative_to(HISTORICAL_ROOT)
        else:raise ValueError('unrecognized_external_project_path')
    else:path=root/path
    result=path.resolve()
    if not result.is_relative_to(root):raise ValueError('path_outside_project')
    return result

def _model_identity(manifest):
    repo=manifest.get('repo_id',''); revision=manifest.get('revision','')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo) or any(p in {'.','..'} for p in repo.split('/')):
        raise ValueError('invalid_model_repo')
    if not re.fullmatch(r'[0-9a-f]{40}',revision):raise ValueError('unpinned_model_revision')
    if not isinstance(manifest.get('files'),dict) or not manifest['files']:raise ValueError('missing_model_files')
    return repo.replace('/','--'),revision

def model_relative_path(manifest, filename):
    slug,revision=_model_identity(manifest); name=Path(filename)
    if name.is_absolute() or '..' in name.parts or not name.parts:raise ValueError('invalid_model_filename')
    return Path('data/models')/slug/revision/name

def file_sha256(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda:handle.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()

def resolve_model_manifest(manifest, *, root, cache_root=None):
    """Return a detached absolute-path map. Root package wins; explicit HF cache optional.

    Historical external paths inside manifests are ignored. Every selected file is
    verified; a corrupt package file fails closed instead of silently using cache.
    """
    slug,revision=_model_identity(manifest); result=deepcopy(manifest)
    for name,artifact in result['files'].items():
        relative=model_relative_path(manifest,name)
        selected=project_path(root,relative)
        if not selected.is_file() and cache_root is not None:
            cache=Path(cache_root).resolve()
            candidate=(cache/('models--'+slug)/'snapshots'/revision/name).resolve()
            if not candidate.is_relative_to(cache):raise ValueError('model_cache_path_outside_root')
            selected=candidate
        if not selected.is_file():raise FileNotFoundError('pinned_model_artifact_missing:'+name)
        expected=artifact.get('sha256','')
        if not re.fullmatch(r'[0-9a-f]{64}',expected) or file_sha256(selected)!=expected:raise ValueError('model_artifact_hash_mismatch:'+name)
        if 'bytes' in artifact and selected.stat().st_size!=artifact['bytes']:raise ValueError('model_artifact_size_mismatch:'+name)
        artifact['path']=str(selected)
    return result
