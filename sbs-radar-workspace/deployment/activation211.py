"""Explicit second process allocation; preserve first210 reservation in same ledger."""
import base64
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import time
from uuid import uuid4
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('incremental211_review', ROOT / 'deployment/incremental_app211.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
CAPS = {'generation_posts': 8, 'embedding_posts': 8, 'embedding_tokens': 80000}
PRIOR_ENVELOPE = 'deployment/state/incremental-app210/attempt2/activation-envelope.json'
PUBLIC = 'deployment/state/incremental-package210/delta/config/runtime210-public-key.pem'


def append_allocation(path, epoch, prior, public_bytes, *, clock=time.time):
    """Core transaction; prior envelope and public key are pinned by allocate's review."""
    u = r.u
    path = Path(path)
    u.require(isinstance(epoch, str) and 16 <= len(epoch) <= 128 and epoch != prior['payload']['epoch'], '211_EPOCH')
    key_path, db_path = path / 'private.pem', path / 'ledger.sqlite'
    u.require(db_path.is_file() and not db_path.is_symlink() and not key_path.is_symlink(), '211_LEDGER')
    u.require(key_path.stat().st_mode & 0o077 == 0, '211_KEY_PERMISSIONS')
    lock = os.open(path, os.O_RDONLY)
    fcntl.flock(lock, fcntl.LOCK_EX)
    db = sqlite3.connect('file:' + str(db_path.resolve()) + '?mode=rw', uri=True)
    try:
        db.execute('PRAGMA synchronous=FULL')
        db.execute('BEGIN IMMEDIATE')
        rows = db.execute('SELECT epoch,payload,signature FROM allocation').fetchall()
        known = {row[0]: {'payload': json.loads(row[1]), 'signature': row[2]} for row in rows}
        u.require(known.get(prior['payload']['epoch']) == prior and len(rows) in (1, 2), '211_PRIOR_ALLOCATION')
        key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
        u.require(isinstance(key, Ed25519PrivateKey), '211_KEY_TYPE')
        public = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        u.require(public == public_bytes, '211_PUBLIC_KEY_CHANGED')
        key.public_key().verify(base64.b64decode(prior['signature'], validate=True), u.canonical(prior['payload']))
        baseline = db.execute('SELECT reserved,binding_sha256 FROM baseline WHERE id=1').fetchone()
        provenance = u.read(path / 'prior-observation.json')
        u.require(baseline and json.loads(baseline[0]) == {'generation_posts': 1, 'embedding_posts': 1, 'embedding_tokens': 20000}
                  and provenance.get('prior_binding_sha256') == baseline[1]
                  and provenance.get('unknown_external_attempts') == 1, '211_PRIOR_BASELINE')
        if epoch in known:
            return known[epoch]  # exact readback; no time extension
        u.require(len(rows) == 1, '211_ALLOCATION_EXHAUSTED')
        now = int(clock())
        payload = {'epoch': epoch, 'activation_id': uuid4().hex, 'issued_at_unix': now,
                   'expires_at_unix': now + 28800, 'caps': dict(CAPS)}
        signature = base64.b64encode(key.sign(u.canonical(payload))).decode()
        db.execute('INSERT INTO allocation VALUES (?,?,?,?)',
                   (epoch, payload['activation_id'], u.canonical(payload).decode(), signature))
        db.commit()
        os.fsync(lock)
        return {'payload': payload, 'signature': signature}
    finally:
        db.close()
        os.close(lock)


def allocate(epoch, *, root=ROOT, clock=time.time):
    root = Path(root)
    r.review(root)
    review = r.u.read(root / r.REVIEW)
    r.u.require(PRIOR_ENVELOPE in review['files_sha256'] and PUBLIC in review['files_sha256'], '211_ACTIVATION_REVIEW')
    return append_allocation(root / 'deployment/state/activation210', epoch,
                             r.u.read(root / PRIOR_ENVELOPE), (root / PUBLIC).read_bytes(), clock=clock)
