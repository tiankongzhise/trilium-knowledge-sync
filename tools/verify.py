#!/usr/bin/env python3
"""Run all local verification checks for trilium-knowledge-sync.

Usage:
    python tools/verify.py                # run every check
    python tools/verify.py validate unittest   # run a subset

Checks:
    validate  - repository structure and documentation governance (tools/validate_repo.py)
    unittest  - Python unit tests (tests/)
    compile   - byte-compile the ETAPI helper
    bash      - bash syntax check of install.sh (skipped if bash is unavailable)
    ps1       - PowerShell syntax check of install.ps1 (skipped if no PowerShell is available)

All selected checks run even when earlier ones fail; the exit code is
non-zero if any check failed. Uses only the Python standard library.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
HELPER = REPO_ROOT / "skill" / "trilium-knowledge-sync" / "scripts" / "trilium_etapi.py"

ALL_CHECKS = ["validate", "unittest", "compile", "bash", "ps1"]


def run(cmd: list[str], **kwargs) -> int:
    print(f"$ {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=REPO_ROOT, **kwargs)
    return proc.returncode


def check_validate() -> int:
    return run([sys.executable, str(REPO_ROOT / "tools" / "validate_repo.py")])


def check_unittest() -> int:
    return run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])


def check_compile() -> int:
    return run([sys.executable, "-m", "py_compile", str(HELPER)])


def check_bash() -> int:
    bash = shutil.which("bash")
    if bash is None:
        print("SKIP: bash not found on PATH; install.sh syntax not checked")
        return 0
    return run([bash, "-n", "install.sh"])


def check_ps1() -> int:
    shell = shutil.which("pwsh") or shutil.which("powershell")
    if shell is None:
        print("SKIP: no PowerShell on PATH; install.ps1 syntax not checked")
        return 0
    script = (
        "$path = '{path}'\n"
        "$source = [System.IO.File]::ReadAllText($path, [System.Text.Encoding]::UTF8)\n"
        "$errors = $null\n"
        "[void][System.Management.Automation.PSParser]::Tokenize($source, [ref]$errors)\n"
        "if ($errors.Count) {{ $errors; exit 1 }}"
    ).format(path=str(REPO_ROOT / "install.ps1").replace("'", "''"))
    return run([shell, "-NoProfile", "-Command", script])


CHECKS = {
    "validate": check_validate,
    "unittest": check_unittest,
    "compile": check_compile,
    "bash": check_bash,
    "ps1": check_ps1,
}


def main(argv: list[str]) -> int:
    selected = argv or list(ALL_CHECKS)
    unknown = [name for name in selected if name not in CHECKS]
    if unknown:
        print(f"unknown check(s): {', '.join(unknown)}", file=sys.stderr)
        print(f"available: {', '.join(ALL_CHECKS)}", file=sys.stderr)
        return 2

    failures: list[str] = []
    for name in selected:
        print(f"\n=== check: {name} ===")
        try:
            code = CHECKS[name]()
        except Exception as exc:  # noqa: BLE001 - report and continue with remaining checks
            print(f"check {name} errored: {exc}", file=sys.stderr)
            code = 1
        if code != 0:
            failures.append(name)
            print(f"--- {name}: FAILED (exit {code}) ---")
        else:
            print(f"--- {name}: ok ---")

    print()
    if failures:
        print(f"verification FAILED: {', '.join(failures)}", file=sys.stderr)
        return 1
    print(f"verification passed ({len(selected)} check(s)).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
