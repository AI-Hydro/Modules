"""dem-to-twi: directions and TWI are computed, the python cell reproduces the JS pipeline, text numbers match."""
import json
import re
import sys

import pytest

from helpers import SHARED, core_block, module_text, run_node, run_python, shared_js, static_cell_sources, json_blob

T = module_text("dem-to-twi")
sys.path.insert(0, str(SHARED))
from d8 import d8_route  # noqa: E402


def _js():
    js = shared_js("d8.js") + core_block(T) + """
console.log(JSON.stringify({flow:FLOW_TO,twi:ROUTE.twi,acc:ROUTE.acc,T1:T1,T2:T2,hill:SYNTH_TWI,
  point:buildPointTwiSource(120,8)}));"""
    return run_node(js)


def test_flow_directions_are_computed_from_the_dem():
    dem = [[92, 90, 88, 86, 85], [85, 82, 79, 78, 79], [78, 75, 72, 73, 76], [74, 71, 68, 70, 72], [72, 69, 66, 68, 71]]
    r = d8_route(dem, 10.0)
    flow = _js()["flow"]
    for rr in range(5):
        for cc in range(5):
            k = r["rec"][rr * 5 + cc]
            assert flow[rr][cc] == (None if k < 0 else [k // 5, k % 5])


def test_python_cell_reproduces_js_means_and_terciles():
    j = _js()
    out = run_python(static_cell_sources(T)["twi-grid"])
    m30 = float(re.search(r"Mean TWI at 30 m : ([0-9.]+)", out).group(1))
    m60 = float(re.search(r"Mean TWI at 60 m : ([0-9.]+)", out).group(1))
    t1, t2 = map(float, re.search(r"Terciles of the 30 m grid: ([0-9.]+) \| ([0-9.]+)", out).groups())
    assert m30 == pytest.approx(sum(j["hill"]) / 400, abs=5e-4)
    assert t1 == pytest.approx(j["T1"], abs=6e-3) and t2 == pytest.approx(j["T2"], abs=6e-3)
    # quiz Q3 quotes these numbers (difference taken from the unrounded means)
    import math
    n = 20
    dem = [[100 + 3.0 * (n - 1 - r) + 1.5 * abs(c - ((n - 1) / 2 + 2 * math.sin(2 * math.pi * r / n)))
            + 4.5 * math.sin(2.3 * r + 0.5) * math.cos(1.9 * c) for c in range(n)] for r in range(n)]
    coarse = [[(dem[2*r][2*c] + dem[2*r+1][2*c] + dem[2*r][2*c+1] + dem[2*r+1][2*c+1]) / 4 for c in range(n // 2)] for r in range(n // 2)]
    e30 = sum(d8_route(dem, 30.0)["twi"]) / 400
    e60 = sum(d8_route(coarse, 60.0)["twi"]) / 100
    assert f"{e30:.2f} at 30 m and {e60:.2f} at 60 m" in T
    assert f"{e60 - e30:.2f}" in T
    assert m60 == pytest.approx(e60, abs=5e-4)


def test_point_cell_runs_and_states_floor():
    out = run_python(_js()["point"])
    assert "TWI      →" in out and "Floor effect" in out
    assert "TAN_FLOOR = 0.001" in _js()["point"]


def test_numbers_quoted_in_text_match_computation():
    j = _js()
    assert f"{j['twi'][22]:.2f}" in T                           # outlet TWI 12.43
    assert f"TWI 2.65 and 2.81" in T and f"{j['twi'][0]:.2f}" == "2.65" and f"{j['twi'][4]:.2f}" == "2.81"
    import math
    assert f"{math.log(100 / 1e-3):.1f}" in T and f"{math.log(100 / 1e-6):.1f}" in T
    assert j["acc"][22] == 25
    assert "6.25" in T and f"{math.log(6.25):.2f}" in T


def test_marker_is_the_camels_outlet_and_catchment_map_has_no_fake_overlay():
    meta = json.load(open(SHARED.parent / "modules/dem-to-twi/data/camels_gauges.json"))["01031500"]
    assert meta["lat"] == 45.17501 and meta["lon"] == -69.3147
    assert 'data-marker-lat="45.17501"' in T and 'data-marker-lng="-69.3147"' in T
    assert "Medford" not in T
    assert "makeTwiCanvas" not in T and "imageOverlay" not in T


def test_no_unsourced_thresholds_or_claims():
    for stale in ["5 – 8", "8 – 11", "&lt; 5", "mean TWI ≈ 8", "1–2 units", "≈ 40,000", "default to <code>method", "pysheds"]:
        assert stale not in T, stale
    assert "relative" in T.lower()


def test_polygon_boundary_ends_at_the_gauge_vertex():
    m = re.search(r'<script type="application/geo\+json">\s*(\{.*?\})\s*</script>', T, re.S)
    coords = json.loads(m.group(1))["geometry"]["coordinates"][0]
    lon, lat = -69.3147, 45.17501
    assert min(abs(x - lon) + abs(y - lat) for x, y in coords) < 0.001
