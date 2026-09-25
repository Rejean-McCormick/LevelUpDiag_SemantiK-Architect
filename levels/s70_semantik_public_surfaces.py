from __future__ import annotations

from pathlib import Path

from levelupdiag_core.semantik import json_from_stdout, run_target_python


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
        ["-m", "semantik_architect.adapters.inbound.cli.main", "--help"],
        timeout=45,
    )
    help_text = (cli.get("stdout_tail") or "") + "\n" + (cli.get("stderr_tail") or "")
    missing_commands = [name for name in p.get("cli_commands", []) if name not in help_text]
    report.add(
        "semantik.public.cli_contract",
        "FAIL" if cli.get("exit_code") != 0 or missing_commands else "PASS",
        "public_surface",
        "The CLI exposes the complete v1 command surface."
        if cli.get("exit_code") == 0 and not missing_commands
        else "The CLI help surface is incomplete or failed to execute.",
        evidence={"missing_commands": missing_commands, "process": cli},
    )

    root = Path(cfg["_target_root"])
    http_source = root / "src/semantik_architect/adapters/inbound/http/server.py"
    text = http_source.read_text(encoding="utf-8", errors="replace") if http_source.is_file() else ""
    missing_paths = [path for path in p.get("http_paths", []) if repr(path) not in text and f'"{path}"' not in text and f"'{path}'" not in text]
    report.add(
        "semantik.public.http_contract",
        "FAIL" if missing_paths else "PASS",
        "public_surface",
        "The minimal HTTP adapter declares the expected health, readiness and v1 communication endpoints."
        if not missing_paths
        else "The HTTP adapter is missing expected v1 routes.",
        evidence=missing_paths or p.get("http_paths", []),
    )
