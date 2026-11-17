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
  /*@@BEGIN css:shared/quiz.css@@*/ ... /*@@END css:shared/quiz.css@@*/
      raw copy of a shared stylesheet (same as js, for CSS)
  <!--@@BEGIN manifest:module@@--> ... <!--@@END manifest:module@@-->
      the embedded <script type="application/vnd.aihydro.module+json"> generated from manifest.json
  <!--@@BEGIN static:<cell-id>@@--> ... <!--@@END static:<cell-id>@@-->
      the pre-rendered output of an executable cell (modules/<id>/static/<cell-id>.txt / .png,
      produced by scripts/render_static_outputs.py); shown where no kernel is attached and
      replaced by the bridge on a real run

Usage:  python scripts/build_modules.py          rewrite module.html files
        python scripts/build_modules.py --check  exit 1 if any file is out of date
"""
from __future__ import annotations

import argparse
import base64
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


def blob_script(name: str, blob) -> str:
    # '</' must not appear inside an HTML script element
    text = json.dumps(blob, separators=(",", ":")).replace("</", "<\\/")
    return f'<script type="application/json" id="{name}">{text}</script>'


def build_blob(module_dir: Path, name: str) -> str:
    data = module_dir / "data"
    # Generic rule: <!--@@BEGIN json:NAME@@--> inlines modules/<id>/data/NAME.json verbatim (minified)
    # as <script type="application/json" id="NAME">. The three CAMELS blobs below have no such file.
    generic = data / f"{name}.json"
    if generic.exists():
        return blob_script(name, json.loads(generic.read_text(encoding="utf-8")))
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
    return blob_script(name, blob)


def embedded_manifest(man: dict) -> dict:
    """The embedded block, in the field names the AI-Hydro preview reads, derived from manifest.json.

    manifest.json keeps the marketplace/API names (moduleId, estimatedMinutes, author); the preview
    reads id, estimated_minutes, authors[]. One source, one mapping, so they cannot disagree.
    """
    name, _, affiliation = man["author"].partition(",")
    author = {"name": name.strip()}
    if affiliation.strip():
        author["affiliation"] = affiliation.strip()
    emb = {
        "id": man["moduleId"],
        "title": man["title"],
        "version": man["version"],
        "authors": [author],
        "license": man["license"],
        "topic": man["topic"],
        "level": man["level"],
        "estimated_minutes": man["estimatedMinutes"],
        "requires": man["requires"],
    }
    if "citation" in man:
        emb["citation"] = man["citation"]
    emb["ai_hydro_preview_min_version"] = "0.2"
    return emb


STRICT_STATIC = True   # render_static_outputs.py turns this off to build before outputs exist


def static_block(module_dir: Path, cell: str) -> str:
    sdir = module_dir / "static"
    txt = sdir / f"{cell}.txt"
    png = sdir / f"{cell}.png"
    if not txt.exists() and not png.exists():
        if not STRICT_STATIC:
            return ""
        raise SystemExit(f"{module_dir.name}: no static output for cell {cell!r} (run scripts/render_static_outputs.py)")
    parts = ['<div class="aihydro-static" data-static-output="prerendered">',
             '<div class="aihydro-static-note">Pre-rendered output with the default settings. '
             'Run the cell in AI-Hydro to recompute it.</div>']
    if txt.exists():
        parts.append('<pre class="aihydro-stdout">' + html.escape(txt.read_text(encoding="utf-8").rstrip("\n"), quote=False) + "</pre>")
    if png.exists():
        alt_path = sdir / "alt.json"
        if not alt_path.exists() and not STRICT_STATIC:
            alt = ""
        else:
            alt = json.loads(alt_path.read_text(encoding="utf-8"))[cell]
        b64 = base64.b64encode(png.read_bytes()).decode("ascii")
        parts.append('<div class="aihydro-static-figure"><img alt="' + html.escape(alt, quote=True)
                     + '" src="data:image/png;base64,' + b64 + '"></div>')
    parts.append("</div>")
    return "".join(parts)


def render(kind: str, arg: str, module_dir: Path) -> str:
    toks = arg.split()
    if kind == "manifest":
        man = json.loads((module_dir / "manifest.json").read_text(encoding="utf-8"))
        return ('<script type="application/vnd.aihydro.module+json">\n'
                + json.dumps(embedded_manifest(man), indent=2, ensure_ascii=False) + "\n</script>")
    if kind == "static":
        return static_block(module_dir, toks[0])
    if kind in ("js", "css"):
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
