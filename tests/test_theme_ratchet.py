"""T2: the hard-coded colour count in each lesson only goes down (ratchet).

A "literal" is a #rgb / #rrggbb hex colour, a three.js 0xRRGGBB colour or an rgb()/rgba()/hsl()/hsla() call in
module.html, outside the regions that are generated from shared sources or data (every @@BEGIN ... @@END marker
pair: shared JS/CSS including shared/theme.css (the token block), data blobs, inlined images, the manifest and the
static outputs). New colours belong in shared/theme.css as --hy-* tokens; a lesson that needs one adds the token
and reads it with var(--hy-...) or HydroTheme.color(...).

tests/theme_hex_baseline.json holds the allowed maximum per module. Lowering a count never fails; raising one
does. After you remove literals, run `python tests/test_theme_ratchet.py --write` to lower the baseline.
`migrated` modules must also stay at or below MIGRATED_MAX (the study's target is 10; the python cells of a lesson
legitimately hold the matplotlib colours of its figures).
"""
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
MODULES = ROOT / "modules"
BASELINE = Path(__file__).resolve().parent / "theme_hex_baseline.json"
MIGRATED_MAX = 15

REGION = re.compile(
    r"(?:/\*|<!--)@@BEGIN (?P<kind>\w+):(?P<arg>[^@]*)@@(?:\*/|-->).*?(?:/\*|<!--)@@END (?P=kind):(?P=arg)@@(?:\*/|-->)",
    re.S,
)
LITERAL = re.compile(r"(?<![\w&])#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})(?![\w-])|\b0x[0-9a-fA-F]{6}\b|(?<![\w.])(?:rgba?|hsla?)\(")


def count_literals(text: str) -> int:
    return len(LITERAL.findall(REGION.sub("", text)))


def counts() -> dict:
    return {p.name: count_literals((p / "module.html").read_text(encoding="utf-8")) for p in sorted(MODULES.iterdir()) if p.is_dir()}


def _baseline() -> dict:
    return json.loads(BASELINE.read_text(encoding="utf-8"))


def test_every_module_has_a_baseline_and_none_is_over_it():
    base, now = _baseline()["max"], counts()
    assert set(now) == set(base), f"modules without a baseline: {sorted(set(now) ^ set(base))}"
    over = {m: (now[m], base[m]) for m in now if now[m] > base[m]}
    assert not over, f"new hard-coded colours (count, allowed): {over}. Use a --hy-* token from shared/theme.css."


def test_migrated_lessons_stay_on_tokens():
    b = _baseline()
    now = counts()
    for m in b["migrated"]:
        assert now[m] <= MIGRATED_MAX, (m, now[m])
        assert 'css:shared/theme.css' in (MODULES / m / "module.html").read_text(encoding="utf-8"), f"{m} must inline shared/theme.css"


def test_the_counter_ignores_generated_regions_and_ids():
    t = '<p style="color:#123456">x</p><a href="#sec-intro">a</a><!--@@BEGIN json:x@@--><script>"#ffffff"</script><!--@@END json:x@@-->'
    t += "/*@@BEGIN css:shared/theme.css@@*/ a{color:#abcdef; b:rgba(0,0,0,.5)} /*@@END css:shared/theme.css@@*/ fill: rgb(1,2,3); c = 0xffffff"
    assert count_literals(t) == 3     # #123456, rgb(, 0xffffff; the href '#sec-intro', the json blob and the token block are ignored


if __name__ == "__main__":
    if "--write" in sys.argv:
        old = _baseline() if BASELINE.exists() else {"migrated": [], "max": {}, "main_before": {}}
        new = counts()
        lowered = {m: new[m] for m in new if m not in old["max"] or new[m] < old["max"][m]}
        old["max"] = {m: min(new[m], old["max"].get(m, new[m])) for m in new}
        BASELINE.write_text(json.dumps(old, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("baseline written;", len(lowered), "entries changed")
    else:
        print(json.dumps(counts(), indent=2))
