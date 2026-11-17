"""precipitation-point-to-basin: the SYNTHETIC field of §2 and the real-record arithmetic of §3-§6 are recomputed here
independently of the page (explicit loops and numpy, not the page's code), the two Python cells are run headless and
their printed numbers compared with the page's JavaScript CORE, and the data, provenance, wording and size rules hold."""
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import zipfile
from decimal import Decimal
from pathlib import Path

import numpy as np
import pytest

from helpers import MODULES, ROOT, core_block, extract_dois, json_blob, module_text, quiz_item, run_node, run_python

MOD = "precipitation-point-to-basin"
T = module_text(MOD)
DATA = json_blob(T, "precip-data")
PROV = json.loads((MODULES / MOD / "data" / "PROVENANCE.json").read_text())
GAUGES = ["01013500", "02472000", "09484000", "14305500"]
CAMELS_ROOT = os.environ.get("CAMELS_ROOT")
START = DATA["daily_start"]


# ── helpers: evaluate the page's CORE / CORE2 blocks under node ──────────────────────────────
def node(expr: str):
    js = core_block(T) + core_block(T, "CORE2") + "\nvar DATA = %s;\n" % json.dumps(DATA) + expr
    return run_node(js)


CONST = node("console.log(JSON.stringify({poly: BASIN_POLY, field: FIELD, sites: GAUGE_SITES, n: GRID_N}));")


def synth(active, p):
    """Independent recomputation of the §2 field and the three estimates (loops, no shared code)."""
    N, poly, F = CONST["n"], CONST["poly"], CONST["field"]

    def inside(x, y):                                   # winding-free ray cast written out differently from the page
        crossings = 0
        for i in range(len(poly)):
            (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
            if min(y1, y2) <= y < max(y1, y2):
                if x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
                    crossings += 1
        return crossings % 2 == 1

    def val(x, y):
        return F["background"] + F["gradient"] * x + F["stormAmp"] * math.exp(-((x - F["stormX"]) ** 2 + (y - F["stormY"]) ** 2) / (2 * F["stormSigma"] ** 2))

    cells = [(i, j) for j in range(N) for i in range(N) if inside(i + 0.5, j + 0.5)]
    sites = [s for s in CONST["sites"] if s["id"] in active]
    reads = [val(s["ix"] + 0.5, s["iy"] + 0.5) for s in sites]
    true = sum(val(i + 0.5, j + 0.5) for i, j in cells) / len(cells)
    counts = [0] * len(sites)
    idw_total = 0.0
    for i, j in cells:
        d = [math.hypot(i - s["ix"], j - s["iy"]) for s in sites]      # cell centre minus gauge centre = index difference
        counts[d.index(min(d))] += 1                                   # nearest gauge, first one on a tie
        if min(d) == 0:
            idw_total += reads[d.index(0.0)]
        else:
            w = [x ** -p for x in d]
            idw_total += sum(a * b for a, b in zip(w, reads)) / sum(w)
    weights = [c / len(cells) for c in counts]
    return {"n": len(cells), "true": true, "arith": sum(reads) / len(reads), "thiessen": sum(w * r for w, r in zip(weights, reads)),
            "idw": idw_total / len(cells), "weights": weights, "reads": reads}


NETWORKS = [
    (["G1", "G2", "G3", "G4", "G5", "G6"], 2),
    (["G1", "G2", "G3", "G5", "G6"], 2),
    (["G1", "G3", "G5"], 3.5),
    (["G4"], 1),
    (["G2", "G4", "G5", "G6"], 4),
]


# ── data, provenance, size ───────────────────────────────────────────────────────────────────
def test_provenance_members_hashes_lengths_and_citations():
    assert PROV["module"] == MOD and PROV["extraction_script"] == "scripts/extract_camels.py"
    assert any("10.5194/hess-19-209-2015" in c for c in PROV["citations"]) and any("10.5194/hess-21-5293-2017" in c for c in PROV["citations"])
    assert set(PROV["series"]) == set(GAUGES) == set(DATA["basins"])
    for g, s in PROV["series"].items():
        b = DATA["basins"][g]
        assert s["forcing_source_member"].startswith("basin_dataset_public_v1p2/basin_mean_forcing/daymet/")
        assert s["forcing_source_member"] == b["source_member"] and s["forcing_source_member_sha256"] == b["source_sha256"]
        assert re.fullmatch(r"[0-9a-f]{64}", s["forcing_source_member_sha256"])
        h = b["prcp_hundredths_mm"]
        assert s["n_days"] == len(h) == DATA["daily_n"] == 1827
        assert all(isinstance(v, int) and v >= 0 for v in h)
        assert s["n_wet_days_with_tmean"] == len(b["tmean_halfdeg_bin_on_wet_days"]) == sum(1 for v in h if v > 0)
        assert s["n_months"] == len(b["monthly_hundredths_mm"]) == 240 == len(DATA["monthly_days"])
        assert sum(b["monthly_hundredths_mm"]) > 0 and sum(DATA["monthly_days"]) == 7305
    assert PROV["extracted_on"] == "2026-11-17"
    for name in ("camels_name.txt", "camels_topo.txt", "camels_clim.txt"):
        assert re.fullmatch(r"[0-9a-f]{64}", PROV["camels_root_relative_sources"]["attribute_files"][name]["sha256"])


def test_inlined_blob_is_the_data_file_and_budgets_hold():
    on_disk = json.loads((MODULES / MOD / "data" / "precip-data.json").read_text())
    assert on_disk == DATA
    total = sum(p.stat().st_size for p in (MODULES / MOD / "data").iterdir())
    assert total < 55_000, total
    assert len(T.encode()) < 200_000, len(T.encode())
    assert all((MODULES / MOD / "static" / f"{c}.png").stat().st_size <= 26_000 for c in ("areal-precip", "precip-climate"))


def test_blob_values_are_consistent_with_themselves():
    """Daily and monthly totals describe the same record: the last five water years of the monthly series equal the daily sums."""
    md = np.array(DATA["monthly_days"])
    for g, b in DATA["basins"].items():
        h = np.array(b["prcp_hundredths_mm"])
        monthly = np.array(b["monthly_hundredths_mm"])
        assert monthly.reshape(20, 12)[6:11].sum() == h.sum(), g                # WY1996-2000 are rows 6..10 of WY1990-2009
        assert (np.array(b["tmean_halfdeg_bin_on_wet_days"]).min() > -80) and (np.array(b["tmean_halfdeg_bin_on_wet_days"]).max() < 90)
    assert md.reshape(20, 12)[:, :].sum(axis=1).tolist() == [366 if y in (1992, 1996, 2000, 2004, 2008) else 365 for y in range(1990, 2010)]


# ── §2 · SYNTHETIC field: JS CORE equals an independent recomputation ────────────────────────
@pytest.mark.parametrize("active,p", NETWORKS)
def test_areal_estimates_match_independent_recomputation(active, p):
    js = node("var e = arealEstimates(%s, %s); console.log(JSON.stringify({n: e.nCells, true: e.trueMean, arith: e.arithmetic, th: e.thiessen, idw: e.idw, w: e.weights, r: e.readings, closest: e.closest, diff: e.diff}));" % (json.dumps(active), p))
    ref = synth(active, p)
    assert js["n"] == ref["n"] == 1942
    for k_js, k_ref in [("true", "true"), ("arith", "arith"), ("th", "thiessen"), ("idw", "idw")]:
        assert js[k_js] == pytest.approx(ref[k_ref], abs=1e-9), k_js
    assert js["w"] == pytest.approx(ref["weights"], abs=1e-12) and js["r"] == pytest.approx(ref["reads"], abs=1e-9)
    assert sum(js["w"]) == pytest.approx(1.0, abs=1e-12)                       # Thiessen weights sum to 1
    assert js["arith"] == pytest.approx(sum(js["r"]) / len(js["r"]), abs=1e-12)  # arithmetic = gauge mean
    diffs = {"arithmetic": js["arith"] - js["true"], "thiessen": js["th"] - js["true"], "idw": js["idw"] - js["true"]}
    assert js["closest"] == min(diffs, key=lambda k: abs(diffs[k]))
    for k in diffs:
        assert js["diff"][k] == pytest.approx(diffs[k], abs=1e-12)


def test_idw_at_a_gauge_cell_is_the_gauge_value_and_thiessen_cells_belong_to_the_nearest_gauge():
    out = node("""var e = arealEstimates(GAUGE_SITES.map(function (s) { return s.id; }), 2), res = [];
      GAUGE_SITES.forEach(function (s, k) { res.push([e.surface[s.iy * GRID_N + s.ix], e.readings[k], e.owner[s.iy * GRID_N + s.ix], k]); });
      console.log(JSON.stringify(res));""")
    for surf, read, owner, k in out:
        assert surf == read and owner == k


def test_removing_g4_flips_the_sign_of_all_three_differences_and_the_note_says_exactly_that_much():
    a = node("var e = arealEstimates(['G1','G2','G3','G4','G5','G6'], 2); console.log(JSON.stringify(e.diff));")
    b = node("var e = arealEstimates(['G1','G2','G3','G5','G6'], 2); console.log(JSON.stringify(e.diff));")
    assert all(v > 0 for v in a.values()) and all(v < 0 for v in b.values())
    # G4 reads the highest value, well above every other gauge
    reads = node("console.log(JSON.stringify(GAUGE_SITES.map(function (s) { return [s.id, siteReading(s)]; })));")
    r = dict(reads)
    assert r["G4"] > max(v for k, v in r.items() if k != "G4") + 5


def test_synthetic_section_is_labelled_and_names_no_station_numbers():
    sec = T[T.index('id="sec-areal"'):T.index('id="sec-storms"')]
    assert "SYNTHETIC" in sec
    assert not re.search(r"\b\d{8}\b", re.sub(r"<script.*?</script>", "", sec, flags=re.S)), "no 8-digit station ids in the synthetic section"
    assert "G1" in sec and "G6" in sec


# ── §3-§6 · real records: independent recomputation ──────────────────────────────────────────
def ref_stats(g, snow_t=0.0):
    b = DATA["basins"][g]
    h = np.array(b["prcp_hundredths_mm"], dtype=np.int64)
    n, total = len(h), int(h.sum())
    dates = np.datetime64(START) + np.arange(n)
    months = dates.astype("datetime64[M]")
    starts = np.nonzero((dates == months.astype("datetime64[D]")) & (months.astype(int) % 12 == 9))[0]
    high = h * n >= 5 * total
    by_wy = [int(x.sum()) for x in np.split(high, starts[1:])]
    run = best = 0
    for v in h:
        run = run + 1 if v < 100 else 0
        best = max(best, run)
    tb = np.array(b["tmean_halfdeg_bin_on_wet_days"])
    mon = np.array(b["monthly_hundredths_mm"])
    imax = int(h.argmax())
    return {
        "mean5": total / 100 / n, "wet": float((h >= 100).mean()), "high": int(high.sum()), "high_py": high.sum() / len(by_wy), "by_wy": by_wy, "thr_mm": 5 * total / 100 / n,
        "dry": best, "max_mm": h[imax] / 100, "max_date": str(dates[imax]), "snow": h[h > 0][tb < 2 * snow_t].sum() / total,
        "pmean20": mon.sum() / 100 / sum(DATA["monthly_days"]),
        "djf": mon.reshape(20, 12)[:, [2, 3, 4]].sum() / mon.sum(), "jja": mon.reshape(20, 12)[:, [8, 9, 10]].sum() / mon.sum(),
        "annual": mon.sum() / 100 / 20, "month_means": (mon.reshape(20, 12).sum(axis=0) / 100 / 20).tolist(),
    }


@pytest.mark.parametrize("g", GAUGES)
def test_basin_stats_match_independent_recomputation(g):
    for snow_t in (-2, 0, 1.5, 3):
        js = node("console.log(JSON.stringify(basinStats(DATA.basins['%s'], DATA.daily_start, DATA.monthly_days, %s)));" % (g, snow_t))
        ref = ref_stats(g, snow_t)
        assert js["meanP5"] == pytest.approx(ref["mean5"], abs=1e-12) and js["wetFrac"] == pytest.approx(ref["wet"], abs=1e-12)
        assert js["highCount"] == ref["high"] and js["highPerYear"] == pytest.approx(ref["high_py"]) and js["highByWY"] == ref["by_wy"]
        assert js["highThresholdMm"] == pytest.approx(ref["thr_mm"], abs=1e-12)
        assert js["dryMax"] == ref["dry"] and js["maxMm"] == ref["max_mm"] and js["maxDate"] == ref["max_date"]
        assert js["snow"] == pytest.approx(ref["snow"], abs=1e-12)
        assert js["pMean20"] == pytest.approx(ref["pmean20"], abs=1e-12) and js["annualMm"] == pytest.approx(ref["annual"], abs=1e-9)
        assert js["djf"] == pytest.approx(ref["djf"], abs=1e-12) and js["jja"] == pytest.approx(ref["jja"], abs=1e-12)


def test_water_years_are_366_365_365_365_366_and_snow_fraction_never_falls_as_the_threshold_rises():
    assert node("console.log(JSON.stringify(wyLengths(DATA.daily_start, 1827)));") == [366, 365, 365, 365, 366]
    grid = [x / 2 for x in range(-4, 7)]
    for g in GAUGES:
        vals = node("console.log(JSON.stringify(%s.map(function (t) { return snowFraction(DATA.basins['%s'].prcp_hundredths_mm, DATA.basins['%s'].tmean_halfdeg_bin_on_wet_days, t); })));" % (json.dumps(grid), g, g))
        assert all(b >= a for a, b in zip(vals, vals[1:])), g
        assert 0 <= vals[0] <= vals[-1] <= 1


def test_reproduction_check_p_mean_within_1e_3_and_high_prec_freq_difference_is_a_period_effect():
    for g in GAUGES:
        s = ref_stats(g)
        c = DATA["basins"][g]["camels"]
        assert abs(s["pmean20"] - c["p_mean_mm_day"]) < 1e-3, g
        assert abs(s["high_py"] - c["high_prec_freq_days_per_year"]) < 3, g
    # the note's numbers are computed by the page: re-derive them
    allwy = [x for g in GAUGES for x in ref_stats(g)["by_wy"]]
    dmax = max(abs(ref_stats(g)["pmean20"] - DATA["basins"][g]["camels"]["p_mean_mm_day"]) for g in GAUGES)
    hmax = max(abs(ref_stats(g)["high_py"] - DATA["basins"][g]["camels"]["high_prec_freq_days_per_year"]) for g in GAUGES)
    note = run_page_note("reproNote")
    assert f"within {dmax:.6f} mm/day" in note and f"is {hmax:.1f} days per year" in note
    assert f"range from {min(allwy)} to {max(allwy)} days" in note
    assert "period, not the data, differs" in note


def run_page_note(element_id: str) -> str:
    js = (ROOT / "tests" / "js" / "fakedom.js").as_posix()
    code = f"""const {{run}} = require({json.dumps(js)}); const fs = require('fs');
      const html = fs.readFileSync({json.dumps((MODULES / MOD / 'module.html').as_posix())}, 'utf8');
      const {{els}} = run(html); console.log(JSON.stringify(els[{json.dumps(element_id)}].textContent));"""
    return run_node(code)


def test_page_notes_state_numbers_the_page_computes():
    storm = run_page_note("stormNote")
    stats = {g: ref_stats(g) for g in GAUGES}
    most = max(GAUGES, key=lambda g: stats[g]["high_py"])
    longest = max(GAUGES, key=lambda g: stats[g]["dry"])
    assert f"({stats[most]['high_py']:.1f})" in storm and f"({stats[longest]['dry']} days)" in storm
    season = run_page_note("seasonNote")
    bd = max(GAUGES, key=lambda g: stats[g]["djf"])
    assert f"{100 * stats[bd]['djf']:.1f} %" in season
    note = run_page_note("arealNote")
    a, b = synth(["G1", "G2", "G3", "G4", "G5", "G6"], 2), synth(["G1", "G2", "G3", "G5", "G6"], 2)
    sg = lambda x: ("+" if x >= 0 else "-") + f"{abs(x):.2f}"
    assert ", ".join([sg(a["arith"] - a["true"]), sg(a["thiessen"] - a["true"])]) in note and sg(a["idw"] - a["true"]) in note
    assert sg(b["arith"] - b["true"]) in note and sg(b["thiessen"] - b["true"]) in note and sg(b["idw"] - b["true"]) in note
    gauge = run_page_note("gaugeRatio")
    area = DATA["basins"]["02472000"]["area_km2"] * 1e6
    funnel = math.pi * 0.1 ** 2

    def jsexp(v):
        m, e = f"{v:.2e}".split("e")
        return f"{m}e{'+' if int(e) >= 0 else '-'}{abs(int(e))}"
    assert f"{funnel:.4f} m" in gauge and jsexp(area) in gauge and jsexp(funnel / area) in gauge and f"{DATA['basins']['02472000']['area_km2']:.2f} km" in gauge


# ── the checkpoint: every answer recomputed independently ───────────────────────────────────
def test_quiz_answers_are_the_independent_values():
    d = synth(["G1", "G2", "G3", "G4", "G5", "G6"], 2)
    errs = [abs(d["arith"] - d["true"]), abs(d["thiessen"] - d["true"]), abs(d["idw"] - d["true"])]
    assert quiz_item(MOD, "q2")["expected"] == errs.index(min(errs))
    assert sorted(errs)[1] - sorted(errs)[0] > 0.1, "the closest method is clearly closest, not a coin toss"
    assert f"{d['true']:.2f} mm" in quiz_item(MOD, "q2")["prompt"]
    assert quiz_item(MOD, "q4")["expected"] == pytest.approx(d["thiessen"], abs=1e-9)
    assert quiz_item(MOD, "q5")["expected"] == pytest.approx(ref_stats("02472000")["high_py"], abs=1e-12)
    assert quiz_item(MOD, "q6")["expected"] == pytest.approx(ref_stats("01013500")["snow"], abs=1e-12)
    djf = [ref_stats(g)["djf"] for g in GAUGES]
    assert quiz_item(MOD, "q7")["expected"] == djf.index(max(djf))
    assert quiz_item(MOD, "q1")["expected"] == 1 and quiz_item(MOD, "q3")["expected"] == 1
    # ≥4 items, ≥3 choice, ≥1 numeric
    items = [quiz_item(MOD, f"q{i}") for i in range(1, 8)]
    assert sum(1 for i in items if i["type"] == "choice") == 4 and sum(1 for i in items if i["type"] == "numeric") == 3


# ── the Python cells: run headless, printed numbers equal the JS CORE ───────────────────────
def num(rx, text):
    m = re.search(rx, text)
    assert m, (rx, text[:300])
    return float(m.group(1))


@pytest.mark.parametrize("active,p", NETWORKS)
def test_areal_cell_runs_and_prints_the_core_numbers(active, p):
    src = node("console.log(JSON.stringify(buildArealSource(%s, %s)));" % (json.dumps(active), p))
    out = run_python(src)
    ref = synth(active, p)
    assert num(r"True mean\s+: ([0-9.]+) mm", out) == pytest.approx(ref["true"], abs=6e-3)
    assert num(r"Arithmetic\s+: ([0-9.]+) mm", out) == pytest.approx(ref["arith"], abs=6e-3)
    assert num(r"Thiessen\s+: ([0-9.]+) mm", out) == pytest.approx(ref["thiessen"], abs=6e-3)
    assert num(r"IDW\s+: ([0-9.]+) mm", out) == pytest.approx(ref["idw"], abs=6e-3)
    assert f"({len(active)} of 6)" in out and "SYNTHETIC" in out and "basin = 1942 cells" in out
    for gid, w, r in zip([s for s in ("G1", "G2", "G3", "G4", "G5", "G6") if s in active], ref["weights"], ref["reads"]):
        m = re.search(rf"{gid}: reading\s+([0-9.]+) mm\s+Thiessen weight ([0-9.]+)", out)
        assert m and float(m.group(1)) == pytest.approx(r, abs=0.06) and float(m.group(2)) == pytest.approx(w, abs=6e-4)


@pytest.mark.parametrize("g,snow_t", [("02472000", 0), ("01013500", 0), ("09484000", -1.5), ("14305500", 2.5), ("01013500", 3)])
def test_climate_cell_runs_and_prints_the_core_numbers(g, snow_t):
    src = node("console.log(JSON.stringify(buildClimSource(DATA.basins['%s'], DATA.daily_start, DATA.monthly_days, %s)));" % (g, snow_t))
    out = run_python(src)
    ref = ref_stats(g, snow_t)
    c = DATA["basins"][g]["camels"]
    assert g in out and DATA["basins"][g]["source_sha256"][:16] in out and "Daymet basin mean" in out
    assert num(r"Mean P, 20 WY\s+: ([0-9.]+) mm/day", out) == pytest.approx(ref["pmean20"], abs=6e-5)
    assert num(r"CAMELS p_mean ([0-9.]+)", out) == pytest.approx(c["p_mean_mm_day"], abs=6e-5)
    assert num(r"Wet days \(>=1mm\): ([0-9.]+) %", out) == pytest.approx(100 * ref["wet"], abs=0.06)
    assert num(r"High-P days\s+: ([0-9.]+) per year", out) == pytest.approx(ref["high_py"], abs=0.06)
    assert [int(x) for x in re.search(r"by water year : ([0-9, ]+) days", out).group(1).split(",")] == ref["by_wy"]
    assert int(num(r"Longest dry spell: ([0-9]+) days", out)) == ref["dry"]
    assert num(r"Largest daily P : ([0-9.]+) mm", out) == pytest.approx(ref["max_mm"], abs=6e-3) and ref["max_date"] in out
    assert num(r"Snow fraction\s+: ([0-9.]+) ", out) == pytest.approx(ref["snow"], abs=6e-4)
    assert num(r"CAMELS frac_snow ([0-9.]+)", out) == pytest.approx(c["frac_snow"], abs=6e-4)
    assert num(r"DJF ([0-9.]+) %", out) == pytest.approx(100 * ref["djf"], abs=0.06) and num(r"JJA ([0-9.]+) %", out) == pytest.approx(100 * ref["jja"], abs=0.06)


def test_climate_cell_rejects_a_threshold_the_half_degree_bins_cannot_resolve():
    src = node("console.log(JSON.stringify(buildClimSource(DATA.basins['02472000'], DATA.daily_start, DATA.monthly_days, 0.3)));")
    with pytest.raises(AssertionError):
        run_python(src)


def test_static_outputs_are_the_default_cell_outputs():
    d = ref_stats("02472000", 0)
    txt = (MODULES / MOD / "static" / "precip-climate.txt").read_text()
    assert f"{d['high_py']:.1f} per year" in txt and f"Snow fraction   : {d['snow']:.3f}" in txt
    a = (MODULES / MOD / "static" / "areal-precip.txt").read_text()
    s = synth(["G1", "G2", "G3", "G4", "G5", "G6"], 2)
    assert f"True mean      : {s['true']:.2f} mm" in a and f"Thiessen       : {s['thiessen']:.2f} mm" in a
    alt = json.loads((MODULES / MOD / "static" / "alt.json").read_text())
    assert set(alt) == {"areal-precip", "precip-climate"} and all(len(v) >= 20 for v in alt.values())


# ── wording: embargo, citations, honest labelling ───────────────────────────────────────────
EMBARGO = re.compile(r"(CAMELS|Addor|p_mean|frac_snow|high_prec)[^.<]{0,120}(wrong|error|incorrect|mistake|bias|overestimat|underestimat)", re.I)


def test_embargo_wording_and_no_slope_fdc_anywhere_in_the_lesson():
    files = [MODULES / MOD / "module.html", MODULES / MOD / "README.md", MODULES / MOD / "manifest.json"] + \
            [p for p in (MODULES / MOD / "static").iterdir() if p.suffix in (".txt", ".json")] + [p for p in (MODULES / MOD / "data").iterdir()]
    for p in files:
        text = p.read_text(encoding="utf-8")
        assert not EMBARGO.search(text), (p.name, EMBARGO.search(text).group(0)[:160])
        assert "slope_fdc" not in text, p.name
    log = (ROOT / "CHANGELOG.md").read_text()
    sec = log[log.index("### precipitation-point-to-basin"):log.index("### evapotranspiration-budyko")]
    assert not EMBARGO.search(sec) and "slope_fdc" not in sec
    # the page never says which threshold CAMELS used
    assert not re.search(r"CAMELS[^.<]{0,100}(threshold of|uses? (a|the) threshold|used (a|the) threshold)", T, re.I)


def test_references_are_the_gated_dois_and_the_thiessen_doi_is_not_truncated_by_the_repo_regex():
    gate = (ROOT / "CITATIONS.verified.md").read_text()
    passed = set(re.findall(r"\| (10\.[^ |]+) \| PASS \|", gate))
    for doi in ["10.1175/1520-0493(1911)39<1082b:PAFLA>2.0.CO;2", "10.1145/800186.810616", "10.1016/S0022-1694(96)03128-9", "10.1038/s41467-018-03629-7",
                "10.5194/hess-19-209-2015", "10.5194/hess-21-5293-2017"]:
        assert doi in passed, doi
    seen = extract_dois(T)
    assert {d.lower() for d in seen} <= {p.lower() for p in passed}
    # the Thiessen DOI is shown as written (markup-escaped) and linked with < and > percent-encoded
    assert "10.1175/1520-0493(1911)39%3C1082b:PAFLA%3E2.0.CO;2" in T and "10.1175/1520-0493(1911)39&lt;1082b:PAFLA&gt;2.0.CO;2" in T
    # claims that were dropped or never allowed
    for banned in ("Fu (1981)", "Fu, B.", "10.2307", "Budyko", "FAO-56"):
        assert banned not in T, banned
    assert "Jennings et al. (2018)" in T and "varies across the Northern Hemisphere" in T


def test_manifest_course_slot_and_embedded_manifest():
    man = json.loads((MODULES / MOD / "manifest.json").read_text())
    assert (man["moduleId"], man["version"], man["license"], man["courseId"], man["courseOrder"], man["level"], man["topic"], man["estimatedMinutes"]) == \
           (MOD, "0.1.0", "CC-BY-4.0", "intro-hydro-2026", 2, "intro", "precipitation", 35)
    assert man["requires"] == {"executable": True, "python": ["numpy", "matplotlib"]} and man["author"] == "Mohammad Galib, Purdue University"
    assert man["createdAt"] == "2026-11-17" and "updatedAt" not in man
    assert "v0.1.0 · CC-BY-4.0" in T or "v0.1.0" in T


def test_cell_structure_standalone_run_fallback_and_agent_tools_exist():
    assert T.count('data-aihydro-cell-id="areal-precip"') == 1 and T.count('data-aihydro-cell-id="precip-climate"') == 1
    assert 'id="arealSource"' in T and 'id="climSource"' in T and "aihydro-run" in T and "Open in AI-Hydro to run" in T
    assert T.count('aria-live="polite"') >= 2
    tools = {"delineate_watershed", "fetch_forcing_data"}
    assert all(f"<code>{x}</code>" in T for x in tools)
    mcp = Path("/Users/mgalib/Documents/AI-Hydro/MCP/aihydro-tools/ai_hydro")
    if mcp.exists():
        text = "".join(p.read_text(errors="ignore") for p in (mcp / "mcp").glob("tools_*.py"))
        for t in tools:
            assert re.search(rf"def {t}\(", text), t
    assert not re.search(r"\bunlock\b", T, re.I)


# ── local only: reproduce the data from the CAMELS archive (skipped without CAMELS_ROOT) ─────
@pytest.mark.skipif(not CAMELS_ROOT, reason="set CAMELS_ROOT to re-extract from a local CAMELS-US v1.2 copy")
def test_extractor_reproduces_the_committed_data_and_matches_an_independent_parse(tmp_path):
    r = subprocess.run([sys.executable, "-s", "-E", str(ROOT / "scripts" / "extract_camels.py"), "--camels-root", CAMELS_ROOT, "--repo", str(tmp_path),
                        "--only", MOD, "--extracted-on", "2026-11-17"], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr
    for name in ("precip-data.json", "PROVENANCE.json"):
        assert (tmp_path / "modules" / MOD / "data" / name).read_bytes() == (MODULES / MOD / "data" / name).read_bytes(), name
    zf = zipfile.ZipFile(Path(CAMELS_ROOT) / "basin_timeseries_v1p2_metForcing_obsFlow.zip")      # independent parse of the raw files
    for g, b in DATA["basins"].items():
        raw = zf.read(b["source_member"])
        assert hashlib.sha256(raw).hexdigest() == b["source_sha256"]
        rows = [ln.split() for ln in raw.decode().splitlines()[4:]]
        date = [f"{int(r[0]):04d}-{int(r[1]):02d}-{int(r[2]):02d}" for r in rows]
        p = np.array([float(r[5]) for r in rows])
        tsum = [Decimal(r[8]) + Decimal(r[9]) for r in rows]          # exact decimal arithmetic: tmax + tmin = 2 x mean
        i0, i1 = date.index("1995-10-01"), date.index("2000-09-30") + 1
        daily = p[i0:i1]
        assert (np.round(daily * 100).astype(int) == np.array(b["prcp_hundredths_mm"])).all()
        wet = daily > 0
        wet_sum = [s for s, w in zip(tsum[i0:i1], wet) if w]
        for t in [x / 2 for x in range(-4, 7)]:                                      # the bins reproduce "mean < T" exactly
            tb = np.array(b["tmean_halfdeg_bin_on_wet_days"])
            below = np.array([s < 2 * Decimal(str(t)) for s in wet_sum])               # (tmax + tmin) / 2 < T
            assert (below == (tb < 2 * t)).all(), (g, t)
            assert daily[wet][below].sum() / daily.sum() == pytest.approx(ref_stats(g, t)["snow"], abs=1e-9)
        j0 = date.index("1989-10-01")
        assert p[j0:j0 + 7305].sum() / 7305 == pytest.approx(b["camels"]["p_mean_mm_day"], abs=1e-3)
    # attribute files
    clim = {ln.split(";")[0].zfill(8): ln.split(";") for ln in (Path(CAMELS_ROOT) / "camels_clim.txt").read_text().splitlines()[1:]}
    for g, b in DATA["basins"].items():
        assert float(clim[g][1]) == pytest.approx(b["camels"]["p_mean_mm_day"], abs=1e-6) and float(clim[g][4]) == pytest.approx(b["camels"]["frac_snow"], abs=1e-6)
        assert float(clim[g][6]) == pytest.approx(b["camels"]["high_prec_freq_days_per_year"], abs=1e-4)


def test_numbers_written_in_the_prose_are_the_model_and_data_constants():
    F = CONST["field"]
    assert CONST["n"] == 60 and "A 60 × 60 grid of 1 km cells" in T
    assert f"{F['background']:.0f} mm of background" in T and f"{F['gradient']:.2f} mm per km" in T
    assert f"{F['stormAmp']:.0f} mm at its peak, σ = {F['stormSigma']}" in T
    assert DATA["daily_start"] == "1995-10-01" and DATA["daily_n"] == 1827 and "1 October 1995 to 30 September 2000, 1827 days" in T
    assert (DATA["monthly_first_wy"], DATA["monthly_last_wy"]) == (1990, 2009) and "20 water years (October 1989 to September 2009, 240 months)" in T
    assert 'data-min="-2" data-max="3" data-step="0.5" data-value="0"' in T and 'data-min="1" data-max="4" data-step="0.5" data-value="2"' in T
    assert "1989–2009" in T and "1989-10-01 to 2009-09-30" in T
