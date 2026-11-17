"""One Lyne-Hollick and one D8: the Python and JavaScript twins agree, and every module
carries the shared text verbatim (scripts/build_modules.py --check is clean)."""
import json
import subprocess
import sys

import pytest

from helpers import ROOT, SHARED, core_block, module_text, run_node, shared_js

sys.path.insert(0, str(SHARED))
from lyne_hollick import baseflow_index, lyne_hollick  # noqa: E402
from d8 import d8_route  # noqa: E402


def test_build_is_clean():
    r = subprocess.run([sys.executable, "-s", "-E", str(ROOT / "scripts" / "build_modules.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def _synthetic():
    js = shared_js("lyne_hollick.js") + core_block(module_text("baseflow-separation")) + \
        "console.log(JSON.stringify(makeSyntheticSeries()));"
    return run_node(js)


def test_synthetic_series_python_cell_equals_javascript():
    from helpers import run_python, static_cell_sources
    s = _synthetic()
    out = run_python(static_cell_sources(module_text("baseflow-separation"))["lh-filter"])
    bfi_cell = float(out.split("BFI (filter)   =")[1].split()[0])
    bfi_true_cell = float(out.split("BFI (true)     =")[1].split()[0])
    base = lyne_hollick(s["Q"], 0.925)
    assert bfi_cell == pytest.approx(baseflow_index(s["Q"], base), abs=5e-5)
    assert bfi_true_cell == pytest.approx(sum(s["bTrue"]) / sum(s["Q"]), abs=5e-5)


@pytest.mark.parametrize("alpha", [0.8, 0.9, 0.925, 0.95, 0.98])
def test_lyne_hollick_python_equals_javascript(alpha):
    s = _synthetic()
    js = shared_js("lyne_hollick.js") + f"var Q={json.dumps(s['Q'])};console.log(JSON.stringify(lyneHollick(Q,{alpha})));"
    b_js = run_node(js)
    b_py = lyne_hollick(s["Q"], alpha)
    assert max(abs(a - b) for a, b in zip(b_js, b_py)) < 1e-9


def test_lyne_hollick_equals_on_real_gauge_series():
    import csv
    rows = list(csv.DictReader((ROOT / "modules/capstone-basin-story/data/09484000_q.csv").open()))
    q = [float(r["q_cfs"]) * 0.028316846592 for r in rows]
    js = shared_js("lyne_hollick.js") + f"var Q={json.dumps(q)};console.log(JSON.stringify(lyneHollick(Q,0.925)));"
    b_js = run_node(js)
    assert max(abs(a - b) for a, b in zip(b_js, lyne_hollick(q, 0.925))) < 1e-9


def test_python_filter_properties():
    q = [1 + 5 * (0.8 ** i) for i in range(60)] + [1.0] * 60
    b = lyne_hollick(q, 0.925)
    assert all(0 <= x <= y + 1e-12 for x, y in zip(b, q))
    assert lyne_hollick([2.0] * 50, 0.925) == pytest.approx([2.0] * 50)


def _hill():
    n = 20
    import math
    return [[100 + 3.0 * (n - 1 - r) + 1.5 * abs(c - ((n - 1) / 2 + 2 * math.sin(2 * math.pi * r / n)))
             + 4.5 * math.sin(2.3 * r + 0.5) * math.cos(1.9 * c) for c in range(n)] for r in range(n)]


@pytest.mark.parametrize("name,dem,cell", [
    ("5x5", [[92, 90, 88, 86, 85], [85, 82, 79, 78, 79], [78, 75, 72, 73, 76], [74, 71, 68, 70, 72], [72, 69, 66, 68, 71]], 10.0),
    ("hill", _hill(), 30.0),
])
def test_d8_python_equals_javascript(name, dem, cell):
    js = shared_js("d8.js") + f"var R=d8Route({json.dumps(dem)},{cell});console.log(JSON.stringify({{rec:R.rec,acc:R.acc,twi:R.twi,filled:R.filled}}));"
    j = run_node(js)
    p = d8_route(dem, cell)
    assert j["rec"] == p["rec"]
    assert j["acc"] == p["acc"]
    assert max(abs(a - b) for a, b in zip(j["twi"], p["twi"])) < 1e-9
    assert max(abs(a - b) for a, b in zip(j["filled"], p["filled"])) < 1e-9


def test_exactly_one_lyne_hollick_implementation_per_module():
    for mod in ["baseflow-separation", "reading-a-hydrograph", "capstone-basin-story", "real-streamflow-data"]:
        t = module_text(mod)
        assert t.count("function lyneHollick(") <= 1, mod
        assert t.count("def lyne_hollick(") <= 1 or "var PY_LH" in t, mod
        for variant in ["lyneHollickProper", "def lh(", "def lh(Q", "function lyneHollick (Q, alpha) {"]:
            assert variant not in t, (mod, variant)
    # the capstone embeds the Python text through one variable that two cells share
    t = module_text("capstone-basin-story")
    assert t.count("var PY_LH =") == 1 and t.count("      PY_LH,") >= 2
