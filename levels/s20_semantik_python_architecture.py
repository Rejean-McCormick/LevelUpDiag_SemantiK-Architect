from __future__ import annotations

from pathlib import Path

from levelupdiag_core.semantik import (
    declared_project_dependencies,
    json_from_stdout,
    run_target_python,
    scan_architecture_imports,
    scan_language_branches,
    scan_python_integrity,
)


def run(cfg, report):
    root = Path(cfg["_target_root"])
    p = cfg.get("semantik", {})
    minimum = tuple(int(x) for x in p.get("minimum_python", [3, 12]))
    py = run_target_python(
        cfg,
        ["-c", "import json,sys; print(json.dumps({'version':list(sys.version_info[:3]),'executable':sys.executable}))"],
        timeout=30,
    )
    py_info = json_from_stdout(py)
    if py.get("exit_code") != 0 or not isinstance(py_info, dict):
        report.add(
            "semantik.python.target_environment",
            "BLOCKED",
            "python_architecture",
            "The selected target Python could not be executed.",
            evidence=py,
        )
    else:
        version = tuple(py_info.get("version", []))
        report.add(
            "semantik.python.target_environment",
            "PASS" if version >= minimum else "FAIL",
            "python_architecture",
            f"Target Python satisfies the SemantiK Architect minimum {minimum[0]}.{minimum[1]}."
            if version >= minimum
            else f"Target Python is older than the required {minimum[0]}.{minimum[1]}.",
            evidence=py_info,
        )

    core_deps, optional = declared_project_dependencies(root)
    forbidden_runtime = sorted(set(p.get("forbidden_runtime_distributions", [])) & core_deps)
    report.add(
        "semantik.python.runtime_dependency_surface",
        "FAIL" if forbidden_runtime else "PASS",
        "python_architecture",
        "The core runtime dependency surface remains clean and does not reintroduce application-framework/infrastructure dependencies."
        if not forbidden_runtime
        else "Forbidden runtime dependencies were reintroduced into project.dependencies.",
        evidence={"project_dependencies": sorted(core_deps), "forbidden_present": forbidden_runtime},
    )
    missing_optional = {}
    for group, required in p.get("required_optional_distributions", {}).items():
        absent = sorted(set(required) - set(optional.get(group, set())))
        if absent:
            missing_optional[group] = absent
    report.add(
        "semantik.python.optional_dependency_contract",
        "FAIL" if missing_optional else "PASS",
        "python_architecture",
        "The gf/dev optional dependency groups declare the expected PGF and validation tooling."
        if not missing_optional
        else "The pyproject optional dependency contract is incomplete.",
        evidence=missing_optional or {k: sorted(v) for k, v in optional.items()},
    )

    scanned, parse_errors, missing_imports, forbidden_refs = scan_python_integrity(cfg)
    report.metrics["python_files_scanned"] = scanned

    report.add(
        "semantik.python.syntax",
        "FAIL" if parse_errors else "PASS",
        "python_architecture",
        "Active Python sources parse successfully."
        if not parse_errors
        else "Syntax errors exist in active SemantiK Architect Python sources.",
        evidence=parse_errors[:100] if parse_errors else {"files_scanned": scanned},
    )
    report.add(
        "semantik.python.local_imports.resolve",
        "FAIL" if missing_imports else "PASS",
        "python_architecture",
        "Absolute imports into the local semantik_architect package resolve under the src layout."
        if not missing_imports
        else "One or more local imports point to a missing module.",
        evidence=missing_imports[:100] if missing_imports else None,
        recommendation=None
        if not missing_imports
        else "Fix the import or restore the canonical module; do not mask it with a compatibility shim.",
    )
    report.add(
        "semantik.python.forbidden_imports.absent",
        "FAIL" if forbidden_refs else "PASS",
        "python_architecture",
        "Active Python sources do not import forbidden alternate application roots."
        if not forbidden_refs
        else "Active code imports a forbidden non-canonical application root.",
        evidence=forbidden_refs[:100] if forbidden_refs else None,
    )

    boundary_violations = scan_architecture_imports(cfg)
    report.add(
        "semantik.python.hexagonal_dependency_direction",
        "FAIL" if boundary_violations else "PASS",
        "python_architecture",
        "Domain/application code does not depend on PGF, web frameworks, or concrete adapters."
        if not boundary_violations
        else "Hexagonal dependency direction is violated by core imports.",
        evidence=boundary_violations[:100] if boundary_violations else None,
    )

    language_branches = scan_language_branches(cfg)
    report.add(
        "semantik.python.no_language_code_branches",
        "FAIL" if language_branches else "PASS",
        "python_architecture",
        "Shared domain/application code contains no direct per-language branching."
        if not language_branches
        else "Shared core code contains direct language-code branching.",
        evidence=language_branches[:100] if language_branches else None,
        recommendation=None
        if not language_branches
        else "Move language-specific behavior to runtime profile data, lexical artifacts, or the GF bridge.",
    )

    pgf_imports = []
    for path in (root / "src/semantik_architect").rglob("*.py") if (root / "src/semantik_architect").is_dir() else []:
        text = path.read_text(encoding="utf-8", errors="replace")
        if "import pgf" in text or "from pgf" in text:
            rel = path.relative_to(root).as_posix()
            if not rel.startswith("src/semantik_architect/adapters/realization/gf/"):
                pgf_imports.append(rel)
    report.add(
        "semantik.python.pgf_adapter_only",
        "FAIL" if pgf_imports else "PASS",
        "python_architecture",
        "PGF imports are confined to the GF realization adapter."
        if not pgf_imports
        else "PGF leaked outside the GF adapter boundary.",
        evidence=pgf_imports or None,
    )
