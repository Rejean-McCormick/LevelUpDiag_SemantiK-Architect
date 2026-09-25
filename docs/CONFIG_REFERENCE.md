# Configuration reference

Configuration is JSON. `levelupdiag.config.json` is committed. `levelupdiag.config.local.json`,
when present, is recursively merged over it.

## Core keys

- `target_repo_root`: target SemantiK Architect checkout.
- `control_dir`: generated evidence directory relative to target root.
- `execution.*`: parallelism, timeouts, mutation/network policy and output bounds.
- `scan.*`: bounded scanner limits and excluded directories.
- `toolchain.*`: generic executable discovery.
- `validators`: explicit additional target validators for the `deep` campaign; v2.1 also runs built-in adversarial S90–S120 probes independently of this list.
- `security.*`: generic hygiene configuration.

## SemantiK v1 keys

- `python_executable`, `python_execution`: target interpreter selection.
- `minimum_python`: required interpreter floor.
- `python_path_entries`: entries injected into target probes (`src` by default).
- `local_packages`: package roots considered local for import resolution.
- `active_python_roots`: Python trees parsed by S20.
- `required_paths`: locked SA v1 docs, schemas and implementation boundaries required by S10.
- `forbidden_paths`, `forbidden_globs`: competing architectures/grammar-source paths rejected by S10.
- `core_forbidden_import_prefixes`, `application_forbidden_import_prefixes`: dependency-direction policy for S20.
- `schema_files`, `schema_example_pairs`: S30 contract set.
- `runtime_root`, `runtime_manifest_globs`: S40 RuntimeSet discovery.
- `required_operations`: S50 executable SA↔GF v1 operation registry.
- `public_sdk_methods`, `cli_commands`, `http_paths`: S70 public surface.
- `canonical_validator`: target-owned validator executed by S80.

## Native target Python

```json
{
  "semantik": {
    "python_execution": "native",
    "python_executable": "python"
  }
}
```

## WSL target Python

```json
{
  "semantik": {
    "python_execution": "wsl",
    "wsl_distro": "Debian",
    "python_executable": "/home/user/.venvs/semantik/bin/python"
  }
}
```

WSL mode converts the target checkout and absolute path arguments to `/mnt/<drive>/...` and
builds a Linux `PYTHONPATH` for the configured `python_path_entries`.

LevelUpDiag never installs the target dependencies itself.

## Security scan scope

`security.scan_untracked` controls whether N06 scans all bounded filesystem files or only Git-tracked files when the target is a Git repository.

- `false` (SemantiK default): ignored/untracked local files such as a developer `.env` are outside diagnostic evidence; tracked sensitive files still generate warnings.
- `true`: include untracked files in the security hygiene scan.

If Git metadata is unavailable, N06 falls back to the bounded filesystem scan because tracked/untracked status cannot be established.
