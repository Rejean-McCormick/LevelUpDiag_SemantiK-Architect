# Profile self-test

Profile 2.1 is self-tested at two layers.

## Diagnostics-frame tests

The LevelUpDiag repository's unit tests validate:

- manifest dependency resolution and the `S10`–`S120` campaign surface;
- deep-only placement and ordering of S90–S120;
- syntax of every embedded adversarial target probe;
- temporary-directory mutation surfaces for RuntimeSet/bridge/packaging attacks;
- src-layout local-module resolution;
- Windows→WSL path conversion;
- target-Python `PYTHONPATH` construction;
- verdict aggregation semantics;
- shell-free command execution;
- run-1 regressions for Windows validator imports and tracked-only security scanning.

## Target validation expectation

`standard` delegates to SemantiK Architect's own `tools/validate_repository.py` as the normal release gate.

`deep` then adds S90–S120. These levels construct temporary synthetic RuntimeSets and deterministic PGF test doubles, attack fail-closed boundaries, exercise repeated and concurrent rendering, and build/import a wheel from a temporary source copy. They do not patch the target checkout.

A checkout with no deployed RuntimeSet should normally retain visible `WARN` findings for real-language release readiness while S90–S120 can still exercise the core engine and runtime contract with synthetic artifacts.
