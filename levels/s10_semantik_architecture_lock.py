from __future__ import annotations

from pathlib import Path


def run(cfg, report):
    root = Path(cfg["_target_root"])
    p = cfg.get("semantik", {})

    required = list(p.get("required_paths", []))
    missing = [rel for rel in required if not (root / rel).exists()]
    report.add(
        "semantik.architecture.required_contracts",
        "FAIL" if missing else "PASS",
        "semantik_architecture",
        "The locked v1 architecture, schemas, source boundaries and release tools are present."
        if not missing
        else "One or more required SemantiK Architect v1 contracts or source boundaries are missing.",
        evidence=missing or {"required_path_count": len(required)},
        recommendation=None
        if not missing
        else "Restore the missing locked contract/source file before trusting implementation diagnostics.",
    )

    forbidden = []
    for rel in p.get("forbidden_paths", []):
        if (root / rel).exists():
            forbidden.append(rel)
    for pattern in p.get("forbidden_globs", []):
        for hit in root.glob(pattern):
            try:
                rel = hit.relative_to(root).as_posix()
            except ValueError:
                rel = str(hit)
            if rel not in forbidden:
                forbidden.append(rel)
    report.add(
        "semantik.architecture.single_canonical_tree",
        "FAIL" if forbidden else "PASS",
        "semantik_architecture",
        "No alternate grammar/application tree competes with the canonical src/semantik_architect architecture."
        if not forbidden
        else "Files or directories exist that violate the single canonical SemantiK Architect tree.",
        evidence=forbidden[:200] if forbidden else None,
        recommendation=None
        if not forbidden
        else "Remove the conflicting path rather than adding compatibility routing around it.",
    )

    expected_dirs = [
        "src/semantik_architect/domain",
        "src/semantik_architect/application",
        "src/semantik_architect/adapters",
        "src/semantik_architect/bootstrap",
        "src/semantik_architect/conformance",
        "src/semantik_architect/observability",
    ]
    missing_dirs = [rel for rel in expected_dirs if not (root / rel).is_dir()]
    report.add(
        "semantik.architecture.hexagonal_modules",
        "FAIL" if missing_dirs else "PASS",
        "semantik_architecture",
        "The hexagonal modular-monolith source boundaries are physically represented."
        if not missing_dirs
        else "The expected hexagonal module boundaries are incomplete.",
        evidence=missing_dirs or expected_dirs,
    )

    readme = (root / "README.md").read_text(encoding="utf-8", errors="replace") if (root / "README.md").is_file() else ""
    architecture = (root / "docs/02_ARCHITECTURE_LOCK.md").read_text(encoding="utf-8", errors="replace") if (root / "docs/02_ARCHITECTURE_LOCK.md").is_file() else ""
    text = (readme + "\n" + architecture).lower()
    markers = [
        "semantic-to-human",
        "communicationrequest",
        "communicationplanner",
        "languageplan",
        "gf",
        "no hidden fallback",
    ]
    missing_markers = [marker for marker in markers if marker not in text]
    report.add(
        "semantik.architecture.lock_documented",
        "FAIL" if missing_markers else "PASS",
        "semantik_architecture",
        "The product boundary and canonical semantic→communication→language→GF pipeline are documented."
        if not missing_markers
        else "The architecture documentation no longer exposes all locked v1 boundary markers.",
        evidence=missing_markers or markers,
    )
