"""Shared-state semantics on injected fixtures; never cloud verification."""
from copy import deepcopy
import pytest
from sbs.operations.shared_control import SharedLedger,SnapshotWriter,DeltaControl,Conflict,UnknownCommit,initial_state

class Backend:
 def __init__(self):self.revision=0;self.state=initial_state();self.conflict=False
 def read(self):return self.revision,deepcopy(self.state)
 def cas(self,revision,state):
  if self.conflict or revision!=self.revision:raise Conflict('CAS_CONFLICT')
  self.state=deepcopy(state);self.revision+=1;return self.revision

def record():return {'request_hash':'a'*64,'job_id':7,'run_id':99,'status':'submitted'}
PREFIX='/Volumes/catalog/sbs_radar/artifacts/sbs-refresh'
def artifact_map(h='c'*64):return {PREFIX+'/runs/99/'+('a'*64)+'/manifest.json':h}
def writer(backend):return SnapshotWriter(backend,job_id=7,writer_guard=lambda j,r:True,artifact_validator=lambda a:True,artifact_prefix=PREFIX)

def test_reservation_conflict_and_shared_clients():
 b=Backend();a=SharedLedger(b);other=SharedLedger(b)
 assert a.reserve('b'*64,record())[1]
 assert not other.reserve('b'*64,record())[1]
 with pytest.raises(ValueError):other.reserve('b'*64,dict(record(),request_hash='c'*64))
 other.update('b'*64,{'status':'queued'});assert a.get('b'*64)['status']=='queued'
 b.conflict=True
 with pytest.raises(Conflict):a.update('b'*64,{'status':'running'})

def test_fenced_publish_and_recovery():
 b=Backend();SharedLedger(b).reserve('b'*64,record());w=writer(b);lease=w.claim(99)
 out=w.publish(99,lease,previous=None,release_id='c'*64,artifacts=artifact_map())
 assert out['status']=='published' and w.current()['release_id']=='c'*64
 assert w.publish(99,lease,previous=None,release_id='c'*64,artifacts=artifact_map())==out
 newer=w.claim(99)
 with pytest.raises(ValueError):w.publish(99,lease,previous='c'*64,release_id='e'*64,artifacts=artifact_map('e'*64))
 with pytest.raises(ValueError):w.publish(99,newer,previous=None,release_id='e'*64,artifacts=artifact_map('e'*64))
 assert w.current()['release_id']=='c'*64

def test_caps_before_mutation():
 b=Backend();l=SharedLedger(b,max_requests=1);l.reserve('b'*64,record())
 with pytest.raises(ValueError):l.reserve('c'*64,record())
 assert len(b.state['requests'])==1

class SQL:
 def __init__(self):self.state=initial_state();self.revision=0;self.update_mode='ok';self.duplicate=False;self.calls=[]
 def execute_statement(self,statement,warehouse_id,**kw):
  self.calls.append(statement)
  if statement.startswith('UPDATE'):
   p={x.name:x.value for x in kw['parameters']}
   if self.update_mode!='zero':self.state=__import__('json').loads(p['state']);self.revision+=1
   if self.update_mode=='timeout_after':raise TimeoutError('secret')
   return {'statement_id':'u','status':{'state':'SUCCEEDED'}}
  import json
  rows=[['control',str(self.revision),json.dumps(self.state)]]*(2 if self.duplicate else 1)
  return {'statement_id':'s','status':{'state':'SUCCEEDED'},'manifest':{'truncated':False,'format':'JSON_ARRAY','total_row_count':len(rows),'total_chunk_count':1,'schema':{'columns':[{'name':n,'type_name':t} for n,t in [('control_id','STRING'),('revision','BIGINT'),('state_json','STRING')]]}},'result':{'data_array':rows,'row_count':len(rows),'row_offset':0,'chunk_index':0}}

def delta(sql,**kw):return DeltaControl(sql,table='c.s.control',warehouse_id='warehouse',identity_probe=lambda:{'table_id':'id','format':'delta','isolation':'Serializable','singleton_admin_controlled':True},expected_table_id='id',**kw)

def test_delta_commit_requires_receipt_even_without_dml_manifest():
 sdk=SQL();b=delta(sdk);v,s=b.read();s['requests']['a']={'x':1};assert b.cas(v,s)==1
 sdk.update_mode='zero';v,s=b.read();s['requests']['b']={'x':2}
 with pytest.raises(Conflict):b.cas(v,s)
 assert 'b' not in sdk.state['requests']

def test_timeout_after_commit_reconciles_receipt_no_retry():
 sdk=SQL();sdk.update_mode='timeout_after';b=delta(sdk);v,s=b.read();s['requests']['a']={'x':1}
 assert b.cas(v,s)==1 and sum(x.startswith('UPDATE') for x in sdk.calls)==1

def test_duplicate_and_limits():
 sdk=SQL();sdk.duplicate=True
 with pytest.raises(ValueError):delta(sdk).read()
 sdk=SQL();b=delta(sdk,max_state_bytes=20)
 with pytest.raises(ValueError):b.read()


def test_timeout_before_commit_unknown_no_blind_retry():
 sdk=SQL();original=sdk.execute_statement
 def fail(statement,**kw):
  if statement.startswith('UPDATE'):sdk.calls.append(statement);raise TimeoutError()
  return original(statement,**kw)
 sdk.execute_statement=fail;b=delta(sdk);v,s=b.read();s['requests']['a']={'x':1}
 with pytest.raises(UnknownCommit) as e:b.cas(v,s)
 assert b.reconcile(e.value.operation_id)['status']=='unknown'
 assert sum(x.startswith('UPDATE') for x in sdk.calls)==1


def test_receipt_can_recover_from_new_adapter():
 sdk=SQL();b=delta(sdk);v,s=b.read();s['requests']['a']={'x':1};b.cas(v,s)
 op=next(iter(sdk.state['receipts']));assert delta(sdk).reconcile(op)['status']=='confirmed'


def test_artifact_validation_failure_preserves_pointer():
 b=Backend();SharedLedger(b).reserve('b'*64,record());w=writer(b);lease=w.claim(99);w.validate=lambda a:False
 with pytest.raises(ValueError,match='CLOSURE'):w.publish(99,lease,previous=None,release_id='c'*64,artifacts=artifact_map())
 assert w.current() is None and not b.state['releases']


def test_unknown_run_and_bad_identity_fail_closed():
 b=Backend()
 with pytest.raises(ValueError,match='REGISTERED'):writer(b).claim(99)
 sdk=SQL();d=delta(sdk);d.probe=lambda:{'table_id':'other'}
 with pytest.raises(ValueError,match='IDENTITY'):d.read()
 assert not sdk.calls


def test_receipt_and_sql_caps():
 sdk=SQL();b=delta(sdk,max_receipts=1);v,s=b.read();s['requests']['a']={};b.cas(v,s);v,s=b.read()
 with pytest.raises(ValueError,match='RECEIPT_CAP'):b.cas(v,s)
 sdk=SQL();b=delta(sdk,max_statements=1);b.read()
 with pytest.raises(ValueError):b.read()

def test_s01_sdk_long_schema_is_accepted():
 from databricks.sdk.service.sql import StatementResponse
 sdk=SQL();original=sdk.execute_statement
 def actual_sdk(**kw):
  r=original(**kw)
  if 'manifest' in r:r['manifest']['schema']['columns'][1]['type_name']='LONG'
  return StatementResponse.from_dict(r)
 sdk.execute_statement=actual_sdk
 assert delta(sdk).read()[0]==0

@pytest.mark.parametrize('field,value',[('next_chunk_index',1),('next_chunk_internal_link','/next'),('external_links',[{'external_link':'unused'}])])
def test_s02_continuations_rejected(field,value):
 sdk=SQL();original=sdk.execute_statement
 def malformed(**kw):
  r=original(**kw);r['result'][field]=value;return r
 sdk.execute_statement=malformed
 with pytest.raises(ValueError):delta(sdk).read()

@pytest.mark.parametrize('run,fence',[(99.0,1),(99,True)])
def test_s03_exact_publish_identity(run,fence):
 b=Backend();SharedLedger(b).reserve('b'*64,record());w=writer(b);w.claim(99)
 with pytest.raises(ValueError):w.publish(run,fence,previous=None,release_id='c'*64,artifacts=artifact_map())
 assert b.state['current'] is None

@pytest.mark.parametrize('receipt',[{'revision':False,'state_sha256':'invalid'},{'revision':1,'state_sha256':'a'*64},{'revision':0,'state_sha256':'a'*64},{'revision':1,'state_sha256':'a'*64,'extra':True}])
def test_s04_invalid_receipts_rejected(receipt):
 sdk=SQL();sdk.state['receipts']['a'*64]=receipt
 with pytest.raises(ValueError):delta(sdk).reconcile('a'*64)

@pytest.mark.parametrize('chunks',[[{'chunk_index':1,'row_count':1,'row_offset':0}],[{'chunk_index':0,'row_count':2,'row_offset':0}]])
def test_manifest_chunk_contradictions_rejected(chunks):
 sdk=SQL();original=sdk.execute_statement
 def changed(**kw):
  r=original(**kw);r['manifest']['chunks']=chunks;return r
 sdk.execute_statement=changed
 with pytest.raises(ValueError):delta(sdk).read()

@pytest.mark.parametrize('path',[PREFIX+'/runs/other/'+('a'*64)+'/manifest.json','/Volumes/other/sbs_radar/artifacts/sbs-refresh/runs/99/'+('a'*64)+'/manifest.json',PREFIX+'/runs/99/../manifest.json'])
def test_published_locator_must_match_run_and_prefix(path):
 b=Backend();SharedLedger(b).reserve('b'*64,record());w=writer(b);f=w.claim(99)
 with pytest.raises(ValueError):w.publish(99,f,previous=None,release_id='c'*64,artifacts={path:'c'*64})
 assert w.current() is None

@pytest.mark.parametrize('field,value',[('fence',True),('fence',1.0),('run_id',99.0),('job_id',7.0),('job_id',True),('fence',2)])
def test_s03r_persisted_owner_rejects_before_publish(field,value):
 sdk=SQL();b=delta(sdk);SharedLedger(b).reserve('b'*64,record());w=writer(b);f=w.claim(99)
 sdk.state['owner'][field]=value
 before=deepcopy(sdk.state);writes=sum(s.startswith('UPDATE') for s in sdk.calls)
 with pytest.raises(ValueError):w.publish(99,f,previous=None,release_id='c'*64,artifacts=artifact_map())
 assert sdk.state==before and sum(s.startswith('UPDATE') for s in sdk.calls)==writes

@pytest.mark.parametrize('section,field,value',[('current','run_id',99.0),('current','job_id',7.0),('current','fence',True),('release','run_id',99.0),('release','fence',True),('request','job_id',7.0),('request','run_id',99.0)])
def test_persisted_identity_fields_validate_before_comparison(section,field,value):
 sdk=SQL();b=delta(sdk);SharedLedger(b).reserve('b'*64,record());w=writer(b);f=w.claim(99)
 out=w.publish(99,f,previous=None,release_id='c'*64,artifacts=artifact_map())
 target=sdk.state['current'] if section=='current' else sdk.state['releases'][out['publication_id']] if section=='release' else sdk.state['requests']['b'*64]
 target[field]=value
 with pytest.raises(ValueError):b.read()
