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


    # Kristal v6 boundary: prove explicit projection, traceability and non-inference.
    kristal_probe = r"""
import json
from pathlib import Path
from semantik_architect.adapters.ecosystem.kristal_v6 import KristalV6Acl, KristalV6ProjectionError

data=json.loads(Path('examples/kristal_v6_communication_projection.json').read_text(encoding='utf-8'))
acl=KristalV6Acl()
req=acl.map_request(data,target_language='fr',target_locale='fr-CA',capability_profile='orgo-operational-1')
force=req.obligations[0].force.value
count=len(req.obligations)
aid=data['selected_assertions'][0]['assertion_id']
role=req.support_values(aid,'kristal-v6:record_role')
auto=json.loads(json.dumps(data))
auto['selected_assertions'][0]['actionability']={'mode':'automatic','requires_human_validation':False}
req2=acl.map_request(auto,target_language='fr',target_locale='fr-CA',capability_profile='orgo-operational-1')
non_inference=(len(req2.obligations)==count and req2.obligations[0].force.value==force)
bad=json.loads(json.dumps(data))
bad['communication_request']['semantic_graph']['statements'][0]['source_refs']=[]
bad['communication_request']['obligations'][0]['source_refs']=[]
traceability_rejected=False
try:
    acl.map_request(bad,target_language='fr',target_locale='fr-CA',capability_profile='orgo-operational-1')
except KristalV6ProjectionError:
    traceability_rejected=True
print(json.dumps({'force':force,'count':count,'role':list(role),'non_inference':non_inference,'traceability_rejected':traceability_rejected}))
"""
    probe = run_target_python(cfg, ["-c", kristal_probe], timeout=90)
    data = json_from_stdout(probe)
    ok = (
        probe.get("exit_code") == 0
        and isinstance(data, dict)
        and data.get("non_inference") is True
        and data.get("traceability_rejected") is True
        and data.get("role") == ["decision"]
    )
    report.add(
        "semantik.contracts.kristal_v6_acl",
        "PASS" if ok else "FAIL",
        "contracts",
        "Kristal v6 ACL preserves explicit obligations/force, selected assertion metadata and fail-closed traceability without inferring communication from actionability."
        if ok
        else "Kristal v6 communication projection boundary failed its executable non-inference/traceability probe.",
        evidence=data if isinstance(data, dict) else probe,
        recommendation=None if ok else "Restore the locked KristalV6Acl projection contract before release.",
    )
