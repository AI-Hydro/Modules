#!/usr/bin/env python3
"""Inline shared code and bundled data into the single-file modules.

Modules stay self-contained HTML files (no new script hosts, no fetches). The shared
sources live in shared/ and the data in modules/<id>/data/; this script copies them
into marked regions of module.html so there is exactly one implementation of each
algorithm in the repository.

Marker forms (inside module.html):

  /*@@BEGIN js:shared/lyne_hollick.js@@*/ ... /*@@END js:shared/lyne_hollick.js@@*/
      raw copy of a shared JavaScript file
  <!--@@BEGIN pypre:shared/lyne_hollick.py@@--> ... <!--@@END pypre:shared/lyne_hollick.py@@-->
      HTML-escaped copy of a Python file, for a <pre> code cell
  /*@@BEGIN pyjs:shared/lyne_hollick.py PY_LH@@*/ ... /*@@END pyjs:shared/lyne_hollick.py@@*/
      `var PY_LH = "<python source as a JS string>";` for cells built by JavaScript
  <!--@@BEGIN json:<blob>@@--> ... <!--@@END json:<blob>@@-->
      <script type="application/json" id="<blob>"> built from modules/<id>/data

Usage:  python scripts/build_modules.py          rewrite module.html files
        python scripts/build_modules.py --check  exit 1 if any file is out of date
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MARK = re.compile(
    r"(?P<open>(?:/\*|<!--)@@BEGIN (?P<kind>\w+):(?P<arg>[^@]*)@@(?:\*/|-->))"
    r"(?P<body>.*?)"
    r"(?P<close>(?:/\*|<!--)@@END (?P=kind):(?P<arg2>[^@]*)@@(?:\*/|-->))",
    re.S,
)


def read_series(csv_path: Path, with_precip: bool) -> dict:
    rows = list(csv.DictReader(csv_path.open()))
    q = [float(r["q_cfs"]) for r in rows]
    est = [i for i, r in enumerate(rows) if r["usgs_qc"] != "A"]
    out = {"start": rows[0]["date"], "end": rows[-1]["date"], "n": len(rows),
           "q_cfs": q, "estimated_idx": est}
    if with_precip:
        out["prcp_mm_day"] = [float(r["prcp_mm_day"]) for r in rows]
    return out


def build_blob(module_dir: Path, name: str) -> str:
    data = module_dir / "data"
    meta = json.loads((data / "camels_gauges.json").read_text())
    prov = json.loads((data / "PROVENANCE.json").read_text()).get("series", {})
    if name == "camels-meta":
        blob = {"gauges": meta}
    elif name in ("camels-5yr", "camels-wy"):
        wy = name == "camels-wy"
        series = {}
        for g in meta:
            files = sorted(data.glob(f"{g}_wy*.csv" if wy else f"{g}_q.csv"))
            p = prov[g]
            series[g] = dict(meta[g], **read_series(files[0], wy),
                             source_member=p.get("source_member") or p["flow_source_member"],
                             source_sha256=p.get("source_member_sha256") or p["flow_source_member_sha256"])
        blob = {"gauges": series, "source": "CAMELS-US v1.2 (Newman et al. 2015; Addor et al. 2017)",
                "units": {"q": "cfs (daily mean)", **({"prcp": "mm/day"} if wy else {})}}
    else:
        raise SystemExit(f"unknown blob {name}")
    # '</' must not appear inside an HTML script element
    text = json.dumps(blob, separators=(",", ":")).replace("</", "<\\/")
    return f'<script type="application/json" id="{name}">{text}</script>'


def render(kind: str, arg: str, module_dir: Path) -> str:
    toks = arg.split()
    if kind == "js":
        return "\n" + (ROOT / toks[0]).read_text().rstrip("\n") + "\n"
    if kind == "pypre":
        return html.escape((ROOT / toks[0]).read_text().rstrip("\n"), quote=False)
    if kind == "pyjs":
        src = (ROOT / toks[0]).read_text().rstrip("\n")
        return f"\n  var {toks[1]} = {json.dumps(src)};\n"
    if kind == "json":
        return build_blob(module_dir, toks[0])
    raise SystemExit(f"unknown marker kind {kind}")


def process(path: Path) -> str:
    module_dir = path.parent
    text = path.read_text(encoding="utf-8")

    def sub(m: re.Match) -> str:
        if m["arg"].split()[0] != m["arg2"].split()[0]:
            raise SystemExit(f"{path}: mismatched markers {m['arg']!r} / {m['arg2']!r}")
        return m["open"] + render(m["kind"], m["arg"], module_dir) + m["close"]

    return MARK.sub(sub, text)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    stale = []
    for path in sorted((ROOT / "modules").glob("*/module.html")):
        new = process(path)
        if new != path.read_text(encoding="utf-8"):
            stale.append(path)
            if not a.check:
                path.write_text(new, encoding="utf-8")
    if stale:
        for p in stale:
            print(("stale: " if a.check else "rebuilt: ") + str(p.relative_to(ROOT)))
        return 1 if a.check else 0
    print("all modules up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
