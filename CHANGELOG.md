# Changelog

## 2.1.3 — 2026-09-25

- hardened S70 so CLI module execution treats `RuntimeWarning` as an error;
- S70 now requires `python -m semantik_architect.adapters.inbound.cli.main --help` to produce empty stderr;
- added regression coverage proving a warning on CLI stderr yields `FAIL`;
- documents the lazy CLI-package import requirement that prevents `runpy` double-import warnings.

## 2.1.2 — 2026-09-25

- fixed S60's negative-coverage probe so it constructs a structurally valid `LanguagePlan` and reaches `CoverageValidator` instead of failing early in the domain constructor;
- S60 still requires the stable `SA-SEM-002` envelope for missing obligation coverage;
- retained the v2.1.1 strict S90 requirement that unknown `sa:operation` hints raise `SA-LANG-003`;
- added regression guards so the structurally-invalid empty-unit probe cannot return.

## 2.1.1 — 2026-09-25

- fixed a false PASS in S90: unknown `sa:operation` hints must now raise the stable `SA-LANG-003` envelope; raw `ValueError` is a failure;
- tightened S60 negative coverage validation to require `SA-SEM-002` rather than accepting arbitrary `ValueError`;
- added regression guards preventing broad Python-exception acceptance from returning to these probes.

## 2.1.0 — 2026-09-25

- Turned `deep` into a real adversarial SemantiK Architect campaign.
- Added S90 semantic/coverage/deadline/constraint negative probes.
- Added S100 synthetic RuntimeSet corruption and release-integrity probes.
- Added S110 strict bridge/lexical fail-closed probes with deterministic PGF test double.
- Added S120 sequential/parallel determinism and temporary-copy wheel build/install/import validation.
- Kept all mutation and packaging artifacts outside the target checkout.
- `standard` remains the normal release-gate campaign; S90–S120 are deep-only.

## 2.0.1 — 2026-09-25

- fixed Windows canonical-validator diagnosis: S80 now distinguishes missing dev dependencies from a target validator that corrupts its child `PYTHONPATH`;
- S80 adds an explicit pre-validator target-package import probe;
- fixed N06 so `security.scan_untracked=false` is actually honored for Git targets;
- removed the redundant PGF warning when no RuntimeSet is deployed; PGF becomes blocking only when real-language acceptance is actually requested;
- added regression tests for all run-1 diagnostic defects.

## 2.0.0 — 2026-09-25

SemantiK Architect v1 alignment.

### Replaced diagnostic model

- Replaced the previous application/runtime-only profile with the clean SA v1 canonical architecture.
- Replaced fixed-PGF diagnostics with composed immutable RuntimeSet/capability-profile diagnostics.
- Replaced FastAPI/frontend checks with SDK/CLI/minimal-HTTP public-surface checks.
- Added JSON Schema and documentation-manifest alignment checks.
- Added executable SA↔GF operation-registry and strict bridge-consumption checks.
- Added pure faithfulness/planning probes that require no deployed language runtime.
- Added canonical target validator delegation in S80.

### Architecture enforcement

- `src/semantik_architect` is treated as the only canonical package tree.
- Domain/application imports are checked for hexagonal dependency-direction violations.
- PGF imports are restricted to the GF realization adapter.
- Direct language-code branching in shared domain/application code is rejected.
- Old application trees, family engines, safe-mode paths and GF source files are rejected by S10.

### Runtime semantics

- No deployed RuntimeSet is a visible `WARN`, not a source failure.
- Deployed RuntimeSets are hash-checked and validated through the public SA SDK.
- Missing `pgf` is a `WARN` without RuntimeSets and `BLOCKED` when real-language acceptance is attempted.

### Self-validation

- Diagnostics-frame unit tests expanded to 14 tests.
- Added src-layout, architecture-import, language-branch and RuntimeSet-discovery tests.
