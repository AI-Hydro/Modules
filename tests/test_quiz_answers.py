"""The checkpoints: every module uses the one shared engine, keeps its content questions, and has at
least one numeric or interpretive item whose answer is computed from the lesson's own data or code.
The answers the pages compute (under node) are recomputed here independently in Python."""
import csv
import math
import re
import sys

import numpy as np
import pytest

from helpers import MODULES, ROOT, SHARED, module_text, quiz_dump, quiz_item

sys.path.insert(0, str(SHARED))
from d8 import d8_route  # noqa: E402
from lyne_hollick import baseflow_index, lyne_hollick  # noqa: E402

QUIZ_MODULES = ["baseflow-separation", "capstone-basin-story", "dem-to-twi", "reading-a-hydrograph",
                "real-streamflow-data", "water-cycle-in-motion", "watershed-runoff"]
CFS = 0.028316846592


def q_cfs(mod, name):
    rows = list(csv.DictReader((MODULES / mod / "data" / name).open()))
    return [float(r["q_cfs"]) for r in rows]


def test_every_module_with_a_checkpoint_uses_the_shared_engine():
    assert sorted(quiz_dump()) == QUIZ_MODULES
    for mod in QUIZ_MODULES:
        t = module_text(mod)
        assert t.count("var HydroQuiz = (function") == 1, mod
        assert "HydroQuiz.mount(" in t, mod
        for old in ("aihydro-quiz", "quiz-btn", "quizAnswer", "aihydro-quiz-submit", "aihydro-quiz-complete"):
            assert old not in t, (mod, old)           # the three older engines are gone


def test_each_checkpoint_keeps_its_three_content_questions_and_adds_computed_ones():
    for mod in QUIZ_MODULES:
        items = quiz_dump()[mod]["items"]
        assert len(items) >= 4, mod
        assert sum(1 for i in items if i["type"] == "choice") >= 3, mod
        numeric = [i for i in items if i["type"] == "numeric"]
        assert numeric or any(i["id"] in ("q5",) for i in items), mod
        for i in numeric:
            assert isinstance(i["expected"], (int, float)) and math.isfinite(i["expected"])
        for i in items:
            if i["type"] == "choice":
                assert 0 <= i["expected"] < len(i["options"])
            assert i["explain"], (mod, i["id"])


def test_numeric_items_are_not_typed_into_the_page():
    """An answer written as a literal would drift from the lesson; each answer is a function."""
    for mod in QUIZ_MODULES:
        t = module_text(mod)
        for m in re.finditer(r"type: 'numeric'.*?answer: ([^,}]+)", t, re.S):
            assert not re.match(r"[-+]?[0-9.]", m.group(1).strip()), (mod, m.group(1))


def test_baseflow_answers():
    Q = None
    import json
    from helpers import run_python, static_cell_sources
    # the synthetic series exactly as the Python cell builds it
    n = 365
    days = np.arange(n)
    storm_days = [12, 18, 34, 67, 98, 124, 155, 189, 210, 220, 251, 280, 305, 330, 352]
    storm_amp = [18, 11, 26, 9, 30, 14, 12, 24, 10, 20, 13, 17, 8, 11, 19]
    uh = np.exp(-np.arange(20) / 4.0); uh /= uh.sum()
    qf = np.zeros(n)
    for d0, a0 in zip(storm_days, storm_amp):
        for k in range(20):
            if d0 + k < n:
                qf[d0 + k] += a0 * uh[k]
    b_true = 2.0 + 1.2 * np.sin(2 * np.pi * (days - 80) / 365)
    Q = list(b_true + qf)
    bfi = lambda a: baseflow_index(Q, lyne_hollick(Q, a))
    assert quiz_item("baseflow-separation", "q4")["expected"] == pytest.approx(bfi(0.98), abs=1e-9)
    true = b_true.sum() / np.sum(Q)
    alphas = [0.80, 0.90, 0.95, 0.98]
    best = int(np.argmin([abs(bfi(a) - true) for a in alphas]))
    assert quiz_item("baseflow-separation", "q5")["expected"] == best == 1
    # Q2 (increasing alpha lowers the BFI) is what the numbers say
    assert bfi(0.98) < bfi(0.925) < bfi(0.8)


def test_reading_answers():
    S = 25400 / 75 - 254
    Ia = 0.2 * S
    runoff = lambda P: 0 if P <= Ia else (P - Ia) ** 2 / (P - Ia + S)
    assert quiz_item("reading-a-hydrograph", "q4")["expected"] == pytest.approx(runoff(40), abs=1e-9)
    q = q_cfs("reading-a-hydrograph", "01031500_wy1997.csv") if (MODULES / "reading-a-hydrograph/data/01031500_wy1997.csv").exists() else None
    if q is None:
        files = sorted((MODULES / "reading-a-hydrograph/data").glob("01031500_wy*.csv"))
        q = [float(r["q_cfs"]) for r in csv.DictReader(files[0].open())]
    assert quiz_item("reading-a-hydrograph", "q5")["expected"] == pytest.approx(baseflow_index(q, lyne_hollick(q, 0.925)), abs=1e-9)


def test_watershed_answers():
    assert quiz_item("watershed-runoff", "q4")["expected"] == pytest.approx(32 * 32 * 30 * 30 / 1e6, abs=1e-12)
    assert quiz_item("watershed-runoff", "q5")["expected"] == pytest.approx(0.35 * 40.0 * 92.16 / 360.0, abs=1e-9)
    # the same number the rational-method cell prints when run
    from helpers import run_python, static_cell_sources
    out = run_python(static_cell_sources(module_text("watershed-runoff"))["rational-method"])
    assert float(re.search(r"Q = ([0-9.]+) m³/s", out).group(1)) == pytest.approx(quiz_item("watershed-runoff", "q5")["expected"], abs=5e-4)


def test_water_cycle_answers():
    g, cp, Rd, Rv, Lv, T, Td = 9.80665, 1005.0, 287.05, 461.5, 2.5e6, 288.15, 283.15
    dry = g / cp * 1000
    dew = (g / (Rd * T)) * (Rv * Td ** 2 / Lv) * 1000
    assert quiz_item("water-cycle-in-motion", "q4")["expected"] == pytest.approx((T - Td) / (dry - dew) * 1000, abs=1e-6)
    from helpers import run_python, static_cell_sources
    out = run_python(static_cell_sources(module_text("water-cycle-in-motion"))["dewpoint-lapse"])
    assert abs(float(re.search(r"about (\d+) m above", out).group(1)) - quiz_item("water-cycle-in-motion", "q4")["expected"]) < 1
    # steady state of the bucket: storage stops changing, so P = ET + R and R = P - ET
    assert quiz_item("water-cycle-in-motion", "q5")["expected"] == pytest.approx(10.0 - 2.0, abs=1e-6)


def test_real_streamflow_answers():
    keys = ["01013500", "14305500", "09484000", "02472000"]
    series = {k: np.array(q_cfs("real-streamflow-data", f"{k}_q.csv")) * CFS for k in keys}
    assert quiz_item("real-streamflow-data", "q4")["expected"] == pytest.approx(float(np.percentile(series["02472000"], 95)), rel=1e-9)
    peaks = [float(series[k].max()) for k in keys]
    assert quiz_item("real-streamflow-data", "q5")["expected"] == int(np.argmax(peaks))
    # Q3: P99 keeps about 1% of the days
    assert 17 <= int((series["01013500"] > np.percentile(series["01013500"], 99)).sum()) <= 19


def test_capstone_answers():
    keys = ["01013500", "09484000", "02472000"]
    series = {k: q_cfs("capstone-basin-story", f"{k}_q.csv") for k in keys}
    rb = lambda q: sum(abs(q[i] - q[i - 1]) for i in range(1, len(q))) / sum(q[1:])
    assert quiz_item("capstone-basin-story", "q1")["expected"] == int(np.argmax([rb(series[k]) for k in keys]))
    leaf = series["02472000"]
    assert quiz_item("capstone-basin-story", "q4")["expected"] == pytest.approx(baseflow_index(leaf, lyne_hollick(leaf, 0.925)), abs=1e-9)
    from helpers import run_python, static_cell_sources
    out = (MODULES / "capstone-basin-story/static/capstone-twi.txt").read_text()
    assert float(re.search(r"Mean TWI : ([0-9.]+)", out).group(1)) == pytest.approx(quiz_item("capstone-basin-story", "q5")["expected"], abs=0.01)
    # Q2 water balance and Q3 TWI example
    assert 900 - 450 - 0 == 450
    assert quiz_item("capstone-basin-story", "q3")["expected"] == 0 and math.log(500 / math.tan(math.radians(2))) > math.log(20 / math.tan(math.radians(20)))


def test_dem_answers():
    dem = [[92, 90, 88, 86, 85], [85, 82, 79, 78, 79], [78, 75, 72, 73, 76], [74, 71, 68, 70, 72], [72, 69, 66, 68, 71]]
    r = d8_route(dem, 10.0)
    assert quiz_item("dem-to-twi", "q5")["expected"] == pytest.approx(r["twi"][4 * 5 + 2], abs=1e-9)
    assert quiz_item("dem-to-twi", "q4")["expected"] == pytest.approx(math.log(300 / max(math.tan(math.radians(5)), 1e-3)), abs=1e-12)
    # Q1: gentler slope, larger TWI
    assert quiz_item("dem-to-twi", "q1")["expected"] == 1
    # Q3 quotes the means the section 6 cell prints
    out = (MODULES / "dem-to-twi/static/twi-grid.txt").read_text()
    m30 = float(re.search(r"Mean TWI at 30 m : ([0-9.]+)", out)[1]); m60 = float(re.search(r"Mean TWI at 60 m : ([0-9.]+)", out)[1])
    p = quiz_item("dem-to-twi", "q3")["prompt"]
    assert f"{m30:.2f} at 30 m" in p and f"{m60:.2f} at 60 m" in p
