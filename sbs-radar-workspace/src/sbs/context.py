"""SK00: deterministic local context resolution. Never performs network I/O."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def _local_path(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError("path_outside_root")
    return path


def resolve_context(task_id: str, *, root: Path | str | None = None) -> dict:
    root = Path(root or Path(__file__).resolve().parents[2]).resolve()
    tasks = json.loads(_local_path(root, "context/tasks.json").read_text())
    entries = json.loads(_local_path(root, "context/source-register.json").read_text())
    if task_id not in tasks:
        raise ValueError(f"Unknown task: {task_id}")
    result = {"task_id": task_id, "status": "ready", "reusable": [],
              "invalidated": [], "gaps": [], "artifacts": [], "warnings": []}
    registry = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str) or not entry["id"]:
            result["warnings"].append({"code": "registry_entry_without_id", "index": index})
            continue
        if entry["id"] in registry:
            raise ValueError("duplicate_artifact_id")
        registry[entry["id"]] = entry
    visited: dict[str, bool] = {}
    active: set[str] = set()

    def gap(ident: str, code: str) -> None:
        item = {"id": ident, "code": code}
        if item not in result["gaps"]:
            result["gaps"].append(item)

    def visit(ident: str) -> bool:
        if ident in active:
            gap(ident, "dependency_cycle")
            return False
        if ident in visited:
            return visited[ident]
        entry = registry.get(ident)
        if entry is None:
            gap(ident, "missing_dependency")
            visited[ident] = False
            return False
        deps = entry.get("depends_on", [])
        if (not isinstance(deps, list) or not all(isinstance(d, str) and d for d in deps)
                or ("path" in entry and (not isinstance(entry["path"], str) or not entry["path"]))):
            gap(ident, "malformed_entry")
            visited[ident] = False
            result["invalidated"].append(ident)
            return False
        active.add(ident)
        # Visit all branches even if one fails, so independent work remains visible.
        dependencies = [visit(dep) for dep in deps]
        valid = all(dependencies)
        if entry.get("kind") == "runtime_capability":
            # Runtime proof must be supplied by the integration verifier (SK12).
            # Local documents/status labels cannot certify environment+actor access.
            gap(ident, "operational_evidence_missing")
            valid = False
        if entry.get("status") != "reusable":
            gap(ident, "not_verified_reusable")
            valid = False
        if "path" in entry:
            try:
                path = _local_path(root, entry["path"])
                actual = hashlib.sha256(path.read_bytes()).hexdigest()
                if actual != entry.get("sha256"):
                    gap(ident, "hash_changed")
                    valid = False
            except ValueError:
                gap(ident, "path_outside_root")
                valid = False
            except OSError:
                gap(ident, "file_unavailable")
                valid = False
        if not all(dependencies):
            gap(ident, "dependency_invalid")
        active.remove(ident)
        visited[ident] = valid
        result["reusable" if valid else "invalidated"].append(ident)
        # Only allowlisted metadata crosses the context boundary.
        result["artifacts"].append({key: entry[key] for key in
            ("id", "kind", "path", "sha256", "status", "scope", "depends_on", "consulted_at") if key in entry})
        return valid

    for requirement in tasks[task_id]["requires"]:
        visit(requirement)
    if result["gaps"]:
        result["status"] = "needs_attention"
    return result
