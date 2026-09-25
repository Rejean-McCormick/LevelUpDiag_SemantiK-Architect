# Profile self-test

Profile 2.0 is self-tested at two layers.

## Diagnostics-frame tests

The LevelUpDiag repository's unit tests validate:

- manifest dependency resolution and the `S10`–`S80` campaign surface;
- src-layout local-module resolution;
- Windows→WSL path conversion;
- target-Python `PYTHONPATH` construction;
- verdict aggregation semantics;
- shell-free command execution.

## Target validation expectation

The profile is intentionally read-oriented. Its strongest target test is S80, which delegates to
the SemantiK Architect repository's own `tools/validate_repository.py` rather than duplicating
the full target test suite.

A checkout with no deployed RuntimeSet should normally finish with visible `WARN` findings for
real-language release readiness while still proving the core architecture, schemas, planning
invariants and public surfaces. Once a RuntimeSet is present, S40/S50 elevate artifact integrity,
capability/conformance evidence and PGF-binding readiness into active acceptance checks.
