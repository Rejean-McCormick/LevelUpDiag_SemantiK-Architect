from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

TOOL_ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = TOOL_ROOT / "levelupdiag_manifest.json"
CONFIG_PATH = TOOL_ROOT / "levelupdiag.config.json"
UI_STATE_PATH = TOOL_ROOT / ".levelupdiag_ui.json"


VERDICT_ORDER = [
    "PASS", "WARN", "FAIL", "BLOCKED", "PARTIAL", "SKIP",
    "INFRA_ERROR", "ERROR", "CONFIG_ERROR",
]


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def console_python() -> str:
    """Prefer python.exe when the UI itself is running under pythonw.exe."""
    current = Path(sys.executable)
    if os.name == "nt" and current.name.lower() == "pythonw.exe":
        candidate = current.with_name("python.exe")
        if candidate.exists():
            return str(candidate)
    return str(current)


def windows_no_window_flags(*, new_process_group: bool = False) -> int:
    """Return Windows creation flags that suppress console windows completely."""
    if os.name != "nt":
        return 0
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    if new_process_group:
        flags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    return flags


def open_path(path: Path) -> None:
    path = path.resolve(strict=False)
    if not path.exists():
        raise FileNotFoundError(path)
    if os.name == "nt":
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


class LevelUpDiagUI(tk.Tk):
    POLL_MS = 100

    def __init__(self):
        super().__init__()
        self.title("LevelUpDiag · SemantiK Architect")
        self.geometry("1180x780")
        self.minsize(940, 650)

        self.manifest = read_json(MANIFEST_PATH, {}) or {}
        self.config = read_json(CONFIG_PATH, {}) or {}
        self.state_data = read_json(UI_STATE_PATH, {}) or {}
        self.campaigns = self.manifest.get("campaigns", {})

        self.proc: subprocess.Popen[str] | None = None
        self.proc_lock = threading.Lock()
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.last_summary_path: Path | None = None
        self.last_target: Path | None = None

        self.target_var = tk.StringVar(value=self.state_data.get("target") or self.config.get("target_repo_root", ""))
        default_campaign = self.state_data.get("campaign", "standard")
        if default_campaign not in self.campaigns and self.campaigns:
            default_campaign = next(iter(self.campaigns))
        self.campaign_var = tk.StringVar(value=default_campaign)
        self.jobs_var = tk.IntVar(value=int(self.state_data.get("jobs", self.config.get("execution", {}).get("max_parallel", 4))))
        self.fail_fast_var = tk.BooleanVar(value=bool(self.state_data.get("fail_fast", False)))
        self.status_var = tk.StringVar(value="Ready")
        self.summary_var = tk.StringVar(value="No run loaded")
        self.python_var = tk.StringVar(value=f"Python: {console_python()}")

        self._build_style()
        self._build_ui()
        self._campaign_changed()
        self.after(self.POLL_MS, self._drain_events)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_style(self) -> None:
        style = ttk.Style(self)
        try:
            if "vista" in style.theme_names():
                style.theme_use("vista")
        except tk.TclError:
            pass
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("Sub.TLabel", font=("Segoe UI", 9))
        style.configure("Run.TButton", font=("Segoe UI", 10, "bold"), padding=(16, 8))
        style.configure("Treeview", rowheight=25)
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=12)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x")
        ttk.Label(header, text="LevelUpDiag", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="SemantiK Architect diagnostic profile", style="Sub.TLabel").pack(side="left", padx=(12, 0), pady=(7, 0))
        ttk.Label(header, textvariable=self.status_var).pack(side="right")

        target_box = ttk.LabelFrame(outer, text="Target", padding=10)
        target_box.pack(fill="x", pady=(10, 8))
        target_box.columnconfigure(1, weight=1)
        ttk.Label(target_box, text="Repository").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(target_box, textvariable=self.target_var).grid(row=0, column=1, sticky="ew")
        ttk.Button(target_box, text="Browse…", command=self._browse_target).grid(row=0, column=2, padx=(8, 0))
        ttk.Button(target_box, text="Open", command=self._open_target).grid(row=0, column=3, padx=(6, 0))
        ttk.Label(target_box, textvariable=self.python_var, style="Sub.TLabel").grid(row=1, column=1, sticky="w", pady=(6, 0))

        controls = ttk.LabelFrame(outer, text="Campaign", padding=10)
        controls.pack(fill="x", pady=(0, 8))
        controls.columnconfigure(5, weight=1)

        ttk.Label(controls, text="Profile").grid(row=0, column=0, sticky="w")
        campaign_combo = ttk.Combobox(
            controls,
            textvariable=self.campaign_var,
            values=list(self.campaigns.keys()),
            state="readonly",
            width=16,
        )
        campaign_combo.grid(row=0, column=1, padx=(6, 14), sticky="w")
        campaign_combo.bind("<<ComboboxSelected>>", lambda _e: self._campaign_changed())

        ttk.Label(controls, text="Jobs").grid(row=0, column=2, sticky="w")
        ttk.Spinbox(controls, from_=1, to=16, textvariable=self.jobs_var, width=5).grid(row=0, column=3, padx=(6, 14))
        ttk.Checkbutton(controls, text="Fail fast", variable=self.fail_fast_var).grid(row=0, column=4, sticky="w")

        self.campaign_desc = ttk.Label(controls, text="", wraplength=700, style="Sub.TLabel")
        self.campaign_desc.grid(row=1, column=0, columnspan=6, sticky="w", pady=(7, 0))

        button_row = ttk.Frame(outer)
        button_row.pack(fill="x", pady=(0, 8))
        self.doctor_btn = ttk.Button(button_row, text="Doctor", command=self._doctor)
        self.doctor_btn.pack(side="left")
        self.run_btn = ttk.Button(button_row, text="Run diagnostics", style="Run.TButton", command=self._run)
        self.run_btn.pack(side="left", padx=(8, 0))
        self.stop_btn = ttk.Button(button_row, text="Stop", command=self._stop, state="disabled")
        self.stop_btn.pack(side="left", padx=(8, 0))
        ttk.Separator(button_row, orient="vertical").pack(side="left", fill="y", padx=12)
        self.open_latest_btn = ttk.Button(button_row, text="Open latest report", command=self._open_latest_report)
        self.open_latest_btn.pack(side="left")
        ttk.Button(button_row, text="Open runs folder", command=self._open_runs).pack(side="left", padx=(8, 0))
        ttk.Button(button_row, text="Reload latest", command=self._load_latest_summary).pack(side="left", padx=(8, 0))

        self.progress = ttk.Progressbar(outer, mode="indeterminate")
        self.progress.pack(fill="x", pady=(0, 8))

        paned = ttk.Panedwindow(outer, orient="vertical")
        paned.pack(fill="both", expand=True)

        result_frame = ttk.LabelFrame(paned, text="Results", padding=8)
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(1, weight=1)
        ttk.Label(result_frame, textvariable=self.summary_var).grid(row=0, column=0, sticky="w", pady=(0, 6))

        columns = ("id", "verdict", "name")
        self.tree = ttk.Treeview(result_frame, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("id", text="Level")
        self.tree.heading("verdict", text="Verdict")
        self.tree.heading("name", text="Name")
        self.tree.column("id", width=70, anchor="center", stretch=False)
        self.tree.column("verdict", width=125, anchor="center", stretch=False)
        self.tree.column("name", width=600, anchor="w")
        self.tree.grid(row=1, column=0, sticky="nsew")
        tree_scroll = ttk.Scrollbar(result_frame, orient="vertical", command=self.tree.yview)
        tree_scroll.grid(row=1, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=tree_scroll.set)
        self.tree.bind("<<TreeviewSelect>>", self._show_selected_level)

        for verdict in VERDICT_ORDER:
            # Tk colors are deliberately modest and only used to make verdict scanning faster.
            bg = {
                "PASS": "#e8f5e9",
                "WARN": "#fff8e1",
                "FAIL": "#ffebee",
                "BLOCKED": "#fff3e0",
                "PARTIAL": "#fffde7",
                "SKIP": "#f5f5f5",
                "INFRA_ERROR": "#fce4ec",
                "ERROR": "#fce4ec",
                "CONFIG_ERROR": "#fce4ec",
            }.get(verdict, "")
            if bg:
                self.tree.tag_configure(verdict, background=bg)

        details = ttk.LabelFrame(paned, text="Level details", padding=8)
        details.columnconfigure(0, weight=1)
        details.rowconfigure(0, weight=1)
        self.details = tk.Text(details, height=10, wrap="word", font=("Consolas", 9), state="disabled")
        self.details.grid(row=0, column=0, sticky="nsew")
        details_scroll = ttk.Scrollbar(details, orient="vertical", command=self.details.yview)
        details_scroll.grid(row=0, column=1, sticky="ns")
        self.details.configure(yscrollcommand=details_scroll.set)

        log_frame = ttk.LabelFrame(paned, text="Live log", padding=8)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.log = tk.Text(log_frame, height=12, wrap="none", font=("Consolas", 9), state="disabled")
        self.log.grid(row=0, column=0, sticky="nsew")
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        log_scroll.grid(row=0, column=1, sticky="ns")
        self.log.configure(yscrollcommand=log_scroll.set)

        paned.add(result_frame, weight=3)
        paned.add(details, weight=2)
        paned.add(log_frame, weight=2)

        self._load_latest_summary(silent=True)

    def _campaign_changed(self) -> None:
        data = self.campaigns.get(self.campaign_var.get(), {})
        desc = data.get("description", "")
        levels = data.get("levels", [])
        suffix = f"  Levels: {', '.join(levels)}" if levels else ""
        self.campaign_desc.configure(text=f"{desc}{suffix}")

    def _browse_target(self) -> None:
        initial = self.target_var.get().strip() or str(TOOL_ROOT.parent)
        chosen = filedialog.askdirectory(title="Select SemantiK Architect repository", initialdir=initial)
        if chosen:
            self.target_var.set(chosen)
            self._load_latest_summary(silent=True)

    def _target_path(self) -> Path:
        raw = self.target_var.get().strip()
        if not raw:
            raise ValueError("Choose a target repository first.")
        target = Path(raw).expanduser().resolve(strict=False)
        if not target.exists() or not target.is_dir():
            raise ValueError(f"Target repository does not exist:\n{target}")
        return target

    def _open_target(self) -> None:
        try:
            open_path(self._target_path())
        except Exception as exc:
            messagebox.showerror("Open target", str(exc), parent=self)

    def _control_root(self, target: Path) -> Path:
        control = self.config.get("control_dir", ".levelupdiag")
        return target / control

    def _latest_summary(self, target: Path) -> Path:
        return self._control_root(target) / "latest" / "summary.json"

    def _open_latest_report(self) -> None:
        try:
            target = self._target_path()
            summary = self._latest_summary(target)
            if not summary.exists():
                raise FileNotFoundError("No latest summary exists yet. Run a campaign first.")
            run_id = (read_json(summary, {}) or {}).get("run_id")
            if run_id:
                run_dir = self._control_root(target) / "runs" / run_id
                text_report = run_dir / "summary.txt"
                open_path(text_report if text_report.exists() else summary)
            else:
                open_path(summary)
        except Exception as exc:
            messagebox.showerror("Open report", str(exc), parent=self)

    def _open_runs(self) -> None:
        try:
            target = self._target_path()
            runs = self._control_root(target) / "runs"
            runs.mkdir(parents=True, exist_ok=True)
            open_path(runs)
        except Exception as exc:
            messagebox.showerror("Open runs", str(exc), parent=self)

    def _clear_log(self) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def _append_log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _set_details(self, text: str) -> None:
        self.details.configure(state="normal")
        self.details.delete("1.0", "end")
        self.details.insert("1.0", text)
        self.details.configure(state="disabled")

    def _set_running(self, running: bool, label: str = "") -> None:
        self.run_btn.configure(state="disabled" if running else "normal")
        self.doctor_btn.configure(state="disabled" if running else "normal")
        self.stop_btn.configure(state="normal" if running else "disabled")
        if running:
            self.progress.start(10)
            self.status_var.set(label or "Running…")
        else:
            self.progress.stop()
            self.status_var.set(label or "Ready")

    def _doctor(self) -> None:
        try:
            target = self._target_path()
        except Exception as exc:
            messagebox.showerror("Doctor", str(exc), parent=self)
            return
        self._clear_log()
        self._start_process(["--target", str(target), "doctor"], "Doctor")

    def _run(self) -> None:
        try:
            target = self._target_path()
            jobs = max(1, min(int(self.jobs_var.get()), 16))
        except Exception as exc:
            messagebox.showerror("Run diagnostics", str(exc), parent=self)
            return
        campaign = self.campaign_var.get().strip() or "standard"
        args = ["--target", str(target), "run", campaign, "--jobs", str(jobs)]
        if self.fail_fast_var.get():
            args.append("--fail-fast")
        self._clear_log()
        self._clear_results()
        self._start_process(args, f"Running {campaign}")

    def _start_process(self, cli_args: list[str], label: str) -> None:
        with self.proc_lock:
            if self.proc is not None and self.proc.poll() is None:
                messagebox.showwarning("LevelUpDiag", "A diagnostic process is already running.", parent=self)
                return

        self._set_running(True, label)
        target = None
        try:
            target = self._target_path()
        except Exception:
            pass
        self.last_target = target

        def worker() -> None:
            cmd = [console_python(), str(TOOL_ROOT / "levelupdiag.py"), *cli_args]
            creationflags = windows_no_window_flags(new_process_group=True)
            try:
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(target or TOOL_ROOT),
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    shell=False,
                    creationflags=creationflags,
                )
                with self.proc_lock:
                    self.proc = proc
                assert proc.stdout is not None
                for line in proc.stdout:
                    self.events.put(("log", line))
                code = proc.wait()
                self.events.put(("done", code))
            except Exception as exc:
                self.events.put(("error", exc))
            finally:
                with self.proc_lock:
                    self.proc = None

        threading.Thread(target=worker, daemon=True).start()

    def _stop(self) -> None:
        with self.proc_lock:
            proc = self.proc
        if proc is None or proc.poll() is not None:
            return
        if not messagebox.askyesno("Stop diagnostics", "Stop the running LevelUpDiag process?", parent=self):
            return
        try:
            if os.name == "nt" and shutil.which("taskkill"):
                subprocess.run(
                    ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                    creationflags=windows_no_window_flags(),
                )
            else:
                proc.terminate()
            self.status_var.set("Stopping…")
        except Exception as exc:
            messagebox.showerror("Stop diagnostics", str(exc), parent=self)

    def _drain_events(self) -> None:
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "log":
                    self._append_log(str(payload))
                elif kind == "done":
                    code = int(payload)
                    self._load_latest_summary(silent=True)
                    label = "Finished" if code == 0 else f"Finished · exit {code}"
                    self._set_running(False, label)
                elif kind == "error":
                    self._set_running(False, "Error")
                    messagebox.showerror("LevelUpDiag", str(payload), parent=self)
        except queue.Empty:
            pass
        finally:
            self.after(self.POLL_MS, self._drain_events)

    def _clear_results(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.summary_var.set("Running…")
        self._set_details("")

    def _load_latest_summary(self, silent: bool = False) -> None:
        try:
            target = self._target_path()
            path = self._latest_summary(target)
            if not path.exists():
                if not silent:
                    messagebox.showinfo("Latest report", "No LevelUpDiag run exists for this target yet.", parent=self)
                return
            data = read_json(path)
            if not isinstance(data, dict):
                raise ValueError(f"Could not read {path}")
            self.last_summary_path = path
            self.last_target = target
            self._populate_summary(data)
        except Exception as exc:
            if not silent:
                messagebox.showerror("Load latest", str(exc), parent=self)

    def _populate_summary(self, summary: dict) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        verdict = summary.get("verdict", "?")
        selection = summary.get("selection", "?")
        run_id = summary.get("run_id", "?")
        counts = summary.get("counts", {}) or {}
        count_text = "  ".join(f"{k}:{counts.get(k, 0)}" for k in VERDICT_ORDER if counts.get(k, 0))
        self.summary_var.set(f"{selection} · {verdict} · {run_id}" + (f"    {count_text}" if count_text else ""))
        for row in summary.get("levels", []):
            lid = str(row.get("id", ""))
            v = str(row.get("verdict", ""))
            name = str(row.get("name", ""))
            self.tree.insert("", "end", iid=lid or None, values=(lid, v, name), tags=(v,))
        if self.tree.get_children():
            first = self.tree.get_children()[0]
            self.tree.selection_set(first)
            self.tree.focus(first)
            self._show_selected_level()

    def _level_result_path(self, level_id: str) -> Path | None:
        if not self.last_summary_path or not self.last_target:
            return None
        summary = read_json(self.last_summary_path, {}) or {}
        run_id = summary.get("run_id")
        if not run_id:
            return None
        return self._control_root(self.last_target) / "runs" / str(run_id) / "levels" / level_id / "result.json"

    def _show_selected_level(self, _event=None) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        item_id = selected[0]
        values = self.tree.item(item_id, "values")
        level_id = str(values[0]) if values else item_id
        path = self._level_result_path(level_id)
        if path is None or not path.exists():
            self._set_details(f"No detailed result available for {level_id}.")
            return
        data = read_json(path, {}) or {}
        lines = [
            f"{data.get('level_id', level_id)}  {data.get('verdict', '?')}  {data.get('level_name', '')}",
            f"Purpose: {data.get('purpose', '')}",
            "",
        ]
        findings = data.get("findings", []) or []
        if not findings:
            lines.append("No findings.")
        for finding in findings:
            lines.append(f"[{finding.get('verdict', '?')}] {finding.get('id', '')}")
            lines.append(str(finding.get("message", "")))
            recommendation = finding.get("recommendation")
            if recommendation:
                lines.append(f"Recommendation: {recommendation}")
            evidence = finding.get("evidence")
            if evidence:
                lines.append("Evidence:")
                lines.append(json.dumps(evidence, ensure_ascii=False, indent=2, default=str))
            lines.append("")
        lines.append(f"Result file: {path}")
        self._set_details("\n".join(lines))

    def _save_state(self) -> None:
        payload = {
            "target": self.target_var.get().strip(),
            "campaign": self.campaign_var.get().strip(),
            "jobs": int(self.jobs_var.get()),
            "fail_fast": bool(self.fail_fast_var.get()),
        }
        try:
            UI_STATE_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        except Exception:
            pass

    def _on_close(self) -> None:
        with self.proc_lock:
            active = self.proc is not None and self.proc.poll() is None
        if active:
            if not messagebox.askyesno("LevelUpDiag", "Diagnostics are still running. Close the UI anyway?", parent=self):
                return
        self._save_state()
        self.destroy()


def main() -> int:
    try:
        app = LevelUpDiagUI()
        app.mainloop()
        return 0
    except tk.TclError as exc:
        # If pythonw has no visible console this message may not be seen, but it remains
        # useful when the .pyw is run with python.exe during diagnostics.
        print(f"LevelUpDiag UI error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
