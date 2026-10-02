"""Operational state is not portable authorization; synthetic temporary tree only."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tarfile
import pytest

@pytest.mark.parametrize('include_models', [False, True])
def test_snapshot_excludes_origin_admission_preserves_config_and_history(tmp_path, capsys, include_models):
    source = Path(__file__).resolve().parents[2] / 'deployment/build_bundle.py'
    spec = importlib.util.spec_from_file_location('bundle039', source)
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    builder.ROOT = tmp_path
    excluded = ['deployment/phase-s-017-authorization.json',
                'deployment/state/phase-s-017/intent.json',
                'deployment/state/phase-s-017/nested/result.json',
                'deployment/state/other-run/journal.json']
    retained = ['deployment/phase-s-017-config.json',
                'deployment/phase-s-017-authorization-template.json',
                'deployment/phase-s-017-authorization.json.example',
                'deployment/stateful/config.json',
                'deployment/state.json',
                'docs/phase-s-017-authorization.json',
                'runs/sk12-notebook-historical.json',
                'data/models/model.bin']
    contents = {p: ('synthetic fixture ' + p).encode() for p in excluded + retained}
    for name, raw in contents.items():
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(raw)
    before = {p: (tmp_path/p).read_bytes() for p in contents}
    builder.build(include_models=include_models)
    suffix = '-models' if include_models else ''
    manifest = json.loads((tmp_path/f'runs/sk12-release-manifest{suffix}.json').read_text())
    assert not set(excluded) & manifest['files'].keys()
    expected = set(retained) - (set() if include_models else {'data/models/model.bin'})
    assert set(manifest['files']) == expected
    with tarfile.open(tmp_path/f'runs/sk12-review-bundle{suffix}.tar.gz') as archive:
        assert set(archive.getnames()) == {'sbs-radar/'+p for p in expected}
        for name in expected:
            raw = archive.extractfile('sbs-radar/'+name).read()
            assert raw == contents[name]
            assert hashlib.sha256(raw).hexdigest() == manifest['files'][name]
    assert before == {p: (tmp_path/p).read_bytes() for p in contents}
