# LevelUpDiag SemantiK Architect 2.2.0 — Kristal v6 validation

Date: 2026-10-01

## Result

- LevelUpDiag self-tests: **24 passed**.
- `levels/s30_semantik_contracts.py`: syntax validation **PASS**.
- Against SemantiK Architect 1.2.0 snapshot:
  - S10 Architecture Lock: **PASS**;
  - S30 Contract & Schema Integrity: **PASS**;
  - overall targeted S30 campaign: **WARN** only because N01 reports external-target context rather than a local VCS checkout.

## New S30 invariant

The diagnostic executes the Kristal v6 communication projection example through `KristalV6Acl` and proves:

1. selected assertion metadata is preserved;
2. selected assertions must remain traceable through request `source_refs`;
3. changing `actionability` to `automatic` does not create an obligation;
4. changing `actionability` does not alter communicative force.

## Runtime note

The uploaded SemantiK Architect SmartSnap contains RuntimeSet manifests but not all referenced real PGF artifacts. Full S40/runtime release acceptance is therefore expected to fail closed until those external release artifacts are mounted. The profile does not downgrade that condition.
