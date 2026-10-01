"""Real local export checks; injected remote boundaries are doubles, not E2E."""
from pathlib import Path
import json
import shutil
import pytest
ROOT=Path(__file__).resolve().parents[2]


def test_pending_configuration_calls_no_remote():
    from sbs.genie.runtime import load_runtime_binding
    binding=load_runtime_binding(ROOT)
    assert binding.genie_snapshot!=binding.rag_snapshot
    assert binding.readiness()['status']=='unavailable'
    context=binding.contexts[0]
    out=binding.ask_scoped('count',context=context)
    assert out['status']=='unavailable' and out['scope_verified'] is False and out['rows']==[]
    assert out['snapshot']==binding.genie_snapshot


def copy_inputs(tmp):
    config=json.loads((ROOT/'config/genie-pilot-002.json').read_text())
    mapping=json.loads((ROOT/config['snapshot_map_path']).read_text())
    names=set(mapping['input_files'])|{'config/genie-pilot-002.json'}
    names.update(str(p.relative_to(ROOT)) for p in (ROOT/config['bundle_path']).iterdir() if p.is_file())
    for name in names:
        dest=tmp/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
    return config


def test_relocated_binding_and_export_tamper(tmp_path,monkeypatch):
    from sbs.genie.runtime import load_runtime_binding
    config=copy_inputs(tmp_path);original=Path.open
    def guarded(p,*a,**k):
        assert not any(p.resolve().is_relative_to(ROOT/d) for d in ('runs','data','context','config'))
        return original(p,*a,**k)
    monkeypatch.setattr(Path,'open',guarded)
    assert load_runtime_binding(tmp_path).readiness()['status']=='unavailable'
    (tmp_path/config['bundle_path']/'provisions.jsonl').write_text('{}\n')
    with pytest.raises(ValueError):load_runtime_binding(tmp_path)


def test_no_certificate_never_calls_genie(tmp_path):
    from sbs.genie.runtime import load_runtime_binding,ServerDependencies
    config=copy_inputs(tmp_path);config.update(warehouse_id='warehouse',space_id='space')
    (tmp_path/'config/genie-pilot-002.json').write_text(json.dumps(config))
    class Forbidden:
        def __getattr__(self,name):raise AssertionError('REMOTE_CALL_FORBIDDEN')
    deps=ServerDependencies(genie=Forbidden(),query_history=Forbidden(),permission_probe=lambda: {},publication_lookup=lambda **kw:None,executor_id=1)
    binding=load_runtime_binding(tmp_path,dependencies=deps)
    out=binding.ask_scoped('count',context=binding.contexts[0])
    assert out['status']=='unavailable' and out['reason']=='PUBLICATION_NOT_VERIFIED'


def test_wrong_context_rejected_before_any_dependency(tmp_path):
    from sbs.genie.runtime import load_runtime_binding
    binding=load_runtime_binding(ROOT);context=binding.contexts[0];context['family']='market_conduct'
    result=binding.ask_scoped('count',context=context)
    assert result['status']=='conflict' and result['rows']==[]


def test_public_metadata_cannot_relabel_snapshots():
    from sbs.genie.runtime import load_runtime_binding
    binding=load_runtime_binding(ROOT)
    with pytest.raises(AttributeError):binding.genie_snapshot=binding.rag_snapshot
    with pytest.raises(AttributeError):binding.mapping_sha256='f'*64
    copied=binding.snapshot_map;copied['mapping_sha256']='f'*64
    assert binding.mapping_sha256!='f'*64


def test_binding_injected_verified_history_preserves_distinct_snapshots(tmp_path):
    from sbs.genie.runtime import load_runtime_binding,ServerDependencies
    from sbs.genie import digest,ScopedCatalog
    from sbs.genie.provenance import literalize_reference
    from test_genie import SDK,grant
    from test_genie_provenance import History
    config=copy_inputs(tmp_path);config.update(warehouse_id='warehouse',space_id='space')
    (tmp_path/'config/genie-pilot-002.json').write_text(json.dumps(config))
    bundle=json.loads((tmp_path/config['bundle_path']/'manifest.json').read_text())
    from sbs.genie import TABLES
    bundle['tables']={t:[json.loads(line) for line in (tmp_path/config['bundle_path']/(t+'.jsonl')).read_text().splitlines()] for t in TABLES}
    context=config['contexts'][0];catalog=ScopedCatalog(bundle,config['contexts'],table_prefix=config['table_prefix'])
    plan=catalog.references(context)['provision_count'];table=plan['source_tables'][0]
    # Explicit remote doubles; this certificate is test data, never evidence of cloud publication.
    certificate={'snapshot':config['snapshot'],'source_tables':[table],'table_content_sha256':{table:digest(bundle['tables']['provisions'])},'attestation_id':'fixture-only','valid_from_ms':0,'valid_until_ms':9999999999999}
    history=History(dict(query_id='q',query_text=literalize_reference(plan['sql'],plan['parameters']),status='FINISHED',is_final=True,
                        warehouse_id='warehouse',executed_as_user_id=1,statement_type='SELECT',query_start_time_ms=100,execution_end_time_ms=200,query_source={'genie_space_id':'space'}))
    sdk=SDK(rows=[['2']]);original=sdk.get_message_query_result
    def result(**kw):
        out=original(**kw);out['statement_response']['manifest']['schema']={'columns':[{'name':'provision_row_count'}]};return out
    sdk.get_message_query_result=result
    grants=grant();grants['snapshot']=config['snapshot']
    deps=ServerDependencies(sdk,history,lambda:grants,lambda **kw:certificate,1)
    binding=load_runtime_binding(tmp_path,dependencies=deps)
    assert sdk.calls==[] and history.calls==[]
    out=binding.ask_scoped('count',context=context)
    assert out['status']=='completed' and out['scope_verified'] is True and out['rows']==[['2']]
    assert out['snapshot']==binding.genie_snapshot and out['lineage']['snapshot']==binding.genie_snapshot
    assert out['rag_snapshot']==binding.rag_snapshot!=binding.genie_snapshot
    assert out['mapping_sha256']==binding.mapping_sha256
    # Global aggregate or mismatched family must fail even after an SDK result.
    history.row['query_text']=history.row['query_text'].split(' WHERE ')[0]
    assert binding.ask_scoped('count',context=context)['status']=='conflict'


def test_independent_config_pin_and_missing_source_fail_closed(tmp_path):
    from sbs.genie.runtime import load_runtime_binding
    config=copy_inputs(tmp_path)
    with pytest.raises(ValueError,match='CONFIG_PIN_MISMATCH'):load_runtime_binding(tmp_path,expected_config_sha256='f'*64)
    mapping=json.loads((tmp_path/config['snapshot_map_path']).read_text())
    source=next(name for name in mapping['input_files'] if name.endswith('.pdf'))
    (tmp_path/source).unlink()
    with pytest.raises(ValueError,match='GENIE_LOCAL_EXPORT_INVALID'):load_runtime_binding(tmp_path)


@pytest.mark.parametrize('field,value',[('target_date','2026-09-27'),('context_id','unregistered')])
def test_entire_context_must_match_registry(field,value):
    from sbs.genie.runtime import load_runtime_binding
    binding=load_runtime_binding(ROOT);context=binding.contexts[0];context[field]=value
    assert binding.ask_scoped('count',context=context)['status']=='conflict'
