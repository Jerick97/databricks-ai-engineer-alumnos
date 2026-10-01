"""Synthetic PDFs only: these tests establish no real family coverage."""
import hashlib
import io
import sqlite3
import pytest
from reportlab.pdfgen.canvas import Canvas
from sbs.contracts import validate_contract


def pdf(*pages):
    stream = io.BytesIO()
    canvas = Canvas(stream, invariant=True)
    for page in pages:
        if page:
            canvas.drawString(30, 700, page)
        canvas.showPage()
    canvas.save()
    return stream.getvalue()


def manifest(**changes):
    return {'allowed_hosts': ['www.sbs.gob.pe'], 'sources': [{
        'document_id': '../../synthetic', 'family': 'cybersecurity',
        'url': 'https://www.sbs.gob.pe/fixture.pdf', 'source_kind': 'normative',
        'synthetic': True, **changes}]}


def ingest_bytes(root, content, **changes):
    from sbs.foundation import ingest
    return ingest(manifest(**changes), 'synthetic-run', root=root,
                  fetcher=lambda url, **kw: (content, url))


def test_retry_deduplicates_object_but_preserves_attempts_and_captures(tmp_path):
    a = ingest_bytes(tmp_path, pdf('SINTETICO obligación'))[0]
    b = ingest_bytes(tmp_path, pdf('SINTETICO obligación'))[0]
    assert a['version_id'] == b['version_id']
    assert validate_contract('SourceDocument', a)['valid']
    assert a['published_on'] is None and a['effective_on'] is None
    assert a['synthetic'] is True
    assert len(list((tmp_path / 'objects').rglob('*.pdf'))) == 1
    with sqlite3.connect(tmp_path / 'foundation.sqlite3') as db:
        assert db.execute('select count(*) from attempts').fetchone()[0] == 2
        assert db.execute('select count(*) from captures').fetchone()[0] == 2
        assert db.execute('select count(*) from documents').fetchone()[0] == 1


def test_changed_bytes_same_url_are_distinct_versions(tmp_path):
    a = ingest_bytes(tmp_path, pdf('SINTETICO uno'))[0]
    b = ingest_bytes(tmp_path, pdf('SINTETICO dos'))[0]
    assert a['version_id'] != b['version_id']
    assert len(list((tmp_path / 'objects').rglob('*.pdf'))) == 2


@pytest.mark.parametrize('content', [b'<html>login</html>', b'%PDF-1.4 broken'])
def test_invalid_pdf_and_retry_failure_remain_visible(tmp_path, content):
    from sbs.foundation import ingest
    assert ingest_bytes(tmp_path, content) == []
    def fail(url, **kw):
        raise OSError('secret-query-token')
    assert ingest(manifest(), 'run', root=tmp_path, fetcher=fail) == []
    assert len(ingest_bytes(tmp_path, pdf('SINTETICO retry'))) == 1
    with sqlite3.connect(tmp_path / 'foundation.sqlite3') as db:
        rows = db.execute('select status,error from attempts').fetchall()
    assert [r[0] for r in rows] == ['failed', 'failed', 'captured']
    assert 'secret-query-token' not in str(rows)


def test_raw_unicode_offsets_page_map_and_idempotent_derivative(tmp_path):
    from sbs.foundation import extract
    source = ingest_bytes(tmp_path, pdf('SINTETICO obligación', 'SINTETICO acción'))[0]
    result = extract(source, root=tmp_path)
    assert result == extract(source, root=tmp_path)
    assert result['layer'] == 'raw_pages'
    assert 'obligación' in result['rawtext']
    assert len(result['pages']) == 2
    for provision in result['provisions']:
        assert validate_contract('Provision', provision)['valid']
        assert result['rawtext'][provision['start']:provision['end']] == provision['text']
        assert provision['synthetic']
    assert len(list((tmp_path / 'derived').rglob('result.json'))) == 1


@pytest.mark.parametrize('pages,changes,limitation', [
    (('',), {}, 'ocr_pending'),
    (('SINTETICO', ''), {}, 'empty_pages'),
    (('SINTETICO Anexo 2',), {'annex_missing': ['Anexo 2']}, 'annex_missing'),
])
def test_quality_limits_are_visible(tmp_path, pages, changes, limitation):
    from sbs.foundation import extract
    source = ingest_bytes(tmp_path, pdf(*pages), **changes)[0]
    result = extract(source, root=tmp_path)
    assert result['quality']['status'] in ('partial', 'pending')
    assert limitation in result['quality']['limitations']


def test_extraction_errors_visible(tmp_path, monkeypatch):
    from sbs.foundation import extract
    from pypdf._page import PageObject
    source = ingest_bytes(tmp_path, pdf('SINTETICO'))[0]
    def fail(*args, **kwargs):
        raise ValueError('bad page')
    monkeypatch.setattr(PageObject, 'extract_text', fail)
    result = extract(source, root=tmp_path)
    assert 'extraction_error' in result['quality']['limitations']
    assert result['provisions'] == []


def test_transport_rejects_unsafe_destination_before_connection(monkeypatch):
    from sbs.foundation.transport import fetch_pdf, TransportError
    import socket
    monkeypatch.setattr(socket, 'getaddrinfo', lambda *a, **k: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('127.0.0.1', 443))])
    with pytest.raises(TransportError):
        fetch_pdf('https://www.sbs.gob.pe/x', allowed_hosts=['www.sbs.gob.pe'])
    with pytest.raises(TransportError):
        fetch_pdf('http://www.sbs.gob.pe/x', allowed_hosts=['www.sbs.gob.pe'])


def test_dns_resolution_timeout_is_bounded(monkeypatch):
    import threading
    import socket
    from sbs.foundation import transport
    finished = threading.Event()
    def stalled(*args, **kwargs):
        finished.wait(1)
        return []
    monkeypatch.setattr(socket, 'getaddrinfo', stalled)
    monkeypatch.setattr(transport, 'TIMEOUT', 0.01)
    import time
    started = time.monotonic()
    try:
        with pytest.raises(transport.TransportError):
            transport.fetch_pdf('https://www.sbs.gob.pe/x', allowed_hosts=['www.sbs.gob.pe'])
        assert time.monotonic() - started < 0.3
    finally:
        finished.set()


@pytest.mark.parametrize('scenario', ['redirect_private', 'peer_private', 'size', 'redirect_loop', 'tls_error'])
def test_transport_fails_closed_at_each_boundary(monkeypatch, scenario):
    from sbs.foundation import transport
    import socket
    requests = []
    class FakeSocket:
        def settimeout(self, seconds):
            pass
        def connect(self, address):
            pass
        def getpeername(self):
            return ('127.0.0.1' if scenario == 'peer_private' else '8.8.8.8', 443)
        def close(self):
            pass
    class FakeContext:
        def wrap_socket(self, sock, *, server_hostname):
            if scenario == 'tls_error':
                raise transport.ssl.SSLError('certificate failure')
            return sock
    class Response:
        status = 302 if scenario.startswith('redirect') else 200
        def getheader(self, name, default=None):
            return {'Location': 'https://127.0.0.1/blocked' if scenario == 'redirect_private'
                    else 'https://www.sbs.gob.pe/again',
                    'Content-Length': str(transport.MAX_BYTES + 1)}.get(name, default)
    class Connection:
        def __init__(self, *args, **kwargs):
            pass
        def request(self, *args, **kwargs):
            requests.append(args)
        def getresponse(self):
            return Response()
        def close(self):
            pass
    monkeypatch.setattr(socket, 'getaddrinfo', lambda *a, **k: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('8.8.8.8', 443))])
    monkeypatch.setattr(socket, 'socket', lambda *a: FakeSocket())
    monkeypatch.setattr(transport.ssl, 'create_default_context', lambda: FakeContext())
    monkeypatch.setattr(transport.http.client, 'HTTPConnection', Connection)
    with pytest.raises(transport.TransportError):
        transport.fetch_pdf('https://www.sbs.gob.pe/x', allowed_hosts=['www.sbs.gob.pe'])
    assert len(requests) == (0 if scenario in ('peer_private', 'tls_error') else 6 if scenario == 'redirect_loop' else 1)


def test_transport_deadline_interrupts_stalled_headers(monkeypatch):
    from sbs.foundation import transport
    import socket
    import threading
    import time
    stopped = threading.Event()
    class Sock:
        def settimeout(self, value): pass
        def connect(self, address): pass
        def getpeername(self): return ('8.8.8.8', 443)
        def shutdown(self, how): stopped.set()
        def close(self): stopped.set()
    class Context:
        def wrap_socket(self, sock, **kwargs): return sock
    class Connection:
        def __init__(self, *a, **kw): pass
        def request(self, *a, **kw): pass
        def getresponse(self):
            stopped.wait(1)
            raise OSError('stalled headers')
        def close(self): stopped.set()
    monkeypatch.setattr(transport, 'TIMEOUT', 0.02)
    monkeypatch.setattr(socket, 'getaddrinfo', lambda *a, **k: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('8.8.8.8', 443))])
    monkeypatch.setattr(socket, 'socket', lambda *a: Sock())
    monkeypatch.setattr(transport.ssl, 'create_default_context', lambda: Context())
    monkeypatch.setattr(transport.http.client, 'HTTPConnection', Connection)
    started = time.monotonic()
    with pytest.raises(transport.TransportError):
        transport.fetch_pdf('https://www.sbs.gob.pe/x', allowed_hosts=['www.sbs.gob.pe'])
    assert time.monotonic() - started < 0.3


def test_citation_identity_binds_extractor_and_extracted_text(tmp_path, monkeypatch):
    import pypdf
    from pypdf._page import PageObject
    from sbs.foundation import extract
    source = ingest_bytes(tmp_path, pdf('SINTETICO'))[0]
    before = extract(source, root=tmp_path)
    monkeypatch.setattr(pypdf, '__version__', 'synthetic-alternate-extractor')
    monkeypatch.setattr(PageObject, 'extract_text', lambda self: 'SINTETICO diferente')
    after = extract(source, root=tmp_path)
    assert before['provisions'][0]['citation_id'] != after['provisions'][0]['citation_id']
    assert before['rawtext'] != after['rawtext']


@pytest.mark.parametrize('corruption', ['text', 'rawhash', 'identity', 'citation', 'rawfile', 'missing_rawfile', 'malformed_json'])
def test_corrupted_derivatives_fail_closed_without_overwrite(tmp_path, corruption):
    import json
    from sbs.foundation import extract
    source = ingest_bytes(tmp_path, pdf('SINTETICO obligación'))[0]
    extract(source, root=tmp_path)
    result_path = next((tmp_path / 'derived').rglob('result.json'))
    raw_path = result_path.with_name('rawtext.txt')
    result = json.loads(result_path.read_text())
    result_path.chmod(0o644)
    raw_path.chmod(0o644)
    if corruption == 'text': result['rawtext'] = 'MODIFIED'
    if corruption == 'rawhash': result['rawtext_sha256'] = '0' * 64
    if corruption == 'identity': result['extractor'] = 'unknown'
    if corruption == 'citation': result['provisions'][0]['text'] = 'MODIFIED'
    if corruption == 'rawfile': raw_path.write_text('MODIFIED')
    if corruption == 'missing_rawfile': raw_path.unlink()
    result_path.write_text('{' if corruption == 'malformed_json' else json.dumps(result))
    tampered = result_path.read_bytes()
    with pytest.raises(ValueError, match='DERIVATIVE_INTEGRITY_FAILED'):
        extract(source, root=tmp_path)
    assert result_path.read_bytes() == tampered


def test_failed_extraction_can_retry_and_retains_failed_evidence(tmp_path, monkeypatch):
    from pypdf._page import PageObject
    from sbs.foundation import extract
    source = ingest_bytes(tmp_path, pdf('SINTETICO recuperado'))[0]
    original_extract = PageObject.extract_text
    def fail(self):
        raise ValueError('transient failure')
    monkeypatch.setattr(PageObject, 'extract_text', fail)
    failed = extract(source, root=tmp_path)
    assert 'extraction_error' in failed['quality']['limitations']
    monkeypatch.setattr(PageObject, 'extract_text', original_extract)
    recovered = extract(source, root=tmp_path)
    assert 'SINTETICO recuperado' in recovered['rawtext']
    assert 'extraction_error' not in recovered['quality']['limitations']
    with sqlite3.connect(tmp_path / 'foundation.sqlite3') as db:
        attempts = db.execute('SELECT status,result FROM extraction_attempts ORDER BY id').fetchall()
    assert [a[0] for a in attempts] == ['failed', 'confirmed']
    import json
    assert json.loads(attempts[0][1]) == failed
    assert json.loads(attempts[1][1]) == recovered
    assert recovered == extract(source, root=tmp_path)


def test_ocr_pending_is_confirmed_without_spurious_retry(tmp_path, monkeypatch):
    from pypdf._page import PageObject
    from sbs.foundation import extract
    source = ingest_bytes(tmp_path, pdf(''))[0]
    pending = extract(source, root=tmp_path)
    def unexpected(self):
        raise AssertionError('blank PDF must not be treated as transient failure')
    monkeypatch.setattr(PageObject, 'extract_text', unexpected)
    assert pending == extract(source, root=tmp_path)
    with sqlite3.connect(tmp_path / 'foundation.sqlite3') as db:
        statuses = db.execute('SELECT status FROM extraction_attempts').fetchall()
    assert statuses == [('confirmed',)]


def test_http_connection_close_body_finishes_without_touching_closed_socket(monkeypatch):
    """Real HTTPConnection/HTTPResponse and socket files; only TLS/DNS are doubles."""
    import socket
    from sbs.foundation import transport
    client, server = socket.socketpair()
    body = pdf('SINTETICO connection close')
    server.sendall(b'HTTP/1.1 200 OK\r\nConnection: close\r\nContent-Length: ' +
                   str(len(body)).encode() + b'\r\n\r\n' + body)
    class PinnedSocket:
        def __getattr__(self, name): return getattr(client, name)
        def connect(self, address): pass
        def getpeername(self): return ('8.8.8.8', 443)
    class Context:
        def wrap_socket(self, sock, **kwargs): return sock
    monkeypatch.setattr(socket, 'getaddrinfo', lambda *a, **k: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('8.8.8.8', 443))])
    monkeypatch.setattr(socket, 'socket', lambda *a: PinnedSocket())
    monkeypatch.setattr(transport.ssl, 'create_default_context', lambda: Context())
    try:
        actual, _ = transport.fetch_pdf('https://www.sbs.gob.pe/x', allowed_hosts=['www.sbs.gob.pe'])
        assert actual == body
    finally:
        client.close()
        server.close()


@pytest.mark.parametrize('failure,expected', [('DNS_NONPUBLIC', 'DNS_NONPUBLIC'),
                                             ('secret-query-token', 'TRANSPORT_FAILED')])
def test_ingest_records_allowlisted_transport_codes_only(tmp_path, failure, expected):
    from sbs.foundation import ingest
    from sbs.foundation.transport import TransportError
    def fail(url, **kwargs):
        raise TransportError(failure)
    assert ingest(manifest(), 'run', root=tmp_path, fetcher=fail) == []
    with sqlite3.connect(tmp_path / 'foundation.sqlite3') as db:
        assert db.execute('SELECT error FROM attempts').fetchone()[0] == expected
