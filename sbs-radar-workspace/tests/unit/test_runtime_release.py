"""Offline release promotion; real cached PDFs/vectors, no provider calls."""
from pathlib import Path
from dataclasses import replace
import json
import pytest
from sbs.runtime import LocalService
ROOT=Path(__file__).resolve().parents[2]

@pytest.fixture(scope='module')
def prepared(tmp_path_factory):
    from sbs.operations import RefreshRunner,load_sealed_plan
    from sbs.operations.preparers import build_real_hooks
    config=json.loads((ROOT/'config/genie-pilot-002.json').read_text())
    pairs={c['pair']['pair_id']:c['pair'] for c in config['contexts']}
    pairs=list(pairs.values());pairs[0]['pair_id']='release-cyber-new'
    runner=RefreshRunner(replace(load_sealed_plan(ROOT),pairs=tuple(pairs)),tmp_path_factory.mktemp('release')/'state')
    result=runner.run(run_id='runtime-014',force_revalidate=True,hooks=build_real_hooks(ROOT))
    assert result['status']=='published'
    return runner

def test_real_release_dynamic_pages_reach_lookup_retrieval_comparison(prepared):
    service=LocalService.from_release(prepared.root,pointer=prepared.current())
    pair=next(p for p in service.catalog()['pairs'] if p['id']=='release-cyber-new')
    assert len(pair['provisions'])>1 and all(p['id']!='art20.3' for p in pair['provisions'])
    focus=pair['provisions'][0]['id'];entry=service.entry(pair['id'],focus)
    display=service.comparison(pair['id'],focus)
    assert display['before']['text']==entry['before']['text']
    question=next(iter(service.query_cache));out=service.rag(question,entry['context'])
    assert out['snapshot']==service.snapshot
    assert entry['before']['citation_id'] in {c['citation_id'] for c in out['evidence']['citations']}
    result=service.compare('antes y después',entry['context'])
    assert result['change_set']['pair']['pair_id']=='release-cyber-new'
    assert result['status']=='partial' and service.generator is None
    with pytest.raises(ValueError,match='GENIE_RELEASE_UNPUBLISHED'):service.initialize_genie()

def test_failed_promotion_preserves_previous_and_session_partition(prepared,tmp_path):
    service=LocalService();old=service.snapshot
    service.sessions[('user','same',old)]='previous-session'
    receipt=service.promote_release(prepared.root,pointer=prepared.current())
    assert receipt['previous_snapshot']==old and service.snapshot!=old
    assert service.session_key('user','same')!=('user','same',old)
    before=service.catalog();snapshot=service.snapshot
    with pytest.raises(ValueError):service.promote_release(tmp_path,pointer={'release_id':'0'*64,'sha256':'0'*64})
    assert service.snapshot==snapshot and service.catalog()==before

def test_hash_model_and_symlink_fail_before_swap(prepared,tmp_path):
    import shutil
    from sbs.operations.runtime_release import load_release
    from sbs.operations import sha
    service=LocalService();old=service.snapshot
    with pytest.raises(ValueError,match='MODEL_INCOMPATIBLE'):
        load_release(prepared.root,pointer=prepared.current(),model_identity='other')
    root=tmp_path/'copy';shutil.copytree(prepared.root,root)
    release=prepared._release();item=release['prepared']['SK04'];path=root/item['artifact_path']
    path.chmod(0o644);path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(ValueError):service.promote_release(root,pointer=prepared.current())
    assert service.snapshot==old
    link=tmp_path/'symlink';link.symlink_to(prepared.root,target_is_directory=True)
    with pytest.raises(ValueError,match='SYMLINK'):service.promote_release(link,pointer=prepared.current())
    assert service.snapshot==old

def test_files_materialization_is_read_only_and_corruption_rejected(prepared,tmp_path):
    from test_volume_artifacts import Files,store
    from sbs.operations.runtime_release import materialize_release
    from sbs.genie import digest
    service=LocalService.from_release(prepared.root,pointer=prepared.current())
    files=Files();volume=store(files)
    staged=volume.stage('014',prepared.root,service.release_metadata['closure'])
    receipt={'release_id':staged['release_id'],'manifest_path':staged['manifest_path'],'manifest_sha256':staged['release_id'],'artifacts_sha256':digest(staged['artifacts'])}
    writes=list(files.calls)
    local=materialize_release(volume,receipt,tmp_path/'downloads')
    recovered=LocalService.from_release(local['state_root'],pointer=local['pointer'])
    assert recovered.snapshot==service.snapshot and recovered.catalog()==service.catalog()
    assert files.calls==writes
    target=next(p for p in files.data if p.endswith('.pdf'));files.data[target]=b'corrupt'
    with pytest.raises(ValueError):materialize_release(volume,receipt,tmp_path/'bad')
    assert files.calls==writes

def test_active_factory_config_no_frozen_fallback(prepared,tmp_path,monkeypatch):
    import sbs.runtime as runtime
    config=tmp_path/'runtime-release.json'
    config.write_text(json.dumps({'enabled':True,'state_root':'missing-runtime-release','pointer':prepared.current()}))
    with pytest.raises(ValueError):runtime.create_service(config)
    config.write_text(json.dumps({'enabled':True,'state_root':'../escape','pointer':prepared.current()}))
    with pytest.raises(ValueError,match='path_invalid'):runtime.create_service(config)
    config.write_text(json.dumps({'enabled':False}))
    assert runtime.create_service(config).snapshot==runtime.LocalService().snapshot

def test_validated_annotations_preserved_as_separate_focus(tmp_path):
    from sbs.operations import RefreshRunner,load_sealed_plan
    from sbs.operations.preparers import build_real_hooks
    from sbs.comparison.pilot import by_provision
    config=json.loads((ROOT/'config/genie-pilot-002.json').read_text())
    pairs={c['pair']['pair_id']:c['pair'] for c in config['contexts']}
    citations={**json.loads((ROOT/'runs/astra-normative-review.json').read_text())['citations'],**json.loads((ROOT/'runs/astra-normative-review-003.json').read_text())['citations']}
    annotations=[{'pair_id':pair,'provision_id':provision,'before':citations[before],'after':citations[after]} for pair,provision,before,after in [('cyber-504','art20.3','v4-art20-3','v5-art20-3'),('market-3274','art27','market-v7-art27','market-v8-art27'),('market-3274','art29.1.4','market-v7-art29-1','market-v8-art29-1')]]
    runner=RefreshRunner(replace(load_sealed_plan(ROOT),pairs=tuple(pairs.values())),tmp_path/'annotated')
    result=runner.run(run_id='with-annotations',force_revalidate=True,hooks=build_real_hooks(ROOT,annotations=annotations))
    assert result['status']=='published'
    service=LocalService.from_release(runner.root,pointer=runner.current())
    context=service.entry('cyber-504','art20.3')['context']
    result=service.compare('antes',context)
    assert service.release_metadata['annotation_count']==3
    assert result['changes'] and all(c['materiality']=='not_assessed' for c in result['changes'])
    assert service._comparison_item(context)['focus_origin']=='SK03_AI_annotated_subset'

def test_added_family_content_is_installed_not_just_snapshot(prepared,tmp_path):
    from sbs.operations import RefreshRunner,load_sealed_plan,canonical,sha
    from sbs.operations.preparers import build_real_hooks
    plan=load_sealed_plan(ROOT)
    entries=[s for s in plan.manifest['sources'] if s['family']=='cybersecurity']
    manifest={**plan.manifest,'sources':entries};urls={s['url'] for s in entries}
    pair=next(p for p in prepared.plan.pairs if p['family']=='cybersecurity')
    plan=replace(plan,manifest=manifest,originals={k:v for k,v in plan.originals.items() if k in urls},hashes={k:v for k,v in plan.hashes.items() if k in urls},identity=sha(canonical(manifest)),pairs=(pair,))
    runner=RefreshRunner(plan,tmp_path/'one-family')
    assert runner.run(run_id='cyber-only',force_revalidate=True,hooks=build_real_hooks(ROOT))['status']=='published'
    service=LocalService.from_release(runner.root,pointer=runner.current())
    old_ids=set(service.originals);old_count=len(service.index._rows)
    assert all(row['family']=='cybersecurity' for row in service.index._rows)
    with pytest.raises(KeyError):service.entry('market-3274','page-1')
    service.promote_release(prepared.root,pointer=prepared.current())
    assert len(service.index._rows)>old_count and set(service.originals)>old_ids
    market=next(p for p in service.pairs if p['family_id']=='market_conduct');focus=market['provisions'][0]['id']
    context=service.entry(market['id'],focus)['context']
    evidence=service.rag(next(iter(service.query_cache)),context)['evidence']
    assert evidence['citations'] and all((c['document_id'],c['version_id']) not in old_ids for c in evidence['citations'])
    display=service.comparison(market['id'],focus)
    assert display['before']['text'] and display['after']['text']
    assert service.compare('antes',context)['change_set']['pair']==context['pair']
