"""runoff-generation: the Green-Ampt column, the mechanism map, the hillslope and the real-event numbers are
recomputed here independently of the page (numpy only) and compared with what the page and its Python cells compute."""
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest

from helpers import MODULES, ROOT, SHARED, core_block, json_blob, module_text, quiz_item, run_node, run_python, shared_js, static_cell_sources

MOD = "runoff-generation"
T = module_text(MOD)
D = MODULES / MOD / "data"
LH_JS = shared_js("lyne_hollick.js")
LH_PY = json.dumps((SHARED / "lyne_hollick.py").read_text().rstrip("\n"))
CORE = core_block(T)
CORE2 = core_block(T, "CORE2")
BLOB = json_blob(T, "runoff-events")
GIDS = ["14305500", "02472000", "09484000"]
CFS = 0.028316846592

KS, PSI, DTH = 10.0, 100.0, 0.30
M = PSI * DTH


# ── independent numpy/stdlib implementations ────────────────────────────────────────────────
def G(F):
    return F - M * math.log(1.0 + F / M)


def tp_ml(i):
    """Mein & Larson ponding time (h): Ks psi dtheta / (i (i - Ks)) for i > Ks."""
    return KS * M / (i * (i - KS))


def f_cap(F):
    return KS * (1.0 + M / F)


def simulate(i, Tend, Dd, dt=2e-5):
    """Explicit time stepping of the same physics (rain i, capacity Ks(1+M/F), store D): no closed forms used."""
    n = int(round(Tend / dt))
    F = rie = rse = 0.0
    for _ in range(n):
        want = i * dt
        cap = f_cap(F) * dt if F > 0 else float("inf")
        room = Dd - F
        take = min(want, cap, max(room, 0.0))
        F += take
        if room <= min(want, cap):               # the store is full by the end of this step: what is left is saturation excess
            rse += want - take
        else:
            rie += want - take
    return F, rie, rse


def run_js(expr: str):
    return run_node(LH_JS + CORE + f"\nconsole.log(JSON.stringify({expr}));")


def ga(i, Tend, Dd):
    return run_js(f"gaRun({i},{Tend},{Dd})")


# ── data and provenance ─────────────────────────────────────────────────────────────────────
def test_provenance_shape_and_agreement_with_the_blob():
    prov = json.loads((D / "PROVENANCE.json").read_text())
    assert prov["module"] == MOD and prov["extraction_script"] == "scripts/extract_camels.py"
    assert any("10.5194/hess-19-209-2015" in c for c in prov["citations"])
    assert any("10.5194/hess-21-5293-2017" in c for c in prov["citations"])
    assert set(prov["series"]) == set(GIDS) == set(BLOB["basins"])
    for g, s in prov["series"].items():
        b = BLOB["basins"][g]
        assert s["flow_source_member"].startswith("basin_dataset_public_v1p2/usgs_streamflow/")
        assert s["precip_source_member"].startswith("basin_dataset_public_v1p2/basin_mean_forcing/daymet/")
        assert s["flow_source_member"] == b["flow_member"] and s["precip_source_member"] == b["precip_member"]
        for k in ("flow_source_member_sha256", "precip_source_member_sha256"):
            assert re.fullmatch(r"[0-9a-f]{64}", s[k])
        assert s["flow_source_member_sha256"] == b["flow_sha256"] and s["precip_source_member_sha256"] == b["precip_sha256"]
        assert s["n_days"] == len(b["q_cfs"]) == len(b["prcp_hundredths_mm"]) == 1827
        assert s["period"] == ["1995-10-01", "2000-09-30"]
        assert set(s["usgs_qc_flags"]) <= {"A", "A:e"}
        assert s["usgs_qc_flags"].get("A:e", 0) == len(b["estimated_idx"])
        assert sum(s["usgs_qc_flags"].values()) == 1827
        assert all(q >= 0 for q in b["q_cfs"]) and all(isinstance(p, int) and p >= 0 for p in b["prcp_hundredths_mm"])
    attr_files = prov["camels_root_relative_sources"]["attribute_files"]
    assert {"camels_soil.txt", "camels_clim.txt", "camels_hydro.txt"} <= set(attr_files)
    assert all(re.fullmatch(r"[0-9a-f]{64}", v["sha256"]) for v in attr_files.values())
    assert prov["omitted_gauge_attributes_only"] == "01013500" and "01013500" in BLOB["omitted"]
    assert "cm/hr" in prov["soil_conductivity_unit"]


def test_sizes_are_within_budget():
    assert sum(f.stat().st_size for f in D.iterdir()) < 50_000
    assert len(T.encode()) < 200_000
    for png in (MODULES / MOD / "static").glob("*.png"):
        assert png.stat().st_size < 25_000, png.name


def test_period_and_counts_in_the_prose_match_the_data():
    assert "water years 1996–2000 (1827 days)" in T
    assert all(len(b["q_cfs"]) == 1827 for b in BLOB["basins"].values())
    assert "Source members and sha256 in <code>data/PROVENANCE.json</code>" in T


def test_one_blob_and_no_fetches():
    assert json.loads(json.dumps(BLOB)) == json.loads((D / "runoff-events.json").read_text())
    assert not re.search(r"\bfetch\s*\(", "\n".join(re.findall(r"<script>(.*?)</script>", T, re.S)))


# ── Green-Ampt column ───────────────────────────────────────────────────────────────────────
def test_ponding_time_matches_mein_larson_and_capacity_equals_rain_there():
    for i in (11, 12.5, 25, 40, 60):
        r = ga(i, 3, 500)
        assert r["tp"] == pytest.approx(tp_ml(i), rel=1e-12)
        assert f_cap(r["Fp"]) == pytest.approx(i, rel=1e-12)            # capacity has fallen to the rain rate at F_p
        assert r["Fp"] == pytest.approx(i * r["tp"], rel=1e-12)
    for i in (2, 5, 10):
        assert ga(i, 3, 500)["tp"] is None                               # i <= Ks never ponds


def test_after_ponding_infiltration_satisfies_the_implicit_green_ampt_equation_and_capacity_stays_above_ks():
    out = run_js("[1,2,3,4,5].map(function(k){return {t: 0.5*k+0.25, i: [12,18,25,40,60][k-1]};}).map(function(c){return {c:c, F: gaFree(c.t, c.i)};})")
    for o in out:
        i, t, F = o["c"]["i"], o["c"]["t"], o["F"]
        tp = tp_ml(i)
        Fp = i * tp
        if t > tp:
            assert G(F) - G(Fp) == pytest.approx(KS * (t - tp), abs=1e-6)
            assert f_cap(F) >= KS - 1e-12
            assert F < i * t                                              # infiltration lags the rain after ponding


def test_closed_form_matches_independent_time_stepping():
    for i, Tend, Dd in [(25, 2, 60), (40, 1.5, 30), (15, 3, 120), (60, 1, 25), (5, 6, 10), (8, 4, 20)]:
        r = ga(i, Tend, Dd)
        F, rie, rse = simulate(i, Tend, Dd)
        assert r["F"] == pytest.approx(F, abs=0.03), (i, Tend, Dd)
        assert r["RIE"] == pytest.approx(rie, abs=0.05), (i, Tend, Dd)
        assert r["RSE"] == pytest.approx(rse, abs=0.05), (i, Tend, Dd)


def test_mass_balance_closes_per_step_and_runoff_rules_hold():
    series = run_js("gaSeries(25,3,45,300)")
    for k in range(len(series["t"])):
        assert series["P"][k] == pytest.approx(series["F"][k] + series["RIE"][k] + series["RSE"][k], abs=1e-9)
        assert series["F"][k] <= 45 + 1e-12 and series["RIE"][k] >= -1e-9 and series["RSE"][k] >= -1e-12
    r = series["run"]
    assert abs(r["resid"]) < 1e-9
    tD = r["tD"]
    assert tD is not None
    for t, rse, F in zip(series["t"], series["RSE"], series["F"]):
        if t < tD - 1e-12:
            assert rse == 0                                               # saturation excess only after the store is full
        assert (F >= 45 - 1e-9) == (t >= tD - 1e-9) or t < tD
    for i in (2, 5, 9.99, 10):
        assert ga(i, 4, 100)["RIE"] == 0                                  # no infiltration excess at or below Ks
        assert ga(i, 4, 100)["RIE"] == 0 and ga(i, 4, 20)["RIE"] == 0
    for i, Tend, Dd in [(25, 2, 60), (25, 2, 40), (5, 6, 10), (60, 6, 120), (12, 0.5, 10)]:
        r = ga(i, Tend, Dd)
        assert abs(r["resid"]) < 1e-9 and r["F"] <= Dd + 1e-12 and r["RIE"] >= 0 and r["RSE"] >= 0


def test_capacity_never_below_ks_in_the_series():
    s = run_js("gaSeries(30,4,200,200)")
    caps = [c for c in s["cap"] if c is not None]
    assert all(c >= KS - 1e-12 for c in caps)
    assert caps[-1] > KS and caps[-1] < caps[len(caps) // 4]               # falling toward Ks, never reaching it


def test_mechanism_classes_and_quiz_scenario():
    assert ga(5, 6, 10)["mech"] == "SE" and ga(5, 6, 10)["RIE"] == 0 and ga(5, 6, 10)["RSE"] == pytest.approx(20)
    assert ga(25, 2, 60)["mech"] == "IE" and ga(25, 2, 60)["RSE"] == 0
    assert ga(5, 1, 120)["mech"] == "none"
    grid = run_js("MAP_I.map(function(i){return MAP_D.map(function(d){return mapCell(i,d,2).mech;});})")
    assert any(m == "IE" for col in grid for m in col) and any(m == "SE" for col in grid for m in col) and any(m == "none" for col in grid for m in col)
    for ci, col in enumerate(grid):
        if [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60][ci] <= KS:
            assert "IE" not in col                                         # the column at or below Ks has no IE


def test_map_cells_agree_with_an_independent_classification():
    grid = run_js("MAP_I.map(function(i){return MAP_D.map(function(d){return mapCell(i,d,2);});})")
    for ci, i in enumerate(range(5, 61, 5)):
        for ri, d in enumerate(range(10, 121, 10)):
            F, rie, rse = simulate(i, 2, d, dt=2e-4)
            tot = rie + rse
            want = "none" if tot < 0.5 else ("IE" if rie >= rse else "SE")
            got = grid[ci][ri]
            if abs(tot - 0.5) > 0.15 and abs(rie - rse) > 0.3:             # away from the labelling thresholds
                assert got["mech"] == want, (i, d, got, rie, rse)


# ── hillslope ───────────────────────────────────────────────────────────────────────────────
def test_hillslope_matches_closed_form_and_saturation_grows_with_storm_depth():
    k = np.arange(20)
    Dk = 4.0 + 76.0 * (1.0 - k / 19.0) ** 1.5
    assert Dk[0] == 80.0 and Dk[-1] == 4.0 and np.all(np.diff(Dk) < 0)
    fr_prev = {False: -1.0, True: -1.0}
    for P in range(0, 101, 5):
        for wet in (False, True):
            h = run_js(f"hillRun({P},{'true' if wet else 'false'})")
            Dw = np.maximum(2.0, Dk - 20.0) if wet else Dk
            assert np.allclose([c["D"] for c in h["cols"]], Dw, atol=1e-12)
            assert np.allclose([c["F"] for c in h["cols"]], np.minimum(P, Dw), atol=1e-9)
            assert np.allclose([c["RSE"] for c in h["cols"]], np.maximum(P - Dw, 0), atol=1e-9)
            assert all(c["RIE"] == 0 for c in h["cols"])                  # 8 mm/h < Ks
            assert h["satCount"] == int((P >= Dw - 1e-9).sum())
            assert h["satFrac"] >= fr_prev[wet]                           # non-decreasing with storm depth
            fr_prev[wet] = h["satFrac"]
    base = run_js("hillRun(30,false)")["satFrac"]
    assert run_js("hillRun(30,true)")["satFrac"] > base                   # a wetter start enlarges the saturated area
    # saturation begins at the stream end (the smallest deficit)
    h = run_js("hillRun(30,false)")
    flags = [c["sat"] for c in h["cols"]]
    assert flags == sorted(flags) and flags[-1] and not flags[0]


# ── the three Python cells run and agree with the page's JS ────────────────────────────────
def syn_source(i, Tend, Dd, P, wet):
    js = LH_JS + CORE + CORE2.replace("PY_LH", "PY_LH") + f"\nconsole.log(JSON.stringify(buildSynSource({i},{Tend},{Dd},{P},{'true' if wet else 'false'})));"
    js = f"var PY_LH={LH_PY};\n" + js
    return run_node(js)


DUMP_SYN = """
import json
print("JSON" + json.dumps({"tp": tp, "Fp": Fp, "tD": tD, "F": F, "RIE": RIE, "RSE": RSE, "resid": resid, "sat": int(sat.sum()),
  "meanRSE": float(RSEH.mean()), "meanRIE": float(RIEH.mean()), "DH": [float(x) for x in DH], "FH": [float(x) for x in FH]}))
"""


@pytest.mark.parametrize("state", [(25, 2, 60, 30, False), (5, 6, 10, 60, True), (40, 1, 120, 100, False), (12, 3, 25, 5, True), (8, 6, 10, 0, False), (60, 6, 15, 95, True)])
def test_synthetic_cell_equals_the_js_models_to_1e_6(state):
    i, Tend, Dd, P, wet = state
    out = run_python(syn_source(i, Tend, Dd, P, wet) + DUMP_SYN)
    py = json.loads(out.split("JSON", 1)[1])
    js = ga(i, Tend, Dd)
    h = run_js(f"hillRun({P},{'true' if wet else 'false'})")
    for k in ("tp", "Fp", "F", "RIE", "RSE"):
        want = js[k]
        if want is None:
            assert py[k] is None
        else:
            assert py[k] == pytest.approx(want, abs=1e-6, rel=1e-9), k
    assert abs(py["resid"]) < 1e-9
    assert py["sat"] == h["satCount"]
    assert py["meanRSE"] == pytest.approx(h["meanRSE"], abs=1e-6) and py["meanRIE"] == pytest.approx(h["meanRIE"], abs=1e-6)
    assert np.allclose(py["DH"], [c["D"] for c in h["cols"]], atol=1e-9) and np.allclose(py["FH"], [c["F"] for c in h["cols"]], atol=1e-9)
    # the printed lines carry the same numbers
    m = re.search(r"stored F\s+: ([0-9.]+) mm", out)
    assert float(m.group(1)) == pytest.approx(js["F"], abs=6e-4)
    assert re.search(rf"saturated columns\s+: {h['satCount']} of 20", out)


def test_default_synthetic_cell_prints_the_numbers_the_text_and_quiz_use():
    txt = (MODULES / MOD / "static" / "column-hillslope.txt").read_text()
    r = ga(25, 2, 60)
    assert f"tp = {r['tp'] * 60:.2f} min" in txt and "48.00 min" in txt
    assert f"R_IE             : {r['RIE']:.3f} mm" in txt and "R_SE             : 0.000 mm" in txt
    assert "saturated columns      : 10 of 20" in txt and "mean R_IE              : 0.00 mm" in txt


def independent_events(b, thr_h=1000):
    """Event detection written differently from the page: array scans, no shared helpers."""
    P = np.array(b["prcp_hundredths_mm"], dtype=np.int64)
    q = np.array(b["q_cfs"], dtype=float)
    f = CFS * 86400.0 / (b["area_km2"] * 1e6) * 1000.0
    sys.path.insert(0, str(SHARED))
    from lyne_hollick import lyne_hollick
    base = np.array(lyne_hollick(q.tolist(), 0.925)) * f
    qmm = q * f
    n = len(P)
    big = np.flatnonzero(P >= thr_h)
    starts = [int(d) for d in big if d >= 7 and P[d - 1] < 100 and P[d - 2] < 100]
    ev = []
    for idx, d in enumerate(starts):
        last = d + 9
        if idx + 1 < len(starts):
            last = min(last, starts[idx + 1] - 1)
        last = min(last, n - 1)
        run = 0
        while d + run <= last and P[d + run] >= 100:
            run += 1
        pe = P[d:d + run].sum() / 100.0
        qf = float((qmm[d:last + 1] - base[d:last + 1]).sum())
        ev.append(dict(d=d, end=last, P=pe, ant=P[d - 7:d].sum() / 100.0, qf=qf, rc=qf / pe))
    return ev


def rank_avg(a):
    a = np.asarray(a, dtype=float)
    order = np.argsort(a, kind="stable")
    r = np.empty(len(a))
    i = 0
    while i < len(a):
        j = i
        while j + 1 < len(a) and a[order[j + 1]] == a[order[i]]:
            j += 1
        r[order[i:j + 1]] = (i + j) / 2 + 1
        i = j + 1
    return r


def js_events(g, thr=None):
    arg = f", {thr}" if thr else ""
    js = LH_JS + CORE + f"\nvar B = {json.dumps(BLOB['basins'][g])};\nvar s = eventStats(B{arg});\nconsole.log(JSON.stringify(s));"
    return run_node(js)


@pytest.mark.parametrize("g", GIDS)
def test_event_detector_agrees_between_python_and_js(g):
    b = BLOB["basins"][g]
    ev = independent_events(b)
    s = js_events(g)
    assert s["n"] == len(ev) and len(ev) > 20
    for a, e in zip(s["events"], ev):
        assert (a["d"], a["end"]) == (e["d"], e["end"])
        assert a["P"] == pytest.approx(e["P"], abs=1e-9) and a["ant"] == pytest.approx(e["ant"], abs=1e-9)
        assert a["qf"] == pytest.approx(e["qf"], abs=1e-9) and a["rc"] == pytest.approx(e["rc"], abs=1e-9)
        assert e["qf"] >= -1e-9
    rc = np.array([e["rc"] for e in ev]); ant = np.array([e["ant"] for e in ev])
    assert s["medianRC"] == pytest.approx(float(np.median(rc)), abs=1e-9)
    assert s["medAnt"] == pytest.approx(float(np.median(ant)), abs=1e-9)
    wet = ant > np.median(ant)
    assert s["wetN"] == int(wet.sum()) and s["dryN"] == int((~wet).sum())
    assert s["wetMedian"] == pytest.approx(float(np.median(rc[wet])), abs=1e-9)
    assert s["dryMedian"] == pytest.approx(float(np.median(rc[~wet])), abs=1e-9)
    rho = float(np.corrcoef(rank_avg(ant), rank_avg(rc))[0, 1])
    assert s["rho"] == pytest.approx(rho, abs=1e-9)
    P = np.array(b["prcp_hundredths_mm"]) / 100.0
    assert s["maxP"] == pytest.approx(P.max()) and s["maxRate"] == pytest.approx(P.max() / 24)
    assert s["ksatMmH"] == pytest.approx(b["soil_conductivity_cm_h"] * 10)
    scipy_stats = pytest.importorskip("scipy.stats")
    assert s["rho"] == pytest.approx(float(scipy_stats.spearmanr(ant, rc)[0]), abs=1e-9)


def test_event_rule_is_what_the_text_says_and_estimated_days_are_counted():
    for g in GIDS:
        est = set(BLOB["basins"][g]["estimated_idx"])
        s = js_events(g)
        assert s["nEst"] == sum(1 for e in independent_events(BLOB["basins"][g]) if any(t in est for t in range(e["d"], e["end"] + 1)))
        for e in s["events"]:
            assert e["end"] - e["d"] <= 9 and e["d"] >= 7                  # at most 10 days, 7 days of antecedent record
    for stated in ["P ≥ 10 mm after 2 days with P &lt; 1 mm", "for up to 10 days", "α = 0.925", "7 days before the start", "needs 7 earlier days of record"]:
        assert stated in T, stated
    assert re.search(r"EV = \{ THR: 1000, DRY: 100, PRE: 2, WIN: 10, ANT: 7 \}", CORE)


@pytest.mark.parametrize("g", GIDS)
def test_event_cell_equals_the_js_numbers(g):
    js = LH_JS + CORE + f"var PY_LH={LH_PY};\n" + CORE2 + f"\nvar B = {json.dumps(BLOB['basins'][g])};\nconsole.log(JSON.stringify({{src: buildEventSource('{g}', B), s: eventStats(B)}}));"
    out = run_node(js)
    s = out["s"]
    dump = "\nimport json\nprint('JSON' + json.dumps({'n': len(ev), 'med': float(np.median(rc)), 'rho': rho, 'wet': float(np.median(rc[wet])), 'dry': float(np.median(rc[dry])), 'above1': int((rc > 1).sum()), 'est': int(ev_est.sum()), 'maxP': float(p_max), 'rate': float(rate_max), 'ksat': ksat_mmh, 'dates': [e[0] for e in ev], 'rcs': [float(x) for x in rc], 'qp': float(sum_q / sum_p)}))\n"
    res = run_python(out["src"] + dump)
    py = json.loads(res.split("JSON", 1)[1])
    assert py["n"] == s["n"] and py["above1"] == s["nAbove1"] and py["est"] == s["nEst"]
    assert py["med"] == pytest.approx(s["medianRC"], abs=1e-6) and py["rho"] == pytest.approx(s["rho"], abs=1e-6)
    assert py["wet"] == pytest.approx(s["wetMedian"], abs=1e-6) and py["dry"] == pytest.approx(s["dryMedian"], abs=1e-6)
    assert py["maxP"] == pytest.approx(s["maxP"]) and py["rate"] == pytest.approx(s["maxRate"]) and py["ksat"] == pytest.approx(s["ksatMmH"])
    assert py["qp"] == pytest.approx(s["sumQ"] / s["sumP"], abs=1e-9)
    assert py["dates"] == [e["d"] for e in s["events"]]
    assert np.allclose(py["rcs"], [e["rc"] for e in s["events"]], atol=1e-6)
    assert f"Events         : N = {s['n']} " in res and f"Median RC      : {s['medianRC']:.3f}" in res
    assert f"rho(antecedent rain, RC) = {s['rho']:.2f}" in res
    assert f"{s['maxP']:.2f} mm on {s['maxPday']}" in res
    assert "sha256" in res and "A:e" in res


def test_default_event_cell_output_is_the_siletz_numbers_in_the_page():
    txt = (MODULES / MOD / "static" / "event-runoff-ratios.txt").read_text()
    s = js_events("14305500")
    assert f"N = {s['n']} " in txt and f"{s['medianRC']:.3f}" in txt
    assert "Q/P = 1.064" in txt                                             # the Daymet/gauge balance is shown, not hidden


def test_cells_declare_their_status_and_use_only_numpy_and_matplotlib():
    for cid, src in [("column-hillslope", syn_source(25, 2, 60, 30, False))]:
        assert "SYNTHETIC" in src
        imports = set(re.findall(r"^\s*(?:import|from)\s+([a-zA-Z_]+)", src, re.M))
        assert imports <= {"numpy", "matplotlib", "math", "json", "datetime"}, imports
    out = run_node(LH_JS + CORE + f"var PY_LH={LH_PY};\n" + CORE2 + f"\nvar B = {json.dumps(BLOB['basins']['14305500'])};\nconsole.log(JSON.stringify(buildEventSource('14305500', B)));")
    assert "REAL DATA" in out
    assert set(re.findall(r"^\s*(?:import|from)\s+([a-zA-Z_]+)", out, re.M)) <= {"numpy", "matplotlib", "math", "datetime"}
    assert out.count("plt.subplots") == 1


# ── checkpoint ──────────────────────────────────────────────────────────────────────────────
def test_quiz_answers_recomputed_independently():
    q1 = quiz_item(MOD, "q1")
    r = simulate(5, 6, 10)
    assert r[1] == pytest.approx(0, abs=1e-9) and r[2] == pytest.approx(20, abs=0.05)
    assert q1["expected"] == 1 and "5 mm/h" in q1["prompt"] and "D = 10 mm" in q1["prompt"]
    assert quiz_item(MOD, "q2")["expected"] == pytest.approx(tp_ml(25) * 60, abs=1e-9) and abs(tp_ml(25) * 60 - 48.0) < 1e-12
    F, rie, rse = simulate(25, 2, 60)
    assert quiz_item(MOD, "q3")["expected"] == pytest.approx(rie, abs=0.05) and rse == 0
    # q4: more rain saturates more columns
    sat = lambda P: float(np.mean(P >= (4.0 + 76.0 * (1.0 - np.arange(20) / 19.0) ** 1.5) - 1e-9))
    assert sat(40) > sat(30) > sat(20)
    assert quiz_item(MOD, "q4")["expected"] == 1 and f"{round(100 * sat(30))}%" in quiz_item(MOD, "q4")["prompt"]
    medians = {g: float(np.median([e["rc"] for e in independent_events(BLOB["basins"][g])])) for g in GIDS}
    assert quiz_item(MOD, "q5")["expected"] == pytest.approx(medians["14305500"], abs=1e-9)
    best = max(GIDS, key=lambda g: medians[g])
    q6 = quiz_item(MOD, "q6")
    assert q6["expected"] == GIDS.index(best) and q6["options"] == [BLOB["basins"][g]["name"] for g in GIDS]
    assert quiz_item(MOD, "q7")["expected"] == 1


def test_quiz_shape_and_feedback_never_names_the_right_answer():
    src = T
    items = re.findall(r"\{ id: 'q\d', type: '(choice|numeric)'", src)
    assert len(items) >= 4 and items.count("choice") >= 3 and items.count("numeric") >= 1
    for m in re.finditer(r"type: 'numeric'.*?answer: ([^,}]+)", src, re.S):
        assert not re.match(r"[-+]?[0-9.]", m.group(1).strip())             # numeric answers are functions of the lesson
    q1 = quiz_item(MOD, "q1")
    assert q1["options"][1] == "Saturation excess"
    block = src[src.index("window.__rgQuiz"):]
    for fb in re.findall(r"feedback: \[(.*?)\],\n\s+explain", block, re.S):
        assert "Saturation excess" not in fb and "saturation excess" not in fb.lower().replace("saturation excess runoff", "")


# ── text, honesty, embargo ──────────────────────────────────────────────────────────────────
def prose():
    body = T[T.index("<main>"):T.index('<script type="application/json" id="runoff-events">')]
    return re.sub(r"<[^>]+>", " ", body)


def test_stated_model_constants_match_the_core():
    consts = run_js("{KS:KS,PSI:PSI,DTH:DTH,M:M,DEF:DEF,HILL:HILL,MAPI:MAP_I,MAPD:MAP_D}")
    assert (consts["KS"], consts["PSI"], consts["DTH"], consts["M"]) == (10, 100, 0.30, 30.0)
    assert consts["DEF"] == {"i": 25, "T": 2, "D": 60} and consts["HILL"]["N"] == 20 and consts["HILL"]["I"] == 8
    text = prose()
    for stated in ["K s = 10 mm/h", "ψ = 100 mm", "Δθ = 0.30", "ψΔθ = 30 mm", "8 mm/h", "20 columns", "0.5 mm"]:
        assert re.sub(r"\s+", "", stated) in re.sub(r"\s+", "", text), stated
    for stated in ['data-value="25"', 'data-value="2"', 'data-value="60"', 'data-value="30"']:
        assert stated in T


def test_status_labels_and_no_gauge_ids_in_synthetic_sections():
    assert "SYNTHETIC" in T
    sec = T[T.index('id="sec-intro"'):T.index('id="sec-real"')]
    assert sec.count("SYNTHETIC") >= 5
    assert not re.search(r"\b\d{8}\b", sec), "synthetic sections must not carry 8-digit gauge ids"
    for h in re.findall(r"<h2>(\d · [^<]*)<span class=\"badge (syn|real)\">", T):
        assert h[1] in ("syn", "real")
    assert 'badge real">REAL' in T and "§6" in T


def test_embargo_and_scope_lint():
    text = prose() + " " + T
    assert not re.search(r"(CAMELS|Addor|p_mean|frac_snow|high_prec)[^.<]{0,120}(wrong|error|incorrect|mistake|bias|overestimat|underestimat)", text, re.I)
    assert "slope_fdc" not in T and "slope_fdc" not in (D / "runoff-events.json").read_text()
    for banned in ["25400/CN", "curve number", "Curve Number", "rational method", "Rational method", "D8", "rational-method"]:
        assert banned not in prose(), banned
    for banned in ["threshold CAMELS", "CAMELS used", "CAMELS defines frac_snow", "CAMELS is wrong"]:
        assert banned not in T, banned
    assert "pet_mean" not in T and "modelOutput" not in T


def test_every_doi_is_the_verified_one_and_ledger_rows_exist():
    gate = (ROOT / "CITATIONS.verified.md").read_text()
    sec = gate[gate.index("### runoff-generation"):]
    sec = sec[:sec.index("\n## ", 1)] if "\n## " in sec[1:] else sec
    passed = set(re.findall(r"\| (10\.[^ |]+) \| PASS \|", sec))
    dois = {d.rstrip(".") for d in re.findall(r"10\.\d{4,}/[A-Za-z0-9._;()/:-]+[A-Za-z0-9)]", T)}
    own = {"10.1029/TR014i001p00446", "10.1029/WR006i005p01296", "10.1017/S0021859600001441", "10.1029/WR009i002p00384",
           "10.1016/j.jhydrol.2006.06.008", "10.1623/hysj.52.5.843", "10.1029/WR020i006p00682", "10.1016/S0022-1694(96)03128-9"}
    assert own <= dois and own <= passed, own - passed
    assert "10.1016/j.jhydrol.2006.03.006" not in T                     # that DOI is a different paper (Arp et al.)
    for d in dois - own:
        assert d.lower() in gate.lower(), d                              # earlier-verified DOIs (CAMELS, baseflow, Beven & Kirkby)
    assert "Merz" in T and "Blume" in T and "Cosby" in T
    for no_doi in ["FAO", "Budyko", "Fu (1981)", "Fu, B"]:
        assert no_doi not in T


def test_manifest_is_the_planned_one():
    man = json.loads((MODULES / MOD / "manifest.json").read_text())
    assert man["moduleId"] == MOD and man["license"] == "CC-BY-4.0" and man["courseId"] == "intro-hydro-2026"
    assert man["level"] == "intro" and man["version"] == "0.1.0" and man["courseOrder"] == 4 and man["estimatedMinutes"] == 40
    assert man["requires"] == {"executable": True, "python": ["numpy", "matplotlib"]} and man["topic"] == "runoff-generation"
    assert man["author"] == "Mohammad Galib, Purdue University" and man["createdAt"] == "2026-11-17"
    assert man["downloadUrl"].endswith(f"/modules/{MOD}/module.html") and man["githubUrl"].endswith(f"/modules/{MOD}")
    assert man["citation"]["doi"] == "10.1029/WR006i005p01296"
    assert T.count('class="callout agent"') == 1                              # one labelled agent callout, naming real tools
    for tool in ("fetch_streamflow_data", "fetch_forcing_data", "extract_hydrological_signatures"):
        assert tool in T


def test_alt_text_and_static_outputs():
    alt = json.loads((MODULES / MOD / "static" / "alt.json").read_text())
    assert set(alt) == {"column-hillslope", "event-runoff-ratios"} and all(len(v) >= 20 for v in alt.values())
    idx = json.loads((MODULES / MOD / "static" / "index.json").read_text())
    assert set(idx) == set(alt) and all(v["figures"] == 1 for v in idx.values())
    cells = re.findall(r'<div class="aihydro-cell" data-aihydro-cell-id="([^"]+)"', T)
    assert cells == ["column-hillslope", "event-runoff-ratios"]


# ── the extractor reproduces the committed data (local only) ────────────────────────────────
@pytest.mark.skipif(not os.environ.get("CAMELS_ROOT"), reason="needs a local CAMELS-US copy (set CAMELS_ROOT)")
def test_extractor_reproduces_the_bundled_data_byte_for_byte():
    with tempfile.TemporaryDirectory() as td:
        r = subprocess.run([sys.executable, "-s", "-E", str(ROOT / "scripts" / "extract_camels.py"), "--camels-root", os.environ["CAMELS_ROOT"],
                            "--repo", td, "--only", MOD, "--extracted-on", "2026-11-17"], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        for name in ("runoff-events.json", "PROVENANCE.json"):
            assert (Path(td) / "modules" / MOD / "data" / name).read_bytes() == (D / name).read_bytes(), name
