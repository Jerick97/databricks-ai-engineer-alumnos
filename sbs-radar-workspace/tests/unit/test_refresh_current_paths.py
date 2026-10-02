"""Static path substitution regressions for SK09 HOOKS-01; local fixtures."""
import json
import pytest
from sbs.operations import RefreshRunner, SealedPlan, sha, canonical


@pytest.mark.parametrize('target', ['pointer', 'release', 'artifact', 'artifact_parent'])
def test_current_rejects_same_bytes_symlink(tmp_path, target):
    root=tmp_path/'state';root.mkdir()
    stage=root/'stage';stage.mkdir()
    artifact=stage/'data.json';artifact.write_text('{"fixture":true}')
    release_id='a'*64
    directory=root/'releases'/release_id;directory.mkdir(parents=True)
    release=directory/'release.json'
    release.write_text(json.dumps({'prepared':{'SK06':{'artifact_path':'stage/data.json','sha256':sha(artifact.read_bytes()),'closure':{}}}}))
    pointer=root/'current.json'
    pointer.write_text(json.dumps({'release_id':release_id,'sha256':sha(release.read_bytes())}))
    manifest={'sources':[]}
    runner=RefreshRunner(SealedPlan(manifest,{}, {},sha(canonical(manifest))),root)
    assert runner.current()['release_id']==release_id
    path={'pointer':pointer,'release':release,'artifact':artifact,'artifact_parent':stage}[target]
    preserved=path.with_name(path.name+'.original')
    path.rename(preserved);path.symlink_to(preserved.name,target_is_directory=preserved.is_dir())
    with pytest.raises(ValueError, match='SYMLINK|INTEGRITY|POINTER'):
        runner.current()
