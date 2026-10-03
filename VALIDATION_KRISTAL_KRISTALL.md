# LevelUpDiag SemantiK Architect 2.3.0 — Kristal/Kristall alignment

Date: 2026-10-03

## Target

SemantiK Architect `1.3.0-alpha.2` with portable `kristal_state/6.0` ingress and Kristal/Kristall `7.0.0-draft.3.2` design baseline.

## S30 invariants

The diagnostic executes the portable communication projection through `KristalV6Acl` and proves:

1. selected assertion metadata remains traceable;
2. changing `actionability` to `automatic` does not create an obligation;
3. communicative force is unchanged by actionability metadata;
4. `PORTABLE_CONTRACT == kristal_state/6.0`;
5. `KRISTALL_DESIGN_BASELINE == 7.0.0-draft.3.2`.

The profile also validates the 1.3 MathKristal/Informath schema/example surface. Full runtime acceptance remains fail-closed when real external PGF/Informath release artifacts are absent.

## Validation results

- LevelUpDiag self-tests: **24 passed**.
- Target SemantiK Architect repository validation: **60 passed; 16 schemas valid**.
- `standard` campaign: **WARN with zero FAIL**.
- `deep` campaign: **WARN with zero FAIL**; S90/S100/S110/S120 all PASS.
- Remaining warnings are expected for an external-target snapshot with no deployed production RuntimeSet/PGF.

