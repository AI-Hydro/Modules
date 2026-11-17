"""Wave 2 repository checks: manifests, generated docs, API, workflows, CSP/external hosts, static
outputs, accessibility structure. Each runs the same script the CI workflow runs."""
import copy
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from helpers import MODULES, ROOT, module_text

sys.path.insert(0, str(ROOT / "scripts"))
import build_api  # noqa: E402
import build_modules  # noqa: E402
import check_csp  # noqa: E402
import gen_docs  # noqa: E402
import validate_manifests  # noqa: E402

IDS = sorted(p.name for p in MODULES.iterdir() if p.is_dir())
BASELINE_TOTAL_BYTES = 671_451          # sum of the eight module.html files at the Wave 1 head (b7d833d)
MAX_GROWTH_BYTES = 1_500_000


def script(name, *args):
    return subprocess.run([sys.executable, "-s", "-E", str(ROOT / "scripts" / name), *args], capture_output=True, text=True, cwd=ROOT)


def embedded(mod):
    m = re.search(r'<script type="application/vnd.aihydro.module\+json">(.*?)</script>', module_text(mod), re.S)
    return json.loads(m.group(1))


# ── manifests ────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("mod", IDS)
def test_every_manifest_has_the_license_and_the_embedded_manifest_agrees(mod):
    man = json.loads((MODULES / mod / "manifest.json").read_text())
    assert man["license"] == "CC-BY-4.0"
    emb = embedded(mod)
    assert emb == build_modules.embedded_manifest(man), "embedded manifest is generated from manifest.json"
    # the same facts under the two naming schemes
    assert (emb["id"], emb["estimated_minutes"], emb["license"], emb["topic"], emb["level"], emb["version"], emb["requires"]) == \
           (man["moduleId"], man["estimatedMinutes"], man["license"], man["topic"], man["level"], man["version"], man["requires"])
    assert ", ".join([emb["authors"][0]["name"], emb["authors"][0]["affiliation"]]) == man["author"]
    assert emb.get("citation") == man.get("citation")


def test_validate_manifests_passes_on_the_repo():
    r = script("validate_manifests.py")
    assert r.returncode == 0, r.stdout + r.stderr


def test_validate_manifests_catches_disagreement_and_bad_fields(tmp_path):
    d = tmp_path / "dem-to-twi"; d.mkdir()
    for f in ("module.html", "manifest.json", "README.md"):
        (d / f).write_bytes((MODULES / "dem-to-twi" / f).read_bytes())
    assert validate_manifests.check_module(d) == []
    man = json.loads((d / "manifest.json").read_text())
    man["license"] = "MIT"                                   # file now disagrees with the embedded block
    (d / "manifest.json").write_text(json.dumps(man))
    assert any("embedded manifest differs" in e for e in validate_manifests.check_module(d))
    man.update(license="CC-BY-4.0", level="expert", version="1.0")
    (d / "manifest.json").write_text(json.dumps(man))
    errs = " ".join(validate_manifests.check_module(d))
    assert "level" in errs and "major.minor.patch" in errs
    del man["license"]
    (d / "manifest.json").write_text(json.dumps(man))
    assert any("license" in e for e in validate_manifests.check_module(d))


def test_course_graph_is_valid_and_matches_manifest_order():
    from repo_lib import courses
    for path, c in courses():
        assert validate_manifests.check_course(path, c, set(IDS)) == []


# ── generated docs ───────────────────────────────────────────────────────────────────────────
def test_readme_table_and_course_page_are_generated_from_the_manifests():
    r = script("gen_docs.py", "--check")
    assert r.returncode == 0, r.stdout + r.stderr
    readme = (ROOT / "README.md").read_text()
    for mod in IDS:
        assert f"(modules/{mod}/)" in readme, mod
    course = (ROOT / "courses/intro-to-hydrology/README.md").read_text()
    assert "flowchart TD" in course
    for mod in IDS:
        assert f"(../../modules/{mod}/)" in course, mod
    cj = json.loads((ROOT / "courses/intro-to-hydrology/course.json").read_text())
    for m in cj["modules"]:
        for p in m.get("prerequisites", []):
            i, j = [x["id"] for x in cj["modules"]].index(p) + 1, [x["id"] for x in cj["modules"]].index(m["id"]) + 1
            assert f"M{i} --> M{j}" in course


# ── API ──────────────────────────────────────────────────────────────────────────────────────
def test_api_files_are_current_with_the_same_code_the_workflow_runs():
    r = script("build_api.py", "--check")
    assert r.returncode == 0, r.stdout + r.stderr


def test_certification_reports_metadata_only_and_leaves_scientific_review_null():
    api = json.loads((ROOT / "api/modules.json").read_text())
    assert [m["moduleId"] for m in api] == IDS
    for m in api:
        c = m["certification"]
        assert set(c) == {"metadata_complete", "checks_passed", "checks_failed", "scientific_review"}
        assert c["metadata_complete"] is True and c["checks_failed"] == []
        assert c["scientific_review"] is None
        assert "certified" not in c and "certified_at" not in c
    incomplete = build_api.certify({"description": "x", "tags": [], "estimatedMinutes": 0})
    assert incomplete["metadata_complete"] is False and len(incomplete["checks_failed"]) == 3 and incomplete["scientific_review"] is None


def test_courses_json_is_generated_from_course_json():
    cj = json.loads((ROOT / "courses/intro-to-hydrology/course.json").read_text())
    api = json.loads((ROOT / "api/courses.json").read_text())[0]
    assert api["courseId"] == cj["courseId"] and api["version"] == cj["version"] and api["abstract"] == cj["abstract"]
    assert [m["moduleId"] for m in api["modules"]] == [m["id"] for m in cj["modules"]]
    assert api["modules"][2]["prerequisites"] == ["water-cycle-in-motion"]


def test_api_dates_come_from_git_not_from_today(monkeypatch):
    calls = []
    monkeypatch.setattr(build_api, "git_date", lambda path, first=False: calls.append((path, first)) or "2001-02-03")
    items = build_api.build_modules({})
    assert all(i["updatedAt"] == "2001-02-03" for i in items)
    assert ("modules/dem-to-twi", False) in calls
    src = (ROOT / "scripts/build_api.py").read_text() + (ROOT / ".github/workflows/build-api.yml").read_text()
    assert "datetime.now" not in src and "date.today" not in src


# ── workflows ────────────────────────────────────────────────────────────────────────────────
def load_yaml(name):
    yaml = pytest.importorskip("yaml")
    return yaml.safe_load((ROOT / ".github/workflows" / name).read_text())


def test_build_api_workflow_triggers_and_runs_the_script():
    wf = load_yaml("build-api.yml")
    on = wf.get("on", wf.get(True))
    assert set(on["push"]["paths"]) == {"modules/**", "courses/**", "shared/**"}
    text = (ROOT / ".github/workflows/build-api.yml").read_text()
    assert "scripts/build_api.py" in text and "fetch-depth: 0" in text
    assert "api/courses.json" in text
    assert "datetime" not in text


def test_pr_workflow_runs_every_check():
    wf = load_yaml("checks.yml")
    assert "pull_request" in wf.get("on", wf.get(True))
    text = (ROOT / ".github/workflows/checks.yml").read_text()
    for cmd in ["scripts/build_modules.py --check", "scripts/render_static_outputs.py --check", "scripts/gen_docs.py --check",
                "scripts/validate_manifests.py", "scripts/check_csp.py", "scripts/build_api.py --check", "pytest tests", "node --test tests/js"]:
        assert cmd in text, cmd


def test_embedded_python_in_the_api_workflow_compiles():
    import textwrap
    text = (ROOT / ".github/workflows/build-api.yml").read_text()
    for m in re.finditer(r"python3 - <<'EOF'\n(.*?)\n\s+EOF", text, re.S):
        compile(textwrap.dedent(m.group(1)), "workflow", "exec")


# ── CSP / external hosts ─────────────────────────────────────────────────────────────────────
def test_csp_check_passes_on_the_modules():
    r = script("check_csp.py")
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.parametrize("snippet,expect", [
    ('<script src="https://cdn.example.org/x.js"></script>', "external <script src>"),
    ('<link rel="stylesheet" href="https://cdn.example.org/x.css">', "cdn.example.org"),
    ('<img src="https://img.example.org/a.png">', "img.example.org"),
    ('<style>@import url("https://evil.example/x.css");</style>', "evil.example"),
    ('<iframe src="x"></iframe>', "iframe"),
    ('<script>fetch("/x");</script>', "fetch()"),
    ('<script>var x = new XMLHttpRequest();</script>', "XMLHttpRequest"),
    ('<script>eval("1")</script>', "eval()"),
    ('<script src="https://evil.example/json.js"></script>', "external <script src>"),
    ('<script type="application/json" src="https://evil.example/d.json"></script>', "external <script src>"),
    ('<script type="text/javascript" src=//evil.example/x.js></script>', "external <script src>"),
    ('<link rel=stylesheet href=//evil.example/x.css>', "evil.example"),
    ('<link rel=stylesheet href=https://evil.example/x.css>', "evil.example"),
    ('<img src=https://e.example/a.png>', "e.example"),
    ('<script>var s = document.createElement("script"); s.src = "https://evil.example/x.js";</script>', "createElement('script')"),
    ('<script>var i = new Image(); i.src = "https://evil.example/p.png";</script>', "external URL to .src/.href"),
    ('<script>el.setAttribute("src", "https://evil.example/a");</script>', "setAttribute src/href"),
    ('<script>import("https://evil.example/m.js");</script>', "dynamic import()"),
])
def test_csp_check_flags_what_the_preview_would_block(tmp_path, snippet, expect):
    d = tmp_path / "bad"; d.mkdir()
    (d / "module.html").write_text(f"<html><head>{snippet}</head><body></body></html>")
    errs = check_csp.scan(d / "module.html")
    assert any(expect in e for e in errs), errs


def test_csp_check_still_allows_inert_json_blocks_and_data_urls(tmp_path):
    d = tmp_path / "ok2"; d.mkdir()
    (d / "module.html").write_text('<html><body><script type="application/vnd.aihydro.module+json">{"a":"https://x.org"}</script>'
                                   '<script type="application/json" id="b">{"u":"https://y.org"}</script>'
                                   '<img src="data:image/png;base64,AAAA"><script>img.src = "data:image/png;base64,AAAA";</script></body></html>')
    assert check_csp.scan(d / "module.html") == []


def test_csp_check_allows_the_fonts_hosts_and_ignores_code_cell_text(tmp_path):
    d = tmp_path / "ok"; d.mkdir()
    (d / "module.html").write_text('<html><head><link href="https://fonts.googleapis.com/css2?family=Nunito" rel="stylesheet">'
                                   '<link rel="preconnect" href="https://fonts.gstatic.com"></head><body>'
                                   '<pre class="aihydro-source">import requests; requests.get("https://x.org"); fetch(1)</pre>'
                                   '<a href="https://doi.org/10.1/x">doi</a></body></html>')
    assert check_csp.scan(d / "module.html") == []


# ── static rendering without the bridge ──────────────────────────────────────────────────────
def test_static_outputs_match_the_cell_sources():
    r = script("render_static_outputs.py", "--check")
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.parametrize("mod", IDS)
def test_every_executable_cell_ships_a_pre_rendered_output(mod):
    t = module_text(mod)
    cells = re.findall(r'<div class="aihydro-cell"[^>]*data-aihydro-cell-id="([^"]+)"', t)
    assert cells or mod in ("course-certificate",), mod
    for cid in cells:
        m = re.search(r"<!--@@BEGIN static:" + re.escape(cid) + r"@@-->(.*?)<!--@@END static:" + re.escape(cid) + r"@@-->", t, re.S)
        assert m and 'data-static-output="prerendered"' in m[1], (mod, cid)
        assert "<pre" in m[1], (mod, cid)
        # inside the cell's own .aihydro-output so the bridge replaces it on a real run
        before = t[:m.start()]
        assert before.rstrip().endswith('aria-live="polite">') or before.rstrip().endswith('<div class="aihydro-output">'), (mod, cid)
        for img in re.findall(r"<img [^>]*>", m[1]):
            assert re.search(r'alt="[^"]{20,}"', img), (mod, cid, "figure needs real alt text")
            assert 'src="data:image/png;base64,' in img


def test_page_size_growth_stays_under_the_budget_and_is_reported():
    sizes = {m: len((MODULES / m / "module.html").read_bytes()) for m in IDS}
    growth = sum(sizes.values()) - BASELINE_TOTAL_BYTES
    assert growth < MAX_GROWTH_BYTES, f"{growth} bytes added in total"
    for mod, sz in sizes.items():
        assert sz < 250_000, (mod, sz)


# ── hygiene ──────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("mod", IDS)
def test_hygiene(mod):
    t = module_text(mod)
    assert "folium-map" not in t and "invalidateLeafletMaps" not in t and "aihydro-leaflet-normalizer" not in t   # dead Leaflet normaliser
    assert not re.search(r"postMessage\([^;]*,\s*'\*'\)", t) and 'postMessage(payload, "*")' not in t
    assert not re.search(r"\bunlock\b", t, re.I)                       # nothing is gated
    assert not re.search(r"\son(click|change|input|keydown)=", t)
    assert not re.search(r"contenteditable", t)
    fonts = [l for l in re.findall(r'<link[^>]+href="(https://fonts[^"]+)"', t)]
    assert len(fonts) <= 2 and all(re.match(r"https://fonts\.(googleapis|gstatic)\.com", f) for f in fonts)


def test_no_red_green_twi_map_remains():
    t = module_text("dem-to-twi")
    assert "239,68,68" not in t and "52,211,153,0.80" not in t         # the old red / amber / green canvas colours
    assert "HydroCmap.css(" in t and "viridis" in t.lower()
