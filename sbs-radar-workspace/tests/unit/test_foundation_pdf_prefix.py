import hashlib
from pathlib import Path
import pytest
from test_foundation import ingest_bytes,pdf

ROOT=Path(__file__).resolve().parents[2]


def test_observed_official_crlf_pdf_preserves_bytes_and_extracts(tmp_path):
    from sbs.foundation import extract
    raw=(ROOT/'data/foundation-holdout/quarantine/090cbc764923809f092f24636b300b2465575295ef909fd151007f05438546b3.pdf').read_bytes()
    assert raw.startswith(b'\r\n%PDF-')
    sources=ingest_bytes(tmp_path,raw)
    assert len(sources)==1
    assert sources[0]['sha256']==hashlib.sha256(raw).hexdigest()
    stored=next((tmp_path/'objects').rglob('*.pdf'));assert stored.read_bytes()==raw
    result=extract(sources[0],root=tmp_path)
    assert len(result['pages'])==2 and '00771-2026' in result['rawtext']


@pytest.mark.parametrize('prefix',[b'<html>',b'arbitrary',b' '*33,b'\x00',b'\xef\xbb\xbf'*2])
def test_arbitrary_or_late_pdf_prefix_rejected(tmp_path,prefix):
    assert ingest_bytes(tmp_path,prefix+pdf('fixture'))==[]
    assert not list((tmp_path/'objects').rglob('*.pdf'))


@pytest.mark.parametrize('prefix',[b'\r\n',b'\xef\xbb\xbf',b' '*32])
def test_bounded_prefix_view_keeps_strict_parser_and_original_hash(tmp_path,prefix):
    from sbs.foundation import extract
    raw=prefix+pdf('FIXTURE prefixed source')
    sources=ingest_bytes(tmp_path,raw)
    assert len(sources)==1 and sources[0]['sha256']==hashlib.sha256(raw).hexdigest()
    result=extract(sources[0],root=tmp_path)
    assert 'FIXTURE prefixed source' in result['rawtext']
    assert result['extractor'].endswith('-prefix-view-v1')


def test_magic_without_real_pdf_rejected(tmp_path):
    assert ingest_bytes(tmp_path,b'\r\n%PDF-1.7\n<html>not PDF</html>')==[]
