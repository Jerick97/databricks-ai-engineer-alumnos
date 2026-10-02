"""Synthetic GET responses exercise a real adapter; no cloud calls or E2E."""
import pytest


def test_registry_adapter_is_available():
    from sbs.genie.publication_registry import HistoryRegistryBuilder,PublisherPolicy,RegistryAdmin,RegistryLookup
    assert HistoryRegistryBuilder and PublisherPolicy and RegistryAdmin and RegistryLookup


def fixture():
    from copy import deepcopy
    from test_genie_publication import inputs,plan,SDK,reader
    from sbs.genie.publication_registry import PublisherPolicy,HistoryRegistryBuilder
    config,bundle=inputs();sdk=SDK(bundle);submit=sdk.execute_statement;observed={}
    def execute(**kw):
        r=submit(**kw);sid='fixture-stmt-'+str(len(sdk.calls));r['statement_id']=sid
        observed[sid]=dict(query_id=sid,query_text=kw['statement'],warehouse_id='warehouse',executed_as_user_id=2,
            status='FINISHED',is_final=True,statement_type='SELECT' if kw['statement'].startswith('SELECT') else 'OTHER',query_start_time_ms=10,execution_end_time_ms=20)
        return r
    sdk.execute_statement=execute;cert=reader(sdk).read(plan())
    class History:
        def __init__(self):self.calls=[];self.override=None
        def list(self,**kw):
            self.calls.append(kw)
            if self.override:return self.override(kw)
            return dict(res=[deepcopy(observed[kw['filter_by'].statement_ids[0]])],has_next_page=False)
    h=History();p=PublisherPolicy(cert.sha256,config['mapping_sha256'],bundle['snapshot_hash'],bundle['config_hash'],'FIXTURE PUBLISHER','warehouse',2,1000,1000,'fixture')
    return HistoryRegistryBuilder(h,p,clock=lambda:100),cert,h,observed,p


def test_exact_32_get_observations_are_sealed_and_registry_roundtrips(tmp_path):
    from sbs.genie.publication_registry import RegistryAdmin,RegistryLookup,validate_entry
    b,cert,h,rows,p=fixture();entry=b.build(cert);payload=validate_entry(entry)
    assert len(h.calls)==32 and all(x['filter_by'].warehouse_ids==['warehouse'] and x['max_results']==2 for x in h.calls)
    assert len({x['filter_by'].statement_ids[0] for x in h.calls})==32
    assert payload['registry']['evidence_mode']=='fixture' and payload['registry']['valid_from_ms']==100
    assert payload['history_records'][0]['query_text']==next(iter(rows.values()))['query_text']
    admin=RegistryAdmin(tmp_path/'registry',administrator='SERVER TEST ADMIN',clock=lambda:200)
    key=admin.publish(entry);lookup=RegistryLookup(tmp_path/'registry')
    assert lookup(certificate_sha256=key)==payload['registry']
    assert not hasattr(lookup,'publish') and not hasattr(lookup,'revoke')
    admin.publish(entry)
    admin.revoke(key,reason='identity_change')
    assert lookup(certificate_sha256=key)['status']=='revoked'
    assert admin.revoke(key,reason='administrative')['reason']=='identity_change'
    with pytest.raises(ValueError,match='REVOKED'):admin.publish(entry)


@pytest.mark.parametrize('field,value',[('query_id','wrong'),('query_text','SELECT 1'),('warehouse_id','other'),('executed_as_user_id',True),('executed_as_user_id',2.0),('status','FAILED'),('is_final',1),('cache_query_id','cache'),('error_message','oops'),('query_start_time_ms',False),('execution_end_time_ms',101),('statement_type','INSERT')])
def test_history_mismatch_fails_closed(field,value):
    b,cert,h,rows,p=fixture();next(iter(rows.values()))[field]=value
    with pytest.raises(ValueError):b.build(cert)


@pytest.mark.parametrize('response',[{}, {'res':[]}, {'res':[{},{}]}, {'res':[],'has_next_page':True}, {'res':[],'has_next_page':False,'next_page_token':'contradiction'}, {'res':[],'has_next_page':1}])
def test_missing_duplicate_and_malformed_history(response):
    b,cert,h,rows,p=fixture();h.override=lambda kw:response
    with pytest.raises(ValueError):b.build(cert)


def test_pagination_bounded_and_duplicate_ids_rejected_before_get():
    b,cert,h,rows,p=fixture();h.override=lambda kw:dict(res=[],has_next_page=True,next_page_token='repeated')
    with pytest.raises(ValueError,match='PAGINATION'):b.build(cert)
    assert len(h.calls)==2


def test_future_and_stale_readback_rejected():
    b,cert,h,rows,p=fixture();b.clock=lambda:5000
    with pytest.raises(ValueError,match='TIME_OUTSIDE'):b.build(cert)
    b.clock=lambda:19
    with pytest.raises(ValueError,match='TIME_OUTSIDE'):b.build(cert)


def test_denied_is_distinct_and_no_raw_provider_error():
    b,cert,h,rows,p=fixture()
    def denied(kw):raise PermissionError('secret provider details')
    h.override=denied
    with pytest.raises(PermissionError,match='^PUBLISHER_HISTORY_DENIED$'):b.build(cert)


def test_entry_tamper_and_mode_mismatch_reject(tmp_path):
    from sbs.genie.publication_registry import RegistryEntry,RegistryAdmin,HistoryRegistryBuilder
    from sbs.genie import canonical
    from dataclasses import replace
    b,cert,h,rows,p=fixture();entry=b.build(cert);data=entry.as_dict();data['registry']['status']='active';data['history_records'][0]['query_text']='SELECT 1'
    with pytest.raises(ValueError):RegistryAdmin(tmp_path/'r',administrator='server').publish(RegistryEntry(canonical(data).encode()))
    h.calls=[]
    with pytest.raises(ValueError,match='PIN'):HistoryRegistryBuilder(h,replace(p,evidence_mode='real')).build(cert)
    assert h.calls==[]


def test_registry_paths_symlinks_and_corruption(tmp_path):
    from sbs.genie.publication_registry import RegistryAdmin,RegistryLookup
    b,cert,h,rows,p=fixture();entry=b.build(cert);admin=RegistryAdmin(tmp_path/'r',administrator='server');key=admin.publish(entry)
    (tmp_path/'escape').symlink_to(tmp_path/'r',target_is_directory=True)
    with pytest.raises(OSError):RegistryLookup(tmp_path/'escape')
    target=tmp_path/'r'/(key+'.json');original=target.read_bytes();target.unlink();target.symlink_to(tmp_path/'outside')
    with pytest.raises(OSError):admin.lookup(certificate_sha256=key)
    target.unlink();target.write_bytes(original.replace(b'FINISHED',b'FAILED'))
    with pytest.raises(ValueError):admin.lookup(certificate_sha256=key)
    with pytest.raises(ValueError):admin.lookup(certificate_sha256='../escape')


def test_valid_pagination_observes_one_record():
    from copy import deepcopy
    b,cert,h,rows,p=fixture()
    def pages(kw):
        if 'page_token' not in kw:return dict(res=[],has_next_page=True,next_page_token='p2')
        return dict(res=[deepcopy(rows[kw['filter_by'].statement_ids[0]])],has_next_page=False)
    h.override=pages
    assert b.build(cert).as_dict()['registry']['readback_execution_verified'] is True
    assert len(h.calls)==64


def test_installed_sdk_transport_is_get_only():
    from databricks.sdk.service.sql import QueryHistoryAPI
    from types import SimpleNamespace
    from copy import deepcopy
    b,cert,h,rows,p=fixture()
    class API:
        _cfg=SimpleNamespace(workspace_id=None)
        def __init__(self):self.calls=[]
        def do(self,method,path,**kwargs):
            self.calls.append((method,path,kwargs))
            sid=kwargs['query']['filter_by']['statement_ids'][0]
            return dict(res=[deepcopy(rows[sid])],has_next_page=False)
    api=API();b.history=QueryHistoryAPI(api)
    assert b.build(cert).as_dict()['registry']['status']=='active'
    assert len(api.calls)==32 and all(c[:2]==('GET','/api/2.0/sql/history/queries') for c in api.calls)


def test_registry_adapter_can_supply_delta_contract_with_explicit_doubles(tmp_path):
    from test_genie_delta_runtime import setup_delta
    from sbs.genie.publication_registry import PublisherPolicy,HistoryRegistryBuilder,RegistryAdmin
    from sbs.genie.publication import _sqls
    from sbs.genie.delta import DeltaPublication
    from sbs.genie.runtime import load_runtime_binding
    from dataclasses import replace
    binding,ctx,sdk,history,registry,gov,ident,calls,deps=setup_delta(tmp_path)
    cap=deps.delta_publication;cert=cap.certificate;p=cert.as_dict();rows={}
    for t in p['tables']:
        sqls=_sqls(t)
        for i,e in enumerate(t['evidence']):
            rows[e['statement_id']]=dict(query_id=e['statement_id'],query_text=sqls[i if i<3 else 0],warehouse_id='publisher',executed_as_user_id=2,
                status='FINISHED',is_final=True,statement_type='SELECT' if i==2 else 'OTHER',query_start_time_ms=1,execution_end_time_ms=2)
    class History:
        def list(self,**kw):return dict(res=[rows[kw['filter_by'].statement_ids[0]]],has_next_page=False)
    policy=PublisherPolicy(cert.sha256,cap.mapping_sha256,p['snapshot'],p['config_hash'],'EXPLICIT TEST DOUBLE','publisher',2,10**15,1000,'real')
    entry=HistoryRegistryBuilder(History(),policy,clock=lambda:50).build(cert)
    admin=RegistryAdmin(tmp_path/'registry',administrator='TEST ADMIN');admin.publish(entry)
    live_shape=DeltaPublication(cert,cert.sha256,cap.mapping_sha256,admin.lookup,cap.identity_access_probe)
    bound=load_runtime_binding(tmp_path,dependencies=replace(deps,delta_publication=live_shape))
    assert bound.ask_scoped('count',context=ctx)['status']=='completed'
    admin.revoke(cert.sha256,reason='retention_lost');sdk.calls.clear()
    assert bound.ask_scoped('count',context=ctx)['status']=='unavailable' and sdk.calls==[]


def test_noncanonical_certificate_does_not_lose_its_byte_pin():
    import json
    from dataclasses import replace
    from sbs.genie.publication import Certificate
    from sbs.genie.publication_registry import HistoryRegistryBuilder
    b,cert,h,rows,p=fixture();altered=Certificate(json.dumps(cert.as_dict(),indent=2).encode())
    b=HistoryRegistryBuilder(h,replace(p,certificate_sha256=altered.sha256))
    with pytest.raises(ValueError,match='CANONICAL_CERTIFICATE'):b.build(altered)
    assert h.calls==[]


@pytest.mark.parametrize('formatting',['indent','reordered'])
def test_noncanonical_registry_entry_rejects_before_append_only_slot(tmp_path,formatting):
    import json
    from sbs.genie.publication_registry import RegistryAdmin,RegistryEntry
    b,cert,h,rows,p=fixture();entry=b.build(cert);data=entry.as_dict()
    raw=(json.dumps(data,indent=2) if formatting=='indent' else json.dumps(dict(reversed(list(data.items()))),separators=(',',':'))).encode()
    admin=RegistryAdmin(tmp_path/'r',administrator='server')
    with pytest.raises(ValueError,match='CANONICAL_ENTRY'):admin.publish(RegistryEntry(raw))
    assert admin.lookup(certificate_sha256=cert.sha256) is None
    key=admin.publish(entry);original=(tmp_path/'r'/(key+'.json')).read_bytes()
    with pytest.raises(ValueError,match='CANONICAL_ENTRY'):admin.publish(RegistryEntry(raw))
    assert (tmp_path/'r'/(key+'.json')).read_bytes()==original
    assert admin.lookup(certificate_sha256=key)==entry.as_dict()['registry']
