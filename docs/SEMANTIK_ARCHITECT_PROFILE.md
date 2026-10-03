# SemantiK Architect v1 / 1.3 diagnostic profile

This LevelUpDiag profile treats the locked SemantiK Architect v1 contracts as the diagnostic
authority.

## Product contract

SA transforms structured semantics and explicit communication obligations into faithful,
context-appropriate multilingual communication. The diagnostic profile therefore protects the
same boundaries as the product:

```text
SemanticGraph + CommunicationObligations + CommunicationContext
  -> CommunicationPlan
  -> LanguagePlan
  -> lexical bindings
  -> versioned SA↔GF bridge
  -> GF/PGF
  -> CommunicationResult + coverage + RuntimeSet identity
```

The profile does not assume one language, one concrete grammar, one PGF filename, a web
framework, a frontend, or a grammar-development subsystem inside SA.

## Target

Committed default:

```text
C:\mycode\SemantiK_Architect\SemantiK_Architect
```

Override with `--target` or `levelupdiag.config.local.json`.

## Campaigns

- `baseline`: generic LevelUpDiag repository evidence only.
- `semantik`: full SA v1 architecture/contracts/runtime-model probes, excluding the target's full validator.
- `standard`: recommended; adds S80 and executes `tools/validate_repository.py`.
- `deep`: standard plus declared validators and the adversarial S90–S120 suite.

## Specialized levels

| ID | Contract |
|---|---|
| S10 | Architecture locks, canonical src tree, required v1 files, no competing application/grammar tree |
| S20 | Python syntax/import integrity, hexagonal direction, PGF adapter confinement, no direct per-language branches |
| S30 | Sixteen JSON Schemas, canonical examples, schema IDs, documentation manifest, MathKristal contracts, and executable Kristal portable-v6 ACL traceability/non-inference + v7-baseline probe |
| S40 | RuntimeSet manifests, artifact/capability hashes, public release validation when artifacts are deployed |
| S50 | SA↔GF operation registry, strict bridge slot/feature consumption, PGF binding readiness |
| S60 | Pure semantic→communication→language planning plus positive/negative coverage invariant probe |
| S70 | Package/SDK/CLI/minimal HTTP public surface without starting services |
| S80 | Canonical repository validator and real-language release-input status |
| S90 | Adversarial semantic/coverage/deadline/constraint invariants |
| S100 | Synthetic RuntimeSet mutation and release-integrity failures |
| S110 | SA↔GF bridge and exact lexical-binding adversarial contract |
| S120 | Sequential/parallel determinism and isolated wheel packaging/import |

## Verdict policy

- Missing required architecture/schema/source contract: `FAIL`.
- Core imports a concrete adapter/PGF/web framework: `FAIL`.
- Shared core branches directly on a language code: `FAIL`.
- Schema or canonical example fails formal validation: `FAIL`.
- Deployed RuntimeSet has hash/profile/evidence failure: `FAIL`.
- No RuntimeSet deployed: `WARN` (engine validation remains useful).
- `pgf` binding absent with no deployed RuntimeSet: `WARN`.
- `pgf` binding absent while a RuntimeSet is deployed for acceptance: `BLOCKED`.
- Canonical target validator missing/failing in `standard`: `FAIL` (or `BLOCKED` if its dev prerequisites are absent).

## Non-mutation

The suite does not install dependencies, compile GF, generate RuntimeSets, start HTTP servers,
modify capability manifests, or patch target source. Evidence is written only under
`.levelupdiag/` in the target repository.

## Deep campaign contract

The deep suite MUST remain target-read-only. Runtime corruption is performed only on synthetic RuntimeSets under temporary directories. Packaging is tested from a temporary source copy. A failing adversarial case is a product/contract signal and MUST NOT be converted to `WARN` merely because the happy-path suite passes.

## Kristal / Kristall boundary

For SemantiK Architect `1.3.0-alpha.2`, S30 retains the explicit `semantik.kristal-v6.communication-projection/1.0` portable schema/example/adapter and additionally verifies the declared Kristal/Kristall `7.0.0-draft.3.2` design baseline. It proves that selected assertions remain source-traceable, changing `actionability` to `automatic` does not create an obligation or alter communicative force, and DaaT is not treated as the communication-selection authority.

S30 also includes the 1.3 MathKristal/Informath schema surface. Grammar-development `.gf` files remain forbidden in the target SA repository.
