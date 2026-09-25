from __future__ import annotations

import re
from pathlib import Path

from levelupdiag_core.commands import run_command, which
from levelupdiag_core.scanner import iter_files
from levelupdiag_core.util import bounded_text, is_excluded

PATTERNS = [
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("github-token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b")),
    ("github-fine-grained-token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{30,}\b")),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    (
        "generic-secret-assignment",
        re.compile(
            r"(?i)\b(?:api[_-]?key|secret|access[_-]?token)\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{20,}"
        ),
    ),
]
SENSITIVE_NAMES = {".env", "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519"}


def _tracked_files(target: Path, cfg, *, max_files: int, extra_globs):
    """Yield tracked files only when the security profile requests it.

    This honors security.scan_untracked=false. A filesystem-wide fallback is used
    only when Git is unavailable or the target is not a Git checkout.
    """
    if not which("git") or not (target / ".git").exists():
        yield from iter_files(target, cfg, max_files=max_files, extra_globs=extra_globs)
        return

    result = run_command(
        ["git", "ls-files"],
        cwd=target,
        timeout_seconds=30,
        capture_limit_kb=2048,
        redact_output=False,
    )
    if result.get("exit_code") != 0:
        yield from iter_files(target, cfg, max_files=max_files, extra_globs=extra_globs)
        return

    scan = cfg.get("scan", {})
    excluded = set(scan.get("exclude_dirs", []))
    count = 0
    for raw in (result.get("stdout_tail") or "").splitlines():
        rel = raw.strip().replace("\\", "/")
        if not rel:
            continue
        p = target / rel
        if not p.is_file():
            continue
        if is_excluded(rel, p.relative_to(target).parts[:-1], excluded, extra_globs):
            continue
        yield p, rel
        count += 1
        if count >= max_files:
            return


def run(cfg, report):
    if not cfg.get("security", {}).get("enabled", True):
        report.add(
            "security.hygiene.enabled",
            "SKIP",
            "security_hygiene",
            "Security hygiene scan is disabled by configuration.",
        )
        return

    target = Path(cfg["_target_root"])
    scan = cfg.get("scan", {})
    security = cfg.get("security", {})
    max_files = int(scan.get("max_security_files", 4000))
    max_bytes = min(int(scan.get("max_file_bytes", 1048576)), 1048576)
    extra = security.get("additional_excluded_globs", [])
    scan_untracked = bool(security.get("scan_untracked", False))
    hits = []
    names = []
    scanned = 0
    custom = []

    for i, pat in enumerate(security.get("additional_patterns", [])):
        try:
            custom.append((f"custom-{i+1}", re.compile(pat)))
        except re.error as exc:
            report.add(
                f"security.pattern.custom_{i+1}",
                "CONFIG_ERROR",
                "security_hygiene",
                "Invalid configured security regex.",
                evidence=str(exc),
            )
            return

    patterns = PATTERNS + custom
    iterator = (
        iter_files(target, cfg, max_files=max_files, extra_globs=extra)
        if scan_untracked
        else _tracked_files(target, cfg, max_files=max_files, extra_globs=extra)
    )

    report.add(
        "security.scan.scope",
        "PASS",
        "security_hygiene",
        "Security scan includes untracked files."
        if scan_untracked
        else "Security scan is restricted to tracked files when Git metadata is available.",
        evidence={"scan_untracked": scan_untracked},
    )

    for p, rel in iterator:
        if p.is_symlink():
            continue
        scanned += 1
        if p.name in SENSITIVE_NAMES:
            names.append(rel)
        text = bounded_text(p, max_bytes)
        if text is None:
            continue
        for pid, rx in patterns:
            m = rx.search(text)
            if m:
                line = text.count("\n", 0, m.start()) + 1
                hits.append({"pattern": pid, "path": rel, "line": line})
                break

    report.add(
        "security.sensitive_filenames.review",
        "WARN" if names else "PASS",
        "security_hygiene",
        "Potentially sensitive filenames were found and should be reviewed."
        if names
        else "No high-risk sensitive filenames were found in the configured scan scope.",
        evidence=names[:100] if names else None,
    )
    report.add(
        "security.secret_patterns.review",
        "WARN" if hits else "PASS",
        "security_hygiene",
        "Potential secret material matched conservative patterns; values are intentionally not copied into evidence."
        if hits
        else "No configured secret pattern matched in the configured scan scope.",
        evidence=hits[:100] if hits else None,
        recommendation="Rotate exposed credentials and remove them from history if any match is genuine."
        if hits
        else None,
    )
    if scanned >= max_files:
        report.add(
            "security.scan.truncated",
            "WARN",
            "security_hygiene",
            "Security hygiene scan reached its file limit.",
            recommendation="Raise scan.max_security_files if broader evidence is required.",
        )
    report.metrics.update(
        {
            "files_scanned": scanned,
            "potential_secret_hits": len(hits),
            "sensitive_filenames": len(names),
            "scan_untracked": scan_untracked,
        }
    )
