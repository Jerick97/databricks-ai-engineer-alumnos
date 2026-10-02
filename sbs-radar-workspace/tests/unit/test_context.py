import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


def load_api():
    spec = importlib.util.find_spec("sbs.context")
    assert spec is not None, "SK00 context resolver not implemented"
    from sbs.context import resolve_context
    return resolve_context


def setup_registry(root):
    (root / "context").mkdir()
    (root / "source.txt").write_text("original")
    h = hashlib.sha256(b"original").hexdigest()
    (root / "context/source-register.json").write_text(json.dumps([
        {"id": "source", "path": "source.txt", "sha256": h, "status": "reusable"},
        {"id": "spans", "depends_on": ["source"], "status": "reusable"},
        {"id": "vectors", "depends_on": ["spans"], "status": "reusable"},
        {"id": "catalog", "depends_on": [], "status": "reusable"},
    ]))
    (root / "context/tasks.json").write_text(json.dumps({"demo": {"requires": ["vectors", "catalog"]}}))


def test_unchanged_inputs_reused_without_network(tmp_path):
    resolve = load_api()
    setup_registry(tmp_path)
    result = resolve("demo", root=tmp_path)
    assert result["status"] == "ready"
    assert set(result["reusable"]) == {"source", "spans", "vectors", "catalog"}
    assert result["gaps"] == []


def test_changed_source_invalidates_only_descendants(tmp_path):
    resolve = load_api()
    setup_registry(tmp_path)
    (tmp_path / "source.txt").write_text("revised")
    result = resolve("demo", root=tmp_path)
    assert set(result["invalidated"]) == {"source", "spans", "vectors"}
    assert result["reusable"] == ["catalog"]
    assert result["status"] == "needs_attention"


def test_missing_dependency_not_silently_ready(tmp_path):
    resolve = load_api()
    setup_registry(tmp_path)
    (tmp_path / "context/tasks.json").write_text('{"demo":{"requires":["absent"]}}')
    result = resolve("demo", root=tmp_path)
    assert result["status"] == "needs_attention"
    assert any(x["code"] == "missing_dependency" for x in result["gaps"])


def test_cycle_rejected_without_recursion_failure(tmp_path):
    resolve = load_api()
    setup_registry(tmp_path)
    (tmp_path / "context/source-register.json").write_text('[{"id":"vectors","depends_on":["vectors"],"status":"reusable"}]')
    result = resolve("demo", root=tmp_path)
    assert any(x["code"] == "dependency_cycle" for x in result["gaps"])


def test_symlink_outside_root_never_read(tmp_path):
    resolve = load_api()
    setup_registry(tmp_path)
    (tmp_path / "escape").symlink_to(tmp_path.parent)
    (tmp_path / "context/source-register.json").write_text('[{"id":"vectors","path":"escape/secret.txt","sha256":"x","status":"reusable"}]')
    result = resolve("demo", root=tmp_path)
    assert any(x["code"] == "path_outside_root" for x in result["gaps"])


def test_documentation_does_not_prove_runtime_capability(tmp_path):
    resolve = load_api()
    setup_registry(tmp_path)
    (tmp_path / "context/source-register.json").write_text('[{"id":"vectors","status":"unverified","kind":"runtime_capability"},{"id":"catalog","status":"reusable"}]')
    result = resolve("demo", root=tmp_path)
    assert result["status"] == "needs_attention"
    assert "vectors" not in result["reusable"]


def test_reusable_label_does_not_prove_runtime_capability(tmp_path):
    resolve = load_api()
    setup_registry(tmp_path)
    (tmp_path / "context/source-register.json").write_text('[{"id":"vectors","status":"reusable","kind":"runtime_capability"},{"id":"catalog","status":"reusable"}]')
    result = resolve("demo", root=tmp_path)
    assert result["status"] == "needs_attention"
    assert any(x["code"] == "operational_evidence_missing" for x in result["gaps"])


@pytest.mark.parametrize("bad", [{"path": None}, {"depends_on": None}, {"depends_on": "source"}])
def test_malformed_required_entry_preserves_independent_branch(tmp_path, bad):
    resolve = load_api()
    setup_registry(tmp_path)
    entries = [{"id": "vectors", "status": "reusable", **bad}, {"id": "catalog", "status": "reusable"}]
    (tmp_path / "context/source-register.json").write_text(json.dumps(entries))
    result = resolve("demo", root=tmp_path)
    assert result["reusable"] == ["catalog"]
    assert any(x["code"] == "malformed_entry" for x in result["gaps"])
    assert not any(x["id"] == "s" for x in result["gaps"])


def test_unrelated_malformed_entry_reports_warning_not_abort(tmp_path):
    resolve = load_api()
    setup_registry(tmp_path)
    registry = tmp_path / "context/source-register.json"
    registry.write_text(json.dumps(json.loads(registry.read_text()) + [{"status": "unverified"}]))
    result = resolve("demo", root=tmp_path)
    assert result["status"] == "ready"
    assert result["warnings"] == [{"code": "registry_entry_without_id", "index": 4}]
