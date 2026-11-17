"""capstone: every number in the story equals a computed value; no asserted per-gauge numbers remain."""
import json
import re
import sys

import pytest

from helpers import SHARED, ROOT, core_block, json_blob, module_text, run_node, run_python, shared_js

T = module_text("capstone-basin-story")
GAUGES = ["01013500", "14305500", "09484000", "02472000"]


def _all():
    blob = json_blob(T, "camels-5yr")["gauges"]
    py_lh = json.dumps((SHARED / "lyne_hollick.py").read_text().rstrip("\n"))
    py_d8 = json.dumps((SHARED / "d8.py").read_text().rstrip("\n"))
    js = shared_js("lyne_hollick.js", "d8.js") + f"\nvar PY_LH={py_lh}, PY_D8={py_d8};\n" + core_block(T) + """
var G=%s,out={},tw=twiStats();
for (var k in G){var g=G[k],st=gaugeStats(g);
  out[k]={rec:buildRecordSrc(g),sig:buildSigsSrc(g),exp:buildExportSrc(g),story:storyValues(g,st,tw),
          bfi:st.bfi,rb:st.rb,q10:st.q10,q50:st.q50,q90:st.q90,flood:st.floodDays,peak:st.peak,mean:st.meanQ,thr:st.thr95};}
out.twi=buildTwiSrc(); out.tw=tw;
console.log(JSON.stringify(out));""" % json.dumps(blob)
    return run_node(js)


@pytest.fixture(scope="module")
def computed():
    return _all()


@pytest.mark.parametrize("g", GAUGES)
def test_python_cells_equal_the_numbers_the_story_narrates(g, computed):
    c = computed[g]
    sig = run_python(c["sig"])
    bfi = float(re.search(r"this 5-year record\): ([0-9.]+)", sig).group(1))
    rb = float(re.search(r"flashiness index\s+: ([0-9.]+)", sig).group(1))
    q10, q50, q90 = (float(re.search(rf"Q{p} \([^)]*\)\s+: ([0-9.]+)", sig).group(1)) for p in (10, 50, 90))
    assert bfi == pytest.approx(c["bfi"], abs=5e-4) and c["story"]["tl3-bfi"] == f"{c['bfi']:.3f}"
    assert rb == pytest.approx(c["rb"], abs=5e-4) and c["story"]["tl2-rb"] == f"{c['rb']:.3f}"
    assert (q10, q50) == (pytest.approx(c["q10"], abs=6e-3), pytest.approx(c["q50"], abs=6e-3))
    assert q90 == pytest.approx(c["q90"], abs=6e-4)
    assert q10 >= q50 >= q90                                  # Q10 is the HIGH flow (exceeded 10% of days)
    rec = run_python(c["rec"])
    assert f"days above: {c['flood']}" in rec and c["story"]["tl4-flood"] == str(c["flood"])
    assert float(re.search(r"Peak Q   : ([0-9.]+)", rec).group(1)) == pytest.approx(c["peak"], abs=6e-3)
    assert c["story"]["tl2-peak"] == f"{c['peak']:.1f}"
    exp = run_python(c["exp"])
    assert f"BFI (LH)  : {c['bfi']:.3f}" in exp


def test_twi_cell_equals_story_value(computed):
    out = run_python(computed["twi"])
    mean = float(re.search(r"Mean TWI : ([0-9.]+)", out).group(1))
    assert mean == pytest.approx(computed["tw"]["mean"], abs=5e-3)
    assert computed["01013500"]["story"]["tl5-twi"] == f"{computed['tw']['mean']:.2f}"
    assert "SYNTHETIC" in out


def test_bfi_flashiness_ordering_quoted_in_quiz(computed):
    rb = {g: computed[g]["rb"] for g in GAUGES}
    for g, name in (("01013500", "Fish River"), ("14305500", "Siletz"), ("09484000", "Sabino"), ("02472000", "Leaf")):
        assert f"{name}" in T and f"{rb[g]:.3f}" in T
    assert max(rb, key=rb.get) == "09484000"                  # quiz answer: Sabino Creek


def test_camels_signature_numbers_on_cards_match_data():
    meta = json.load(open(ROOT / "modules/capstone-basin-story/data/camels_gauges.json"))
    for g, m in meta.items():
        assert f"CAMELS BFI {m['baseflow_index']:.3f}" in T
        assert f"aridity {m['aridity']:.2f}" in T and f"snow fraction {m['frac_snow']:.2f}" in T


def test_quiz_twi_example():
    import math
    assert f"{math.log(500 / math.tan(math.radians(2))):.2f}" in T and f"{math.log(20 / math.tan(math.radians(20))):.2f}" in T


def test_no_asserted_numbers_or_fake_gauge_names_remain():
    body = re.sub(r"<style.*?</style>", "", T, flags=re.S)
    for pat in [r"BFI[^<\n]{0,24}\b0\.(55|62|08|82)\b", r"TWI[^<\n]{0,40}\b(8\.2|7\.8|5\.4|9\.1)\b",
                r"twiMean", r"Rillito", r"Bogue Chitto", r"~1 000 mm", r"≈ 1000 mm", r"default_rng",
                r"percentile\(Q,10\)", r"Q90 \(low flow, 10% exceed", r"10-year", r"dataretrieval", r"Other gauge"]:
        assert not re.search(pat, body), pat
    assert "twi = twi - twi.mean()" not in body            # the forced-mean line
    assert "SYNTHETIC" in body


def test_quiz_is_not_a_one_shot_lock_on_a_wrong_claim():
    # the arid-basin BFI claim that contradicted the module's own cell must be gone
    assert "Rillito Creek (AZ) has a BFI of about 0.08" not in T
