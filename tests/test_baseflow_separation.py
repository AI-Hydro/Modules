"""Baseflow module: the BFI the page shows is the BFI the filter computes."""
import re

import pytest

from helpers import SHARED, core_block, module_text, run_node, run_python, shared_js, static_cell_sources

T = module_text("baseflow-separation")


def _node_bfi(alpha):
    js = shared_js("lyne_hollick.js") + core_block(T) + \
        f"var s=makeSyntheticSeries();console.log(JSON.stringify({{bfi:baseflowIndex(s.Q,lyneHollick(s.Q,{alpha})),tr:s.bTrue.reduce(function(a,b){{return a+b}},0)/s.Q.reduce(function(a,b){{return a+b}},0)}}));"
    return run_node(js)


def test_static_bfi_numbers_equal_computed():
    at = {a: _node_bfi(a)["bfi"] for a in (0.925, 0.8, 0.975)}
    true_bfi = _node_bfi(0.925)["tr"]
    shown = re.search(r'id="bfiEstDisplay"[^>]*>([0-9.]+)<', T).group(1)
    assert float(shown) == pytest.approx(at[0.925], abs=5e-4)
    width = re.search(r'id="bfiBar" style="width:([0-9.]+)%', T).group(1)
    assert float(width) == pytest.approx(at[0.925] * 100, abs=0.05)
    assert f"BFI {at[0.8]:.3f}" in T and f"BFI {at[0.975]:.3f}" in T
    assert f"({true_bfi:.3f})" in T
    assert f"BFI = {at[0.925]:.3f}" in T


def test_python_cell_prints_the_same_bfi():
    out = run_python(static_cell_sources(T)["lh-filter"])
    assert float(re.search(r"BFI \(filter\)\s+=\s+([0-9.]+)", out).group(1)) == pytest.approx(_node_bfi(0.925)["bfi"], abs=5e-5)


def test_old_made_up_claims_are_gone():
    for stale in ["estimateBFI", "BFI ≈ 0.55", "~0.55", "0.4 and 0.8", "lower values for sub-daily", "default_rng(42)", "seed 42"]:
        assert stale not in T, stale
    assert "SYNTHETIC" in T


def test_one_series_in_js_and_python():
    # the hand-typed JS hydrograph (storms list with 3.5 + s * 0.4) is gone; both use STORM_DAYS/STORM_AMPS
    assert "(3.5 + s * 0.4)" not in T
    assert "STORM_AMPS" in T and "storm_amp" in T


def test_slider_cell_rewrite_keeps_alpha_line():
    src = static_cell_sources(T)["lh-filter"]
    assert re.search(r"^alpha = [\d.]+", src, re.M)


def test_standard_filter_stated_with_verified_references():
    assert "each pass filters the baseflow left by the previous pass" in T
    assert "reflected" in T
    assert "10.1029/WR026i007p01465" in T and "10.7158/13241583.2013.11465417" in T
    assert "Lyne, V." not in T  # 1979 report failed the citation gate


def test_fonts_linked_once():
    assert T.count("fonts.googleapis.com/css2") == 1
