"""Runtime routing tests; injected unavailable binding is not live Genie."""
import pytest
import sbs.runtime as runtime

class UnavailableBinding:
    genie_snapshot='a'*64
    mapping_sha256='c'*64
    rag_snapshot=None
    def ask_scoped(self, question, *, context):
        return {'status':'unavailable','limitations':['Genie requiere publicación y permisos verificados.']}

@pytest.fixture
def service(monkeypatch,tmp_path):
    service=runtime.create_service()
    service.genie_binding=UnavailableBinding()
    service.genie_binding.rag_snapshot=service.snapshot
    (tmp_path/'runs').mkdir()
    monkeypatch.setattr(runtime,'ROOT',tmp_path)
    def forbidden():raise AssertionError('Pure counts must not initialize generation or embedding')
    monkeypatch.setattr(service,'initialize_models',forbidden)
    return service

def test_unavailable_genie_count_is_explicit_without_initializing_models(service):
    out=service.ask('isolated-session','¿Cuántos registros hay en esa disposición?','cyber-504','art20.3')
    assert out['status']=='structured_result_unavailable'
    assert out['answer'] and 'Genie' in out['answer']
    assert service.generator is None and service.embedding is None
    assert service.last_result['trace']['routes']==['genie']
    assert 'generator' not in service.last_result['trace']['calls']['real']
    assert service.last_result['trace']['calls']['real']['genie']==1


def test_normative_route_does_not_load_genie_configuration(service,monkeypatch):
    calls=[]
    def forbidden_genie():
        calls.append('called')
        raise ValueError('broken_genie_export')
    monkeypatch.setattr(service,'initialize_genie',forbidden_genie)
    out=service.ask('s2','¿Qué cambió antes y después?','cyber-504','art20.3')
    assert not calls
    assert out['status']=='insufficient_evidence'  # Models deliberately forbidden in this fixture.


def test_bad_genie_configuration_returns_unavailable_without_models(service,monkeypatch):
    monkeypatch.setattr(service,'initialize_genie',lambda:(_ for _ in ()).throw(ValueError('invalid_export')))
    out=service.ask('s3','¿Cuántos registros hay?','cyber-504','art20.3')
    assert out['status']=='structured_result_unavailable' and service.generator is None


class VerifiedCountFixture(UnavailableBinding):
    def ask_scoped(self,question,*,context):
        from copy import deepcopy
        params={'family':context['family'],'corpus_hash':'e'*64,'provision_id':context['selected_provision_id']}
        for side in ('before','after'):
            for key in ('document_id','version_id'):params[side+'_'+key]=context['pair'][side][key]
        return {'status':'completed','kind':'structured_query_result','snapshot':self.genie_snapshot,
            'context':deepcopy(context),'scope_verified':True,'scope_verification':'exact_executed_reference_sql_and_pinned_rows',
            'reference_query_id':'provision_count','rows':[['2']],'columns':['provision_row_count'],
            'query':'SELECT COUNT(*) FROM fixture','query_id':'fixture-query','parameters':params,
            'source_tables':['fixture.sbs_radar.provisions'],'lineage':{'snapshot':self.genie_snapshot,
            'corpus_hash':'e'*64,'pair':deepcopy(context['pair']),'selected_provision_id':context['selected_provision_id'],'rows':[]},
            'limitations':['Injected fixture, not a real Genie execution.']}


def test_count_wrapper_reaches_channel_with_meaning_and_distinct_snapshot(service):
    service.genie_binding=VerifiedCountFixture();service.genie_binding.rag_snapshot=service.snapshot
    out=service.ask('s4','¿Cuántos registros hay?','cyber-504','art20.3')
    assert out['status']=='answered_structured'
    assert out['answer'].startswith('2 filas de disposiciones.')
    assert 'no cuenta cambios materiales' in out['answer']
    assert out['structured_results'][0]['snapshot']!=service.snapshot
    assert out['citations']==[] and service.generator is None


def test_cross_family_counts_keep_two_separate_scopes(service):
    service.genie_binding=VerifiedCountFixture();service.genie_binding.rag_snapshot=service.snapshot
    out=service.ask('s5','¿Cuántos registros hay?','cyber-504','art20.3',True)
    assert out['status']=='answered_structured' and len(out['structured_results'])==2
    assert {w['context']['family'] for w in out['structured_results']}=={'cybersecurity','market_conduct'}
    assert service.generator is None and out['citations']==[]
