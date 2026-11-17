"""evapotranspiration-budyko: provenance, the PET models, the Budyko fit and the wording rules.

Every number the lesson shows is recomputed here from the bundled blob with independent numpy code and
compared with (a) the page's own JavaScript CORE block, (b) the Python cells the page generates, run
headless, and (c) the checkpoint answers the page computes."""
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

from helpers import MODULES, ROOT, core_block, json_blob, module_text, quiz_item, run_node, run_python

MOD = "evapotranspiration-budyko"
D = MODULES / MOD / "data"
T = module_text(MOD)
BLOB = json.loads((D / "et-budyko.json").read_text())
PROV = json.loads((D / "PROVENANCE.json").read_text())
IDS4 = ["01013500", "02472000", "09484000", "14305500"]
PAGE_CAP = 250_000           # the repository cap (test_wave2_repo); the plan target of 200 000 is reported, not asserted
DATA_BUDGET = 65_000


# ── independent numpy implementation (written separately from the page) ─────────────────────────
def decode(g):
    b = BLOB["basins"][g]
    out = {k: np.array(b[k + "_x100"], dtype=float) / 100.0 for k in ("srad", "tmax", "tmin", "vp")}
    out["dayl"] = np.cumsum(np.array(b["dayl_x100"], dtype=float)) / 100.0
    out["lat"], out["elev"] = b["lat"], b["elev_m"]
    start = np.datetime64(BLOB["wy"]["start"])
    dates = start + np.arange(365)
    out["doy"] = np.array([int((d - dates[i].astype("datetime64[Y]").astype("datetime64[D]")).astype(int)) + 1 for i, d in enumerate(dates)])
    return out


def ra(lat, doy):
    phi = math.radians(lat)
    dr = 1 + 0.033 * np.cos(2 * np.pi * doy / 365)
    de = 0.409 * np.sin(2 * np.pi * doy / 365 - 1.39)
    ws = np.arccos(np.clip(-math.tan(phi) * np.tan(de), -1, 1))
    return (24 * 60 / np.pi) * 0.0820 * dr * (ws * math.sin(phi) * np.sin(de) + math.cos(phi) * np.cos(de) * np.sin(ws))


def hargreaves(x):
    r = ra(x["lat"], x["doy"])
    return np.maximum(0, 0.0023 * (r / 2.45) * ((x["tmax"] + x["tmin"]) / 2 + 17.8) * np.sqrt(np.maximum(x["tmax"] - x["tmin"], 0)))


def priestley_taylor(x, alpha):
    r = ra(x["lat"], x["doy"])
    rs = x["srad"] * x["dayl"] / 1e6
    rso = (0.75 + 2e-5 * x["elev"]) * r
    ratio = np.clip(rs / rso, 0.3, 1.0)
    ea = x["vp"] / 1000
    rnl = 4.903e-9 * (((x["tmax"] + 273.16) ** 4 + (x["tmin"] + 273.16) ** 4) / 2) * (0.34 - 0.14 * np.sqrt(ea)) * (1.35 * ratio - 0.35)
    rn = 0.77 * rs - rnl
    tm = (x["tmax"] + x["tmin"]) / 2
    es = 0.6108 * np.exp(17.27 * tm / (tm + 237.3))
    delta = 4098 * es / (tm + 237.3) ** 2
    gamma = 0.000665 * 101.3 * ((293 - 0.0065 * x["elev"]) / 293) ** 5.26
    return np.maximum(0, alpha * delta / (delta + gamma) * rn / 2.45)


def fu(phi, w):
    return 1 + phi - (1 + phi ** w) ** (1 / w)


def sample():
    a = BLOB["all"]
    ids = a["ids"].split(" ")
    keep = [i for i, r in enumerate(a["runoff_ratio"]) if r is not None]
    return (np.array([ids[i] for i in keep]), np.array([a["aridity"][i] for i in keep]),
            np.array([a["runoff_ratio"][i] for i in keep]), np.array([a["frac_snow"][i] for i in keep]))


def fit(phi, ep):
    ws = np.arange(1100, 6001) / 1000.0
    sse = np.array([np.sum((ep - fu(phi, w)) ** 2) for w in ws])
    return float(ws[int(np.argmin(sse))]), float(np.sqrt(sse.min() / len(ep)))


def core_js(*extra):
    return core_block(T, "CORE") + "\n" + core_block(T, "CORE2") + "\n".join(extra)


def jsrun(expr_js):
    """Run the page's CORE/CORE2 blocks with the bundled blob in node; the script prints one JSON value."""
    js = core_js() + "\nvar BLOB=" + json.dumps(BLOB) + ";\n" + expr_js
    return run_node(js)


def page_cell_sources():
    r = subprocess.run(["node", str(ROOT / "scripts" / "cell_sources.js"), str(MODULES / MOD / "module.html")],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def printed(out, label):
    m = re.search(re.escape(label) + r"\s*:\s*([-+0-9.]+)", out)
    assert m, (label, out)
    return float(m.group(1))


# ── provenance and size ────────────────────────────────────────────────────────────────────────
def test_provenance_shape_and_hashes():
    assert PROV["module"] == MOD and PROV["extraction_script"] == "scripts/extract_camels.py"
    assert (ROOT / PROV["extraction_script"]).exists()
    assert any("10.5194/hess-19-209-2015" in c for c in PROV["citations"])
    assert any("10.5194/hess-21-5293-2017" in c for c in PROV["citations"])
    assert set(PROV["series"]) == set(IDS4) == set(BLOB["basins"])
    for g, s in PROV["series"].items():
        assert s["forcing_member"].startswith("basin_dataset_public_v1p2/basin_mean_forcing/daymet/")
        assert s["forcing_member"].endswith(f"/{g}_lump_cida_forcing_leap.txt")
        assert re.fullmatch(r"[0-9a-f]{64}", s["forcing_member_sha256"])
        assert BLOB["basins"][g]["sha256"] == s["forcing_member_sha256"]
        assert s["forcing_member"].split("/")[-2] == BLOB["basins"][g]["huc"]
        assert s["period"] == ["1996-10-01", "1997-09-30"]
        n = s["n_days"]
        assert n == 365 and all(len(BLOB["basins"][g][k + "_x100"]) == n for k in ("dayl", "srad", "tmax", "tmin", "vp"))
    allt = PROV["all_gauges_table"]
    assert allt["n_gauges"] == 671 and len(BLOB["all"]["ids"].split(" ")) == 671
    assert allt["na_runoff_ratio_gauges"] == ["03281100"]
    assert "rounded to 4 decimal places" in allt["rounding"]
    assert "modelOutput" not in json.dumps(PROV).replace("no modelOutput PET is used", "")


def test_data_and_page_sizes_are_within_budget():
    total = sum(f.stat().st_size for f in D.iterdir())
    assert total <= DATA_BUDGET, total
    assert len(T.encode()) < PAGE_CAP, len(T.encode())


def test_blob_is_the_data_file_inlined():
    assert json_blob(T, "et-budyko") == BLOB


def test_integer_encoding_is_lossless_two_decimals_and_dayl_is_delta_coded():
    for g in IDS4:
        b = BLOB["basins"][g]
        assert all(isinstance(v, int) for k in ("dayl", "srad", "tmax", "tmin", "vp") for v in b[k + "_x100"])
        dayl = np.cumsum(b["dayl_x100"]) / 100
        assert 0 < dayl.min() and dayl.max() < 86400          # seconds of daylight
        assert b["vp_x100"] and min(b["vp_x100"]) > 0


# ── PET models: JS CORE, Python cell and independent numpy agree ───────────────────────────────
def test_js_core_matches_independent_numpy_for_both_methods_and_every_basin():
    js = """var out={};
['01013500','02472000','09484000','14305500'].forEach(function(g){
  var b=decodeBasin(BLOB.basins[g],BLOB.wy.start);
  out[g]={hs:hargreavesSeries(b),pt:ptSeries(b,1.26),pt15:ptSeries(b,1.5),ra:b.ra,doy:b.doy,dayl:b.dayl,match:alphaMatching(b,BLOB.course[g].pet_mean)};});
console.log(JSON.stringify(out));"""
    out = jsrun(js)
    for g in IDS4:
        x = decode(g)
        assert np.array(out[g]["doy"]) == pytest.approx(x["doy"])
        assert np.array(out[g]["dayl"]) == pytest.approx(x["dayl"], abs=1e-9)
        assert np.array(out[g]["ra"]) == pytest.approx(ra(x["lat"], x["doy"]), abs=1e-9)
        assert np.array(out[g]["hs"]) == pytest.approx(hargreaves(x), abs=1e-6)
        assert np.array(out[g]["pt"]) == pytest.approx(priestley_taylor(x, 1.26), abs=1e-6)
        assert np.array(out[g]["pt15"]) == pytest.approx(priestley_taylor(x, 1.5), abs=1e-6)
        assert out[g]["match"] == pytest.approx(BLOB["course"][g]["pet_mean"] / priestley_taylor(x, 1.0).mean(), abs=1e-9)


def test_pet_is_non_negative_and_ra_is_physical():
    for g in IDS4:
        x = decode(g)
        assert hargreaves(x).min() >= 0 and priestley_taylor(x, 1.26).min() >= 0
        r = ra(x["lat"], x["doy"])
        assert 0 < r.min() and r.max() < 45                      # MJ m-2 day-1, below the solar-constant limit
        assert 0 < hargreaves(x).mean() < 10 and 0 < priestley_taylor(x, 1.26).mean() < 10


def test_priestley_taylor_is_proportional_to_alpha_so_the_matching_alpha_is_exact():
    for g in IDS4:
        x = decode(g)
        a1, a2 = priestley_taylor(x, 1.0), priestley_taylor(x, 1.37)
        assert a2 == pytest.approx(1.37 * a1, abs=1e-12)
        match = BLOB["course"][g]["pet_mean"] / a1.mean()
        assert priestley_taylor(x, match).mean() == pytest.approx(BLOB["course"][g]["pet_mean"], abs=1e-9)


def test_python_cell_prints_the_numbers_the_javascript_computes_for_every_basin_and_alpha():
    js = """var out={};
['01013500','02472000','09484000','14305500'].forEach(function(g){[1.0,1.26,1.5].forEach(function(a){
  var b=decodeBasin(BLOB.basins[g],BLOB.wy.start);
  out[g+'|'+a]={src:buildPetSource(g,BLOB.basins[g],BLOB.course[g].pet_mean,a,BLOB.wy.start),hs:mean(hargreavesSeries(b)),pt:mean(ptSeries(b,a)),
    hsz:countZero(hargreavesSeries(b)),ptz:countZero(ptSeries(b,a)),match:alphaMatching(b,BLOB.course[g].pet_mean)};});});
console.log(JSON.stringify(out));"""
    out = jsrun(js)
    for key, o in out.items():
        g, a = key.split("|")
        res = run_python(o["src"])
        assert printed(res, "Hargreaves-Samani mean PET") == pytest.approx(o["hs"], abs=6e-4)
        assert printed(res, "Priestley-Taylor mean PET") == pytest.approx(o["pt"], abs=6e-4)
        assert printed(res, "alpha matching pet_mean") == pytest.approx(o["match"], abs=6e-4)
        x = decode(g)
        assert o["hs"] == pytest.approx(hargreaves(x).mean(), abs=1e-6)
        assert o["pt"] == pytest.approx(priestley_taylor(x, float(a)).mean(), abs=1e-6)
        assert f"{o['hsz']} days at 0" in res and f"{o['ptz']} days at 0" in res


def test_cell_arrays_decode_to_the_independent_numpy_series():
    """Exec the generated source's data section and compare with the independent decode."""
    src = page_cell_sources()["petSource"]
    head = src.split("# ─── choices stated on the page")[0]
    ns = {}
    exec(head, ns)                                         # numpy import + the data arrays only
    x = decode("09484000")
    for k, name in (("srad", "SRAD"), ("tmax", "TMAX"), ("tmin", "TMIN"), ("vp", "VP"), ("dayl", "DAYL")):
        assert ns[name] == pytest.approx(x[k], abs=1e-9)
    assert ns["GAUGE"] == "09484000" and ns["SOURCE_SHA256"] == BLOB["basins"]["09484000"]["sha256"]
    assert ns["SOURCE_MEMBER"] == PROV["series"]["09484000"]["forcing_member"]


def test_page_default_cell_source_and_static_output_match():
    srcs = page_cell_sources()
    assert 'GAUGE  = "09484000"' in srcs["petSource"] and re.search(r"^ALPHA  = 1\.26 ", srcs["petSource"], re.M)
    res = run_python(srcs["petSource"])
    shipped = (MODULES / MOD / "static" / "pet-two-ways.txt").read_text()
    assert res == shipped
    assert run_python(srcs["budykoSource"]) == (MODULES / MOD / "static" / "budyko-camels.txt").read_text()


# ── Budyko: counts, the Fu curve, the fit ──────────────────────────────────────────────────────
def test_670_points_and_the_na_gauge_is_named_and_excluded():
    ids, phi, rr, fs = sample()
    assert len(ids) == 670 and "03281100" not in ids
    assert BLOB["all"]["runoff_ratio"][BLOB["all"]["ids"].split(" ").index("03281100")] is None
    assert "03281100" in T and sum(r is None for r in BLOB["all"]["runoff_ratio"]) == 1
    assert len(BLOB["all"]["aridity"]) == len(BLOB["all"]["frac_snow"]) == 671
    assert phi.min() > 0 and 0 <= fs.min() and fs.max() <= 1
    for g in IDS4:                                           # the four course basins agree with the 671-gauge table
        i = list(ids).index(g)
        assert phi[i] == pytest.approx(BLOB["course"][g]["aridity"], abs=5.1e-5)
        assert rr[i] == pytest.approx(BLOB["course"][g]["runoff_ratio"], abs=5.1e-5)
        assert fs[i] == pytest.approx(BLOB["course"][g]["frac_snow"], abs=5.1e-5)


def test_fu_curve_stays_inside_the_limits_and_approaches_them():
    phi = np.concatenate([np.linspace(0.05, 6, 400), [0.226, 1.0, 5.2]])
    for w in (1.1, 1.5, 2.0, 2.383, 4.0, 6.0):
        e = fu(phi, w)
        assert (e >= 0).all() and (e <= np.minimum(1, phi) + 1e-12).all(), w
    assert np.all(fu(phi, 6.0) >= fu(phi, 2.0) - 1e-12)         # a larger omega moves the curve toward the limits
    assert np.max(np.minimum(1, phi) - fu(phi, 200.0)) < 5e-3      # ... and omega -> infinity reaches them
    assert np.abs(fu(phi, 1.0000001)).max() < 1e-5               # omega -> 1 gives E/P -> 0
    out = jsrun("""var o=[];[1.1,2,2.383,6].forEach(function(w){[0.1,0.5,1,2.5,5].forEach(function(p){o.push([p,w,fu(p,w)]);});});console.log(JSON.stringify(o));""")
    for p, w, v in out:
        assert v == pytest.approx(fu(p, w), abs=1e-12)


def test_fitted_omega_js_python_cell_and_independent_numpy_agree():
    ids, phi, rr, fs = sample()
    w_np, rmse_np = fit(phi, 1 - rr)
    js_fit = jsrun("var s=budykoSample(BLOB.all);var r=fitOmega(s.phi,s.ep);console.log(JSON.stringify({w:r.omega,rmse:r.rmse,n:r.n,skipped:s.skipped}));")
    assert js_fit["n"] == 670 and js_fit["skipped"] == ["03281100"]
    assert js_fit["w"] == w_np and js_fit["rmse"] == pytest.approx(rmse_np, abs=1e-12)
    res = run_python(page_cell_sources()["budykoSource"])
    assert printed(res, "Fitted omega") == pytest.approx(w_np, abs=1e-12)
    assert printed(res, "RMSE of E/P at that omega") == pytest.approx(rmse_np, abs=5e-4)
    assert 2.3 < w_np < 2.5                                       # sanity: the fit is interior to the grid


def test_limit_counts_match_the_cell_and_the_independent_numpy_counts():
    ids, phi, rr, fs = sample()
    ep = 1 - rr
    want = {"above1": int((ep > 1).sum()), "aboveEnergy": int((ep > phi).sum()), "below0": int((ep < 0).sum())}
    got = jsrun("var s=budykoSample(BLOB.all);console.log(JSON.stringify(limitCounts(s.phi,s.ep)));")
    assert got == want
    res = run_python(page_cell_sources()["budykoSource"])
    assert (f"Outside the limits        : {want['above1']} above E/P = 1, {want['aboveEnergy']} above E/P = PET/P, "
            f"{want['below0']} below E/P = 0") in res
    assert f"Snow-influenced basins    : {int((fs > 0.3).sum())} with frac_snow > 0.3" in res
    q7 = quiz_item(MOD, "q7")["prompt"]
    assert f"{want['below0']} basins lie below" in q7 and f"{want['aboveEnergy']} lie above the energy limit" in q7


def test_course_basin_rows_in_the_cell_match_independent_numbers():
    res = run_python(page_cell_sources()["budykoSource"])
    ids, phi, rr, fs = sample()
    w, _ = fit(phi, 1 - rr)
    for g in IDS4:
        c = BLOB["course"][g]
        line = next(l for l in res.splitlines() if l.strip().startswith(g))
        assert f"aridity {c['aridity']:.3f}" in line
        assert f"E/P {1 - c['runoff_ratio']:.3f}" in line
        assert f"Fu {fu(c['aridity'], w):.3f}" in line
        assert f"difference {1 - c['runoff_ratio'] - fu(c['aridity'], w):+.3f}" in line


# ── the checkpoint: every answer recomputed independently ──────────────────────────────────────
def test_quiz_answers_equal_independent_recomputation():
    ids, phi, rr, fs = sample()
    w, _ = fit(phi, 1 - rr)
    c = BLOB["course"]
    assert quiz_item(MOD, "q1")["expected"] == (0 if c["14305500"]["aridity"] < 1 else 1)
    assert quiz_item(MOD, "q2")["expected"] == pytest.approx(hargreaves(decode("09484000")).mean(), abs=1e-6)
    assert quiz_item(MOD, "q3")["expected"] == pytest.approx(priestley_taylor(decode("02472000"), 1.26).mean(), abs=1e-6)
    assert quiz_item(MOD, "q4")["expected"] == pytest.approx(1 - c["02472000"]["runoff_ratio"], abs=1e-12)
    assert quiz_item(MOD, "q5")["expected"] == pytest.approx(w, abs=1e-12)
    diffs = [abs(1 - c[g]["runoff_ratio"] - fu(c[g]["aridity"], w)) for g in IDS4]
    assert quiz_item(MOD, "q6")["expected"] == int(np.argmax(diffs))
    assert quiz_item(MOD, "q7")["expected"] == 0
    # the Siletz basin sits farthest from the curve and the numbers the explanation quotes are the computed ones
    assert IDS4[int(np.argmax(diffs))] == "14305500"
    e6 = quiz_item(MOD, "q6")["explain"]
    g = IDS4[int(np.argmax(diffs))]
    assert f"observed E / P {1 - c[g]['runoff_ratio']:.3f}, curve {fu(c[g]['aridity'], w):.3f}" in e6


def test_quiz_wrong_answer_feedback_never_names_the_right_answer():
    sp = re.search(r"id: 'q7'.*?feedback: \[(.*?)\],\s*explain", T, re.S).group(1)
    assert "assumptions" not in sp and "steady" not in sp and "closed" not in sp
    q1 = re.search(r"id: 'q1'.*?feedback: \[(.*?)\],\s*explain", T, re.S).group(1)
    assert "energy-limited" not in q1 and "water-limited" not in q1
    assert ("Energy" in quiz_item(MOD, "q1")["options"][0])


def test_checkpoint_shape_three_choice_and_four_numeric():
    from helpers import quiz_dump
    items = quiz_dump()[MOD]["items"]
    assert sum(i["type"] == "choice" for i in items) >= 3 and sum(i["type"] == "numeric" for i in items) >= 1 and len(items) >= 4


# ── wording rules ──────────────────────────────────────────────────────────────────────────────
def prose(text):
    text = re.sub(r"<script.*?</script>", " ", text, flags=re.S)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.S)
    return re.sub(r"<[^>]+>", " ", text)


def test_embargo_wording_and_no_slope_fdc():
    pat = re.compile(r"(CAMELS|Addor|p_mean|pet_mean|aridity|runoff_ratio)[^.<]{0,120}(wrong|error|incorrect|mistake|bias|overestimat|underestimat)", re.I)
    for name, text in (("page", T), ("readme", (MODULES / MOD / "README.md").read_text()),
                       ("static", "".join(p.read_text() for p in (MODULES / MOD / "static").glob("*.txt"))),
                       ("alt", (MODULES / MOD / "static" / "alt.json").read_text())):
        assert not pat.search(text), (name, pat.search(text) and pat.search(text).group(0))
        assert "slope_fdc" not in text, name
    # the source of the generated code panes is JS in the page; scan the sources too
    for src in page_cell_sources().values():
        assert not pat.search(src) and "slope_fdc" not in src
    assert "slope_fdc" not in json.dumps(PROV) and "slope_fdc" not in (ROOT / "scripts" / "extract_camels.py").read_text().split("BEGIN extract_evapotranspiration_budyko")[1].split("END extract_evapotranspiration_budyko")[0]


def test_no_assertion_that_a_dataset_is_wrong_and_outside_limit_points_are_assumptions():
    p = prose(T)
    assert re.search(r"assumptions do not hold", p)
    assert "does not decide which assumption fails" in p
    for banned in ("data error", "measurement error", "bad data", "faulty", "unreliable", "erroneous"):
        assert banned not in p.lower(), banned
    assert "CAMELS tabulates no runoff ratio for gauge 03281100" in p


def test_pet_mean_is_a_reproduction_check_with_the_calibration_stated_next_to_addor():
    p = re.sub(r"\s+", " ", prose(T))
    m = re.search(r"calibrated for each catchment[^.]{0,40}\(Addor et al\., 2017\)", p)
    assert m, "calibrated-for-each-catchment must sit beside the Addor citation"
    assert "Reproduction check" in p
    assert "they are not a verdict on either" in p
    # the cell says the same thing
    assert "calibrated for each catchment there (Addor et al. 2017)" in page_cell_sources()["petSource"]


def test_handbooks_without_doi_only_in_the_marked_block_and_dois_are_real():
    block_start = T.index("Reference without DOI — pending owner decision")
    refs_start = T.index('id="refsH"')
    before, block = T[:block_start], T[block_start:]
    for name in ("Allen, R.G.", "Budyko, M.I. (1974)"):
        assert name in block and name not in before, name
    for bad in ("Fu, B.P.", "Fu (1981)", "Fu, 1981", "Jenson", "Lyne, V."):
        assert bad not in T, bad
    # the DOIs listed are exactly the ones the ledger passed
    ledger = (ROOT / "CITATIONS.verified.md").read_text()
    section = ledger.split("### evapotranspiration-budyko")[1].split("###")[0]
    rows = re.findall(r"\| (10\.[^ |]+) \| PASS \|", section)
    page_dois = re.findall(r'href="https://doi\.org/([^"]+)"', T)
    import urllib.parse
    page_dois = [urllib.parse.unquote(d) for d in page_dois]
    assert {d.lower() for d in page_dois} >= {d.lower() for d in rows if d.lower() not in (
        "10.5194/hess-19-209-2015", "10.5194/hess-21-5293-2017")}
    for d in rows:
        assert d.lower() in {x.lower() for x in page_dois}, d
    assert len(rows) == len(set(rows)) == 5


def test_synthetic_is_labelled_in_section_1_and_no_gauge_ids_there():
    s1 = T[T.index('id="sec-limits"'):T.index('id="sec-hargreaves"')]
    assert "SYNTHETIC" in s1
    assert not re.search(r"\b\d{8}\b", s1)


def test_the_page_states_its_assumptions_where_they_are_used():
    p = re.sub(r"\s+", " ", prose(T))
    for phrase in ("Albedo is held at 0.23 for every day and basin (a stated assumption, not a measurement)",
                   "The ground heat flux G is taken as 0", "set to 0 if negative"):
        assert phrase in p, phrase
    assert "E ≈ P − Q" in p and "ΔS → 0" in p


def test_estimated_minutes_and_manifest():
    man = json.loads((MODULES / MOD / "manifest.json").read_text())
    assert man["estimatedMinutes"] == 40 and man["courseOrder"] == 3 and man["topic"] == "evapotranspiration"
    assert man["requires"] == {"executable": True, "python": ["numpy", "matplotlib"]}
    assert man["createdAt"] == "2026-11-17" and man["courseId"] == "intro-hydro-2026" and man["version"] == "0.1.0"


def test_agent_callouts_name_only_tools_that_exist():
    tools = set(re.findall(r"<code>([a-z_]+)</code>", " ".join(re.findall(r'class="callout agent".*?</div>', T, re.S))))
    assert tools >= {"fetch_forcing_data", "fetch_camels_us"}
    mcp = Path("/Users/mgalib/Documents/AI-Hydro/MCP/aihydro-tools/ai_hydro/mcp/tools_analysis.py")
    if mcp.exists():
        src = mcp.read_text()
        for t in tools - {"runoff_ratio", "aridity", "frac_snow"}:
            assert f"def {t}(" in src, t


def test_fonts_linked_once_and_no_external_hosts():
    assert T.count("fonts.googleapis.com/css2") == 1
    assert not re.search(r"<script[^>]+\bsrc=", T)


# ── extractor reproduction (needs the local CAMELS copy; skipped otherwise) ────────────────────
@pytest.mark.skipif(not os.environ.get("CAMELS_ROOT"), reason="set CAMELS_ROOT to rerun the extractor")
def test_extractor_reproduces_the_bundled_files_byte_for_byte():
    root = Path(os.environ["CAMELS_ROOT"])
    with tempfile.TemporaryDirectory() as td:
        r = subprocess.run([sys.executable, "-s", "-E", str(ROOT / "scripts" / "extract_camels.py"), "--camels-root", str(root),
                            "--repo", td, "--only", MOD, "--extracted-on", PROV["extracted_on"]], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        for name in ("et-budyko.json", "PROVENANCE.json"):
            assert (Path(td) / "modules" / MOD / "data" / name).read_bytes() == (D / name).read_bytes(), name
        # the blob values equal the CAMELS attribute files
        import csv
        clim = {r["gauge_id"].zfill(8): r for r in csv.DictReader((root / "camels_clim.txt").open(), delimiter=";")}
        hyd = {r["gauge_id"].zfill(8): r for r in csv.DictReader((root / "camels_hydro.txt").open(), delimiter=";")}
        ids = BLOB["all"]["ids"].split(" ")
        assert ids == sorted(set(clim) & set(hyd)) and len(ids) == 671
        for i, g in enumerate(ids):
            assert BLOB["all"]["aridity"][i] == pytest.approx(float(clim[g]["aridity"]), abs=5.1e-5)
            assert BLOB["all"]["frac_snow"][i] == pytest.approx(float(clim[g]["frac_snow"]), abs=5.1e-5)
            rr = hyd[g]["runoff_ratio"]
            assert (BLOB["all"]["runoff_ratio"][i] is None) == (rr == "NA")
            if rr != "NA":
                assert BLOB["all"]["runoff_ratio"][i] == pytest.approx(float(rr), abs=5.1e-5)
        for g in IDS4:
            assert BLOB["course"][g]["aridity"] == float(clim[g]["aridity"])
            assert BLOB["course"][g]["pet_mean"] == float(clim[g]["pet_mean"])
            assert BLOB["course"][g]["runoff_ratio"] == float(hyd[g]["runoff_ratio"])
