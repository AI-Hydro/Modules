"""water-cycle: no unsourced magnitudes, computed lapse rates, mass-conserving bucket, working scrubber."""
import re

import pytest

from helpers import core_block, module_text, run_node, run_python, static_cell_sources

T = module_text("water-cycle-in-motion")


def test_dew_point_cell_numbers_match_text():
    out = run_python(static_cell_sources(T)["dewpoint-lapse"])
    dry = float(re.search(r"Dry adiabatic lapse rate : ([0-9.]+) K/km", out).group(1))
    dew = float(re.search(r"Dew-point lapse rate     : ([0-9.]+) K/km", out).group(1))
    g, cp, Rd, Rv, Lv, Tk, Td = 9.80665, 1005.0, 287.05, 461.5, 2.5e6, 288.15, 283.15
    assert dry == pytest.approx(g / cp * 1000, abs=5e-3)
    assert dew == pytest.approx((g / (Rd * Tk)) * (Rv * Td ** 2 / Lv) * 1000, abs=5e-3)
    assert f"{dry:.2f} K/km" in T and f"{dew:.2f} K/km" in T
    assert dew < dry / 4                                       # dew point falls far more slowly than the air


def test_bucket_conserves_mass():
    js = core_block(T) + """
var S=45,err=0,seq=[0,3,10,10,0.5,7,10,10,0],bal=0;
for(var k=0;k<3000;k++){var P=seq[k%seq.length],s=stepBucket(S,P,2,0.05);bal+= (P-s.ET-s.R)*0.05;
 err=Math.max(err,Math.abs(S+(P-s.ET-s.R)*0.05-s.S));S=s.S;}
console.log(JSON.stringify({err:err,closure:45+bal-S}));"""
    r = run_node(js)
    assert r["err"] < 1e-10 and abs(r["closure"]) < 1e-8


def test_unsourced_magnitudes_removed():
    for stale in ["1 200 mm", "1 000 mm", "≈ 1 000", "≈ 40 %", "40 000 km", "1 °C per 100 m", "1–300 mm", "snowpack", "default_rng"]:
        assert stale not in T, stale
    assert "ΔS" in T and "Only over many years" in T


def test_scrubber_has_a_range_fallback_and_balance_readouts():
    assert 'id="stageRange"' in T and "wireStageRange" in T
    for ident in ['id="bET"', 'id="bR"', 'id="bDS"', 'id="bS"']:
        assert ident in T
