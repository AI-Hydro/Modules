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
    assert "All seven learning modules done" in T and "7 Learning Modules" in T
    import json
    course = json.load(open(ROOT / "courses/intro-to-hydrology/course.json"))
    assert "Seven learning modules" in course["abstract"] and "Eight modules" not in course["abstract"]
    assert len([m for m in course["modules"] if m["id"] != "course-certificate"]) == 7


def test_owner_decisions_unchanged():
    # institution wording, signature block and "all 7 modules" prerequisite are left exactly as authored
    for keep in ['<div class="sig-line">Mohammad Galib</div>', '<div class="sig-line">Purdue University</div>',
                 '<div class="sig-label">Institution</div>', "Requires completion of all 7 course modules"]:
        assert keep in T
