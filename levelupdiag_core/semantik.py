from __future__ import annotations

import ast
import json
import os
import re
from pathlib import Path

from .commands import run_command

MODULE_NOT_FOUND_RE = re.compile(r"ModuleNotFoundError:\s+No module named ['\"]([^'\"]+)['\"]")
WINDOWS_ABS_RE = re.compile(r"^([A-Za-z]):[\\/](.*)$")
LANGUAGE_BRANCH_RE = re.compile(
    r"\b(?:target_language|language|lang)\b\s*==\s*['\"][A-Za-z]{2,3}(?:-[A-Za-z0-9]+)?['\"]"
)


def profile(cfg):
    return cfg.get("semantik", {})


def target_root(cfg) -> Path:
    return Path(cfg["_target_root"])


def target_python(cfg) -> str:
    return str(profile(cfg).get("python_executable") or "python")


def target_python_execution(cfg) -> str:
    return str(profile(cfg).get("python_execution") or "native").strip().lower()


def windows_path_to_wsl(value: str) -> str:
    """Convert an absolute Windows path to the standard /mnt/<drive>/ WSL form."""
    m = WINDOWS_ABS_RE.match(str(value))
    if not m:
        return str(value)
    drive = m.group(1).lower()
    rest = re.sub(r"[\\/]+", "/", m.group(2))
    return f"/mnt/{drive}/{rest}"


def _target_arg_for_wsl(value: str) -> str:
    value = str(value)
    return windows_path_to_wsl(value) if WINDOWS_ABS_RE.match(value) else value


def command_limit(cfg) -> int:
    return int(cfg.get("execution", {}).get("capture_limit_kb", 256))


def _pythonpath_value(cfg, *, wsl: bool) -> str:
    root = target_root(cfg)
    entries = []
    for rel in profile(cfg).get("python_path_entries", []):
        path = root / rel
        rendered = windows_path_to_wsl(str(path)) if wsl else str(path)
        entries.append(rendered)
    return os.pathsep.join(entries) if not wsl else ":".join(entries)


def target_python_env(cfg, extra=None, *, wsl: bool | None = None):
    mode = target_python_execution(cfg)
    use_wsl = mode == "wsl" if wsl is None else bool(wsl)
    env = {}
    pythonpath = _pythonpath_value(cfg, wsl=use_wsl)
    if pythonpath:
        existing = os.environ.get("PYTHONPATH", "")
        if existing and not use_wsl:
            pythonpath = pythonpath + os.pathsep + existing
        env["PYTHONPATH"] = pythonpath
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if extra:
        env.update({str(k): str(v) for k, v in extra.items()})
    return env


def run_target_python(cfg, args, *, timeout=120, env=None):
    target = target_root(cfg)
    mode = target_python_execution(cfg)
    merged_extra = target_python_env(cfg, env, wsl=(mode == "wsl"))

    if mode == "wsl":
        p = profile(cfg)
        distro = str(p.get("wsl_distro") or "Debian")
        python_exe = target_python(cfg)
        target_wsl = windows_path_to_wsl(str(target))
        target_args = [_target_arg_for_wsl(x) for x in args]

        command = [
            "wsl.exe",
            "-d",
            distro,
            "--cd",
            target_wsl,
            "--",
            "/usr/bin/env",
            *[f"{key}={value}" for key, value in merged_extra.items()],
            python_exe,
            *target_args,
        ]

        return run_command(
            command,
            cwd=target,
            timeout_seconds=timeout,
            capture_limit_kb=command_limit(cfg),
            env=os.environ.copy(),
            redact_output=cfg.get("redaction", {}).get("enabled", True),
        )

    if mode != "native":
        raise ValueError(f"Unsupported semantik.python_execution: {mode}")

    merged = os.environ.copy()
    merged.update(merged_extra)
    return run_command(
        [target_python(cfg), *args],
        cwd=target,
        timeout_seconds=timeout,
        capture_limit_kb=command_limit(cfg),
        env=merged,
        redact_output=cfg.get("redaction", {}).get("enabled", True),
    )


def extract_missing_module(result):
    text = (result.get("stderr_tail") or "") + "\n" + (result.get("stdout_tail") or "")
    m = MODULE_NOT_FOUND_RE.search(text)
    return m.group(1) if m else None


def is_local_module_name(name: str, cfg) -> bool:
    roots = set(profile(cfg).get("local_packages", []))
    return bool(name) and name.split(".", 1)[0] in roots


def module_exists(root: Path, module: str, source_roots=()) -> bool:
    rel = Path(*module.split("."))
    bases = [root, *(root / item for item in source_roots)]
    for base in bases:
        p = base / rel
        if p.with_suffix(".py").is_file() or (p / "__init__.py").is_file():
            return True
    return False


def iter_active_python_files(cfg):
    root = target_root(cfg)
    excluded = set(cfg.get("scan", {}).get("exclude_dirs", []))
    for rel_root in profile(cfg).get("active_python_roots", []):
        base = root / rel_root
        if base.is_file() and base.suffix == ".py":
            yield base, base.relative_to(root).as_posix()
            continue
        if not base.is_dir():
            continue
        for p in base.rglob("*.py"):
            try:
                rel = p.relative_to(root)
            except ValueError:
                continue
            if any(part in excluded for part in rel.parts[:-1]):
                continue
            yield p, rel.as_posix()


def _absolute_imports(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node, alias.name
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node, node.module


def scan_python_integrity(cfg):
    root = target_root(cfg)
    parse_errors = []
    missing_imports = []
    forbidden_refs = []
    prefixes = tuple(profile(cfg).get("forbidden_import_prefixes", []))
    source_roots = tuple(profile(cfg).get("python_path_entries", []))
    scanned = 0
    for path, rel in iter_active_python_files(cfg):
        scanned += 1
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(text, filename=rel)
        except SyntaxError as exc:
            parse_errors.append({"path": rel, "line": exc.lineno, "message": exc.msg})
            continue
        except OSError as exc:
            parse_errors.append({"path": rel, "line": None, "message": str(exc)})
            continue
        for node, name in _absolute_imports(tree):
            if prefixes and any(name == p or name.startswith(p + ".") for p in prefixes):
                forbidden_refs.append({"path": rel, "line": getattr(node, "lineno", None), "module": name})
            if is_local_module_name(name, cfg) and not module_exists(root, name, source_roots):
                missing_imports.append({"path": rel, "line": getattr(node, "lineno", None), "module": name})

    def uniq(items):
        seen = set()
        out = []
        for item in items:
            key = tuple(sorted(item.items()))
            if key not in seen:
                seen.add(key)
                out.append(item)
        return out

    return scanned, uniq(parse_errors), uniq(missing_imports), uniq(forbidden_refs)


def scan_architecture_imports(cfg):
    root = target_root(cfg)
    problems = []
    zones = [
        (
            root / "src/semantik_architect/domain",
            tuple(profile(cfg).get("core_forbidden_import_prefixes", [])),
            "domain",
        ),
        (
            root / "src/semantik_architect/application",
            tuple(profile(cfg).get("application_forbidden_import_prefixes", [])),
            "application",
        ),
    ]
    for base, prefixes, zone in zones:
        if not base.is_dir():
            continue
        for path in base.rglob("*.py"):
            rel = path.relative_to(root).as_posix()
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(text, filename=rel)
            except (SyntaxError, OSError):
                continue
            for node, name in _absolute_imports(tree):
                if any(name == p or name.startswith(p + ".") for p in prefixes):
                    problems.append(
                        {
                            "path": rel,
                            "line": getattr(node, "lineno", None),
                            "module": name,
                            "zone": zone,
                        }
                    )
    return problems


def scan_language_branches(cfg):
    root = target_root(cfg)
    hits = []
    for base_rel in ("src/semantik_architect/domain", "src/semantik_architect/application"):
        base = root / base_rel
        if not base.is_dir():
            continue
        for path in base.rglob("*.py"):
            text = path.read_text(encoding="utf-8", errors="replace")
            for line_no, line in enumerate(text.splitlines(), 1):
                if LANGUAGE_BRANCH_RE.search(line):
                    hits.append(
                        {
                            "path": path.relative_to(root).as_posix(),
                            "line": line_no,
                            "source": line.strip()[:240],
                        }
                    )
    return hits


def normalize_distribution(raw: str) -> str:
    raw = raw.strip()
    if not raw or raw.startswith("#"):
        return ""
    raw = raw.split(";", 1)[0].strip()
    raw = re.split(r"[<>=!~ ]", raw, maxsplit=1)[0]
    raw = raw.split("[", 1)[0]
    return re.sub(r"[-_.]+", "-", raw).lower().strip()


def requirements_distributions(path: Path):
    if not path.is_file():
        return set()
    out = set()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        n = normalize_distribution(line)
        if n:
            out.add(n)
    return out


def load_pyproject(root: Path):
    path = root / "pyproject.toml"
    if not path.is_file():
        return None
    try:
        import tomllib

        with path.open("rb") as handle:
            return tomllib.load(handle)
    except Exception:
        return None


def declared_project_dependencies(root: Path):
    data = load_pyproject(root) or {}
    project = data.get("project") if isinstance(data, dict) else None
    if not isinstance(project, dict):
        return set(), {}
    deps = {
        normalize_distribution(str(item))
        for item in project.get("dependencies", [])
        if normalize_distribution(str(item))
    }
    optional = {}
    for group, values in (project.get("optional-dependencies") or {}).items():
        optional[str(group)] = {
            normalize_distribution(str(item))
            for item in values
            if normalize_distribution(str(item))
        }
    return deps, optional


def json_from_stdout(result):
    text = (result.get("stdout_tail") or "").strip()
    if not text:
        return None
    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    return None


def runtime_manifest_paths(cfg):
    root = target_root(cfg)
    runtime_root = root / profile(cfg).get("runtime_root", "runtime")
    if not runtime_root.is_dir():
        return []
    found = set()
    for pattern in profile(cfg).get("runtime_manifest_globs", ["runtime.manifest.json"]):
        found.update(runtime_root.rglob(pattern))
    return sorted(found)
