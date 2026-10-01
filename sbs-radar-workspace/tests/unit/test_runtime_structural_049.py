"""049 uses frozen real local bytes; no inference or acceptance assertion."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from sbs.runtime import LocalService, create_service, ROOT

PROFILE={'enabled':True,'profile':'structural-development-047-v2'}

def config(tmp_path, value=PROFILE):
    p=tmp_path/'structural.json';p.write_text(json.dumps(value));return p

def test_explicit_profile_loads_real231_preserves_default_and_focus(tmp_path):
    baseline=LocalService()
    s=create_service(structural_config_path=config(tmp_path))
    assert len(baseline.index._rows)==135
    assert len(s.index._rows)==231
    assert s.index.index_hash=='dbf90d1bd8296ac22e07640a5b335cc440e449c8ba8167d94c3272889c5120ce'
    assert s.snapshot!=baseline.snapshot
    assert s.entries==baseline.entries and s.sources==baseline.sources
    assert s.generator is s.embedding is s.reranker is None
    assert s.query_cache==baseline.query_cache
    assert s.structural_metadata['promotion']=='not_approved'
    assert s.catalog()['retrieval_profile']==s.structural_metadata

@pytest.mark.parametrize('value',[{}, {'enabled':True,'profile':'other'}, {'enabled':True,'profile':'structural-development-047-v2','approve':True}, {'enabled':1,'profile':'structural-development-047-v2'}])
def test_bad_config_fails_explicitly(tmp_path,value):
    with pytest.raises(ValueError,match='STRUCTURAL_CONFIG'):
        create_service(structural_config_path=config(tmp_path,value))

def test_structural_profile_not_cloud_or_release_activation(tmp_path):
    p=config(tmp_path)
    with pytest.raises(ValueError,match='STRUCTURAL_LOCAL_ONLY'):create_service(mode='cloud',structural_config_path=p)
    with pytest.raises(ValueError,match='STRUCTURAL_MIXED_BOOTSTRAP'):create_service(config_path=p,structural_config_path=p)

def test_runtime_rag_uses231_and_keeps_counterparts_and_literals(tmp_path):
    s=create_service(structural_config_path=config(tmp_path))
    questions=json.loads((ROOT/'data/retrieval/structural-development-026/questions.json').read_bytes())
    for q in questions:
        ctx=s.entry(q['pair_id'],q['provision_ids'][0])['context']
        out=s.rag(q['question'],ctx)
        assert out['snapshot']==s.snapshot
        assert out['trace']['runtime_retrieval_profile']['index_hash']==s.index.index_hash
        assert out['trace']['runtime_retrieval_profile']['vectors']=='real231_cached'
        ids={r['citation']['citation_id'] for r in s.index._rows}
        assert all(pid in ids for pid,score in out['trace']['vector'])
        assert out['trace']['vector']
        allowed={(ctx['pair'][side]['document_id'],ctx['pair'][side]['version_id']) for side in ('before','after')}
        citations=out['evidence']['citations']
        assert {(c['document_id'],c['version_id']) for c in citations}==allowed
        assert all(s.originals[(c['document_id'],c['version_id'])][c['start']:c['end']]==c['text'] for c in citations)
        assert out['trace']['selected_provision_expansion']['retrieval_strategy']=='structural231_plus_verified_focus_expansion'
    with pytest.raises(ValueError,match='STRUCTURAL_QUERY_NOT_REVIEWED'):s.rag('consulta nueva',ctx)
    forged=deepcopy(ctx);forged['family']='cybersecurity'
    with pytest.raises(ValueError,match='STRUCTURAL_CONTEXT_MISMATCH'):s.rag(questions[-1]['question'],forged)
    with pytest.raises(ValueError,match='GENIE_STRUCTURAL_UNPUBLISHED'):s.initialize_genie()

@pytest.mark.parametrize('target', ['records','index','query','model','pdf','raw','result','record'])
def test_tampered_closure_fails_before_index_construction(tmp_path,monkeypatch,target):
    import shutil
    import sbs.runtime_structural as structural
    candidate=structural.load_profile(ROOT,config(tmp_path))
    clone=tmp_path/'clone';clone.mkdir()
    for name in candidate['closure']:
        dest=clone/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
    targets={'records':structural.BASE+'records.json','index':structural.BASE+'index.json',
             'record':structural.BASE+'record.json','query':'data/retrieval/sk04-real-001/queries-000.json',
             'model':'config/pilot-model-bundle.json'}
    targets['pdf']=next(n for n in candidate['closure'] if n.endswith('.pdf'))
    targets['raw']=next(n for n in candidate['closure'] if n.endswith('/rawtext.txt'))
    targets['result']=next(n for n in candidate['closure'] if n.endswith('/result.json'))
    p=clone/targets[target];p.write_bytes(p.read_bytes()+b' ')
    def forbidden(*a,**kw):raise AssertionError('index constructed before source integrity validation')
    monkeypatch.setattr(structural,'LocalIndex',forbidden)
    with pytest.raises(ValueError,match='ANCHORED_INPUT_HASH|STRUCTURAL_SOURCE_CLOSURE'):
        structural.load_profile(clone,config(tmp_path))


def test_failed_candidate_does_not_mutate_previous_service_or_sessions(tmp_path):
    previous=LocalService();previous.sessions['retained']={'sentinel':True}
    old=(previous.snapshot,previous.index.index_hash,deepcopy(previous.sessions))
    with pytest.raises(ValueError):create_service(structural_config_path=config(tmp_path,{'enabled':True,'profile':'invalid'}))
    assert old==(previous.snapshot,previous.index.index_hash,previous.sessions)
    s=create_service(structural_config_path=config(tmp_path))
    assert s.session_key('same-subject','same-session')!=previous.session_key('same-subject','same-session')
    with pytest.raises(ValueError,match='STRUCTURAL_MIXED_PROMOTION'):s.promote_release(tmp_path,pointer={})
