from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import threading
from unittest.mock import patch
import pytest
from sbs.runtime import LocalService
import sbs.operations.runtime_release as loader

@pytest.mark.parametrize('operation',['source','comparison'])
def test_authorized_read_finishes_on_same_snapshot_during_promotion(operation):
    service=LocalService()
    actor=dict(authenticated=True,subject='cyber-reader',role='reader',families=['cybersecurity'])
    view=service.for_actor(actor)
    source_id=next(k for k,v in service.source_families.items() if v=='cybersecurity')
    market_id=next(k for k,v in service.source_families.items() if v=='market_conduct')
    pair=next(p for p in service.pairs if p['family_id']=='cybersecurity')
    key=(pair['id'],pair['provisions'][0]['id'])
    call=(lambda:view.source(source_id)) if operation=='source' else (lambda:view.comparison(*key))
    before=call()
    candidate=dict(snapshot='f'*64,sources={**service.sources,source_id:service.sources[market_id]},
        source_families={**service.source_families,source_id:'market_conduct'},
        release_metadata={'annotation_count':0},entries=deepcopy(service.entries))
    candidate['entries'][key]['context']['family']='market_conduct'
    candidate['entries'][key]['before']['quote_raw']='different-family-candidate'
    authorized=threading.Event();resume=threading.Event();prepared=threading.Event()
    allow=view._allow
    def paused(family,action='chat'):
        allow(family,action);authorized.set();assert resume.wait(5)
    view._allow=paused
    def load(*args,**kw):prepared.set();return candidate
    with ThreadPoolExecutor(max_workers=2) as pool,patch.object(loader,'load_release',side_effect=load):
        reader=pool.submit(call)
        try:
            assert authorized.wait(5)
            acquired=service.lock.acquire(blocking=False)
            if acquired:service.lock.release()
            promoter=pool.submit(service.promote_release,'controlled-candidate',pointer={})
            assert prepared.wait(5)
        finally:resume.set()
        returned=reader.result(timeout=5);promoter.result(timeout=5)
    assert acquired is False, 'Promotion must not interleave authorization and read'
    assert returned==before
    with pytest.raises(PermissionError):call()
