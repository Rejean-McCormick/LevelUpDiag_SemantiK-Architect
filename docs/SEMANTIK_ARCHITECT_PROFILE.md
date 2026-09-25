# SemantiK Architect v1 diagnostic profile

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
- `deep`: standard plus explicitly declared generic validators.

## Specialized levels

| ID | Contract |
|---|---|
| S10 | Architecture locks, canonical src tree, required v1 files, no competing application/grammar tree |
| S20 | Python syntax/import integrity, hexagonal direction, PGF adapter confinement, no direct per-language branches |
| S30 | Eleven JSON Schemas, canonical examples, schema IDs, documentation manifest |
| S40 | RuntimeSet manifests, artifact/capability hashes, public release validation when artifacts are deployed |
| S50 | SA↔GF operation registry, strict bridge slot/feature consumption, PGF binding readiness |
| S60 | Pure semantic→communication→language planning plus positive/negative coverage invariant probe |
| S70 | Package/SDK/CLI/minimal HTTP public surface without starting services |
| S80 | Canonical repository validator and real-language release-input status |

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
