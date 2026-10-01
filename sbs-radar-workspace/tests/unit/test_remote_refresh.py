from sbs.operations.remote_refresh import observed_pairs,discover_candidates

def test_same_url_change_pair_direction_and_family():
 old={'source_key':'key','document_id':'doc','family':'cybersecurity','sha256':'a'*64}
 new={**old,'sha256':'b'*64}
 pairs,provenance=observed_pairs([old],[new])
 assert pairs[0]['before']['version_id']=='a'*64 and pairs[0]['after']['version_id']=='b'*64
 assert provenance[0]['basis']=='same_registered_url_observed_bytes_change' and not provenance[0]['legal_effect_established']
 assert observed_pairs([old],[old])==([],[])

def test_candidate_discovery_no_auto_eligibility():
 html=b'<a href="https://intranet2.sbs.gob.pe/x.pdf">Seguridad de la informacion bancos</a><a href="https://evil.test/x.pdf">bancos</a>'
 r=discover_candidates(html,index_url='https://www.sbs.gob.pe/autorizacion-de-nuevas-empresas/marco-normativo-y-documentos-de-apoyo',observed_at='2026-09-28T00:00:00Z')
 assert len(r['candidates'])==1 and r['candidates'][0]['status']=='candidate_only' and not r['candidates'][0]['auto_include']

from pathlib import Path
from dataclasses import replace
import json
from sbs.operations import load_sealed_plan,RefreshRunner
from sbs.operations.remote_refresh import run_refresh
ROOT=Path(__file__).resolve().parents[2]

def pilot_plan():
 cfg=json.load(open(ROOT/'config/genie-pilot-002.json'));pairs={x['pair']['pair_id']:x['pair'] for x in cfg['contexts']};return replace(load_sealed_plan(ROOT),pairs=tuple(pairs.values()))

def test_remote_changed_same_url_retained_and_materializes_with_cached_text(tmp_path):
 plan=pilot_plan();selected=next(iter(plan.originals));calls=[]
 def fetch(url,**kw):
  calls.append(url);raw=plan.originals[url].read_bytes()
  # Fixture byte-only trailer update preserves exact PDF text/embedding inputs.
  return (raw+b'\n% fixture-capture-revision\n' if url==selected else raw),url
 out=run_refresh(ROOT,plan,tmp_path/'state',run_id='changed',capture_mode='remote',fetcher=fetch)
 assert out['status']=='published' and len(calls)==6 and len(out['observed_pair_provenance'])==1
 runner=RefreshRunner(plan,tmp_path/'state');release=runner._release()
 assert len(release['sources'])==7 and sum(bool(x.get('retained')) for x in release['sources'])==1
 from sbs.runtime import LocalService
 service=LocalService.from_release(tmp_path/'state',pointer=runner.current())
 assert len(service.catalog()['pairs'])==3
 assert json.load(open(tmp_path/'state/last_capture_success.json'))['legal_changes']=='not_assessed'


def test_new_text_stays_pending_and_remote_attempt_idempotent(tmp_path):
 import io
 from pypdf import PdfWriter
 plan=pilot_plan();selected=next(iter(plan.originals));calls=[]
 # A real valid fixture PDF with different raw text, no provider needed.
 from test_foundation import pdf as pdf_bytes
 raw=pdf_bytes('Resolucion SBS 3274-2017 New remote fixture text')
 def fetch(url,**kw):calls.append(url);return (raw if url==selected else plan.originals[url].read_bytes()),url
 result=run_refresh(ROOT,plan,tmp_path/'state',run_id='newtext',capture_mode='remote',fetcher=fetch)
 assert result['status']=='pending_validation' and result['pending_hooks']['SK04'] in ('TOKENIZER_PENDING','EMBEDDINGS_MISSING')
 assert json.load(open(tmp_path/'state/last_capture_success.json'))['mode']=='remote'
 assert run_refresh(ROOT,plan,tmp_path/'state',run_id='newtext',capture_mode='remote',fetcher=fetch)==result and len(calls)==6

import pytest
from sbs.operations.remote_refresh import registered_fetcher

def test_wrong_document_and_redirect_rejected_and_pointer_preserved(tmp_path):
 from test_foundation import pdf
 plan=pilot_plan();selected=next(iter(plan.originals));runner=RefreshRunner(plan,tmp_path/'state');runner.bootstrap_capture();prior=runner.current()
 wrong=pdf('Resolucion SBS 9999-2026 another document')
 def fetch(url,**kw):return (wrong if url==selected else plan.originals[url].read_bytes()),url
 out=run_refresh(ROOT,plan,tmp_path/'state',run_id='wrong',capture_mode='remote',fetcher=fetch)
 assert out['status']=='failed' and runner.current()==prior and not (tmp_path/'state/last_capture_success.json').exists()
 with pytest.raises(ValueError,match='REDIRECT'):registered_fetcher(plan,lambda url,**kw:(plan.originals[url].read_bytes(),url+'?other'))(selected,allowed_hosts=plan.manifest['allowed_hosts'])


def test_failure_preserves_capture_success_but_records_latest_attempt(tmp_path):
 plan=pilot_plan();root=tmp_path/'state'
 def same(url,**kw):return plan.originals[url].read_bytes(),url
 good=run_refresh(ROOT,plan,root,run_id='good',capture_mode='remote',fetcher=same)
 previous=json.load(open(root/'last_capture_success.json'));pointer=RefreshRunner(plan,root).current()
 def failed(url,**kw):raise TimeoutError('untrusted detail')
 result=run_refresh(ROOT,plan,root,run_id='failed',capture_mode='remote',fetcher=failed)
 assert result['status']=='failed' and 'untrusted' not in json.dumps(result)
 assert json.load(open(root/'last_attempt.json'))['run_id']=='failed' and json.load(open(root/'last_capture_success.json'))==previous
 assert RefreshRunner(plan,root).current()==pointer


def test_discovery_scope_caps_and_sector():
 url='https://www.sbs.gob.pe/autorizacion-de-nuevas-empresas/marco-normativo-y-documentos-de-apoyo'
 html='<a href="/a.pdf">conducta de mercado seguros</a><a href="/b.pdf">seguridad de la información</a>'
 result=discover_candidates(html.encode(),index_url=url,observed_at='now')
 assert [x['eligibility'] for x in result['candidates']]==['excluded_sector_mismatch','pending_family_or_sector']
 with pytest.raises(ValueError):discover_candidates(b'x',index_url='https://evil.test',observed_at='now')
 with pytest.raises(ValueError):discover_candidates(b'x'*(1024*1024+1),index_url=url,observed_at='now')


def test_remote_cloud_writer_pending_requires_durable_capability_keeps_local_state(tmp_path):
 from test_cloud_writer import Writer
 from test_volume_artifacts import Files,store
 from sbs.operations.cloud_writer import prepare_and_publish
 from test_foundation import pdf
 plan=pilot_plan();selected=next(iter(plan.originals));w=Writer();f=Files()
 def fetch(url,**kw):return (pdf('Resolucion SBS 3274-2017 New remote text') if url==selected else plan.originals[url].read_bytes()),url
 with pytest.raises(ValueError,match='CAPTURE_DURABLE_WRITER_REQUIRED'):
  prepare_and_publish(ROOT,plan,run_id=99,artifact_store=store(f),writer=w,capture_mode='remote',capture_state_root=tmp_path/'persistent',fetcher=fetch)
 assert w.claimed==0 and not f.calls
 assert (tmp_path/'persistent/last_attempt.json').exists() and (tmp_path/'persistent/backlog.json').exists()


def test_missing_remote_state_after_shared_publication_fails_closed(tmp_path):
 from test_volume_artifacts import Files,store
 from sbs.operations.cloud_writer import prepare_and_publish
 class Writer:
  def current(self):return {'run_id':98,'release_id':'a'*64,'publication_id':'b'*64}
 with pytest.raises(ValueError,match='RECOVERY_REQUIRED'):
  prepare_and_publish(ROOT,pilot_plan(),run_id=99,artifact_store=store(Files()),writer=Writer(),capture_mode='remote',capture_state_root=tmp_path/'absent')


def test_observed_pair_catalog_survives_stable_and_next_change(tmp_path):
 plan=pilot_plan();selected=next(iter(plan.originals));revision=[b'one']
 def fetch(url,**kw):
  raw=plan.originals[url].read_bytes()
  return (raw+b'\n% fixture '+revision[0]+b'\n' if url==selected else raw),url
 runner=RefreshRunner(plan,tmp_path/'state');catalogs=[]
 for run,value in [('first',b'one'),('stable',b'one'),('next',b'two')]:
  revision[0]=value
  assert run_refresh(ROOT,plan,runner.root,run_id=run,capture_mode='remote',fetcher=fetch)['status']=='published'
  release=runner._release();payload=json.loads((runner.root/release['prepared']['SK03']['artifact_path']).read_bytes())['payload']
  catalogs.append(payload['pairs'])
 assert catalogs[0]==catalogs[1]
 assert all(p in catalogs[2] for p in catalogs[0]) and len(catalogs[2])==len(catalogs[0])+1
 assert len(release['observed_pair_provenance'])==2
 assert all(not p['legal_effect_established'] for p in release['observed_pair_provenance'])


def test_resume_exact_prepared_run_after_upload_failure_without_recapture(tmp_path):
 from sbs.operations.cloud_writer import prepare_and_publish
 from sbs.operations.shared_control import SharedLedger,SnapshotWriter
 from sbs.operations.cloud_dispatch import digest
 from test_shared_control import Backend
 from test_volume_artifacts import Files,store
 plan=pilot_plan();volume=store(Files());backend=Backend();ledger=SharedLedger(backend)
 for run in (99,100,101):ledger.reserve(digest(run),{'request_hash':digest(run),'job_id':7,'run_id':run,'status':'submitted'})
 writer=SnapshotWriter(backend,job_id=7,writer_guard=lambda *a:True,artifact_validator=volume.verify,artifact_prefix=volume.prefix)
 calls=[];selected=next(iter(plan.originals));changed=[False]
 def fetch(url,**kw):
  calls.append(url);raw=plan.originals[url].read_bytes()
  return (raw+b'\n% fixture next\n' if changed[0] and url==selected else raw),url
 def execute(run):return prepare_and_publish(ROOT,plan,run_id=run,artifact_store=volume,writer=writer,capture_mode='remote',capture_state_root=tmp_path/'state',fetcher=fetch)
 assert execute(99)['status']=='published';prior=writer.current();changed[0]=True;stage=volume.stage
 def fail(*a,**k):raise RuntimeError('fixture upload failure')
 volume.stage=fail
 with pytest.raises(RuntimeError):execute(100)
 assert writer.current()==prior and len(calls)==12
 volume.stage=stage
 with pytest.raises(ValueError,match='RECOVERY_REQUIRED'):execute(101)
 record_path=tmp_path/'state/runs/job-100/result.json';record=json.loads(record_path.read_bytes())
 for key,value in [('previous',{'release_id':'0'*64,'sha256':'0'*64}),('current',None),('run_id','job-101'),('publication_committed',False)]:
  record_path.write_text(json.dumps({**record,key:value}))
  with pytest.raises(ValueError,match='RECOVERY_REQUIRED'):execute(100)
  assert writer.current()==prior and len(calls)==12
 record_path.write_text(json.dumps(record))
 locator_path=tmp_path/'state/last_shared_publication.json';locator=json.loads(locator_path.read_bytes())
 locator_path.write_text(json.dumps({**locator,'publication_id':'0'*64}))
 with pytest.raises(ValueError,match='RECOVERY_REQUIRED'):execute(100)
 locator_path.write_text(json.dumps(locator))
 assert execute(100)['status']=='published' and len(calls)==12
 assert writer.current()['run_id']==100
 assert execute(100)['recovered'] is True and len(calls)==12


def test_fresh_machine_recovers_published_capture_then_unchanged_changed(tmp_path):
 from sbs.operations.cloud_writer import prepare_and_publish
 from sbs.operations.shared_control import SharedLedger,SnapshotWriter
 from sbs.operations.cloud_dispatch import digest
 from test_shared_control import Backend
 from test_volume_artifacts import Files,store
 import sqlite3
 plan=pilot_plan();volume=store(Files());backend=Backend();ledger=SharedLedger(backend)
 for run in (201,202,203):ledger.reserve(digest(run),{'request_hash':digest(run),'job_id':7,'run_id':run,'status':'submitted'})
 writer=SnapshotWriter(backend,job_id=7,writer_guard=lambda *a:True,artifact_validator=volume.verify,artifact_prefix=volume.prefix)
 selected=next(iter(plan.originals));revision=[b'one'];calls=[]
 def fetch(url,**kw):
  calls.append(url);raw=plan.originals[url].read_bytes()
  return (raw+b'\n% recovery fixture '+revision[0]+b'\n' if url==selected else raw),url
 def execute(run,path):return prepare_and_publish(ROOT,plan,run_id=run,artifact_store=volume,writer=writer,capture_mode='remote',capture_state_root=path,fetcher=fetch)
 assert execute(201,tmp_path/'machine1')['status']=='published'
 first=RefreshRunner(plan,tmp_path/'machine1')._release()
 prior=writer.current();remote_pdf=next(k for k in volume.files.data if k.endswith('.pdf'));saved=volume.files.data[remote_pdf]
 volume.files.data[remote_pdf]=b'corrupt published artifact'
 with pytest.raises(ValueError):execute(202,tmp_path/'corrupt-machine')
 assert writer.current()==prior and len(calls)==6 and not (tmp_path/'corrupt-machine').exists()
 volume.files.data[remote_pdf]=saved
 assert execute(202,tmp_path/'machine2')['status']=='published'
 second=RefreshRunner(plan,tmp_path/'machine2')._release()
 assert first['observed_pair_provenance']==second['observed_pair_provenance']
 with sqlite3.connect(tmp_path/'machine2/foundation/foundation.sqlite3') as db:
  assert db.execute("SELECT count(*) FROM attempts WHERE status='restored_published'").fetchone()[0]==7
 assert json.loads((tmp_path/'machine2/capture_recovery.json').read_bytes())['unpublished_attempts_restored'] is False
 revision[0]=b'two';prior=writer.current();stage=volume.stage
 def fail(*a,**k):raise RuntimeError('fixture stage unavailable')
 volume.stage=fail
 with pytest.raises(RuntimeError):execute(203,tmp_path/'machine3')
 assert writer.current()==prior and len(calls)==18
 volume.stage=stage
 assert execute(203,tmp_path/'machine3')['status']=='published' and len(calls)==18
 final=RefreshRunner(plan,tmp_path/'machine3')._release()
 assert len(final['observed_pair_provenance'])==2
