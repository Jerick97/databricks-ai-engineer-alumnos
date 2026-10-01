"""Real sealed local sources/cache through preparation, promotion and HTTP; no models."""
from pathlib import Path
from dataclasses import replace
import json
import pytest
from fastapi.testclient import TestClient
from sbs.operations import RefreshRunner,load_sealed_plan
from sbs.operations.preparers import build_real_hooks
from sbs.runtime import LocalService
from sbs.webapp import create_app
from sbs.contracts import validate_contract
ROOT=Path(__file__).resolve().parents[2]

@pytest.fixture(scope='module')
def structural_release(tmp_path_factory):
 config=json.loads((ROOT/'config/genie-pilot-002.json').read_text());pairs={x['pair']['pair_id']:x['pair'] for x in config['contexts']}
 root=tmp_path_factory.mktemp('structural').resolve()/'state'
 runner=RefreshRunner(replace(load_sealed_plan(ROOT),pairs=tuple(pairs.values())),root)
 assert runner.run(run_id='structural-022',force_revalidate=True,hooks=build_real_hooks(ROOT))['status']=='published'
 return runner

def payload(runner,key):
 row=runner._release()['prepared'][key]
 return json.loads((runner.root/row['artifact_path']).read_text())['payload']

def test_preparation_persists_wrappers_and_exact_cached_page_strategy(structural_release):
 c=payload(structural_release,'SK03');r=payload(structural_release,'SK04');g=payload(structural_release,'SK06')
 assert c['structural_evidence_version']==1 and len(c['structural_wrappers'])==2
 assert r['embedding_calls']==0 and len(r['records'])==135
 assert g['curation_config']['structural_evidence_sha256']
 assert len(g['bundle']['tables']['provisions'])>135

def test_release_http_evidence_closed_contract_with_metadata(structural_release):
 service=LocalService.from_release(structural_release.root,pointer=structural_release.current())
 pair=service.catalog()['pairs'][0];focus=next(p for p in pair['provisions'] if p.get('evidence_origin')=='SK03_structural_heuristic')
 client=TestClient(create_app(service));response=client.get('/api/comparison',params={'pair_id':pair['id'],'provision_id':focus['id']})
 assert response.status_code==200;out=response.json()
 assert out['alignment_provenance']['method']=='heuristic_textual_correspondence'
 evidence=out['evidence'];assert validate_contract('EvidencePack',evidence)['valid']
 assert all('pages' not in c and 'synthetic' not in c for c in evidence['citations'])
 metadata=out['citation_metadata'];assert all(c['citation_id'] in metadata for c in evidence['citations'])
 for c in evidence['citations']:
  assert service.originals[(c['document_id'],c['version_id'])][c['start']:c['end']]==c['text']
  assert metadata[c['citation_id']]['pages']
 assert out['evidence_context']['global_limitations']
 assert out['derived_comparison']['before']['citable'] is False
 assert service.release_metadata['semantic_vectors']=='pending_not_built'
 with pytest.raises(ValueError,match='GENIE_RELEASE_UNPUBLISHED'):service.initialize_genie()

def test_rag_expands_structural_evidence_without_changing_index(structural_release):
 s=LocalService.from_release(structural_release.root,pointer=structural_release.current())
 p=s.pairs[0];focus=next(x for x in p['provisions'] if x.get('evidence_origin')=='SK03_structural_heuristic')
 e=s.entry(p['id'],focus['id']);r=s.rag(next(iter(s.query_cache)),e['context'])
 assert validate_contract('EvidencePack',r['evidence'])['valid']
 assert r['trace']['selected_provision_expansion']['origin']=='SK03_structural_heuristic'
 assert r['trace']['selected_provision_expansion']['retrieval_strategy']=='cached_raw_pages_plus_structural_expansion'
 assert r['evidence_context']['global_limitations'] and r['citation_metadata']

def test_legacy_raw_release_still_loads(tmp_path):
 config=json.loads((ROOT/'config/genie-pilot-002.json').read_text());pairs={x['pair']['pair_id']:x['pair'] for x in config['contexts']}
 r=RefreshRunner(replace(load_sealed_plan(ROOT),pairs=tuple(pairs.values())),tmp_path.resolve()/'legacy')
 assert r.run(run_id='legacy',force_revalidate=True,hooks=build_real_hooks(ROOT,structural_evidence=False))['status']=='published'
 s=LocalService.from_release(r.root,pointer=r.current())
 assert s.release_metadata['structural_evidence_version'] is None
 assert all('evidence_origin' not in p for pair in s.pairs for p in pair['provisions'])


def test_resealed_wrong_map_rejected_before_swap(structural_release,tmp_path):
 from sbs.genie import digest
 from sbs.operations import sha
 s=LocalService.from_release(structural_release.root,pointer=structural_release.current());old=s.snapshot;oldentries=s.entries;s.sessions['sentinel']='preserve'
 r=RefreshRunner(structural_release.plan,tmp_path.resolve()/'bad-map');hooks=build_real_hooks(ROOT);normal=hooks['SK03']
 def corrupt(ctx):
  out=normal(ctx)
  if out['status']=='validated':
   path=Path(ctx['stage'])/out['artifact_path'];envelope=json.loads(path.read_text())
   envelope['payload']['structural_wrappers'][0]['derived_comparison'][0]['before']['mapping'][0]['derived_text']='tampered'
   envelope['sha256']=digest(envelope['payload']);path.write_text(json.dumps(envelope));out['sha256']=sha(path.read_bytes())
  return out
 hooks['SK03']=corrupt
 assert r.run(run_id='resealed',force_revalidate=True,hooks=hooks)['status']=='published'
 with pytest.raises(ValueError,match='RELEASE_STRUCTURAL_REPLAY_MISMATCH'):s.promote_release(r.root,pointer=r.current())
 assert s.snapshot==old and s.entries is oldentries and s.sessions['sentinel']=='preserve'


def test_global_unresolved_notes_propagate_without_ownership_inference():
 # Historical4036 remains outside sealed six-source preparation.
 from sbs.comparison.structural import compare_structural
 from sbs.operations.structural_evidence import focus
 pins=json.loads((ROOT/'runs/sk03-market-018-inputs.json').read_text());raw=[json.loads((ROOT/p).read_text()) for p in pins['hashes'] if p.endswith('result.json')]
 w=compare_structural(pins['pair'],*raw);b={(p['document_id'],p['version_id']):r for r in raw for p in r['provisions']}
 pid=next(p['provision_id'] for p in w['evidence_context']['after']['provisions'] if p['text'].startswith('Segunda'))
 item,_=focus(w,pid,b)
 assert any('11' in text for text in item['evidence_context']['global_limitations'])
 assert any(n['marker']=='11' for n in item['evidence_context']['after']['notes'])
 assert not any(l['marker']=='11' for l in item['evidence_context']['after']['links'])
 assert validate_contract('EvidencePack',item['change_set']['evidence'])['valid']
