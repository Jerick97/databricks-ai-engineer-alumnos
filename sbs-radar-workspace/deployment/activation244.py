"""Explicit twelfth process allocation; preserve210,214,218,221 223,225 and229 reservations in same ledger."""
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
spec = importlib.util.spec_from_file_location('incremental244_review', ROOT / 'deployment/incremental_app244.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
CAPS = {'generation_posts': 6, 'embedding_posts': 5, 'embedding_tokens': 50000}
PRIOR_ENVELOPES = ('deployment/state/incremental-app210/attempt2/activation-envelope.json',
                   'deployment/state/incremental-app214/activation-envelope.json',
                   'deployment/state/incremental-app218/activation-envelope.json',
                   'deployment/state/incremental-app221/activation-envelope.json',
                   'deployment/state/incremental-app223/activation-envelope.json',
                   'deployment/state/incremental-app225/activation-envelope.json',
                   'deployment/state/incremental-app229/activation-envelope.json',
                   'deployment/state/incremental-app232/activation-envelope.json',
                   'deployment/state/incremental-app234/activation-envelope.json',
                   'deployment/state/incremental-app236/activation-envelope.json',
                   'deployment/state/incremental-app240/activation-envelope.json')
PUBLIC = 'deployment/state/incremental-package210/delta/config/runtime210-public-key.pem'


def append_allocation(path, epoch, priors, public_bytes, *, clock=time.time):
    """Core transaction; prior envelope and public key are pinned by allocate's review."""
    u = r.u
    path = Path(path)
    u.require(isinstance(priors, list) and len(priors) == 11
              and len({p['payload']['epoch'] for p in priors}) == 11, '244_PRIOR_COUNT')
    u.require(isinstance(epoch, str) and 16 <= len(epoch) <= 128
              and epoch not in {p['payload']['epoch'] for p in priors}, '244_EPOCH')
    key_path, db_path = path / 'private.pem', path / 'ledger.sqlite'
    u.require(db_path.is_file() and not db_path.is_symlink() and not key_path.is_symlink(), '244_LEDGER')
    u.require(key_path.stat().st_mode & 0o077 == 0, '244_KEY_PERMISSIONS')
    lock = os.open(path, os.O_RDONLY)
    fcntl.flock(lock, fcntl.LOCK_EX)
    db = sqlite3.connect('file:' + str(db_path.resolve()) + '?mode=rw', uri=True)
    try:
        db.execute('PRAGMA synchronous=FULL')
        db.execute('BEGIN IMMEDIATE')
        rows = db.execute('SELECT epoch,payload,signature FROM allocation').fetchall()
        known = {row[0]: {'payload': json.loads(row[1]), 'signature': row[2]} for row in rows}
        u.require(all(known.get(p['payload']['epoch']) == p for p in priors) and len(rows) in (11, 12), '244_PRIOR_ALLOCATION')
        key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
        u.require(isinstance(key, Ed25519PrivateKey), '244_KEY_TYPE')
        public = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        u.require(public == public_bytes, '244_PUBLIC_KEY_CHANGED')
        for index,prior in enumerate(priors):
            u.require(prior['payload']['caps'] == ({'generation_posts': 8, 'embedding_posts': 8, 'embedding_tokens': 80000} if index<2 else CAPS), '244_PRIOR_CAPS')
            key.public_key().verify(base64.b64decode(prior['signature'], validate=True), u.canonical(prior['payload']))
        baseline = db.execute('SELECT reserved,binding_sha256 FROM baseline WHERE id=1').fetchone()
        provenance = u.read(path / 'prior-observation.json')
        u.require(baseline and json.loads(baseline[0]) == {'generation_posts': 1, 'embedding_posts': 1, 'embedding_tokens': 20000}
                  and provenance.get('prior_binding_sha256') == baseline[1]
                  and provenance.get('unknown_external_attempts') == 1, '244_PRIOR_BASELINE')
        if epoch in known:
            return known[epoch]  # exact readback; no time extension
        u.require(len(rows) == 11, '244_ALLOCATION_EXHAUSTED')
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
    r.u.require(all(p in review['files_sha256'] for p in PRIOR_ENVELOPES) and PUBLIC in review['files_sha256'], '244_ACTIVATION_REVIEW')
    return append_allocation(root / 'deployment/state/activation210', epoch,
                             [r.u.read(root / p) for p in PRIOR_ENVELOPES], (root / PUBLIC).read_bytes(), clock=clock)
