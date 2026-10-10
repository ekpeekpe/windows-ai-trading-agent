"""Discover already-installed terminal executables. Never launches MT5."""
from __future__ import annotations
import os
from pathlib import Path

def discover_terminals(appdata: Path | None = None, extra_dirs: list[Path] | None = None) -> list[str]:
    candidates: set[Path] = set()
    root = appdata if appdata is not None else Path(os.getenv("APPDATA", "")) / "MetaQuotes" / "Terminal"
    if root.is_dir():
        for origin in root.glob("*/origin.txt"):
            try:
                install_dir = Path(origin.read_text(encoding="utf-16").strip("\ufeff\r\n\0 "))
            except (UnicodeError, OSError):
                try:
                    install_dir = Path(origin.read_text(encoding="utf-8-sig").strip("\r\n\0 "))
                except (UnicodeError, OSError):
                    continue
            candidates.add(install_dir / "terminal64.exe")
    for folder in (extra_dirs or []):
        candidates.add(folder / "terminal64.exe")
    program_files = os.environ.get("PROGRAMFILES")
    if appdata is None and program_files:
        candidates.add(Path(program_files) / "MetaTrader 5" / "terminal64.exe")
    return sorted({str(p.resolve()) for p in candidates if p.is_file() and p.name.lower() == "terminal64.exe"})
