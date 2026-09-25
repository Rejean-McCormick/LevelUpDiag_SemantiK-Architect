# Deep Adversarial Diagnostics

Status: **LevelUpDiag SemantiK Architect v2.1.3**

The `deep` campaign is the bug-hunting layer above the normal release gate. It does not require a deployed real-language RuntimeSet and does not mutate the target checkout.

## S90 — Adversarial Semantic Invariants

Checks duplicate obligation IDs, missing semantic references, invalid supporting-context subjects, impossible framing constraints, expired deadlines, missing/unknown coverage, negative polarity preservation, canonical role→operation selection, and rejection of unknown operation hints through the stable `SA-LANG-003` envelope; raw Python exceptions are diagnostic failures.

## S100 — RuntimeSet Mutation & Release Integrity

Builds valid synthetic RuntimeSets in temporary storage, then independently tests artifact hash tampering, capability-manifest tampering, failed conformance evidence, missing capability-profile artifacts, ambiguous released runtimes without activation, explicit activation, and incompatible SA version ranges.

## S110 — Bridge & Lexical Adversarial Contract

Uses a deterministic PGF test double and temporary artifacts. It verifies that every lexical slot and semantic feature must be consumed, contract-version mismatches fail, missing concrete languages fail, missing concept lexemes are not guessed, and exact lexical bindings succeed when present.

## S120 — Determinism, Concurrency & Packaging Isolation

Runs repeated full renders against a synthetic RuntimeSet both sequentially and concurrently and requires identical deterministic result IDs and surface output. It then copies the target source tree into a temporary directory, builds a wheel without dependency/network resolution, installs it into an isolated target directory, and imports it under isolated Python mode.

## Non-mutation rule

All generated RuntimeSets, corrupted files, build outputs and installs live under temporary directories. `.levelupdiag/` remains the only diagnostic evidence written under the target repository by the LevelUpDiag runner itself.
