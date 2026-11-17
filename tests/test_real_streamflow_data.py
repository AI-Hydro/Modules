"""real-streamflow-data: real bundled data, loud failures, text numbers recomputed from the CSVs."""
import csv
import datetime as dt
import json
import re
import sys

import numpy as np
import pytest

from helpers import ROOT, core_block, json_blob, module_text, run_node, run_python

T = module_text("real-streamflow-data")
D = ROOT / "modules/real-streamflow-data/data"
GAUGES = ["01013500", "14305500", "09484000", "02472000"]


def series(g):
    rows = list(csv.DictReader((D / f"{g}_q.csv").open()))
    return [dt.date.fromisoformat(r["date"]) for r in rows], np.array([float(r["q_cfs"]) for r in rows]) * 0.028316846592


def _cells():
    blob = json_blob(T, "camels-5yr")["gauges"]
    js = core_block(T) + "var G=%s,out={};for(var k in G)out[k]=buildSnapshotSource(G[k],'2026-11-17');console.log(JSON.stringify(out));" % json.dumps(blob)
    return run_node(js)


def test_blob_equals_csv_and_data_are_complete():
    blob = json_blob(T, "camels-5yr")["gauges"]
    for g in GAUGES:
        d, q = series(g)
        assert blob[g]["n"] == len(q) == 1827
        assert np.allclose(np.array(blob[g]["q_cfs"]) * 0.028316846592, q)
        assert d[0] == dt.date(1995, 10, 1) and d[-1] == dt.date(2000, 9, 30)
        assert (np.diff([x.toordinal() for x in d]) == 1).all()


@pytest.mark.parametrize("g", GAUGES)
def test_snapshot_cell_runs_and_prints_provenance(g):
    out = run_python(_cells()[g])
    for need in ["parameter 00060", "Period       : 1995-10-01 to 2000-09-30  (1827 days)", "Status", "provisional", "CAUTION: only 5 annual maxima"]:
        assert need in out
    d, q = series(g)
    assert f"Zero-flow    : {int((q == 0).sum())} days" in out
    assert f"Mean Q       : {q.mean():.2f} m3/s" in out


def test_weibull_return_periods_are_ranked_annual_maxima():
    out = run_python(_cells()["01013500"])
    rows = re.findall(r"WY(\d{4}):\s+([0-9.]+) m3/s\s+T = ([0-9.]+) yr", out)
    assert [float(r[2]) for r in rows] == [6.0, 3.0, 2.0, 1.5, 1.2]
    assert [r[0] for r in rows][0] == "1996"    # largest annual maximum 305.8 m3/s on 1996-04-28
    assert "Dividing the record length" not in T      # the old, wrong return-period rule


def test_text_claims_match_data():
    d, q = series("09484000")
    assert (q == 0).sum() == 704 and "704 of 1 827" in T and f"{(q==0).mean()*100:.1f}%" in T
    months = np.array([x.month for x in d])
    thr = np.percentile(q, 95)
    fl = q > thr
    assert int(fl.sum()) == 92
    assert int(fl[(months >= 2) & (months <= 4)].sum()) == 72 and int(fl[(months >= 7) & (months <= 9)].sum()) == 19
    assert round(q.max() / q.mean()) in (127, 128, 129, 130)       # "about 130 times its mean"
    # Fish River
    d1, q1 = series("01013500"); m1 = np.array([x.month for x in d1]); f1 = q1 > np.percentile(q1, 95)
    mm = [q1[m1 == k].mean() for k in range(1, 13)]
    assert f"{mm[4]:.1f} m³/s" in T and f"{mm[3]:.1f} m³/s" in T and f"{mm[7]:.1f} m³/s" in T
    assert int(f1[(m1 == 4) | (m1 == 5)].sum()) == 92
    # Siletz
    d2, q2 = series("14305500"); m2 = np.array([x.month for x in d2]); f2 = q2 > np.percentile(q2, 95)
    assert int(f2[np.isin(m2, [11, 12, 1, 2])].sum()) == 84 and "84 of the 92" in T
    mm2 = [q2[m2 == k].mean() for k in range(1, 13)]
    assert f"{mm2[11]:.1f} m³/s" in T and f"{mm2[7]:.1f} m³/s" in T
    # Leaf
    d3, q3 = series("02472000"); m3 = np.array([x.month for x in d3]); f3 = q3 > np.percentile(q3, 95)
    assert int(f3[np.isin(m3, [12, 1, 2, 3, 4])].sum()) == 90 and "90 of the 92" in T
    mm3 = [q3[m3 == k].mean() for k in range(1, 13)]
    assert f"{mm3[8]:.1f} m³/s" in T and 51 <= min(mm3[0:4]) and max(mm3[0:4]) <= 57.5


def test_no_synthetic_fallback_and_old_gauges_gone():
    for stale in ["default_rng", "Rillito", "Bogue Chitto", "Falls back to seeded synthetic", "synthetic fallback kicks in", "CAMELS-shaped", "Moore, C.", "Pettitt", "month = (t % 365)"]:
        assert stale not in T, stale
    assert "Sabino Creek near Tucson, AZ" in T and "Leaf River near Collins, MS" in T


def test_nwis_cell_fails_loudly_without_dataretrieval():
    src = "import sys\nsys.modules['dataretrieval']=None\nsys.modules['dataretrieval.nwis']=None\n" + \
        run_node(core_block(T) + "console.log(JSON.stringify(buildNwisSource('01013500')));")
    out = run_python(src)
    assert "NWIS request FAILED" in out and "Nothing was substituted" in out
    assert "parameter 00060" in out and "accessed" in out


def test_map_uses_camels_coordinates():
    geo = json.load(open(D / "camels_gauges.json"))
    for g in GAUGES:
        assert f"[{geo[g]['lon']},{geo[g]['lat']}]" in T.replace(" ", "")


def test_card_facts_are_camels_attributes():
    meta = json.load(open(D / "camels_gauges.json"))
    for g, m in meta.items():
        assert f"baseflow index {m['baseflow_index']:.3f}" in T, g
    low = T.lower()
    assert f"snow fraction of precipitation {meta['01013500']['frac_snow']:.2f}" in low
    assert f"snow fraction {meta['14305500']['frac_snow']:.2f}" in low and f"mean precipitation {meta['14305500']['p_mean_mm_day']:.2f} mm/day" in low
    assert f"pet/p = {meta['09484000']['aridity']:.2f}" in low
    assert f"fraction {meta['02472000']['frac_snow']:.3f}" in low and f"mean precipitation {meta['02472000']['p_mean_mm_day']:.2f}" in low
    assert "2 253 km²" in T and round(meta["01013500"]["area_km2"]) == 2253
