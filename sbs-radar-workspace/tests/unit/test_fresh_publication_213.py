from pathlib import Path
import importlib.util,json,shutil,sys,types
import pytest
ROOT=Path(__file__).resolve().parents[2]
def load(path='runs/sk06-sk11-fresh-213.py'):
 s=importlib.util.spec_from_file_location('fresh213test'+path[-6:-3],ROOT/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def setup_prior(tmp_path,m):
 root=tmp_path.resolve();shutil.copytree(ROOT/m.PRIOR_STATE,root/m.PRIOR_STATE);return root,m.prepare(ROOT)

def test_prior_zero_sql_keeps_legacy112_and_start_intent(tmp_path):
 m=load();root,p=setup_prior(tmp_path,m);before={x.name:x.read_bytes() for x in (root/m.PRIOR_STATE).iterdir() if x.is_file()};out=m.prior_zero_sql(root,p)
 assert out['prior_sql_reserved']==0 and out['prior_warehouse_start_attempts']==1 and out['new_warehouse_start_allowed'] is False
 assert out['legacy_scope112']['limit']==112 and out['legacy_scope112']['reserved']==99
 assert before=={x.name:x.read_bytes() for x in (root/m.PRIOR_STATE).iterdir() if x.is_file()}

@pytest.mark.parametrize('name',['intent-01.json','submission-01.json','result-01.json','files-intent-pointer.json','published.json'])
def test_any_sql_or_publication_evidence_blocks_new_session(tmp_path,name):
 m=load();root,p=setup_prior(tmp_path,m);(root/m.PRIOR_STATE/name).write_text('{}')
 with pytest.raises(ValueError,match='PRIOR_SQL_OR_PUBLICATION_RESERVED'):m.prior_zero_sql(root,p)

def test_new_state_exclusive_cfg_retained_original_unchanged(tmp_path,monkeypatch):
 m=load();root,p=setup_prior(tmp_path,m);cfg=object();called=[]
 monkeypatch.setattr(m,'check_review',lambda *a:None);monkeypatch.setattr(m,'prepare',lambda *a:p);monkeypatch.setattr(m,'preflight',lambda *a:{'connector_ready':True})
 fake=types.ModuleType('databricks.sql.client');fake.Connection=lambda:None;monkeypatch.setitem(sys.modules,'databricks.sql.client',fake)
 monkeypatch.setattr(m,'_execute',lambda *a,**kw:called.append(kw['cfg']) or {'status':'fixture_only'})
 assert m.execute(root,'review',cfg=cfg)=={'status':'fixture_only'};assert called==[cfg]
 with pytest.raises(FileExistsError):m.execute(root,'review',cfg=cfg)
 assert called==[cfg] and (root/m.PRIOR_STATE/'warehouse-start-intent.json').exists()

def test_allow_start_false_does_not_post_even_when_stopped(tmp_path):
 activity=load('runs/sk12-phase-s-017.py')
 class Fake:
  id='warehouse';calls=[]
  def call(self,method):self.calls.append(method);assert method=='GET';return {'state':'STOPPED'}
 fake=Fake()
 with pytest.raises(ValueError,match='START_NOT_AUTHORIZED'):activity.ensure_running(fake,tmp_path.resolve(),allow_start=False)
 assert fake.calls==['GET'] and not (tmp_path/'warehouse-start-intent.json').exists()


def test_publication_execution_body_changes_only_state_no_start_and_lineage():
 old=(ROOT/'runs/sk06-sk11-fresh-205.py').read_text();new=(ROOT/'runs/sk06-sk11-fresh-213.py').read_text()
 body=old[old.index('def execute('):old.index('\ndef reconcile(')]
 expected=body.replace('def execute(', 'def _execute(').replace('deployment/state/fresh-readback-081','deployment/state/fresh-readback-213').replace('allow_start=True','allow_start=False')
 expected=expected.replace("    journal=Journal(state,plan_sha256=sha(p['plan'].payload))", "    journal=Journal(state,plan_sha256=sha(p['plan'].payload))\n    journal.save('recovery213.json',prior_zero_sql(root,p))")
 expected=expected.replace("sql_reserved=journal.count,thrift_requests=budget.calls", "sql_reserved=journal.count,prior081_sql_reserved=0,aggregate_fresh_sql_reserved=journal.count,warehouse_start_attempts_prior=1,warehouse_start_attempts_current=0,legacy_scope112=p['oldledger'],thrift_requests=budget.calls")
 assert new[new.index('def _execute('):new.index('\ndef reconcile(')]==expected
