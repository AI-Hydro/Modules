#!/usr/bin/env python3
"""Validate every module manifest and course.json.

Checks (exit 1 on any failure):
  * modules/<id>/ has module.html, manifest.json and README.md;
  * manifest.json has the required fields with valid values (see CONTRIBUTING.md), moduleId equals the
    directory name, version is semver, level is intro/intermediate/advanced, tags are a non-empty list;
  * the manifest embedded in module.html equals the one generated from manifest.json
    (scripts/build_modules.py embedded_manifest), so the two never disagree;
  * the module footer shows the manifest version;
  * each course.json lists only modules that exist, its prerequisite graph is acyclic and refers to
    modules of the course, and each module's courseId / courseOrder match the course.

Usage:  python scripts/validate_manifests.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_modules import embedded_manifest  # noqa: E402
from repo_lib import ROOT, courses, read_json  # noqa: E402

REQUIRED = ["moduleId", "title", "description", "version", "license", "author", "topic", "level", "estimatedMinutes", "tags", "requires"]
LEVELS = {"intro", "intermediate", "advanced"}
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
EMBEDDED = re.compile(r'<script type="application/vnd\.aihydro\.module\+json">\s*(.*?)\s*</script>', re.S)


def check_module(d: Path) -> list[str]:
    errs: list[str] = []
    for f in ("module.html", "manifest.json", "README.md"):
        if not (d / f).exists():
            errs.append(f"{d.name}: missing {f}")
    if errs:
        return errs
    try:
        m = read_json(d / "manifest.json")
    except json.JSONDecodeError as e:
        return [f"{d.name}: manifest.json is not valid JSON ({e})"]
    for k in REQUIRED:
        if k not in m or m[k] in ("", None, []):
            errs.append(f"{d.name}: manifest.json missing or empty {k!r}")
    if errs:
        return errs
    if m["moduleId"] != d.name:
        errs.append(f"{d.name}: moduleId {m['moduleId']!r} must equal the directory name")
    if not SEMVER.match(m["version"]):
        errs.append(f"{d.name}: version {m['version']!r} is not major.minor.patch")
    if m["level"] not in LEVELS:
        errs.append(f"{d.name}: level {m['level']!r} not in {sorted(LEVELS)}")
    if not isinstance(m["estimatedMinutes"], int) or m["estimatedMinutes"] <= 0:
        errs.append(f"{d.name}: estimatedMinutes must be a positive integer")
    if not (isinstance(m["tags"], list) and all(isinstance(t, str) and t for t in m["tags"])):
        errs.append(f"{d.name}: tags must be a non-empty list of strings")
    if "citation" in m and not (isinstance(m["citation"], dict) and str(m["citation"].get("text", "")).strip()):
        errs.append(f"{d.name}: citation must be an object with text")
    html = (d / "module.html").read_text(encoding="utf-8")
    emb = EMBEDDED.search(html)
    if not emb:
        errs.append(f"{d.name}: module.html has no embedded manifest block")
    else:
        try:
            if json.loads(emb[1]) != embedded_manifest(m):
                errs.append(f"{d.name}: embedded manifest differs from manifest.json (run python scripts/build_modules.py)")
        except json.JSONDecodeError:
            errs.append(f"{d.name}: embedded manifest is not valid JSON")
    if f"v{m['version']}" not in html:
        errs.append(f"{d.name}: module footer does not show v{m['version']}")
    return errs


def check_course(path: Path, c: dict, ids: set[str]) -> list[str]:
    errs: list[str] = []
    name = path.parent.name
    mods = c.get("modules", [])
    order = {m["id"]: i + 1 for i, m in enumerate(mods)}
    for m in mods:
        if m["id"] not in ids:
            errs.append(f"{name}: module {m['id']!r} has no modules/{m['id']}/")
        for p in m.get("prerequisites", []):
            if p not in order:
                errs.append(f"{name}: {m['id']} requires {p!r}, which is not in the course")
    # cycle check (Kahn)
    deps = {m["id"]: set(m.get("prerequisites", [])) & set(order) for m in mods}
    ready = [k for k, v in deps.items() if not v]
    seen = 0
    while ready:
        k = ready.pop()
        seen += 1
        for j, v in deps.items():
            if k in v:
                v.discard(k)
                if not v:
                    ready.append(j)
    if seen != len(mods):
        errs.append(f"{name}: prerequisite graph has a cycle")
    for mid, idx in order.items():
        mp = ROOT / "modules" / mid / "manifest.json"
        if mp.exists():
            man = read_json(mp)
            if man.get("courseId") != c["courseId"]:
                errs.append(f"{mid}: manifest courseId {man.get('courseId')!r} != {c['courseId']!r}")
            if man.get("courseOrder") != idx:
                errs.append(f"{mid}: manifest courseOrder {man.get('courseOrder')} != position {idx} in {name}/course.json")
    return errs


def main() -> int:
    dirs = sorted(p for p in (ROOT / "modules").iterdir() if p.is_dir())
    errs: list[str] = []
    for d in dirs:
        errs += check_module(d)
    ids = {d.name for d in dirs}
    for path, c in courses():
        errs += check_course(path, c, ids)
    for e in errs:
        print("FAIL " + e)
    if not errs:
        print(f"manifests valid: {len(dirs)} modules, {len(courses())} course(s)")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
