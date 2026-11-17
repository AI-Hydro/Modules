"""Shared helpers for the repo-local tests (pytest + node, no network, no installs)."""
from __future__ import annotations

import html
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODULES = ROOT / "modules"
SHARED = ROOT / "shared"


def module_text(mod: str) -> str:
    return (MODULES / mod / "module.html").read_text(encoding="utf-8")


def scripts(text: str) -> list[str]:
    """Bodies of executable inline <script> elements (JS only; JSON/geojson blocks excluded)."""
    out = []
    for m in re.finditer(r"<script(?P<attr>[^>]*)>(?P<body>.*?)</script>", text, re.S):
        attr = m["attr"]
        if "src=" in attr or "json" in attr:
            continue
        out.append(m["body"])
    return out


def json_blob(text: str, blob_id: str) -> dict:
    m = re.search(rf'<script type="application/json" id="{blob_id}">(.*?)</script>', text, re.S)
    assert m, f"blob {blob_id} not found"
    return json.loads(m.group(1).replace("<\\/", "</"))


def core_block(text: str, tag: str = "CORE") -> str:
    """The hand-maintained pure-logic block between CORE markers."""
    m = re.search(rf"/\*@@{tag}-BEGIN@@\*/(.*?)/\*@@{tag}-END@@\*/", text, re.S)
    assert m, f"no {tag} block"
    return m.group(1)


def static_cell_sources(text: str) -> dict[str, str]:
    """Python sources of cells whose <pre class="aihydro-source"> is written in the HTML."""
    out = {}
    for m in re.finditer(
        r'<div class="aihydro-cell"[^>]*data-aihydro-cell-id="(?P<id>[^"]+)"[^>]*>(?P<body>.*?)<pre class="aihydro-source"[^>]*>(?P<src>.*?)</pre>',
        text, re.S):
        src = re.sub(r"<!--.*?-->", "", m["src"], flags=re.S)
        out[m["id"]] = html.unescape(src)
    return out


def run_python(src: str, timeout: int = 120) -> str:
    """Run a cell headless (Agg backend) in a scratch directory; return stdout."""
    env = dict(os.environ, MPLBACKEND="Agg", PYTHONHASHSEED="0")
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "cell.py"
        p.write_text(src, encoding="utf-8")
        r = subprocess.run([sys.executable, "-s", "-E", str(p)], capture_output=True,
                           text=True, cwd=td, env=env, timeout=timeout)
    assert r.returncode == 0, f"cell failed:\n{r.stderr}\n--- source head ---\n{src[:400]}"
    return r.stdout


def run_node(js: str, timeout: int = 60):
    """Run JS under node; the script must console.log one JSON document."""
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.js"
        p.write_text(js, encoding="utf-8")
        r = subprocess.run(["node", str(p)], capture_output=True, text=True, timeout=timeout)
    assert r.returncode == 0, f"node failed:\n{r.stderr}"
    return json.loads(r.stdout)


def shared_js(*names: str) -> str:
    return "\n".join((SHARED / n).read_text() for n in names)
