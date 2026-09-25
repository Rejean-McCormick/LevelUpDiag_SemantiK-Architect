# Adaptation guide

The neutral frame is intentionally incomplete with respect to any particular application. Adapt only after observing the real repository.

## 1. Inventory first

Run:

```bash
python levelupdiag/levelupdiag.py run baseline
```

Use the inventory and tooling reports to learn what the repository actually contains.

## 2. Prefer public target validators

If the target already exposes canonical commands for tests, linting, build validation, schema validation, package verification, or similar contracts, declare those commands under `validators` before recreating their logic in LevelUpDiag.

This keeps LevelUpDiag a diagnostics orchestrator rather than a duplicate test framework.

## 3. Add a level only for a real diagnostic domain

Create a new level when one of these is true:

- the target has a contract not represented by existing public validators;
- evidence needs target-specific interpretation;
- several checks form a coherent diagnostic domain;
- dependencies or blocking semantics require an independent unit.

Do **not** add levels merely to preserve a numbering pattern from another repository.

## 4. Change anything that should change

A copied suite may change:

```text
manifest
campaigns
config keys
core
levels
schemas
CLI
launchers
documentation
```

The neutral frame is lineage, not a compatibility prison.

## 5. Define target policy explicitly

Decide which levels are required, what `WARN` means, which validators are networked or mutating, and what evidence is required for the target's own merge/release process.

Do not create a universal release gate unless the target actually has a defined release evidence contract.

## 6. Keep target mutation explicit

A command that installs dependencies, formats files, generates committed code, updates lock files, starts persistent services, changes databases, or otherwise mutates the target should declare `mutates_target: true`.

Mutation remains blocked until `execution.allow_target_mutation` is explicitly enabled in local configuration.

## 7. Keep secrets out of diagnostics

Do not put credentials in committed config. Prefer environment variables or the target's established secret mechanism. Avoid copying secret values into findings or artifacts.
