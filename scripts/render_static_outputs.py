#!/usr/bin/env python3
"""Pre-render the output of every executable cell so a module shows real results with no kernel.

For each `.aihydro-cell` the cell's source (the text the learner sees at the default settings) is
run headless with `python -s -E` (Agg backend) in a scratch directory. Its stdout becomes
modules/<id>/static/<cell>.txt and each matplotlib figure becomes <cell>.png (palette-quantised to
keep the page small). scripts/build_modules.py embeds both into the cell's `.aihydro-output`
between `static:<cell>` markers; the bridge replaces them on a real run.

static/index.json records, per cell, the sha256 of the source that produced the output plus the
interpreter and library versions. `--check` (no execution) fails if a cell's source changed
since its output was rendered, so a stale figure can never ship.

Two kinds of cell are not executed here and carry an authored text instead (said openly in the
output): one that needs the network (NWIS) and the Manim animation, for which the final frame is
rendered with Manim itself (`-s`) and the video is left to a real run.

Usage:  python scripts/render_static_outputs.py            render everything
        python scripts/render_static_outputs.py --check    exit 1 if any output is stale
        python scripts/render_static_outputs.py --only <module-id>
"""
from __future__ import annotations

import argparse
import hashlib
import html
import io
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODULES = ROOT / "modules"

# a stable matplotlib config dir so the font cache is built once, not per cell
MPLCFG = str(Path(tempfile.gettempdir()) / "aihydro-modules-mplcfg")

CELL_RE = re.compile(r'<div class="aihydro-cell"(?P<attrs>[^>]*)>(?P<body>.*?)</pre>', re.S)

# cells that are not run headless: (module, cell) -> (mode, text)
SPECIAL = {
    ("real-streamflow-data", "streamflow-nwis"): (
        "text",
        "Not pre-rendered: this cell requests USGS NWIS over the network (dataretrieval).\n"
        "When run in AI-Hydro it prints the live record, or says plainly that the request failed.\n"
        "It never substitutes synthetic discharge.",
    ),
    ("water-cycle-in-motion", "water-cycle-film"): (
        "manim",
        "Final frame of the animation, rendered with Manim (stored image).\n"
        "Run the cell in AI-Hydro to render the full ~15 s video (requires Manim in the kernel).",
    ),
}

RUNNER = r'''
import sys, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
src = open(sys.argv[1], encoding="utf-8").read()
g = {"__name__": "__main__"}
exec(compile(src, "<cell>", "exec"), g)
for i, n in enumerate(plt.get_fignums()):
    fig = plt.figure(n)
    fig.savefig(os.path.join(sys.argv[2], "fig%d.png" % i), dpi=100, facecolor=fig.get_facecolor())
'''


def cells_of(mod: str) -> list[dict]:
    # build the page (shared code and data inlined, static outputs optional) so its scripts can run
    sys.path.insert(0, str(ROOT / "scripts"))
    import build_modules
    build_modules.STRICT_STATIC = False
    text = build_modules.process(MODULES / mod / "module.html")
    with tempfile.TemporaryDirectory() as td:
        built = Path(td) / "module.html"
        built.write_text(text, encoding="utf-8")
        node = subprocess.run(["node", str(ROOT / "scripts" / "cell_sources.js"), str(built)],
                              capture_output=True, text=True, check=True)
    scripted = json.loads(node.stdout)
    out = []
    for m in CELL_RE.finditer(text):
        cid = re.search(r'data-aihydro-cell-id="([^"]+)"', m["attrs"])[1]
        pre = re.search(r'<pre class="aihydro-source"([^>]*)>(.*)$', m["body"], re.S)
        pid = re.search(r'id="([^"]+)"', pre[1])
        static = html.unescape(re.sub(r"<!--.*?-->", "", pre[2], flags=re.S))
        source = scripted.get(pid[1]) if pid and scripted.get(pid[1]) else static
        out.append({"id": cid, "source": source})
    return out


def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def quantise(png: bytes) -> bytes:
    from PIL import Image
    im = Image.open(io.BytesIO(png)).convert("RGB")
    im = im.quantize(colors=96, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    buf = io.BytesIO()
    im.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def run_cell(source: str) -> tuple[str, list[bytes]]:
    env = dict(os.environ, MPLBACKEND="Agg", PYTHONHASHSEED="0", MPLCONFIGDIR=MPLCFG)
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "cell.py").write_text(source, encoding="utf-8")
        (Path(td) / "runner.py").write_text(RUNNER, encoding="utf-8")
        r = subprocess.run([sys.executable, "-s", "-E", "runner.py", "cell.py", td],
                           capture_output=True, text=True, cwd=td, env=env, timeout=300)
        if r.returncode != 0:
            raise SystemExit(f"cell failed:\n{r.stderr[-1500:]}")
        figs = [p.read_bytes() for p in sorted(Path(td).glob("fig*.png"))]
    return r.stdout, figs


def manim_last_frame(source: str) -> bytes:
    env = dict(os.environ, PYTHONHASHSEED="0", MPLCONFIGDIR=MPLCFG)
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "scene.py").write_text(source, encoding="utf-8")
        r = subprocess.run([sys.executable, "-s", "-E", "-m", "manim", "render", "-s", "-ql", "--media_dir", td + "/media",
                            "scene.py", "WaterCycle"], capture_output=True, text=True, cwd=td, env=env, timeout=600)
        if r.returncode != 0:
            raise SystemExit(f"manim failed:\n{(r.stdout + r.stderr)[-1500:]}")
        pngs = sorted(Path(td, "media").rglob("*.png"))
        if not pngs:
            raise SystemExit("manim produced no frame")
        return pngs[-1].read_bytes()


def versions() -> dict:
    import matplotlib
    import numpy
    return {"python": sys.version.split()[0], "numpy": numpy.__version__, "matplotlib": matplotlib.__version__}


def process(mod: str, check: bool) -> list[str]:
    sdir = MODULES / mod / "static"
    index_path = sdir / "index.json"
    index = json.loads(index_path.read_text()) if index_path.exists() else {}
    problems = []
    new_index = {}
    for cell in cells_of(mod):
        cid, digest = cell["id"], sha(cell["source"])
        special = SPECIAL.get((mod, cid))
        key_digest = digest if not special or special[0] != "text" else sha(special[1])
        prev = index.get(cid, {})
        have = (sdir / f"{cid}.txt").exists() or (sdir / f"{cid}.png").exists()
        if check:
            if not have or prev.get("source_sha256") != key_digest:
                problems.append(f"{mod}/{cid}: static output missing or stale")
            continue
        sdir.mkdir(exist_ok=True)
        if special and special[0] == "text":
            (sdir / f"{cid}.txt").write_text(special[1] + "\n", encoding="utf-8")
            new_index[cid] = {"mode": "text", "source_sha256": key_digest}
            continue
        if special and special[0] == "manim":
            (sdir / f"{cid}.txt").write_text(special[1] + "\n", encoding="utf-8")
            (sdir / f"{cid}.png").write_bytes(quantise(manim_last_frame(cell["source"])))
            new_index[cid] = {"mode": "manim-last-frame", "source_sha256": key_digest}
            continue
        stdout, figs = run_cell(cell["source"])
        (sdir / f"{cid}.txt").write_text(stdout if stdout.strip() else "(no printed output)\n", encoding="utf-8")
        png_path = sdir / f"{cid}.png"
        if figs:
            png_path.write_bytes(quantise(figs[0]))
        elif png_path.exists():
            png_path.unlink()
        new_index[cid] = {"mode": "headless", "source_sha256": digest, "figures": len(figs), **versions()}
        if len(figs) > 1:
            print(f"warning: {mod}/{cid} made {len(figs)} figures; only the first is stored")
    if not check:
        index_path.write_text(json.dumps(new_index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        alt_path = sdir / "alt.json"
        alt = json.loads(alt_path.read_text()) if alt_path.exists() else {}
        for cid in new_index:
            if (sdir / f"{cid}.png").exists() and cid not in alt:
                problems.append(f"{mod}/{cid}: add alt text for the figure in {alt_path.relative_to(ROOT)}")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--only")
    a = ap.parse_args()
    mods = [a.only] if a.only else sorted(p.name for p in MODULES.iterdir() if (p / "module.html").exists())
    problems = []
    for mod in mods:
        problems += process(mod, a.check)
    for p in problems:
        print(p)
    if not problems:
        print("static outputs up to date" if a.check else "rendered")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
