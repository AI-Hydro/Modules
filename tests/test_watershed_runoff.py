"""watershed-runoff: routing reaches the outlet; rational-method and SCS-CN cells match their formulas."""
import re

import pytest

from helpers import core_block, module_text, run_node, run_python, shared_js, static_cell_sources

T = module_text("watershed-runoff")


def test_d8_reaches_outlet_from_at_least_95_percent_of_cells():
    js = shared_js("d8.js") + core_block(T) + "console.log(JSON.stringify({f:reachFraction(),o:ROUTE.outlet,n:N*N}));"
    r = run_node(js)
    assert r["n"] == 1024 and r["f"] >= 0.95
    assert r["o"]["r"] == 31  # outlet on the south edge


def test_python_d8_twin_reaches_outlet_on_the_same_dem():
    import sys
    from helpers import SHARED
    sys.path.insert(0, str(SHARED))
    from d8 import d8_route, d8_path
    js = shared_js("d8.js") + core_block(T) + "console.log(JSON.stringify(DEM));"
    dem = run_node(js)
    r = d8_route(dem, 30.0)
    o = r["outlet"][0] * 32 + r["outlet"][1]
    ok = sum(1 for i in range(1024) if d8_path(r["rec"], i)[-1] == o)
    assert ok / 1024 >= 0.95


def test_scs_cn_cell_matches_formula_and_both_storms_run_off():
    out = run_python(static_cell_sources(T)["scs-cn"])
    S = 25400 / 75 - 254
    Ia = 0.2 * S
    q = lambda p: 0 if p <= Ia else (p - Ia) ** 2 / (p - Ia + S)
    assert q(40) > 0 and q(80) > 0
    for p in (40, 80):
        m = re.search(rf"storm P =\s+{p}\.0 mm\s+->\s+runoff Q =\s+([0-9.]+) mm", out)
        assert float(m.group(1)) == pytest.approx(q(p), abs=0.005)
    assert "S = 84.7 mm" in out and "Ia = 16.9 mm" in out


def test_rational_cell_matches_formula():
    out = run_python(static_cell_sources(T)["rational-method"])
    C, i, A = 0.35, 40.0, 92.16
    want = C * (i / 1000 / 3600) * (A * 1e4)
    assert want == pytest.approx(C * i * A / 360)
    assert float(re.search(r"Q = ([0-9.]+) m³/s", out).group(1)) == pytest.approx(want, abs=5e-4)
    assert "SYNTHETIC" in out


def test_area_in_cells_matches_dem():
    # 32 x 32 cells of 30 m = 921 600 m² = 92.16 ha, as stated in the lesson
    assert 32 * 32 * 30 * 30 == 921600 and 921600 / 1e4 == pytest.approx(92.16)
    assert "921 600 m² = 92.16 ha" in T


def test_text_claims():
    assert "Jenson" not in T                       # D8 is O'Callaghan & Mark (1984)
    assert "greatest elevation difference" not in T
    assert "drop per unit distance" in T
    assert "SYNTHETIC" in T and "synthetic metres" in T
    assert "Python required" not in T and "no Python" not in T
