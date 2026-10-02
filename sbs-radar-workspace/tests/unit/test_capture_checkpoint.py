"""Offline complete-capture pending checkpoint, never a published RAG release."""
import json
import pytest
from test_remote_refresh import ROOT,pilot_plan
from test_shared_control import Backend
from test_volume_artifacts import Files,store
from test_foundation import pdf
from sbs.operations.shared_control import SharedLedger,SnapshotWriter
from sbs.operations.cloud_dispatch import digest
from sbs.operations.cloud_writer import prepare_and_publish


def test_pending_capture_restores_on_new_machine_without_refetch(tmp_path):
 plan=pilot_plan();selected=next(iter(plan.originals));backend=Backend();files=Files();volume=store(files)
 SharedLedger(backend).reserve(digest(301),{'request_hash':digest(301),'job_id':7,'run_id':301,'status':'submitted'})
 writer=SnapshotWriter(backend,job_id=7,writer_guard=lambda *a:True,artifact_validator=volume.verify,artifact_prefix=volume.prefix)
 calls=[]
 def fetch(url,**kw):calls.append(url);return (pdf('Resolucion SBS 3274-2017 New text pending embeddings') if url==selected else plan.originals[url].read_bytes()),url
 def execute(path):return prepare_and_publish(ROOT,plan,run_id=301,artifact_store=volume,writer=writer,capture_mode='remote',capture_state_root=path,fetcher=fetch)
 original_stage=volume.stage
 def fail(*a,**kw):raise RuntimeError('fixture stage failure')
 volume.stage=fail
 with pytest.raises(RuntimeError):execute(tmp_path/'one')
 assert writer.current() is None and writer.latest_capture_checkpoint(None) is None and len(calls)==6
 volume.stage=original_stage
 first=execute(tmp_path/'one')
 assert first['status']=='pending_validation' and first['capture_durable'] is True and writer.current() is None
 assert len(calls)==6
 second=execute(tmp_path/'two')
 assert second['status']=='pending_validation' and second['capture_durable'] is True and len(calls)==6
 assert writer.current() is None
 assert json.loads((tmp_path/'two/backlog.json').read_bytes())==json.loads((tmp_path/'one/backlog.json').read_bytes())
 restored=json.loads((tmp_path/'two/capture_recovery.json').read_bytes())
 assert restored['unpublished_attempts_restored'] is True and restored['fresh_remote_capture'] is False
 assert (tmp_path/'two/foundation/foundation.sqlite3').exists()
 assert not any(k.endswith('.sqlite3') for k in files.data)
 receipt=writer.latest_capture_checkpoint(None)
 bad=next(k for k in files.data if k.startswith(receipt['manifest_path'].rsplit('/',1)[0]) and k.endswith('.pdf'))
 saved=files.data[bad];files.data[bad]=b'corrupt'
 with pytest.raises(ValueError):execute(tmp_path/'corrupt')
 assert writer.current() is None and len(calls)==6 and not (tmp_path/'corrupt').exists()
 files.data[bad]=saved


def test_capture_receipt_type_and_scope_fail_closed():
 from copy import deepcopy
 from sbs.operations.shared_control import _state,initial_state,_capture_receipt
 from sbs.operations.cloud_dispatch import digest
 p={'job_id':7,'run_id':301,'base_publication':None,'manifest_path':'/Volumes/catalog/sbs_radar/artifacts/sbs-refresh/runs/capture-301/'+'a'*64+'/manifest.json','manifest_sha256':'b'*64,'artifacts_sha256':'c'*64,'plan_fingerprint':'d'*64,'status':'pending_validation','revision':1}
 p['checkpoint_id']=digest(p);_capture_receipt(p)
 for key,value in [('job_id',True),('run_id',301.0),('revision',False),('manifest_path','/Volumes/other/wrong'),('status','published')]:
  bad={**p,key:value};bad['checkpoint_id']=digest({k:v for k,v in bad.items() if k!='checkpoint_id'})
  with pytest.raises(ValueError):_capture_receipt(bad)
 s=initial_state();s['requests']['a'*64]={'job_id':7,'run_id':302,'capture_checkpoint':p}
 with pytest.raises(ValueError,match='SCOPE'):_state(s)
