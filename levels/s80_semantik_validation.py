from __future__ import annotations

from pathlib import Path

from levelupdiag_core.semantik import extract_missing_module, run_target_python, runtime_manifest_paths


def run(cfg, report):
    root = Path(cfg["_target_root"])
    p = cfg.get("semantik", {})
    validator = root / p.get("canonical_validator", "tools/validate_repository.py")
    if not validator.is_file():
        report.add(
            "semantik.validation.canonical_validator_present",
            "FAIL",
            "validation",
            "The canonical repository validator is missing.",
            evidence={"path": str(validator)},
        )
        return
    report.add(
        "semantik.validation.canonical_validator_present",
        "PASS",
        "validation",
        "The canonical repository validator is present.",
        evidence={"path": str(validator)},
    )

    result = run_target_python(cfg, [str(validator)], timeout=1200)
    if result.get("timed_out"):
        verdict = "INFRA_ERROR"
    elif result.get("exit_code") == 0:
        verdict = "PASS"
    else:
        missing = extract_missing_module(result)
        verdict = "BLOCKED" if missing in {"pytest", "jsonschema"} else "FAIL"
    report.add(
        "semantik.validation.canonical_result",
        verdict,
        "validation",
        "The canonical SemantiK Architect repository validator passed."
        if verdict == "PASS"
        else "The canonical SemantiK Architect repository validator did not complete successfully.",
        evidence=result,
        recommendation=None
        if verdict == "PASS"
        else "Use the development environment with pytest/jsonschema installed and inspect the validator output.",
    )

    manifests = runtime_manifest_paths(cfg)
    report.add(
        "semantik.validation.real_language_release_input",
        "PASS" if manifests else "WARN",
        "validation",
        "At least one RuntimeSet is deployed, so real-language release validation is part of this run."
        if manifests
        else "No RuntimeSet is deployed; this campaign validates the SA engine but not a real released language/profile.",
        evidence={"runtime_manifest_count": len(manifests)},
    )
