# LevelUpDiag SemantiK Architect profile manifest

Profile version: **2.1.3**

Target architecture: **SemantiK Architect v1 clean canonical repository**.

Specialized levels: `S10` through `S120`.

Key profile rules:

- `src/semantik_architect` is the canonical Python tree;
- domain/application dependency direction is enforced;
- PGF imports are confined to the GF realization adapter;
- direct language-code branching in the shared core is rejected;
- all eleven v1 JSON Schemas are part of the contract surface;
- RuntimeSets are composed, immutable, hashed and capability-profile gated;
- SA↔GF is a versioned operation/bridge contract, not a hard-coded single PGF path;
- obligation and semantic-reference coverage are tested without requiring a runtime language;
- SDK, CLI and minimal stdlib HTTP surfaces replace assumptions about FastAPI or a frontend;
- `standard` delegates final repository validation to `tools/validate_repository.py`;
- `deep` adds fail-closed semantic probes, synthetic RuntimeSet corruption, bridge/lexical attacks, deterministic concurrent rendering, and isolated wheel packaging/import;
- missing real-language RuntimeSets remain visible without being misclassified as source defects;
- no dependency installation, network access, GF compilation, server startup or target mutation is performed.
