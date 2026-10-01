"""Immutable content objects and transactional capture history.

Filesystem root is trusted application configuration, never corpus input.
Existing objects are byte-verified; exclusive atomic publication never replaces.
"""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def publish(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.pending-')
    try:
        with os.fdopen(fd, 'wb') as file:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        os.chmod(name, 0o444)
        try:
            os.link(name, path)
        except FileExistsError:
            if path.read_bytes() != data:
                raise ValueError('IMMUTABLE_CONFLICT')
    finally:
        os.unlink(name)


def database(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(root / 'foundation.sqlite3')
    db.executescript('''
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY, run TEXT NOT NULL, requested_url TEXT NOT NULL,
            captured_at TEXT NOT NULL, status TEXT NOT NULL, error TEXT);
        CREATE TABLE IF NOT EXISTS documents (
            identity TEXT PRIMARY KEY, source TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS captures (
            attempt_id INTEGER PRIMARY KEY REFERENCES attempts(id),
            identity TEXT NOT NULL, requested_url TEXT NOT NULL,
            final_url TEXT NOT NULL, source TEXT NOT NULL, metadata TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS extraction_artifacts (
            artifact_key TEXT PRIMARY KEY, result_sha256 TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS extraction_attempts (
            id INTEGER PRIMARY KEY, artifact_key TEXT NOT NULL,
            started_at TEXT NOT NULL, status TEXT NOT NULL, result TEXT);
    ''')
    return db


def object_path(root, sha256):
    if len(sha256) != 64 or any(c not in '0123456789abcdef' for c in sha256):
        raise ValueError('HASH_INVALID')
    return Path(root) / 'objects' / sha256[:2] / (sha256 + '.pdf')
