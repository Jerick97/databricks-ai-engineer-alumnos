"""SK06 provenance hardening fixtures: no execution or cloud success claim."""
from copy import deepcopy
import importlib
import importlib.util
import json
from pathlib import Path
import pytest
from test_genie import scoped_fixture


def provenance():
    assert importlib.util.find_spec('sbs.genie.provenance'), 'provenance module missing'
    return importlib.import_module('sbs.genie.provenance')


def literal_plan():
    p=provenance(); adapter,contexts,sdk,receipt,catalog=scoped_fixture()
    plan=catalog.references(contexts[0])['provision_count']
    return p,adapter,contexts,sdk,receipt,catalog,plan


def test_literalized_query_is_verified_from_executed_ast():
    p,a,ctx,sdk,r,cat,plan=literal_plan()
    r.update(statement=p.literalize_reference(plan['sql'],plan['parameters']),parameters={},parameter_mode='executed_literals')
    out=a.ask_scoped('count',context=ctx[0])
    assert out['status']=='completed' and out['parameters']==plan['parameters']
    assert out['parameters_origin']=='verified_executed_literal_values'


@pytest.mark.parametrize('mutation',[
    lambda s:s.replace("'cybersecurity'","'market_conduct'"),
    lambda s:s.split(' WHERE ')[0],
    lambda s:s+' OR 1=1',
    lambda s:s+'; DROP TABLE test_catalog.sbs_radar.provisions',
    lambda s:s.replace('COUNT(*)','COUNT(DISTINCT id)'),
    lambda s:s.replace('test_catalog.sbs_radar.provisions','other.sbs_radar.provisions'),
    lambda s:s+' -- hidden suffix',
    lambda s:s.replace("'cybersecurity'", "'cyber\\security'")])
def test_literal_ast_rejects_scope_mutations(mutation):
    p,a,ctx,sdk,r,cat,plan=literal_plan()
    r.update(statement=mutation(p.literalize_reference(plan['sql'],plan['parameters'])),parameters={},parameter_mode='executed_literals')
    assert a.ask_scoped('count',context=ctx[0])['status']=='conflict'


def test_literal_ast_allows_whitespace_backticks_but_not_unbound_markers():
    p,a,ctx,sdk,r,cat,plan=literal_plan()
    sql=p.literalize_reference(plan['sql'],plan['parameters']).replace('test_catalog.sbs_radar.provisions','`test_catalog`.`sbs_radar`.`provisions`').replace('SELECT','select\n')
    assert p.matches_literal_reference(sql,plan['sql'],plan['parameters'])
    assert not p.matches_literal_reference(plan['sql'],plan['sql'],plan['parameters'])


def test_literal_values_with_escapes_are_conservatively_unsupported():
    p=provenance()
    for value in ("a'b",'a\\b','a\nb'):
        with pytest.raises(ValueError):p.literalize_reference('SELECT :family',{'family':value})


class History:
    def __init__(self,row):self.row=row;self.calls=[]
    def list(self,**kwargs):self.calls.append(kwargs);return {'res':[deepcopy(self.row)],'has_next_page':False}


def probe_fixture():
    p,a,ctx,sdk,r,cat,plan=literal_plan()
    row=dict(query_id='qid',query_text=p.literalize_reference(plan['sql'],plan['parameters']),status='FINISHED',is_final=True,
             warehouse_id='wh',executed_as_user_id=42,statement_type='SELECT',query_start_time_ms=100,execution_end_time_ms=200,
             query_source={'genie_space_id':'space'})
    history=History(row)
    certificate=dict(snapshot=cat.snapshot,source_tables=plan['source_tables'],attestation_id='verified-publication-1',
                     table_content_sha256={plan['source_tables'][0]:'a'*64},valid_from_ms=0,valid_until_ms=1000)
    lookup=lambda **kwargs:deepcopy(certificate)
    probe=p.DatabricksHistoryProbe(history,warehouse_id='wh',space_id='space',executor_id=42,snapshot=cat.snapshot,
        table_content_sha256={plan['source_tables'][0]:'a'*64},publication_lookup=lookup)
    return probe,history,certificate,cat


def test_realistic_get_history_probe_uses_ids_and_independent_publication_receipt():
    probe,h,cert,cat=probe_fixture();r=probe('qid')
    assert r['query_id']=='qid' and r['snapshot']==cat.snapshot and r['parameter_mode']=='executed_literals'
    assert r['parameters']=={} and r['execution_provenance']['provider']=='databricks_query_history_get'
    assert h.calls[0]['filter_by'].statement_ids==['qid']
    assert h.calls[0]['filter_by'].warehouse_ids==['wh']


@pytest.mark.parametrize('field,value', [('query_id','wrong'),('warehouse_id','other'),('executed_as_user_id',7),('status','FAILED'),('is_final',False),('query_source',{}),('cache_query_id','cached'),('query_text','SELECT :unknown'),('execution_end_time_ms',None)])
def test_history_provenance_mismatch_declines(field,value):
    probe,h,cert,cat=probe_fixture();h.row[field]=value
    with pytest.raises(ValueError):probe('qid')


@pytest.mark.parametrize('change',[{'valid_until_ms':150},{'snapshot':'forged'},{'table_content_sha256':{}},{'attestation_id':''}])
def test_history_without_publication_coverage_declines(change):
    probe,h,cert,cat=probe_fixture();cert.update(change)
    with pytest.raises(ValueError):probe('qid')


def test_history_unknown_or_duplicated_statement_declines():
    probe,h,cert,cat=probe_fixture()
    h.list=lambda **kw:{'res':[]}
    with pytest.raises(ValueError):probe('qid')
    h.list=lambda **kw:{'res':[h.row,h.row]}
    with pytest.raises(ValueError):probe('qid')


def test_source_snapshot_mapping_preserves_distinct_hashes():
    p=provenance();mapping=p.build_project_snapshot_mapping(Path(__file__).resolve().parents[2])
    assert mapping['sk06_snapshot']!=mapping['rag_snapshot']
    assert mapping['status']=='source_and_raw_page_compatible' and len(mapping['sources'])==6
    assert mapping['matched_citations']==135 and len(mapping['pair_mappings'])==3
    assert mapping['semantic_provision_ids_equivalent'] is False


def test_mapping_rejects_wrong_source_even_resealed_hash():
    p=provenance();root=Path(__file__).resolve().parents[2]
    inputs=p.snapshot_inputs(root);inputs['rag_corpus'][0]['original_sha256']='f'*64
    with pytest.raises(ValueError):p.reconcile_snapshots(**inputs)


def test_mapping_rejects_mismatching_citation_family_and_text():
    p=provenance();root=Path(__file__).resolve().parents[2]
    for field,value in [('family','cybersecurity'),('citation',{})]:
        inputs=p.snapshot_inputs(root);inputs['rag_records'][0][field]=value
        with pytest.raises(ValueError):p.reconcile_snapshots(**inputs)


def test_selected_article_absent_from_curated_rows_is_not_zero():
    p,a,ctx,sdk,r,cat,plan=literal_plan()
    # A trusted registry can contain a semantic focus absent from raw-page tables;
    # this should refuse, not report zero documentary provision rows.
    c=deepcopy(ctx[0]);c['selected_provision_id']='art999';c['context_id']='missing'
    cat._contexts[c['context_id']]=c
    with pytest.raises(ValueError):cat.references(c)


@pytest.mark.parametrize('field,value',[('query_source',None),('error_message','failed despite final'),('query_text',None)])
def test_malformed_or_contradictory_history_is_rejected(field,value):
    probe,h,cert,cat=probe_fixture();h.row[field]=value
    with pytest.raises(ValueError):probe('qid')


def test_mapping_resealed_wrong_original_still_rejected():
    p=provenance();inputs=p.snapshot_inputs(Path(__file__).resolve().parents[2])
    inputs['rag_corpus'][0]['original_sha256']='f'*64
    inputs['rag_protocol_envelope']['payload']['corpus_hash']=p.digest(inputs['rag_corpus'])
    inputs['rag_protocol_envelope']['sha256']=p.digest(inputs['rag_protocol_envelope']['payload'])
    with pytest.raises(ValueError,match='LINEAGE'):p.reconcile_snapshots(**inputs)


def test_history_permission_error_is_sanitized_and_classified():
    probe,h,cert,cat=probe_fixture()
    class Denied(Exception):error_code='PERMISSION_DENIED'
    def denied(**kw):raise Denied('secret arbitrary upstream text')
    h.list=denied
    with pytest.raises(PermissionError,match='HISTORY_ACCESS_DENIED') as exc:probe('qid')
    assert 'secret' not in str(exc.value)


def test_mapping_relocated_without_original_reads(tmp_path, monkeypatch):
    import shutil
    p=provenance();root=Path(__file__).resolve().parents[2]
    expected=p.build_project_snapshot_mapping(root)
    for name in expected['input_files']:
        target=tmp_path/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(root/name,target)
    original=Path.open
    def guarded(path,*args,**kwargs):
        assert not any(path.resolve().is_relative_to(root/d) for d in ('runs','data','context')), 'original corpus read'
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'open',guarded)
    assert p.build_project_snapshot_mapping(tmp_path)==expected


def test_mapping_relocated_rejects_external_symlink(tmp_path):
    import shutil
    p=provenance();root=Path(__file__).resolve().parents[2]
    inputs=p.snapshot_inputs(root)
    for name in inputs['input_files']:
        target=tmp_path/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(root/name,target)
    capture=json.loads((tmp_path/'runs/sk02-repository-capture.json').read_text())
    from sbs.paths import project_path
    target=project_path(tmp_path,capture['sources'][0]['original_path'])
    target.unlink();target.symlink_to(root/target.relative_to(tmp_path))
    with pytest.raises(ValueError):p.build_project_snapshot_mapping(tmp_path)
