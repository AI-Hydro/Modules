#!/usr/bin/env python3
"""Generate the module table in README.md and courses/<dir>/README.md from the manifests.

The README tables and the course page (module table plus prerequisite DAG) are derived from
modules/*/manifest.json and courses/*/course.json, so they cannot drift from what the API and the
extension read.

  README.md                           only the block between the markers
                                      <!-- BEGIN modules-table --> and <!-- END modules-table -->
  courses/<dir>/README.md             the whole file

Usage:  python scripts/gen_docs.py           rewrite the generated parts
        python scripts/gen_docs.py --check   exit 1 if any generated part is out of date
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from repo_lib import ROOT, courses, manifests  # noqa: E402

BEGIN, END = "<!-- BEGIN modules-table -->", "<!-- END modules-table -->"
LEVELS = {"intro": "Intro", "intermediate": "Intermediate", "advanced": "Advanced"}


def topic_label(topic: str) -> str:
    return topic.replace("-", " ").capitalize()


def modules_table(mans: dict[str, dict]) -> str:
    rows = ["| Module | Topic | Level | Time | Version |", "|---|---|---|---|---|"]
    for mid, m in mans.items():
        rows.append(f"| [{m['title']}](modules/{mid}/) | {topic_label(m['topic'])} | {LEVELS.get(m['level'], m['level'])} | {m['estimatedMinutes']} min | {m['version']} |")
    return "\n".join(rows)


def course_page(c: dict, mans: dict[str, dict]) -> str:
    mods = c["modules"]
    minutes = sum(m["estimatedMinutes"] for m in mods)
    level = sorted({mans[m["id"]]["level"] for m in mods if m["id"] in mans})
    author = c["authors"][0]
    index = {m["id"]: i + 1 for i, m in enumerate(mods)}
    L = [f"# {c['title']}", "",
         f"**{len(mods)} modules · ~{c['estimatedHours']} hours ({minutes} min of lessons) · {', '.join(LEVELS.get(x, x) for x in level)} level · {c['license']}**  ",
         f"**Author:** {author['name']}, {author.get('affiliation', '')}", "",
         c["abstract"], "",
         "## Module sequence", "",
         "| # | Module | Time | Prerequisites |", "|---|--------|------|---------------|"]
    for m in mods:
        pre = ", ".join(f"M{index[p]}" for p in m.get("prerequisites", [])) or "none"
        L.append(f"| {index[m['id']]} | [{m['title']}](../../modules/{m['id']}/) | {m['estimatedMinutes']} min | {pre} |")
    L += ["", "## Prerequisite graph", "",
          "Generated from the `prerequisites` of each module in `course.json`; an arrow means \"comes before\".", "",
          "```mermaid", "flowchart TD"]
    for m in mods:
        label = m["title"].replace('"', "'")
        L.append(f'    M{index[m["id"]]}["M{index[m["id"]]} · {label}"]')
    for m in mods:
        for p in m.get("prerequisites", []):
            L.append(f"    M{index[p]} --> M{index[m['id']]}")
    L += ["```", "",
          "## Loading the course in AI-Hydro", "",
          "Open the HTML Preview panel → Courses → paste the `course.json` URL:", "", "```",
          f"https://raw.githubusercontent.com/AI-Hydro/Modules/main/courses/{c['dir']}/course.json", "```", "",
          "## License", "", f"[{c['license']}](https://creativecommons.org/licenses/by/4.0/)", ""]
    return "\n".join(L)


def targets() -> dict[Path, str]:
    mans = manifests()
    out: dict[Path, str] = {}
    readme = ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")
    if BEGIN not in text or END not in text:
        raise SystemExit(f"README.md needs the markers {BEGIN} / {END}")
    new = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END), lambda _m: f"{BEGIN}\n{modules_table(mans)}\n{END}", text, flags=re.S)
    out[readme] = new
    for path, c in courses():
        c = dict(c, dir=path.parent.name)
        out[path.parent / "README.md"] = course_page(c, mans)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    stale = []
    for path, new in targets().items():
        old = path.read_text(encoding="utf-8") if path.exists() else None
        if old != new:
            stale.append(path)
            if not a.check:
                path.write_text(new, encoding="utf-8")
    for p in stale:
        print(("stale: " if a.check else "rewrote: ") + str(p.relative_to(ROOT)))
    if not stale:
        print("generated docs up to date")
    return 1 if (stale and a.check) else 0


if __name__ == "__main__":
    sys.exit(main())
