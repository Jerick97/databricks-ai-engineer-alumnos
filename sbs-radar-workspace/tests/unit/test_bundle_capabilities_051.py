"""051: operational capabilities excluded by placement, not workflow number."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tarfile
import pytest


def builder(root):
    path=Path(__file__).resolve().parents[2]/'deployment/build_bundle.py'
    spec=importlib.util.spec_from_file_location('bundle051',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.ROOT=root;return module


@pytest.mark.parametrize('models',[False,True])
def test_live_capabilities_excluded_without_losing_configs_plans_history(tmp_path,models):
    excluded=['deployment/phase-s-017-authorization.json',
              'deployment/phase-s-050-authorization.json',
              'deployment/phase-s-050-corrected-authorization.json',
              'deployment/another-workflow-authorization.json',
              'deployment/state/phase-s-050/intent.json']
    retained=['deployment/phase-s-050-config.json','deployment/phase-s-050-plan.json',
              'deployment/phase-s-050-authorization-template.json',
              'deployment/phase-s-050-authorization.json.example',
              'deployment/phase-s-050-authorization-history.json',
              'deployment/history/phase-s-050-authorization.json',
              'deployment/stateful/config.json','deployment/state.json',
              'docs/phase-s-050-authorization.json','runs/sk12-notebook-historical.json',
              'data/models/model.bin']
    content={n:('synthetic051 '+n).encode() for n in excluded+retained}
    for name,raw in content.items():
        p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    module=builder(tmp_path);module.build(include_models=models)
    suffix='-models' if models else ''
    manifest=json.loads((tmp_path/f'runs/sk12-release-manifest{suffix}.json').read_bytes())
    assert not set(excluded)&set(manifest['files'])
    expected=set(retained)-(set() if models else {'data/models/model.bin'})
    assert set(manifest['files'])==expected
    with tarfile.open(tmp_path/f'runs/sk12-review-bundle{suffix}.tar.gz') as archive:
        assert set(archive.getnames())=={'sbs-radar/'+n for n in expected}
        for n in expected:
            raw=archive.extractfile('sbs-radar/'+n).read()
            assert raw==content[n]
            assert hashlib.sha256(raw).hexdigest()==manifest['files'][n]
    assert all((tmp_path/n).read_bytes()==raw for n,raw in content.items())


def test_file_selection_is_read_only_and_matches_build_policy(tmp_path,monkeypatch):
    (tmp_path/'deployment').mkdir();(tmp_path/'runs').mkdir()
    (tmp_path/'deployment/live-authorization.json').write_text('synthetic capability')
    (tmp_path/'deployment/live-config.json').write_text('synthetic config')
    module=builder(tmp_path)
    assert hasattr(module,'selected_paths'), 'builder needs a shared nonwriting file-selection function'
    def no_tar(*a,**kw):raise AssertionError('selection must not build archive')
    monkeypatch.setattr(module.tarfile,'open',no_tar)
    assert {str(p.relative_to(tmp_path)) for p in module.selected_paths()}=={'deployment/live-config.json'}
    assert list((tmp_path/'runs').iterdir())==[]

@pytest.mark.parametrize('models',[False,True])
def test_opt_in_profile049_has_complete_frozen_closure_without_default_activation(tmp_path,models):
    root=Path(__file__).resolve().parents[2]
    module=builder(root)
    import inspect
    assert 'include_structural_profile' in inspect.signature(module.selected_paths).parameters, 'seven missing profile049 inputs need explicit optional packaging'
    evidence=json.loads((root/'runs/sk07-runtime-structural-049-runtime-evidence.json').read_bytes())
    required=set(evidence['queries'][0]['result']['trace']['runtime_retrieval_profile']['closure'])|{'src/sbs/runtime.py','src/sbs/runtime_structural.py','runs/sk07-runtime-structural-049-config.json'}
    defaults={p.relative_to(root).as_posix() for p in module.selected_paths(models)}
    selected={p.relative_to(root).as_posix() for p in module.selected_paths(models,include_structural_profile=True)}
    assert len(required-defaults)==7
    assert required<=selected
    assert selected-defaults==required-defaults
    assert 'deployment/phase-s-050-authorization.json' not in selected
    assert 'deployment/phase-s-050-corrected-authorization.json' not in selected
    # Copy only selected closure to isolated root; real loader pins must succeed.
    for name in required:
        target=tmp_path/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((root/name).read_bytes())
    from sbs.runtime_structural import load_profile
    profile=load_profile(tmp_path,tmp_path/'runs/sk07-runtime-structural-049-config.json')
    assert len(profile['index']._rows)==231


def test_optional_profile_missing_input_fails_before_any_build(tmp_path):
    import inspect
    module=builder(tmp_path)
    assert 'include_structural_profile' in inspect.signature(module.selected_paths).parameters
    with pytest.raises(ValueError,match='STRUCTURAL_PROFILE_FILE_MISSING'):
        module.selected_paths(include_structural_profile=True)
    assert list(tmp_path.iterdir())==[]
