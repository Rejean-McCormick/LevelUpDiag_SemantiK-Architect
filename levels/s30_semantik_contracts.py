from __future__ import annotations

import json
from pathlib import Path

from levelupdiag_core.semantik import json_from_stdout, run_target_python


def run(cfg, report):
    root = Path(cfg["_target_root"])
    p = cfg.get("semantik", {})
    schema_files = list(p.get("schema_files", []))

    parse_errors = []
    parsed = {}
    for rel in schema_files:
        path = root / rel
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("schema root is not an object")
            parsed[rel] = data
        except Exception as exc:
            parse_errors.append({"path": rel, "error": f"{type(exc).__name__}: {exc}"})
    report.add(
        "semantik.contracts.schemas_parse",
        "FAIL" if parse_errors else "PASS",
        "contracts",
        "All declared SemantiK Architect v1 JSON Schemas parse as JSON objects."
        if not parse_errors
        else "One or more declared schemas are missing or invalid JSON.",
        evidence=parse_errors or {"schema_count": len(parsed)},
    )

    ids = {}
    duplicate_ids = []
    for rel, data in parsed.items():
        sid = data.get("$id")
        if not sid:
            duplicate_ids.append({"path": rel, "problem": "missing_$id"})
        elif sid in ids:
            duplicate_ids.append({"path": rel, "problem": "duplicate_$id", "other": ids[sid], "$id": sid})
        else:
            ids[sid] = rel
    report.add(
        "semantik.contracts.schema_ids_unique",
        "FAIL" if duplicate_ids else "PASS",
        "contracts",
        "Declared schemas expose unique explicit contract identities."
        if not duplicate_ids
        else "Schema contract identities are missing or duplicated.",
        evidence=duplicate_ids or sorted(ids),
    )

    # jsonschema is a development dependency, not a production dependency. Use it when available.
    script = r'''
import json, pathlib
try:
 import jsonschema
except Exception:
 print(json.dumps({"available":False})); raise SystemExit(0)
root=pathlib.Path('.')
errors=[]
for rel in %r:
 try:
  schema=json.loads((root/rel).read_text(encoding='utf-8'))
  jsonschema.Draft202012Validator.check_schema(schema)
 except Exception as exc:
  errors.append({"path":rel,"error":str(exc)})
for example,schema_rel in %r:
 try:
  data=json.loads((root/example).read_text(encoding='utf-8'))
  schema=json.loads((root/schema_rel).read_text(encoding='utf-8'))
  jsonschema.validate(data,schema)
 except Exception as exc:
  errors.append({"example":example,"schema":schema_rel,"error":str(exc)})
print(json.dumps({"available":True,"errors":errors}))
''' % (schema_files, list(p.get("schema_example_pairs", [])))
    probe = run_target_python(cfg, ["-c", script], timeout=90)
    data = json_from_stdout(probe)
    if probe.get("exit_code") != 0 or not isinstance(data, dict):
        report.add(
            "semantik.contracts.jsonschema_validation",
            "WARN",
            "contracts",
            "Draft 2020-12 schema validation could not be established in the selected Python.",
            evidence=probe,
        )
    elif not data.get("available"):
        report.add(
            "semantik.contracts.jsonschema_validation",
            "WARN",
            "contracts",
            "jsonschema is not installed in the selected development Python; JSON parsing succeeded but formal schema validation was skipped.",
            recommendation="Install the project's dev extra when running release-grade diagnostics.",
        )
    else:
        errors = data.get("errors") or []
        report.add(
            "semantik.contracts.jsonschema_validation",
            "FAIL" if errors else "PASS",
            "contracts",
            "All schemas and canonical examples validate under Draft 2020-12."
            if not errors
            else "Formal schema/example validation failed.",
            evidence=errors or {"schema_count": len(schema_files), "example_pairs": len(p.get("schema_example_pairs", []))},
        )

    manifest = root / "DOCUMENTATION_MANIFEST.md"
    text = manifest.read_text(encoding="utf-8", errors="replace") if manifest.is_file() else ""
    missing_refs = [rel for rel in schema_files if rel not in text]
    report.add(
        "semantik.contracts.documentation_manifest_alignment",
        "FAIL" if missing_refs else "PASS",
        "contracts",
        "Every declared schema is indexed by the documentation authority manifest."
        if not missing_refs
        else "The documentation manifest does not index every active schema contract.",
        evidence=missing_refs or None,
    )
