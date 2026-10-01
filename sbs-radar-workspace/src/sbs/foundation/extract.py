"""Versioned raw page spans; no semantic chunking or reliable table claim.

span-limpio-contexto-v1 v1 remains unvalidated for SBS. Only literal citation
text is emitted here. Embedding text/model/tokenizer and response expansion are
not selected. Physical pages are explicitly a raw layer, not complete ideas.
"""
import io
import json
from datetime import datetime, timezone
from pathlib import Path
import re
import pypdf
from .pdf_reader import strict_pdf_reader, pdf_header_offset
from sbs.contracts import validate_contract
from .store import canonical, database, digest, object_path, publish


def _verified_cache(artifact, artifact_key, source, extractor, config_hash, root):
    """Reject damaged/unconfirmed artifacts; never repair evidence in place."""
    db = database(root)
    try:
        seal = db.execute('SELECT result_sha256 FROM extraction_artifacts WHERE artifact_key=?',
                          (artifact_key,)).fetchone()
        result = json.loads((artifact / 'result.json').read_text())
        raw = (artifact / 'rawtext.txt').read_bytes()
        if (seal is None or digest(canonical(result).encode()) != seal[0]
                or result['sha256'] != source['sha256'] or result['extractor'] != extractor
                or result['config_hash'] != config_hash
                or raw != result['rawtext'].encode() or digest(raw) != result['rawtext_sha256']):
            raise ValueError('invalid artifact')
        for span in result['provisions']:
            if (not validate_contract('Provision', span)['valid']
                    or span['document_id'] != source['document_id']
                    or span['version_id'] != source['version_id']
                    or span['synthetic'] != source['synthetic']
                    or result['rawtext'][span['start']:span['end']] != span['text']):
                raise ValueError('invalid span')
        return result
    except Exception:
        raise ValueError('DERIVATIVE_INTEGRITY_FAILED') from None
    finally:
        db.close()


def extract(source, *, root):
    """Extract stable Unicode offsets [start,end), preserving all extracted text.

    No whitespace normalization or OCR. Page separator is one newline, excluded
    from each page span. Quality is always partial/pending until expert checks;
    references to annexes remain pending even when the main PDF has text.
    """
    if not validate_contract('SourceDocument', source)['valid']:
        raise ValueError('SOURCE_CONTRACT_INVALID')
    db = database(root)
    try:
        row = db.execute('SELECT metadata FROM captures WHERE source=? ORDER BY attempt_id DESC LIMIT 1',
                         (canonical(source),)).fetchone()
    finally:
        db.close()
    if row is None:
        raise ValueError('CAPTURE_MISSING')
    metadata = json.loads(row[0])
    config = {'layer': 'raw_pages', 'separator': '\n', 'normalization': 'none',
              'annex_missing': metadata.get('annex_missing', []),
              'table_review_pending': metadata.get('table_review_pending', False),
              'document_id': source['document_id'], 'source_kind': source['source_kind'],
              'synthetic': source['synthetic'], 'family': source['family']}
    config_hash = digest(canonical(config).encode())
    original_content = object_path(root, source['sha256']).read_bytes()
    if digest(original_content) != source['sha256']:raise ValueError('ORIGINAL_HASH_MISMATCH')
    prefix_offset = pdf_header_offset(original_content)
    extractor = 'pypdf-' + pypdf.__version__ + '-raw-v2' + ('-prefix-view-v1' if prefix_offset else '')
    artifact = Path(root) / 'derived' / source['sha256'] / digest(extractor.encode()) / config_hash
    artifact_key = digest(canonical([source['sha256'], extractor, config_hash]).encode())
    content = object_path(root, source['sha256']).read_bytes()
    if digest(content) != source['sha256']:
        raise ValueError('ORIGINAL_HASH_MISMATCH')
    if (artifact / 'result.json').exists():
        return _verified_cache(artifact, artifact_key, source, extractor, config_hash, root)
    db = database(root)
    try:
        with db:
            attempt_id = db.execute(
                'INSERT INTO extraction_attempts(artifact_key,started_at,status) VALUES(?,?,?)',
                (artifact_key, datetime.now(timezone.utc).isoformat(), 'started')).lastrowid
    finally:
        db.close()
    limitations = ['semantic_segmentation_pending', 'layout_table_review_pending']
    if config['annex_missing']:
        limitations.append('annex_missing')
    text, pages, provisions = '', [], []
    try:
        reader = strict_pdf_reader(content)
        for number, page in enumerate(reader.pages, 1):
            if number > 1:
                text += '\n'
            start = len(text)
            try:
                extracted = page.extract_text() or ''
                error = None
            except Exception:
                extracted, error = '', 'extraction_error'
                limitations.append(error)
            text += extracted
            pages.append({'page': number, 'start': start, 'end': len(text), 'error': error})
            if not extracted.strip():
                limitations.append('empty_pages')
                continue
            if source['source_kind'] == 'draft':
                limitations.append('draft_not_normative_provision')
                continue
            identifier = digest(canonical([source['document_id'], source['sha256'], extractor,
                                           config_hash, number, start, len(text), digest(extracted.encode())]).encode())
            provisions.append({'citation_id': identifier, 'provision_id': 'raw-page-' + str(number),
                               'document_id': source['document_id'], 'version_id': source['version_id'],
                               'page': number, 'start': start, 'end': len(text), 'text': extracted,
                               'source_kind': source['source_kind'], 'synthetic': source['synthetic']})
    except Exception:
        limitations.append('extraction_error')
    if not text.strip():
        limitations.append('ocr_pending')
    annexes = sorted(set(re.findall(r'\banexo(?:\s+\d+)?', text, flags=re.I)))
    if annexes:
        limitations.append('annex_references_pending')
    result = {'layer': 'raw_pages', 'extractor': extractor, 'config_hash': config_hash,
              'sha256': source['sha256'], 'rawtext': text, 'rawtext_sha256': digest(text.encode()),
              'pages': pages, 'provisions': provisions, 'annex_references_pending': annexes,
              'quality': {'status': 'partial' if text.strip() else 'pending',
                          'limitations': sorted(set(limitations))}}
    if 'extraction_error' in limitations:
        # Preserve the complete failed output in the append-only attempt history;
        # do not occupy the confirmed artifact path. A subsequent call retries.
        db = database(root)
        try:
            with db:
                db.execute("UPDATE extraction_attempts SET status='failed',result=? WHERE id=? AND status='started'",
                           (canonical(result), attempt_id))
        finally:
            db.close()
        return result
    publish(artifact / 'rawtext.txt', text.encode())
    publish(artifact / 'result.json', canonical(result).encode())
    db = database(root)
    try:
        with db:
            db.execute('INSERT OR IGNORE INTO extraction_artifacts VALUES(?,?)',
                       (artifact_key, digest(canonical(result).encode())))
            db.execute("UPDATE extraction_attempts SET status='confirmed',result=? WHERE id=? AND status='started'",
                       (canonical(result), attempt_id))
    finally:
        db.close()
    return result
