"""Deterministic doubles exercise adapter contracts; not real model evidence."""
import json
from types import SimpleNamespace
import numpy as np
import pytest
from tokenizers import Tokenizer, models, pre_tokenizers, processors
from sbs.models.reranker import LocalOnnxReranker, verify_manifest


def tokenizer():
    t = Tokenizer(models.WordLevel({'[UNK]':0,'[CLS]':1,'[SEP]':2,'a':3,'b':4}, unk_token='[UNK]'))
    t.pre_tokenizer = pre_tokenizers.Whitespace()
    t.post_processor = processors.TemplateProcessing(single='[CLS] $A [SEP]', pair='[CLS] $A [SEP] $B:1 [SEP]:1', special_tokens=[('[CLS]',1),('[SEP]',2)])
    return t


class Session:
    def __init__(self, output=None):
        self.calls = []
        self.output = output
    def get_inputs(self):
        return [SimpleNamespace(name=n) for n in ['input_ids','attention_mask','token_type_ids']]
    def run(self, _, inputs):
        self.calls.append(inputs)
        return [np.array([[len(self.calls)]]) if self.output is None else self.output]


def row(text):
    return {'citation': {'text':text, 'citation_id':'original'}}


def test_windows_cover_original_without_mutating_citation():
    session = Session()
    r = LocalOnnxReranker(tokenizer(), session, max_tokens=8)
    text = 'a b ' * 12 + '尾'
    rows = [row(text)]
    assert r('a', rows) == [float(len(session.calls))]
    windows = r.last_trace[0]['windows']
    assert len(windows) > 1
    assert ''.join(text[w['start']:w['end']] for w in windows) == text
    assert all(w['pair_tokens'] <= 8 for w in windows)
    assert rows == [row(text)]
    assert all(x['input_ids'].shape[1] <= 8 for x in session.calls)


def test_query_overflow_rejected_before_inference():
    s = Session()
    with pytest.raises(ValueError, match='query_token_budget'):
        LocalOnnxReranker(tokenizer(), s, max_tokens=8)('a '*5, [row('b')])
    assert not s.calls


@pytest.mark.parametrize('output', [np.array([[float('nan')]]), np.array([[1.,2.]]), np.array([])])
def test_invalid_scores_fail_closed(output):
    with pytest.raises(ValueError, match='invalid_reranker_response'):
        LocalOnnxReranker(tokenizer(), Session(output), max_tokens=8)('a', [row('b')])


def test_hash_verification_rejects_tampering(tmp_path):
    p = tmp_path/'weights'
    p.write_bytes(b'changed')
    manifest = {'revision':'a'*40, 'files': {'config.json': {'path':str(p), 'sha256':'0'*64}}}
    with pytest.raises(ValueError, match='hash_mismatch'):
        verify_manifest(manifest)


def test_preflight_all_rows_before_inference():
    s = Session()
    with pytest.raises(ValueError, match='invalid_citation_text'):
        LocalOnnxReranker(tokenizer(), s, max_tokens=8)('a', [row('b'),row(None)])
    assert not s.calls
