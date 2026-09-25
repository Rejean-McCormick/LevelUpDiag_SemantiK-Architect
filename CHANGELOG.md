# Changelog

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
