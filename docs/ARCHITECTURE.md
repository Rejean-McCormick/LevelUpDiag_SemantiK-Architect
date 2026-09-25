# Architecture

## Design goal

LevelUpDiag is a **copy-in frame**, not a centralized runtime framework. The copy inside a target repository owns its future evolution.

## Dependency direction

```text
CLI / launchers
      ↓
manifest + config
      ↓
campaign scheduler
      ↓  separate process per level
levels
      ↓
small shared core
      ↓
read-only target observation OR explicitly declared validator commands
```

The core must never depend on one specific level or one target technology.

## Source vs runtime data

```text
<target>/levelupdiag/     committed diagnostics source
<target>/.levelupdiag/    generated evidence and run history
```

Scans exclude both by default where appropriate, preventing self-observation from contaminating target evidence.

## Process isolation

Each level is launched in a fresh Python process. This keeps crashes, imports, exit behavior and transient state isolated from the campaign scheduler.

## Parallel scheduler

The manifest defines `depends_on` and `parallel_safe`. The scheduler runs independent safe levels concurrently up to `execution.max_parallel`. A level with `parallel_safe: false` executes exclusively.

Numeric order is presentation order, not dependency semantics.

## Neutrality

The base frame distinguishes:

1. universal evidence that is safe to collect generically;
2. discovered capabilities that are informative but not automatically mandatory;
3. explicitly declared validators that may execute target tooling;
4. target-specific levels added after copy.

This separation prevents “manifest found → guessed command executed” behavior.
