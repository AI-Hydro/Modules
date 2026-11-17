"""course-certificate: acquireVsCodeApi once, no auto-open; owner-decision wording untouched."""
import re

from helpers import ROOT, module_text

T = module_text("course-certificate")


def test_acquire_vscode_api_is_called_once():
    calls = [m for m in re.finditer(r"acquireVsCodeApi\(\)", T)]
    assert len(calls) == 1


def test_no_auto_open_on_load_and_button_exists():
    assert "aihydro_cert_opened_browser" not in T
    assert 'id="openBrowserBtn"' in T and "hidden" in T.split('id="openBrowserBtn"')[1][:120]
    # the only openInBrowser post sits inside a click handler
    posts = [m.start() for m in re.finditer(r"command: 'openInBrowser'", T)]
    assert len(posts) == 1 and "addEventListener('click'" in T[posts[0] - 200:posts[0]]


def test_module_counts_agree():
    assert "All ten learning modules done" in T and "10 Learning Modules" in T
    import json
    course = json.load(open(ROOT / "courses/intro-to-hydrology/course.json"))
    assert "Ten learning modules" in course["abstract"] and "Seven learning modules" not in course["abstract"]
    assert len([m for m in course["modules"] if m["id"] != "course-certificate"]) == 10


def test_owner_decisions_unchanged():
    # institution wording, signature block and "all 10 modules" prerequisite are left exactly as authored
    for keep in ['<div class="sig-line">Mohammad Galib</div>', '<div class="sig-line">Purdue University</div>',
                 '<div class="sig-label">Institution</div>', "Requires completion of all 10 course modules"]:
        assert keep in T


def test_course_hours_follow_the_minutes_and_the_certificate_says_so():
    import json
    import math
    from helpers import MODULES
    mins = sum(json.load(open(p))["estimatedMinutes"] for p in MODULES.glob("*/manifest.json"))
    course = json.load(open(ROOT / "courses/intro-to-hydrology/course.json"))
    assert course["estimatedHours"] == math.ceil(mins / 60) == 8, mins
    assert f"~{course['estimatedHours']} Hours" in T
    assert json.load(open(MODULES / "course-certificate/manifest.json"))["version"] == "0.1.4" and "v0.1.4" in T
    ws = next(m for m in course["modules"] if m["id"] == "watershed-runoff")
    assert ws["estimatedMinutes"] == json.load(open(MODULES / "watershed-runoff/manifest.json"))["estimatedMinutes"] == 50
    assert "Fish River" in ws["abstract"]
