#!/usr/bin/env python3
"""Run `prisma generate` with Scripts dir on PATH (Windows Store Python fix)."""

from __future__ import annotations

import os
import subprocess
import sys
import sysconfig
from pathlib import Path


def _scripts_dirs() -> list[Path]:
    dirs: list[Path] = []
    seen: set[str] = set()

    def add(path: Path) -> None:
        key = str(path).lower()
        if path.is_dir() and key not in seen:
            seen.add(key)
            dirs.append(path)

    try:
        import site

        add(Path(site.getusersitepackages()).parent / "Scripts")
    except Exception:
        pass

    try:
        add(Path(sysconfig.get_path("scripts")))
    except Exception:
        pass

    # Microsoft Store Python shim
    add(Path(sys.executable).resolve().parent / "Scripts")
    return dirs


def ensure_prisma_path() -> None:
    path = os.environ.get("PATH", "")
    additions = []
    for scripts in _scripts_dirs():
        scripts_str = str(scripts)
        if scripts_str.lower() not in path.lower():
            additions.append(scripts_str)
    if additions:
        os.environ["PATH"] = os.pathsep.join(additions) + os.pathsep + path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    ensure_prisma_path()
    result = subprocess.run(
        [sys.executable, "-m", "prisma", "generate"],
        env=os.environ.copy(),
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
