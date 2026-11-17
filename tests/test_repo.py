"""Repository-level checks: manifests agree, scripts parse, modules stay self-contained,
data are bundled with provenance, and every cited DOI passed the gate."""
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

import pytest

from helpers import MODULES, ROOT, extract_dois, module_text, scripts

IDS = sorted(p.name for p in MODULES.iterdir() if p.is_dir())


def embedded(mod):
    m = re.search(r'<script type="application/vnd.aihydro.module\+json">(.*?)</script>', module_text(mod), re.S)
    return json.loads(m.group(1))


def test_every_course_module_exists_and_every_directory_has_a_manifest():
    course = json.loads((ROOT / "courses/intro-to-hydrology/course.json").read_text())
    for m in course["modules"]:
        assert (MODULES / m["id"] / "module.html").exists(), m["id"]
    for mod in IDS:
        assert (MODULES / mod / "manifest.json").exists(), mod
    # the module directories and the course are the same set, in the manifests' courseOrder
    assert sorted(m["id"] for m in course["modules"]) == IDS
    for i, m in enumerate(course["modules"], 1):
        man = json.loads((MODULES / m["id"] / "manifest.json").read_text())
        assert man["courseOrder"] == i, m["id"]


@pytest.mark.parametrize("mod", IDS)
def test_manifest_and_embedded_versions_agree(mod):
    man = json.loads((MODULES / mod / "manifest.json").read_text())
    emb = embedded(mod)
    assert man["version"] == emb["version"], mod
    assert man["moduleId"] == emb["id"] == mod
    assert "updatedAt" not in man                              # the API takes it from git; no hand-kept copy
    assert f"v{man['version']}" in module_text(mod)          # footer shows the same version


@pytest.mark.parametrize("mod", IDS)
def test_changelog_records_each_version(mod):
    ver = json.loads((MODULES / mod / "manifest.json").read_text())["version"]
    log = (ROOT / "CHANGELOG.md").read_text()
    assert re.search(rf"### {re.escape(mod)} .*→ {re.escape(ver)}", log), mod


@pytest.mark.parametrize("mod", IDS)
def test_inline_scripts_parse(mod):
    for i, body in enumerate(scripts(module_text(mod))):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "s.js"
            p.write_text(body)
            r = subprocess.run(["node", "--check", str(p)], capture_output=True, text=True)
        assert r.returncode == 0, f"{mod} script {i}: {r.stderr[:300]}"


@pytest.mark.parametrize("mod", IDS)
def test_self_contained_no_new_script_hosts(mod):
    t = module_text(mod)
    assert not re.search(r"<script[^>]+\bsrc=", t), "no external scripts"
    hosts = set(re.findall(r'<link[^>]+href="https?://([^/"]+)', t))
    assert hosts <= {"fonts.googleapis.com", "fonts.gstatic.com"}, hosts


def test_every_module_status_synthetic_is_labelled():
    # modules that still contain synthetic content say SYNTHETIC; modules with real data say where it comes from
    for mod in ["baseflow-separation", "watershed-runoff", "dem-to-twi", "capstone-basin-story", "reading-a-hydrograph",
                "precipitation-point-to-basin", "runoff-generation"]:
        assert "SYNTHETIC" in module_text(mod), mod
    for mod in ["real-streamflow-data", "capstone-basin-story", "reading-a-hydrograph",
                "precipitation-point-to-basin", "evapotranspiration-budyko", "runoff-generation"]:
        assert "CAMELS" in module_text(mod)


@pytest.mark.parametrize("mod", ["real-streamflow-data", "capstone-basin-story", "reading-a-hydrograph", "dem-to-twi"])
def test_bundled_data_and_provenance(mod):
    d = MODULES / mod / "data"
    assert sum(f.stat().st_size for f in d.iterdir()) < 200_000, "under ~200 KB per module"
    prov = json.loads((d / "PROVENANCE.json").read_text())
    assert prov["extraction_script"] == "scripts/extract_camels.py" and (ROOT / prov["extraction_script"]).exists()
    assert any("10.5194/hess-19-209-2015" in c for c in prov["citations"])
    assert any("10.5194/hess-21-5293-2017" in c for c in prov["citations"])
    for g, s in prov["series"].items():
        member = s.get("source_member") or s.get("flow_source_member")
        assert member.startswith("basin_dataset_public_v1p2/usgs_streamflow/")
        sha = s.get("source_member_sha256") or s.get("flow_source_member_sha256")
        assert re.fullmatch(r"[0-9a-f]{64}", sha)
        assert s["usgs_qc_flags"] and set(s["usgs_qc_flags"]) <= {"A", "A:e"}
        assert s["units"]
        csvp = d / Path(s["file"]).name
        lines = csvp.read_text().splitlines()
        assert len(lines) - 1 == s["n_days"] and lines[1].startswith(s["period"][0]) and lines[-1].startswith(s["period"][1])
    meta = json.loads((d / "camels_gauges.json").read_text())
    for g, m in meta.items():
        assert m["gauge_id"] == g and m["name"] and -180 < m["lon"] < 0 and 20 < m["lat"] < 55 and 0 <= m["baseflow_index"] <= 1


def test_gauge_names_match_camels():
    meta = json.loads((MODULES / "real-streamflow-data/data/camels_gauges.json").read_text())
    assert meta["02472000"]["camels_name"].lower().startswith("leaf river")
    assert "SABINO CREEK" in meta["09484000"]["camels_name"].upper()
    assert "SILETZ RIVER" in meta["14305500"]["camels_name"].upper()
    assert "Fish River" in meta["01013500"]["camels_name"]


def test_doi_extraction_matches_sici_style_dois_in_full():
    a = "10.1175/1520-0493(1911)39<1082b:PAFLA>2.0.CO;2"
    b = "10.1175/1520-0493(1972)100<0081:OTAOSH>2.3.CO;2"
    html_text = (
        '<a href="https://doi.org/10.1175/1520-0493(1911)39%3C1082b:PAFLA%3E2.0.CO;2">DOI: '
        "10.1175/1520-0493(1911)39&lt;1082b:PAFLA&gt;2.0.CO;2</a> and "
        '<a href="https://doi.org/10.1175%2F1520-0493(1972)100%3C0081:OTAOSH%3E2.3.CO;2">x</a> '
        "10.1175/1520-0493(1972)100&lt;0081:OTAOSH&gt;2.3.CO;2. Plain 10.5194/hess-19-209-2015."
    )
    assert extract_dois(html_text) == {a, b, "10.5194/hess-19-209-2015"}


def test_every_doi_in_the_modules_passed_the_gate():
    gate = (ROOT / "CITATIONS.verified.md").read_text()
    passed = set(re.findall(r"\| (10\.[^ |]+) \| PASS \|", gate))
    seen = set()
    for mod in IDS:
        t = module_text(mod)
        seen.update(extract_dois(t))
    passed_l = {p.lower() for p in passed}
    unknown = {d for d in seen if d.lower() not in passed_l}
    assert not unknown, unknown
    for mod in IDS:
        man = json.loads((MODULES / mod / "manifest.json").read_text())
        doi = man.get("citation", {}).get("doi")
        if doi:
            assert doi.lower() in passed_l, (mod, doi)


def test_failed_citations_are_not_cited():
    for mod in IDS:
        t = module_text(mod)
        man = (MODULES / mod / "manifest.json").read_text() + (MODULES / mod / "README.md").read_text()
        for bad in ["Lyne, V.", "Lyne &amp; Hollick (1979)", "Jenson", "Domingue", "Moore, C.", "Pettitt", "Hodson"]:
            assert bad not in t and bad not in man, (mod, bad)


def test_dingman_is_cited_consistently_as_a_book_without_chapters():
    for mod in IDS:
        for m in re.finditer(r"Dingman[^<]{0,120}", module_text(mod)):
            assert "Chapter" not in m.group(0), mod
    assert "Physical Hydrology" in (ROOT / "CITATIONS.verified.md").read_text()
