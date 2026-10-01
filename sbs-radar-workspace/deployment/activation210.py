"""Durable, conservative allocation before signing one process-epoch activation.

Private app-control key stays here; no account credentials. No network calls.
"""
import base64
import fcntl
import json
import os
from pathlib import Path
import sqlite3
import time
from uuid import uuid4
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

CAPS = {'generation_posts': 8, 'embedding_posts': 8, 'embedding_tokens': 80000}
PRIOR_RESERVED = {'generation_posts': 1, 'embedding_posts': 1, 'embedding_tokens': 20000}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def sync_dir(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def initialize(path, prior_binding_sha256):
    """Only initialize a fresh control directory; deleting DB cannot reset allocation."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=False)
    os.chmod(path, 0o700)
    key = Ed25519PrivateKey.generate()
    fd = os.open(path / 'private.pem', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        stream.flush()
        os.fsync(stream.fileno())
    db = sqlite3.connect(path / 'ledger.sqlite')
    try:
        db.execute('PRAGMA synchronous=FULL')
        db.execute('CREATE TABLE baseline (id INTEGER PRIMARY KEY CHECK (id=1), binding_sha256 TEXT, reserved TEXT)')
        db.execute('INSERT INTO baseline VALUES (1, ?, ?)', (prior_binding_sha256, canonical(PRIOR_RESERVED).decode()))
        db.execute('CREATE TABLE allocation (epoch TEXT PRIMARY KEY, activation_id TEXT UNIQUE, payload TEXT, signature TEXT)')
        db.commit()
    finally:
        db.close()
    os.chmod(path / 'ledger.sqlite', 0o600)
    provenance = {'prior_binding_sha256': prior_binding_sha256,
                  'unknown_external_attempts': 1,
                  'note': 'User broad question returned HTML; original POST not captured; actual provider use unknown.'}
    with (path / 'prior-observation.json').open('x') as stream:
        json.dump(provenance, stream, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    sync_dir(path)
    return key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)


def allocate(path, epoch, *, clock=time.time):
    """One8/8/80000 allocation total210; ambiguous delivery never refunded/re-signed."""
    path = Path(path)
    if not isinstance(epoch, str) or not 16 <= len(epoch) <= 128:
        raise ValueError('ACTIVATION210_EPOCH')
    key_path, db_path = path / 'private.pem', path / 'ledger.sqlite'
    if not db_path.is_file() or db_path.is_symlink() or key_path.is_symlink():
        raise ValueError('ACTIVATION210_LEDGER_MISSING')
    if key_path.stat().st_mode & 0o077:
        raise ValueError('ACTIVATION210_KEY_PERMISSIONS')
    lock = os.open(path, os.O_RDONLY)
    fcntl.flock(lock, fcntl.LOCK_EX)
    db = sqlite3.connect('file:' + str(db_path.resolve()) + '?mode=rw', uri=True)
    try:
        db.execute('PRAGMA synchronous=FULL')
        db.execute('BEGIN IMMEDIATE')
        baseline = db.execute('SELECT reserved,binding_sha256 FROM baseline WHERE id=1').fetchone()
        provenance = json.loads((path / 'prior-observation.json').read_bytes())
        if baseline is None or provenance.get('prior_binding_sha256') != baseline[1] or provenance.get('unknown_external_attempts') != 1:
            raise ValueError('ACTIVATION210_PROVENANCE_CHANGED')
        if baseline is None or json.loads(baseline[0]) != PRIOR_RESERVED:
            raise ValueError('ACTIVATION210_BASELINE_CHANGED')
        # Readback same epoch is safe, but never extends issue time or expiration.
        existing = db.execute('SELECT payload,signature FROM allocation WHERE epoch=?', (epoch,)).fetchone()
        if existing:
            return {'payload': json.loads(existing[0]), 'signature': existing[1]}
        if db.execute('SELECT COUNT(*) FROM allocation').fetchone()[0]:
            raise ValueError('ACTIVATION210_ALLOCATION_EXHAUSTED_REVIEW_NEW_ALLOCATION')
        now = int(clock())
        payload = {'epoch': epoch, 'activation_id': uuid4().hex, 'issued_at_unix': now,
                   'expires_at_unix': now + 28800, 'caps': dict(CAPS)}
        key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
        if not isinstance(key, Ed25519PrivateKey):
            raise ValueError('ACTIVATION210_KEY_TYPE')
        signature = base64.b64encode(key.sign(canonical(payload))).decode()
        db.execute('INSERT INTO allocation VALUES (?,?,?,?)',
                   (epoch, payload['activation_id'], canonical(payload).decode(), signature))
        db.commit()
        sync_dir(path)
        return {'payload': payload, 'signature': signature}
    finally:
        db.close()
        os.close(lock)
