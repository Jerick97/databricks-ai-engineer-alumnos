"""Actual223 result fixtures; no remote requests or invented expected counts."""
import os,json,copy,shutil,subprocess,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[2]
INNER=os.environ.get('SBS_TEST_OVERLAY225')=='1'
only=pytest.mark.skipif(not INNER,reason='isolated225 overlay')
def test_isolated_overlay225(tmp_path):
    if INNER:pytest.skip('outer launcher')
    for name in ('src','contracts','config'):shutil.copytree(ROOT/name,tmp_path/name)
    for n in ('sk06-platform-counts-223-overlay','sk06-genie-result-225-overlay'):
        p=ROOT/'runs'/n/'source/src'
        if p.exists():shutil.copytree(p,tmp_path/'src',dirs_exist_ok=True)
    names=['test_genie_result_225.py','test_platform_counts_223.py','test_immutable_snapshot_221.py','test_genie_governance.py','test_genie_delta_runtime.py','test_publication_rotation_078.py']
    result=subprocess.run([sys.executable,'-m','pytest',*[str(ROOT/'tests/unit'/n) for n in names],'-q','-o','pythonpath='+str(tmp_path/'src'),'-k','not isolated_overlay'],cwd=ROOT,env={**os.environ,'SBS_TEST_OVERLAY225':'1','SBS_TEST_OVERLAY223':'1','SBS_TEST_OVERLAY221':'1','PYTHONPATH':str(tmp_path/'src')+os.pathsep+str(ROOT/'tests/unit')},capture_output=True,text=True,timeout=120)
    print(result.stdout);assert result.returncode==0,result.stdout+result.stderr

def actuals():return json.loads((ROOT/'runs/ui223/genie-query-results-raw.json').read_text())

@only
def test_actual_sdk_loss_then_raw_preservation_and_decode():
    from sbs.genie.result225 import RawResultGenie,decode_result
    from databricks.sdk.service.dashboards import GenieAPI,GenieGetMessageQueryResultResponse
    from sbs.genie import GenieAdapter
    messages=json.loads((ROOT/'runs/ui223/genie-messages-observed.json').read_text())
    for conv,raw in actuals().items():
        msg=messages[conv]['messages'][0];calls=[]
        class Transport:
            _cfg=type('Cfg',(),{'workspace_id':None})()
            def do(self,method,path,**kwargs):
                calls.append((method,path))
                if path.endswith('/query-result'):return copy.deepcopy(raw)
                if method=='POST':return {'conversation_id':conv,'message_id':msg['message_id']}
                return copy.deepcopy(msg)
        t=Transport();sdk=GenieAPI(t);wrapped=RawResultGenie(sdk,t)
        assert 'data_typed_array' not in GenieGetMessageQueryResultResponse.from_dict(raw).as_dict()['statement_response']['result']
        preserved=wrapped.get_message_query_result(space_id=msg['space_id'],conversation_id=conv,message_id=msg['message_id'])
        assert preserved==raw and calls==[('GET',f"/api/2.0/genie/spaces/{msg['space_id']}/conversations/{conv}/messages/{msg['message_id']}/query-result")]
        rows=decode_result(preserved['statement_response'])
        expected=[[cell['str'] for cell in row['values']] for row in raw['statement_response']['result']['data_typed_array']]
        assert rows==expected
        cfg={'namespace':'sbs_radar','warehouse_id':'w','space_id':msg['space_id'],'snapshot':'snap','max_polls':1}
        permissions=lambda:dict(warehouse_id='w',snapshot='snap',can_use=True,tables_read=True,genie_access=True,read_only_backend=True,scope_verified=True,state='RUNNING',warehouse_type='PRO')
        decoded=GenieAdapter(wrapped,cfg,permissions).ask('fixture replay')
        assert decoded['status']=='completed' and decoded['rows']==expected
        from sbs.genie import ScopedCatalog,TABLES
        cfg_live=json.loads((ROOT/'runs/sk06-platform-counts-223-overlay/source/config/genie-runtime-068.json').read_text())
        bundle_path=ROOT/cfg_live['bundle_path'];bundle=json.loads((bundle_path/'manifest.json').read_text())
        bundle['tables']={t:[json.loads(line) for line in (bundle_path/(t+'.jsonl')).read_text().splitlines()] for t in TABLES}
        certificate=json.loads((ROOT/'deployment/state/fresh-readback-219/certificate.json').read_text())
        versions={t['full_name']:t['delta_version'] for t in certificate['tables']}
        catalog=ScopedCatalog(bundle,cfg_live['contexts'],table_prefix=cfg_live['table_prefix'],delta_versions=versions,counts_only=True)
        context=json.loads(msg['content'].split('Resolved documentary scope: ')[1].split('\nUse one')[0])
        histories=json.loads((ROOT/'runs/ui223/counts-first-query-history.json').read_text())['res'];lookups=[]
        def history(query_id):
            lookups.append(query_id);row=next(row for row in histories if row['query_id']==query_id)
            return {'query_id':query_id,'snapshot':catalog.snapshot,'state':'SUCCEEDED','statement':row['query_text'],'parameters':{},'parameter_mode':'executed_literals','source_tables':[cfg_live['table_prefix']+'.documents']}
        cfg['snapshot']=catalog.snapshot
        permissions=lambda:dict(warehouse_id='w',snapshot=catalog.snapshot,can_use=True,tables_read=True,genie_access=True,read_only_backend=True,scope_verified=True,state='RUNNING',warehouse_type='PRO')
        scoped=GenieAdapter(wrapped,cfg,permissions,scope_catalog=catalog,execution_probe=history).ask_scoped('¿Cuántas versiones documentales hay por familia?',context=context)
        assert scoped['status']=='completed' and scoped['scope_verified'] is True and scoped['rows']==expected
        assert lookups==[raw['statement_response']['statement_id']]

@only
@pytest.mark.parametrize('mutation',['format','extra_variant','negative','decimal','overflow','boolean','missing','truncated','chunks','offset','width','column','row_count','dual'])
def test_closed_proto_rejects_malformed(mutation):
    from sbs.genie.result225 import decode_result
    s=copy.deepcopy(next(iter(actuals().values()))['statement_response']);m=s['manifest'];d=s['result'];v=d['data_typed_array'][0]['values'][0]
    if mutation=='format':m['format']='ARROW_STREAM'
    elif mutation=='extra_variant':v['int']=2
    elif mutation=='negative':v['str']='-1'
    elif mutation=='decimal':v['str']='2.0'
    elif mutation=='overflow':v['str']=str(2**63)
    elif mutation=='boolean':v['str']=True
    elif mutation=='missing':d.pop('data_typed_array')
    elif mutation=='truncated':m['truncated']=True
    elif mutation=='chunks':m['total_chunk_count']=2
    elif mutation=='offset':d['row_offset']=1
    elif mutation=='width':d['data_typed_array'][0]['values'].append({'str':'3'})
    elif mutation=='column':m['schema']['columns'][0]['name']='untrusted'
    elif mutation=='row_count':d['row_count']=2
    else:d['data_array']=[['2']]
    with pytest.raises(ValueError):decode_result(s)

@only
def test_json_array_legacy_and_values_not_hardcoded():
    from sbs.genie.result225 import decode_result
    s=copy.deepcopy(next(iter(actuals().values()))['statement_response'])
    for v in ('0','123','9223372036854775807'):
        s['result']['data_typed_array'][0]['values'][0]['str']=v
        assert decode_result(s)==[[v]]
    s['manifest']['format']='JSON_ARRAY';s['result'].pop('data_typed_array');s['result']['data_array']=[['19']]
    assert decode_result(s)==[['19']]
