from pathlib import Path
from copy import deepcopy
from types import SimpleNamespace
import importlib.util,json
import pytest
from sbs.app133.runtime import ProcessBudget,RouteGenerator,AppService
from sbs.app133.bootstrap import create_service133,load_config
ROOT=Path(__file__).resolve().parents[2]
def module(path,name):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def fixture():return module('tests/unit/test_hybrid_125.py','app133hybridfixture')
def config():return {**load_config(ROOT),'deadline_unix':100}
def router(tmp_path,max_posts=2):
 f=fixture();_,raw,_=f.make(tmp_path/'unused',f.proposal_response())
 budget=ProcessBudget(deadline=100,max_posts=max_posts,clock=lambda:0)
 return RouteGenerator(raw,tmp_path,ROOT,budget),raw,f

def test_deadline_absolute_and_restart():
 for _ in range(2):
  budget=ProcessBudget(deadline=20,max_posts=2,clock=lambda:20)
  with pytest.raises(ValueError,match='DEADLINE'):budget.check()

def test_routes_capture_unique_and_process_budget(tmp_path):
 g,raw,f=router(tmp_path,1)
 out=g(f.source());assert out['material_claims'][0]['text'].startswith('Antes:') and not raw.calls
 g(f.source(3));assert len(raw.calls)==1 and raw.calls[0]['temperature']==0
 with pytest.raises(ValueError,match='PROCESS_POST_LIMIT'):g(f.source(3))
 assert len(raw.calls)==1 and g.requests==1
 assert len(list(tmp_path.glob('request-*')))==3
 assert g.last_attempt['budget_scope']=='process_only'

def test_mixed_request_preserved_no_focal_reduction(tmp_path):
 g,raw,f=router(tmp_path);request=f.source(3);d=json.loads(request['messages'][1]['content']);d['tool_results']['genie']={'rows':[[2]],'fixture':True}
 d['question']='¿Cuántos registros hay y qué cambió?';request['messages'][1]['content']=json.dumps(d)
 g(request)
 assert raw.calls[0]['messages']==request['messages'] and 'temperature' not in raw.calls[0]
 assert g.last_attempt['route']=='generic_preserved_request'

def test_hybrid_failure_does_not_fallback(tmp_path):
 g,raw,f=router(tmp_path)
 bad=f.proposal_response('Antes')
 class Bad:
  calls=0;last_attempt={}
  def __call__(self,body):self.calls+=1;self.last_attempt={'stage':'http_completed'};return bad
 b=Bad();g.raw.delegate=b
 with pytest.raises(ValueError,match='PROPOSAL_INTENT'):g(f.source(3))
 assert b.calls==1

def test_real_cloud_initializer_keeps_mode_and_m2m_identity(tmp_path):
 c=config();client=SimpleNamespace(config=SimpleNamespace(host=c['workspace_host'],auth_type='oauth-m2m',client_id=c['reader_client_id'],authenticate=lambda:(_ for _ in ()).throw(AssertionError('noauth'))))
 service=AppService(mode='cloud').configure133(ROOT,c,clock=lambda:0,client_factory=lambda:client)
 service.initialize_models()
 assert service.mode=='cloud' and isinstance(service.generator,RouteGenerator)
 assert service.generator.requests==0 and service.embedding.calls_attempted==0
 assert service.embedding.max_calls==2 and service.reranker is not None
 client.config.auth_type='pat'
 bad=AppService(mode='cloud').configure133(ROOT,c,clock=lambda:0,client_factory=lambda:client)
 with pytest.raises(ValueError,match='IDENTITY'):bad.initialize_models()

def test_count_keeps_genie_and_user_scoping_without_model(tmp_path,monkeypatch):
 import sbs.runtime as runtime
 f=module('tests/unit/test_runtime_genie.py','counts133')
 s=AppService(mode='cloud').configure133(ROOT,config(),clock=lambda:0)
 binding=f.VerifiedCountFixture();binding.rag_snapshot=s.snapshot;s.genie_binding=binding
 (tmp_path/'runs').mkdir();monkeypatch.setattr(runtime,'ROOT',tmp_path)
 actor={'authenticated':True,'subject':'user-a','role':'reader','families':['cybersecurity','market_conduct']}
 out=s.ask('same','¿Cuántos registros hay?','cyber-504','art20.3',actor=actor)
 assert out['status']=='answered_structured' and s.generator is None
 s.ask('same','¿Cuántos registros hay?','cyber-504','art20.3',actor={**actor,'subject':'user-b'})
 assert len(s.sessions)==2
 with pytest.raises(PermissionError):s.ask('same','¿Cuántos registros hay?','cyber-504','art20.3')

def test_default_deadline_blocks_queries_and_cloud_requires_rotation():
 s=create_service133({'SBS_MODE':'local'},root=ROOT)
 with pytest.raises(ValueError,match='DEADLINE'):s.ask('x','hello','cyber-504','art20.3')
 with pytest.raises(ValueError,match='ROTATION'):create_service133({'SBS_MODE':'cloud'},root=ROOT)
 with pytest.raises(ValueError,match='ALTERNATE'):create_service133({'SBS_GENERATION_SELECTION':'config/generation-selection-077.json'},root=ROOT)

def test_source_closure_and_quality_fail_before_release(tmp_path):
 m=module('deployment/app_source_133.py','builder133')
 names=m.closure()
 assert {'app133.py','app098.py','src/sbs/conversation/hybrid_125.py','src/sbs/conversation/GeneratedClaims.json','runs/sk06-pilot-002/processes.jsonl'}<=set(names)
 assert not any(n.startswith('deployment/state/') for n in names)
 assert not any('fresh_publication_081' in n for n in names)
 # Minimal valid manifest reaches the real quality gate, no release side effect.
 (tmp_path/'manifest.json').write_text(json.dumps({'files_sha256':{},'source_sha256':m.sha(m.encoded({}))}))
 review=tmp_path/'failed.json';review.write_text(json.dumps({'status':'FAIL_CONTROLLED_SAMPLE','demo_sample_accepted':False}))
 with pytest.raises(ValueError,match='REAL125_QUALITY'):m.release_gate(tmp_path,review,tmp_path/'absent.json')
