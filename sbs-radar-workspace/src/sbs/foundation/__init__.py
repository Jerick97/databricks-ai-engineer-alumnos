"""SK02 capture/extract API, requiring pypdf 6.13.3.

    ingest(manifest, run, *, root, fetcher=fetch_pdf) -> list[SourceDocument]
    extract(source, *, root) -> dict with provisions, rawtext, pages and quality

manifest = {allowed_hosts: [exact trusted hosts], sources: [dict]}; each source
requires document_id, family, url, source_kind and synthetic (explicit boolean).
Optional dates, date_unknown_reasons, annex_missing and table_review_pending are
preserved. run is a run ID or JSON serializable run record. Injected fetchers are
trusted adapters accepting (url, allowed_hosts=...) and returning (bytes, final
URL). They must enforce the transport boundary themselves; use only for fixtures
or equally secure adapters. Failures return no SourceDocument and remain in SQLite.
No fetch or import executes a download automatically.
"""
from datetime import datetime, timezone
import io
from pathlib import Path
from .pdf_reader import strict_pdf_reader
from sbs.contracts import validate_contract
from sbs.guardrails import check_source_url
from .store import canonical, database, digest, object_path, publish
from .transport import fetch_pdf, MAX_BYTES, TransportError


def ingest(manifest, run, *, root, fetcher=fetch_pdf):
    results = []
    hosts = manifest['allowed_hosts']
    db = database(root)
    try:
        for entry in manifest['sources']:
            now = datetime.now(timezone.utc).isoformat()
            with db:
                attempt = db.execute(
                    'INSERT INTO attempts(run,requested_url,captured_at,status) VALUES(?,?,?,?)',
                    (canonical(run), entry['url'], now, 'started')).lastrowid
            try:
                if not check_source_url(entry['url'], hosts)['valid']:
                    raise ValueError('URL_DENIED')
                content, final_url = fetcher(entry['url'], allowed_hosts=hosts)
                if not check_source_url(final_url, hosts)['valid']:
                    raise ValueError('FINAL_URL_DENIED')
                if not isinstance(content, bytes) or len(content) > MAX_BYTES:
                    raise ValueError('PDF_INVALID')
                reader = strict_pdf_reader(content)
                if reader.is_encrypted or not len(reader.pages):
                    raise ValueError('PDF_UNREADABLE')
                sha = digest(content)
                reasons = dict(entry.get('date_unknown_reasons', {}))
                for field in ('published_on', 'effective_on'):
                    if entry.get(field) is None:
                        reasons.setdefault(field, 'Not established from authoritative source metadata')
                source = {key: entry[key] for key in (
                    'document_id', 'family', 'source_kind', 'synthetic')}
                source.update(version_id=sha, sha256=sha, url=entry['url'], captured_at=now,
                              published_on=entry.get('published_on'), effective_on=entry.get('effective_on'),
                              date_unknown_reasons=reasons)
                if not validate_contract('SourceDocument', source)['valid']:
                    raise ValueError('SOURCE_CONTRACT_INVALID')
                identity = digest(canonical([source['document_id'], source['family'], sha]).encode())
                publish(object_path(root, sha), content)
                with db:
                    db.execute('INSERT OR IGNORE INTO documents VALUES(?,?)', (identity, canonical(source)))
                    db.execute('INSERT INTO captures VALUES(?,?,?,?,?,?)',
                               (attempt, identity, entry['url'], final_url, canonical(source), canonical(entry)))
                    db.execute("UPDATE attempts SET status='captured' WHERE id=?", (attempt,))
                results.append(source)
            except Exception as error:
                # Exception messages may include tokens, URLs or untrusted PDF text.
                with db:
                    db.execute("UPDATE attempts SET status='failed',error=? WHERE id=?",
                               (error.code if isinstance(error, TransportError) else type(error).__name__, attempt))
    finally:
        db.close()
    return results


from .extract import extract

__all__ = ['ingest', 'extract']
