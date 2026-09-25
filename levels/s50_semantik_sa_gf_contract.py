from __future__ import annotations

import json
from pathlib import Path

from levelupdiag_core.semantik import json_from_stdout, run_target_python, runtime_manifest_paths


def run(cfg, report):
    root = Path(cfg["_target_root"])
    p = cfg.get("semantik", {})
    expected = set(p.get("required_operations", []))

    script = r'''
import json
from semantik_architect.domain.language.operations import V1_OPERATION_IDS
from semantik_architect.adapters.realization.gf import GfBridgeRealizer, GfBridgeSpec, PgfRuntime
print(json.dumps({"operations":sorted(V1_OPERATION_IDS),"bridge":GfBridgeRealizer.__name__,"spec":GfBridgeSpec.__name__,"runtime":PgfRuntime.__name__}))
'''
    probe = run_target_python(cfg, ["-c", script], timeout=60)
    data = json_from_stdout(probe)
    if probe.get("exit_code") != 0 or not isinstance(data, dict):
        report.add(
            "semantik.gf.contract_importable",
            "FAIL",
            "sa_gf_contract",
            "The SA↔GF contract modules could not be imported from the canonical package.",
            evidence=probe,
        )
        return
    actual = set(data.get("operations") or [])
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    report.add(
        "semantik.gf.operation_registry",
        "FAIL" if missing or unexpected else "PASS",
        "sa_gf_contract",
        "The executable SA↔GF v1 operation registry matches the diagnostic contract."
        if not missing and not unexpected
        else "The executable SA↔GF operation registry drifted from the locked v1 profile.",
        evidence={"missing": missing, "unexpected": unexpected, "count": len(actual)},
    )

    bridge_doc = root / "docs/reference/GF_BRIDGE_SPEC.md"
    bridge_schema = root / "schemas/gf_bridge_spec.schema.json"
    bridge_source = root / "src/semantik_architect/adapters/realization/gf/bridge.py"
    text = bridge_source.read_text(encoding="utf-8", errors="replace") if bridge_source.is_file() else ""
    strict_markers = ["lexical_slots<=placeholders", "semantic_features", "SA-GF-001"]
    missing_markers = [marker for marker in strict_markers if marker not in text]
    report.add(
        "semantik.gf.strict_consumption",
        "FAIL" if missing_markers or not bridge_doc.is_file() or not bridge_schema.is_file() else "PASS",
        "sa_gf_contract",
        "The bridge enforces fail-closed consumption of semantic lexical slots/features and its format is documented/schema-locked."
        if not missing_markers and bridge_doc.is_file() and bridge_schema.is_file()
        else "The strict bridge fidelity contract is incomplete or drifted.",
        evidence={"missing_source_markers": missing_markers, "bridge_doc": bridge_doc.is_file(), "bridge_schema": bridge_schema.is_file()},
    )

    pgf_probe = run_target_python(
        cfg,
        ["-c", "import importlib.util,json; print(json.dumps({'pgf':importlib.util.find_spec('pgf') is not None}))"],
        timeout=30,
    )
    pgf_data = json_from_stdout(pgf_probe) or {}
    pgf_available = bool(pgf_data.get("pgf"))
    deployed = bool(runtime_manifest_paths(cfg))
    verdict = "PASS" if (pgf_available or not deployed) else "BLOCKED"
    message = (
        "The selected Python can import the optional PGF binding."
        if pgf_available
        else (
            "A RuntimeSet is deployed but the selected Python cannot import pgf; real GF acceptance is blocked."
            if deployed
            else "No RuntimeSet is deployed, so the optional PGF binding is not required for this core-only campaign."
        )
    )
    report.add(
        "semantik.gf.pgf_binding",
        verdict,
        "sa_gf_contract",
        message,
        evidence={"pgf_available": pgf_available, "runtime_sets_deployed": deployed},
        recommendation=(
            "Install the project's gf extra in the runtime Python used for real-language acceptance."
            if deployed and not pgf_available
            else None
        ),
    )
