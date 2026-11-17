"""reading-a-hydrograph: SCS-CN demo is non-degenerate and its numbers match the formula; §6 uses real data."""
import json
import re

import pytest

from helpers import SHARED, core_block, json_blob, module_text, run_node, run_python, shared_js

T = module_text("reading-a-hydrograph")


def q(P, CN=75):
    S = 25400 / CN - 254
    Ia = 0.2 * S
    return 0 if P <= Ia else (P - Ia) ** 2 / (P - Ia + S)


def test_scs_numbers_in_text_match_formula():
    S = 25400 / 75 - 254
    assert f"{S:.1f}" in T and f"{0.2 * S:.1f}" in T
    assert f"{q(25):.2f}" in T and f"{q(50):.2f}" in T
    assert q(25) > 0 and q(50) > 0
    assert f"{q(50) / q(25):.0f}-fold" in T or "about 13" in T
    assert round(q(50) / q(25)) == 13
    assert f"{2 * q(25):.2f} mm" in T          # what proportional runoff would give


def test_formula_typo_and_wrong_quiz_are_gone():
    assert "P · (P − Ia)² / (P − Ia + S)" not in T
    assert "already-wet" not in T
    assert "saturated soil at work" not in T
    assert "published Lyne–Hollick default" not in T
    assert "Small storm (10 mm)" not in T


def test_python_cells_run_for_each_real_gauge_and_bfi_matches_js():
    blob = json_blob(T, "camels-wy")["gauges"]
    assert set(blob) == {"14305500", "01031500", "02472000"}
    js = shared_js("lyne_hollick.js") + "\nvar PY_LH=%s;\n" % json.dumps((SHARED / "lyne_hollick.py").read_text().rstrip("\n")) + \
        core_block(T, "CORE2") + """
var G=%s, out={};
for (var k in G){var g=G[k];var qm=g.q_cfs.map(function(v){return v*0.028316846592;});
  out[k]={src:buildPySource(g),bfi:baseflowIndex(qm,lyneHollick(qm,0.925))};}
console.log(JSON.stringify(out));""" % json.dumps(blob)
    out = run_node(js)
    for gid, o in out.items():
        res = run_python(o["src"])
        bfi = float(re.search(r"BFI \(LH\)\s+: ([0-9.]+)", res).group(1))
        assert bfi == pytest.approx(o["bfi"], abs=5e-4), gid
        assert "observed" in res and "CAMELS" in res
        g = blob[gid]
        assert g["n"] == 365 and len(g["prcp_mm_day"]) == 365
        # runoff ratio printed from the data
        qmm = sum(g["q_cfs"]) * 0.028316846592 * 86400 / (g["area_km2"] * 1e6) * 1000
        pm = sum(g["prcp_mm_day"])
        assert f"Total P      : {pm:.0f} mm   Total Q: {qmm:.0f} mm" in res


def test_gauge_labels_corrected():
    for ok in ["Siletz River at Siletz, OR", "Piscataquis River near Dover-Foxcroft, ME", "Leaf River near Collins, MS"]:
        assert ok in T
    for bad in ["Cascades", "Medford", "Mississippi)", "real-shape", "synthesises a year", "rng.gamma"]:
        assert bad not in T, bad


def test_bfi_explorer_uses_shared_filter_and_quiz_direction_holds():
    assert "lyneHollickProper" not in T
    js = shared_js("lyne_hollick.js") + core_block(T) + \
        "var b=function(a){return baseflowIndex(EVENT_Q,lyneHollick(EVENT_Q,a));};console.log(JSON.stringify([b(0.925),b(0.985)]));"
    a, b = run_node(js)
    assert b < a
