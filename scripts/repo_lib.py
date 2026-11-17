"""Small helpers shared by the repository scripts (API build, docs generation, validation)."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = "https://raw.githubusercontent.com/AI-Hydro/Modules/main"
TREE = "https://github.com/AI-Hydro/Modules/tree/main"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def manifests() -> dict[str, dict]:
    """moduleId -> manifest.json content, sorted by module directory name."""
    out = {}
    for p in sorted((ROOT / "modules").glob("*/manifest.json")):
        m = read_json(p)
        out[m.get("moduleId") or p.parent.name] = m
    return out


def courses() -> list[tuple[Path, dict]]:
    return [(p, read_json(p)) for p in sorted((ROOT / "courses").glob("*/course.json"))]


def git_date(path: str, first: bool = False) -> str | None:
    """Author date (YYYY-MM-DD) of the last (or first) commit touching `path`; None without history."""
    cmd = ["git", "-C", str(ROOT), "log", "--format=%as"]
    cmd += ["--diff-filter=A"] if first else ["-1"]
    cmd += ["--", path]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    lines = [ln for ln in r.stdout.split() if ln]
    if not lines:
        return None
    return lines[-1] if first else lines[0]
