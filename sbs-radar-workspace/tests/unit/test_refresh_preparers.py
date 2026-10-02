"""Real six-PDF cache-backed staging, no network/model inference."""
from pathlib import Path
from dataclasses import replace
import json
import pytest
ROOT=Path(__file__).resolve().parents[2]


def test_cache_requires_exact_input_and_model_identity():
    from sbs.operations.preparers import VerifiedEmbeddingCache
    cache=VerifiedEmbeddingCache.from_project(ROOT)
    row=cache.records[0]
    assert cache.lookup(tuple(row['input_parts']),cache.identity) is not None
    assert cache.lookup((row['input_parts'][0],row['input_parts'][1]+'x'),cache.identity) is None
    assert cache.lookup(tuple(row['input_parts']),'other-model') is None


def test_real_staging_failure_recovery_and_closure(tmp_path):
    from sbs.operations import RefreshRunner,load_sealed_plan
    from sbs.operations.preparers import build_real_hooks
    config=json.loads((ROOT/'config/genie-pilot-002.json').read_text())
    pairs={c['pair']['pair_id']:c['pair'] for c in config['contexts']}
    plan=replace(load_sealed_plan(ROOT),pairs=tuple(pairs.values()))
    runner=RefreshRunner(plan,tmp_path/'state');runner.bootstrap_capture();before=runner.current()
    hooks=build_real_hooks(ROOT)
    failed=runner.run(run_id='before-publish',force_revalidate=True,hooks=hooks,fail_at='before_publish')
    assert failed['status']=='failed' and runner.current()==before
    out=runner.run(run_id='recovery',force_revalidate=True,hooks=hooks)
    assert out['status']=='published' and out['real_preparation_completed'] is True
    assert out['production_validated'] is False
    release=runner._release();assert set(release['prepared'])=={'SK03','SK04','SK06'}
    artifacts={k:json.loads((runner.root/v['artifact_path']).read_text())['payload'] for k,v in release['prepared'].items()}
    assert len(artifacts['SK04']['records'])==135 and artifacts['SK04']['embedding_calls']==0
    assert len(artifacts['SK03']['comparisons'])==2
    assert len(artifacts['SK06']['bundle']['tables']['provisions'])>135
    assert artifacts['SK03']['structural_evidence_version']==1
    assert artifacts['SK06']['bundle']['snapshot_hash']!=config['snapshot']
    closure=release['prepared']['SK06']['closure'];path=runner.root/next(iter(closure))
    path.chmod(0o644);path.write_bytes(b'tampered')
    with pytest.raises(ValueError,match='INTEGRITY'):runner.current()


def fixture_plan(tmp_path):
    from test_foundation import pdf
    from sbs.operations import SealedPlan,sha,canonical
    entries=[];originals={};hashes={}
    for index in range(2):
        url='https://www.sbs.gob.pe/fixture-'+str(index)+'.pdf';p=tmp_path/('fixture-'+str(index)+'.pdf');p.write_bytes(pdf('NEW FIXTURE TEXT '+str(index)))
        originals[url]=p;hashes[url]=sha(p.read_bytes())
        entries.append(dict(document_id='fixture',family='cybersecurity',url=url,source_kind='normative',synthetic=True))
    manifest={'allowed_hosts':['www.sbs.gob.pe'],'sources':entries}
    pair={'pair_id':'fixture-pair','family':'cybersecurity','before':{'document_id':'fixture','version_id':hashes[entries[0]['url']]},'after':{'document_id':'fixture','version_id':hashes[entries[1]['url']]}}
    return SealedPlan(manifest,originals,hashes,sha(canonical(manifest)),(pair,))


def test_new_exact_input_without_inference_remains_pending(tmp_path):
    from sbs.operations import RefreshRunner
    from sbs.operations.preparers import build_real_hooks
    runner=RefreshRunner(fixture_plan(tmp_path),tmp_path/'state')
    out=runner.run(run_id='new-input',hooks=build_real_hooks(ROOT))
    assert out['status']=='pending_validation'
    assert out['pending_hooks']=={'SK04':'TOKENIZER_PENDING','SK06':'UPSTREAM_PENDING'}
    assert runner.current() is None


def test_adapter_quota_checked_before_call(tmp_path):
    from sbs.operations import RefreshRunner
    from sbs.operations.preparers import build_real_hooks,VerifiedEmbeddingCache
    from sbs.models import TokenCounter
    cache=VerifiedEmbeddingCache.from_project(ROOT)
    class ForbiddenAdapter:
        identity=cache.identity;dimension=cache.dimension
        def embed_documents(self,inputs):raise AssertionError('INFERENCE_FORBIDDEN')
    counter=TokenCounter(cache.tokenizer,cache.revision,cache.identity,lambda parts:3)
    hooks=build_real_hooks(ROOT,embedding_adapter=ForbiddenAdapter(),token_counter=counter,allow_inference=True,max_embedding_calls=0,max_embedding_inputs=2,max_embedding_tokens=20)
    out=RefreshRunner(fixture_plan(tmp_path),tmp_path/'state').run(run_id='quota',hooks=hooks)
    assert out['status']=='pending_validation' and out['pending_hooks']['SK04']=='INFERENCE_QUOTA_EXCEEDED'


def test_plan_pairs_change_invalidates_same_run_and_closure_escapes(tmp_path):
    from sbs.operations import RefreshRunner,verify_closure
    plan=fixture_plan(tmp_path);runner=RefreshRunner(plan,tmp_path/'state');runner.run(run_id='same')
    with pytest.raises(ValueError,match='RUN_PLAN_CONFLICT'):RefreshRunner(replace(plan,pairs=()),runner.root).run(run_id='same')
    with pytest.raises(ValueError,match='CLOSURE_INTEGRITY'):verify_closure(runner.root,{'../fixture-0.pdf':'f'*64})


def test_annotations_for_other_source_are_not_reused(tmp_path):
    from sbs.operations import RefreshRunner
    from sbs.operations.preparers import build_real_hooks
    annotation={'pair_id':'fixture-pair','provision_id':'art1','before':{'document_id':'wrong','version_id':'f'*64},'after':{}}
    out=RefreshRunner(fixture_plan(tmp_path),tmp_path/'state').run(run_id='annotation',hooks=build_real_hooks(ROOT,annotations=[annotation]))
    assert out['pending_hooks']['SK03']=='ANNOTATION_SOURCE_CHANGED' and out['status']=='pending_validation'


def test_validated_annotation_reuses_only_current_literal_span(tmp_path):
    from sbs.operations import RefreshRunner,plan_fingerprint
    from sbs.operations.preparers import build_real_hooks,_current_inputs
    plan=fixture_plan(tmp_path);runner=RefreshRunner(plan,tmp_path/'state');sources,_=runner._capture('current')
    stage=runner.root/'runs/current/stage';stage.mkdir(parents=True)
    ctx={'hook':'SK03','run_id':'current','plan_id':plan.identity,'plan_fingerprint':plan_fingerprint(plan),'pairs':plan.pairs,'state_root':runner.root,'stage':stage,'foundation_root':runner.root/'foundation','sources':sources}
    docs,bundles,closure=_current_inputs(ctx);annotation={'pair_id':'fixture-pair','provision_id':'art1'}
    for side in ('before','after'):
        ref=plan.pairs[0][side];b=bundles[(ref['document_id'],ref['version_id'])];p=b['provisions'][0]
        annotation[side]={**p,'original_sha256':b['sha256'],'quote_raw':p['text']}
    output=build_real_hooks(ROOT,annotations=[annotation])['SK03'](ctx)
    assert output['status']=='validated'
    result=json.loads((stage/output['artifact_path']).read_text())['payload']
    assert len([p for p in result['structural_provisions'] if p['provision_id']=='art1'])==2
    assert result['structural_evidence_version']==1
    assert result['annotation_reuse'][0]['human_gold'] is False
    assert result['comparisons'][-1]['change_set']['pair']==plan.pairs[0]
