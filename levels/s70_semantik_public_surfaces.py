from __future__ import annotations

from pathlib import Path

from levelupdiag_core.semantik import json_from_stdout, run_target_python


def _clean_stderr(value):
    return (value or "").strip()


def run(cfg, report):
    p = cfg.get("semantik", {})
    sdk_methods = list(p.get("public_sdk_methods", []))
    script = r'''
import json
import semantik_architect
from semantik_architect.adapters.inbound.python_sdk import SemantikArchitect
from semantik_architect.adapters.inbound.cli.main import main
from semantik_architect.adapters.inbound.http.server import serve
print(json.dumps({"version":semantik_architect.__version__,"sdk":{name:hasattr(SemantikArchitect,name) for name in %r},"cli_callable":callable(main),"http_callable":callable(serve)}))
''' % sdk_methods
    probe = run_target_python(cfg, ["-c", script], timeout=60)
    data = json_from_stdout(probe)
    ok = (
        probe.get("exit_code") == 0
        and isinstance(data, dict)
        and all((data.get("sdk") or {}).values())
        and data.get("cli_callable") is True
        and data.get("http_callable") is True
    )
    report.add(
        "semantik.public.python_surface",
        "PASS" if ok else "FAIL",
        "public_surface",
        "Package, SDK, CLI and minimal HTTP adapters import through the canonical src package."
        if ok
        else "One or more public Python surfaces are missing or not importable.",
        evidence=data if isinstance(data, dict) else probe,
    )

    cli = run_target_python(
        cfg,
        [
            "-W",
            "error::RuntimeWarning",
            "-m",
            "semantik_architect.adapters.inbound.cli.main",
            "--help",
        ],
        timeout=45,
    )
    stdout = cli.get("stdout_tail") or ""
    stderr = _clean_stderr(cli.get("stderr_tail"))
    missing_commands = [name for name in p.get("cli_commands", []) if name not in stdout]
    cli_ok = cli.get("exit_code") == 0 and not missing_commands and not stderr
    report.add(
        "semantik.public.cli_contract",
        "PASS" if cli_ok else "FAIL",
        "public_surface",
        "The CLI exposes the complete v1 command surface and emits no warnings/errors on stderr."
        if cli_ok
        else "The CLI help surface failed, is incomplete, or emitted unexpected stderr output.",
        evidence={
            "missing_commands": missing_commands,
            "stderr_clean": not bool(stderr),
            "runtime_warning": "RuntimeWarning" in stderr,
            "process": cli,
        },
        recommendation=(
            "Keep package __init__ modules from eagerly importing the CLI execution module; "
            "`python -m semantik_architect.adapters.inbound.cli.main --help` must complete with empty stderr."
            if stderr
            else None
        ),
    )

    root = Path(cfg["_target_root"])
    http_source = root / "src/semantik_architect/adapters/inbound/http/server.py"
    text = http_source.read_text(encoding="utf-8", errors="replace") if http_source.is_file() else ""
    missing_paths = [
        path
        for path in p.get("http_paths", [])
        if repr(path) not in text and f'"{path}"' not in text and f"'{path}'" not in text
    ]
    report.add(
        "semantik.public.http_contract",
        "FAIL" if missing_paths else "PASS",
        "public_surface",
        "The minimal HTTP adapter declares the expected health, readiness and v1 communication endpoints."
        if not missing_paths
        else "The HTTP adapter is missing expected v1 routes.",
        evidence=missing_paths or p.get("http_paths", []),
    )
