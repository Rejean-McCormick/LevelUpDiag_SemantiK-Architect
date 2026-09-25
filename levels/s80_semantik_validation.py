from __future__ import annotations

from pathlib import Path

from levelupdiag_core.semantik import (
    extract_missing_module,
    is_local_module_name,
    run_target_python,
    runtime_manifest_paths,
)


def diagnose_validator_failure(cfg, result, *, import_ok: bool):
    missing = extract_missing_module(result)
    if result.get("timed_out"):
        return "INFRA_ERROR", missing, "Increase the validation timeout only after checking whether the validator is hung."
    if result.get("exit_code") == 0:
        return "PASS", missing, None
    if missing in {"pytest", "jsonschema"}:
        return "BLOCKED", missing, f"Install the missing development dependency `{missing}` in the selected target Python."
    if missing and is_local_module_name(missing, cfg) and import_ok:
        return (
            "FAIL",
            missing,
            "The package imports successfully before the validator starts, but the validator's child process "
            "loses the local package. Inspect how tools/validate_repository.py composes PYTHONPATH; use "
            "os.pathsep instead of a hard-coded ':' and preserve any existing PYTHONPATH.",
        )
    return (
        "FAIL",
        missing,
        "Inspect the validator stdout/stderr; this is a target validation failure, not a missing diagnostic dependency.",
    )


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

    import_probe = run_target_python(
        cfg,
        ["-c", "import semantik_architect; print(semantik_architect.__version__)"],
        timeout=60,
    )
    import_ok = import_probe.get("exit_code") == 0
    report.add(
        "semantik.validation.target_import_probe",
        "PASS" if import_ok else "FAIL",
        "validation",
        "The target package imports correctly in the configured diagnostic environment."
        if import_ok
        else "The target package cannot be imported in the configured diagnostic environment.",
        evidence=import_probe,
        recommendation=None
        if import_ok
        else "Fix the profile Python/PYTHONPATH configuration before interpreting repository-validator failures.",
    )
    if not import_ok:
        return

    result = run_target_python(cfg, [str(validator)], timeout=1200)
    verdict, missing, recommendation = diagnose_validator_failure(
        cfg, result, import_ok=import_ok
    )

    report.add(
        "semantik.validation.canonical_result",
        verdict,
        "validation",
        "The canonical SemantiK Architect repository validator passed."
        if verdict == "PASS"
        else "The canonical SemantiK Architect repository validator did not complete successfully.",
        evidence={**result, "missing_module": missing},
        recommendation=recommendation,
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
