#!/usr/bin/env python3
"""Build api/modules.json and api/courses.json from the manifests and course.json files.

This is the code the `Build Modules API` workflow runs, so the committed API is whatever a local run
produces. Nothing here uses today's date:

  * updatedAt  = author date of the last git commit that touched modules/<id>/ (courses/<dir>/ for a
                 course). Without git history (a shallow clone) it falls back to the committed value.
  * createdAt  = the manifest's createdAt, else the date of the first commit touching the module.
  * certification  has two independent fields:
        metadata_complete   True when the manifest carries a citation, description, tags and a
                            positive estimatedMinutes (checks_passed / checks_failed list them). It
                            says NOTHING about whether the hydrology is right.
        scientific_review   null until a human reviewer records one. Never set by this script.

api/courses.json is generated from courses/<dir>/course.json (and the module manifests for level);
it is never edited by hand.

Usage:  python scripts/build_api.py           write api/modules.json and api/courses.json
        python scripts/build_api.py --check   exit 1 if the committed files differ (updatedAt ignored)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from repo_lib import RAW, ROOT, TREE, courses, git_date, manifests, read_json  # noqa: E402

API = ROOT / "api"


def certify(module: dict) -> dict:
    """What the checker looks at is exactly what is listed: metadata, not science."""
    passed, failed = [], []
    citation = module.get("citation") or {}
    text = citation.get("text", "").strip() if isinstance(citation, dict) else str(citation).strip()
    (passed if text else failed).append("citation" if text else "citation: missing or has no text")
    desc = module.get("description") or ""
    ok = isinstance(desc, str) and bool(desc.strip())
    (passed if ok else failed).append("description" if ok else "description: missing or empty")
    tags = module.get("tags") or []
    ok = isinstance(tags, list) and len(tags) > 0
    (passed if ok else failed).append("tags" if ok else "tags: missing or empty list")
    mins = module.get("estimatedMinutes") or 0
    ok = isinstance(mins, int) and mins > 0
    (passed if ok else failed).append("estimatedMinutes" if ok else "estimatedMinutes: missing or not a positive integer")
    return {"metadata_complete": not failed, "checks_passed": passed, "checks_failed": failed, "scientific_review": None}


def build_modules(existing: dict[str, dict]) -> list[dict]:
    items = []
    for module_id, man in manifests().items():
        data = dict(man)
        data["moduleId"] = module_id
        data.setdefault("downloadUrl", f"{RAW}/modules/{module_id}/module.html")
        data.setdefault("githubUrl", f"{TREE}/modules/{module_id}")
        prev = existing.get(module_id, {})
        data.setdefault("createdAt", git_date(f"modules/{module_id}", first=True) or prev.get("createdAt"))
        data["updatedAt"] = git_date(f"modules/{module_id}") or prev.get("updatedAt") or data["createdAt"]
        data.setdefault("downloadCount", prev.get("downloadCount", 0))
        data.setdefault("githubReactions", prev.get("githubReactions", 0))
        data.setdefault("discussionUrl", prev.get("discussionUrl", ""))
        data.setdefault("isFeatured", False)
        data["certification"] = certify(data)
        items.append(data)
    return items


def build_courses(existing: dict[str, dict]) -> list[dict]:
    mans = manifests()
    out = []
    for path, c in courses():
        rel = path.parent.relative_to(ROOT).as_posix()
        authors = c.get("authors") or []
        first = authors[0] if authors else {}
        levels = sorted({mans[m["id"]]["level"] for m in c["modules"] if m["id"] in mans})
        item = {
            "courseId": c["courseId"],
            "title": c["title"],
            "abstract": c["abstract"],
            "version": c["version"],
            "author": ", ".join(x for x in (first.get("name"), first.get("affiliation")) if x),
            "authorAffiliation": first.get("affiliation", ""),
            "authorUrl": c.get("authorUrl", ""),
            "trustLevel": c.get("trustLevel", "community"),
            "contributors": [{k: v for k, v in a.items() if k != "profileUrl"} for a in authors],
            "citation": c.get("citation", ""),
            "citationUrl": c.get("citationUrl", ""),
            "license": c["license"],
            "estimatedHours": c["estimatedHours"],
            "level": levels[0] if len(levels) == 1 else "mixed",
            "topic": c.get("topic", ""),
            "tags": c.get("tags", []),
            "modules": [
                {"moduleId": m["id"], "title": m["title"], "estimatedMinutes": m["estimatedMinutes"],
                 **({"prerequisites": m["prerequisites"]} if m.get("prerequisites") else {})}
                for m in c["modules"]
            ],
            "isFeatured": bool(c.get("isFeatured", False)),
            "manifestUrl": f"{RAW}/{rel}/course.json",
            "githubUrl": f"{TREE}/{rel}",
        }
        prev = existing.get(c["courseId"], {})
        item["updatedAt"] = git_date(rel) or prev.get("updatedAt", "")
        out.append(item)
    return out


def dump(obj) -> str:
    return json.dumps(obj, indent=2) + "\n"


def strip_dates(items: list[dict]) -> list[dict]:
    return [{k: v for k, v in it.items() if k != "updatedAt"} for it in items]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    api_m, api_c = API / "modules.json", API / "courses.json"
    old_m = read_json(api_m) if api_m.exists() else []
    old_c = read_json(api_c) if api_c.exists() else []
    new_m = build_modules({e["moduleId"]: e for e in old_m})
    new_c = build_courses({e["courseId"]: e for e in old_c})
    if a.check:
        bad = []
        if strip_dates(new_m) != strip_dates(old_m):
            bad.append("api/modules.json")
        if strip_dates(new_c) != strip_dates(old_c):
            bad.append("api/courses.json")
        for b in bad:
            print(f"stale: {b} (run python scripts/build_api.py)")
        if not bad:
            print("api up to date")
        return 1 if bad else 0
    API.mkdir(exist_ok=True)
    api_m.write_text(dump(new_m), encoding="utf-8")
    api_c.write_text(dump(new_c), encoding="utf-8")
    print(f"Built api/modules.json with {len(new_m)} module(s):")
    for it in new_m:
        c = it["certification"]
        print(f"  - {it['moduleId']}: {it['title']}  [metadata_complete={c['metadata_complete']}, scientific_review={c['scientific_review']}]")
    print(f"Built api/courses.json with {len(new_c)} course(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
