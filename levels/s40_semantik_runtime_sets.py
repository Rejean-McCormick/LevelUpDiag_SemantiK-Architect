from __future__ import annotations

import hashlib
import json
from pathlib import Path

from levelupdiag_core.semantik import (
    json_from_stdout,
    run_target_python,
    runtime_manifest_paths,
)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cfg, report):
    root = Path(cfg["_target_root"])
    p = cfg.get("semantik", {})
    runtime_root = root / p.get("runtime_root", "runtime")
    report.add(
        "semantik.runtime.directory_contract",
        "PASS" if runtime_root.is_dir() else "FAIL",
        "runtime_set",
        "The runtime artifact boundary exists."
        if runtime_root.is_dir()
        else "The runtime artifact boundary directory is missing.",
        evidence={"path": str(runtime_root)},
    )

    manifests = runtime_manifest_paths(cfg)
    report.metrics["runtime_manifests"] = len(manifests)
    if not manifests:
        report.add(
            "semantik.runtime.deployed_sets",
            "WARN",
            "runtime_set",
            "No RuntimeSet is deployed in the repository. The SA core can be valid, but no real language/profile can be accepted from this checkout alone.",
            evidence={"runtime_root": str(runtime_root)},
            recommendation="Deploy a released RuntimeSet when performing real-language acceptance diagnostics.",
        )
        return

    static_errors = []
    runtime_ids = []
    for manifest_path in manifests:
        rel = manifest_path.relative_to(root).as_posix()
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            runtime_id = str(data["runtime_set_id"])
            runtime_ids.append(runtime_id)
            if data.get("schema_version") != "1.0":
                static_errors.append({"manifest": rel, "error": "schema_version"})
            if data.get("status") not in {"CANDIDATE", "RELEASED", "RETIRED"}:
                static_errors.append({"manifest": rel, "error": "status"})
            cap_ref = str(data.get("capability_manifest_ref") or "")
            cap_path = manifest_path.parent / cap_ref
            expected = str(data.get("capability_manifest_sha256") or "").lower()
            if not cap_path.is_file():
                static_errors.append({"manifest": rel, "error": "missing_capability_manifest", "ref": cap_ref})
            elif not expected or _sha256(cap_path).lower() != expected:
                static_errors.append({"manifest": rel, "error": "capability_manifest_hash", "ref": cap_ref})
            for artifact in data.get("artifacts", []):
                path_value = artifact.get("path")
                if not path_value:
                    continue
                path = manifest_path.parent / str(path_value)
                if not path.is_file():
                    static_errors.append({"manifest": rel, "error": "missing_artifact", "artifact": artifact.get("artifact_id")})
                elif _sha256(path).lower() != str(artifact.get("sha256") or "").lower():
                    static_errors.append({"manifest": rel, "error": "artifact_hash", "artifact": artifact.get("artifact_id")})
        except Exception as exc:
            static_errors.append({"manifest": rel, "error": f"{type(exc).__name__}: {exc}"})
    report.add(
        "semantik.runtime.static_integrity",
        "FAIL" if static_errors else "PASS",
        "runtime_set",
        "RuntimeSet manifests and pinned local artifact hashes are structurally consistent."
        if not static_errors
        else "One or more RuntimeSet manifests/artifact hashes are inconsistent.",
        evidence=static_errors or {"runtime_set_ids": runtime_ids},
    )

    script = r'''
import json
from semantik_architect import SemantikArchitect
app=SemantikArchitect.from_runtime_root(%r)
ids=%r
print(json.dumps({rid:app.validate_runtime(rid) for rid in ids}))
''' % (str(runtime_root), runtime_ids)
    dynamic = run_target_python(cfg, ["-c", script], timeout=180)
    data = json_from_stdout(dynamic)
    if dynamic.get("exit_code") != 0 or not isinstance(data, dict):
        report.add(
            "semantik.runtime.release_validation",
            "FAIL",
            "runtime_set",
            "RuntimeSet release validation could not execute through the public SA SDK.",
            evidence=dynamic,
        )
    else:
        invalid = {rid: value for rid, value in data.items() if not isinstance(value, dict) or value.get("valid") is not True}
        report.add(
            "semantik.runtime.release_validation",
            "FAIL" if invalid else "PASS",
            "runtime_set",
            "All deployed RuntimeSets pass SA release validation."
            if not invalid
            else "One or more deployed RuntimeSets fail SA release validation.",
            evidence=invalid or data,
        )
