import json
from dataclasses import replace
from pathlib import Path
from sbs.operations import load_sealed_plan
from sbs.operations.cloud_writer import prepare_and_publish
from test_volume_artifacts import Files,store
ROOT=Path(__file__).resolve().parents[2]
class Writer:
 def __init__(self):self.published=[];self.claimed=0
 def current(self):return None
 def claim(self,run_id):self.claimed+=1;return 1
 def publish(self,run_id,fence,**kw):self.published.append(kw);return {'status':'published','publication_id':'a'*64}

def test_six_pdf_real_preparation_remote_fixture_publish(tmp_path):
 plan=load_sealed_plan(ROOT);config=json.loads((ROOT/'config/genie-pilot-002.json').read_text());pairs={c['pair']['pair_id']:c['pair'] for c in config['contexts']};plan=replace(plan,pairs=tuple(pairs.values()));w=Writer();files=Files();v=store(files)
 out=prepare_and_publish(ROOT,plan,run_id=99,artifact_store=v,writer=w,local_parent=tmp_path)
 assert out['status']=='published'
 values=[]
 for content in files.data.values():
  try:value=json.loads(content)
  except (UnicodeDecodeError,json.JSONDecodeError):continue
  if isinstance(value,dict):values.append(value)
 envelopes=[v['payload'] for v in values if isinstance(v.get('payload'),dict)]
 comparison=next(v for v in envelopes if 'structural_wrappers' in v)
 curated=next(v['bundle'] for v in envelopes if 'bundle' in v)
 raw=[v for v in values if v.get('layer')=='raw_pages']
 original={(p['document_id'],p['version_id']):b['rawtext'] for b in raw for p in b['provisions']}
 expected={p['citation_id']:p for b in raw for p in b['provisions']}
 expected.update({p['citation_id']:p for p in comparison['structural_provisions']})
 actual={p['id']:json.loads(p['payload_json']) for p in curated['tables']['provisions']}
 assert actual==expected and len(actual)==814 # v8:135 raw +679 exact structural/context projections
 assert len(actual)==len(curated['tables']['provisions']) # no duplicate identity rows
 assert all(original[(p['document_id'],p['version_id'])][p['start']:p['end']]==p['text'] for p in actual.values())
 assert out['counts']=={'sources':6,'comparisons':2,'records':135,'embedding_calls':0,'curated_provisions':len(actual)}
 assert w.claimed==1 and len(w.published)==1 and v.verify(w.published[0]['artifacts'])

def test_pending_never_claims_or_uploads(tmp_path):
 w=Writer();f=Files();out=prepare_and_publish(ROOT,load_sealed_plan(ROOT),run_id=99,artifact_store=store(f),writer=w,local_parent=tmp_path)
 assert out['status']=='pending_validation' and w.claimed==0 and not w.published and not f.calls

def test_preparation_failure_never_uploads_or_claims(tmp_path):
 config=json.loads((ROOT/'config/genie-pilot-002.json').read_text());pairs={c['pair']['pair_id']:c['pair'] for c in config['contexts']};plan=replace(load_sealed_plan(ROOT),pairs=tuple(pairs.values()));w=Writer();f=Files()
 out=prepare_and_publish(ROOT,plan,run_id=99,artifact_store=store(f),writer=w,local_parent=tmp_path,fail_at='before_publish')
 assert out['status']=='failed' and w.claimed==0 and not f.calls

def test_remote_readback_failure_never_claims(tmp_path):
 import pytest
 config=json.loads((ROOT/'config/genie-pilot-002.json').read_text());pairs={c['pair']['pair_id']:c['pair'] for c in config['contexts']};plan=replace(load_sealed_plan(ROOT),pairs=tuple(pairs.values()));w=Writer();v=store(Files());v.verify=lambda artifacts:False
 with pytest.raises(ValueError):prepare_and_publish(ROOT,plan,run_id=99,artifact_store=v,writer=w,local_parent=tmp_path)
 assert w.claimed==0 and not w.published

def test_restart_recovers_durable_manifest_without_recapture(tmp_path,monkeypatch):
 from test_shared_control import Backend,record
 from sbs.operations.shared_control import SharedLedger,SnapshotWriter
 from sbs.operations.volume_artifacts import sha
 import sbs.operations.cloud_writer as module
 b=Backend();SharedLedger(b).reserve('b'*64,record());f=Files();v=store(f)
 (tmp_path/'x').write_bytes(b'original');staged=v.stage('99',tmp_path,{'x':sha(b'original')})
 w=SnapshotWriter(b,job_id=7,writer_guard=lambda j,r:True,artifact_validator=v.verify,artifact_prefix=v.prefix)
 w.publish(99,w.claim(99),previous=None,release_id=staged['release_id'],artifacts=staged['artifacts'])
 monkeypatch.setattr(module,'build_real_hooks',lambda *a,**k:(_ for _ in ()).throw(AssertionError('recapture')))
 out=prepare_and_publish(ROOT,None,run_id=99,artifact_store=store(f),writer=w)
 assert out['recovered'] is True and out['publication']==w.current()
 f.data[next(p for p in f.data if p.endswith('/x'))]=b'corrupt'
 import pytest
 with pytest.raises(ValueError):prepare_and_publish(ROOT,None,run_id=99,artifact_store=store(f),writer=w)
