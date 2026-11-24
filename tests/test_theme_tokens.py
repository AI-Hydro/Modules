"""T1: automated contrast and colour-vision check over the shared theme tokens (shared/theme.css).

Gates (WCAG 2.x relative luminance): text tokens >= 4.5:1 on --hy-bg and --hy-surface, body text (--hy-fg) >= 7:1,
graphics (axis, outline, series, rain) >= 3:1 on bg, surface and stage. Series must stay separable under simulated
protan/deutan/tritan vision (Machado et al. 2009, severity 1.0; CIE Lab delta E*ab >= 10) in light and dark; the two
high-contrast sets cannot get there by hue alone, so they must define distinct dash patterns instead.
APCA Lc is computed and printed (python tests/test_theme_tokens.py) but not gated: it is not part of WCAG 2.

Run as a script to print the contrast table used in the PR description.
"""
import itertools
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CSS = (ROOT / "shared" / "theme.css").read_text(encoding="utf-8")

THEMES = ("light", "dark", "hc-dark", "hc-light")
HEX = re.compile(r"^#([0-9a-fA-F]{6})$")
TEXT = ("fg", "heading", "fg-muted", "link", "accent", "accent-strong", "ok", "warn", "err")
GRAPHIC = ("axis", "outline", "series-1", "series-2", "series-3", "series-4", "series-5", "rain")
SURFACES = ("bg", "surface")


def _block(selector: str, css: str = CSS) -> dict:
    """Custom properties declared in the first rule whose selector is exactly `selector`."""
    m = re.search(r"(?:^|[\s}])" + re.escape(selector) + r"\s*\{(?P<body>[^{}]*)\}", css)
    assert m, f"no rule {selector!r} in shared/theme.css"
    return {k: v.strip() for k, v in re.findall(r"--(hy-[\w-]+)\s*:\s*([^;]+);", m["body"])}


def tokens(theme: str) -> dict:
    """Effective tokens of a theme: the :root defaults overlaid with the theme's own block."""
    base = _block(":root")
    if theme == "light":
        return base
    return {**base, **_block(f':root[data-aihydro-theme="{theme}"]')}


def _rgb(h: str):
    m = HEX.match(h)
    assert m, f"not a #rrggbb colour: {h!r}"
    return tuple(int(m[1][i:i + 2], 16) for i in (0, 2, 4))


def _lin(c: int) -> float:
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def over(rgba: str, base: str) -> str:
    """Composite a token like rgba(0,102,138,0.08) over an opaque #rrggbb and return #rrggbb."""
    m = re.match(r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\s*\)", rgba)
    assert m, f"not an rgba() colour: {rgba!r}"
    a = float(m[4])
    fg = tuple(int(m[i]) for i in (1, 2, 3))
    bg = _rgb(base)
    return "#%02x%02x%02x" % tuple(round(fg[i] * a + bg[i] * (1 - a)) for i in range(3))


def luminance(h: str) -> float:
    r, g, b = (_lin(c) for c in _rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a: str, b: str) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def apca(text: str, bg: str) -> float:
    """APCA-W3 0.0.98G-4g lightness contrast Lc (positive: dark text on light; negative: light on dark)."""
    def y(h):
        r, g, b = (c / 255 for c in _rgb(h))
        v = 0.2126729 * r ** 2.4 + 0.7151522 * g ** 2.4 + 0.0721750 * b ** 2.4
        return v if v > 0.022 else v + (0.022 - v) ** 1.414
    yt, yb = y(text), y(bg)
    if abs(yb - yt) < 0.0005:
        return 0.0
    if yb > yt:
        s = (yb ** 0.56 - yt ** 0.57) * 1.14
        return 0.0 if s < 0.1 else (s - 0.027) * 100
    s = (yb ** 0.65 - yt ** 0.62) * 1.14
    return 0.0 if s > -0.1 else (s + 0.027) * 100


# Machado, Oliveira & Fernandes (2009), severity 1.0, applied to linear RGB
_CVD = {
    "protan": ((0.152286, 1.052583, -0.204868), (0.114503, 0.786281, 0.099216), (-0.003882, -0.048116, 1.051998)),
    "deutan": ((0.367322, 0.860646, -0.227968), (0.280085, 0.672501, 0.047413), (-0.011820, 0.042940, 0.968881)),
    "tritan": ((1.255528, -0.076749, -0.178779), (-0.078411, 0.930809, 0.147602), (0.004733, 0.691367, 0.303900)),
}


def _lab(rgb_lin):
    r, g, b = rgb_lin
    x = (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / 0.95047
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    z = (0.0193339 * r + 0.1191920 * g + 0.9503041 * b) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 216 / 24389 else (24389 / 27 * t + 16) / 116
    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def _sim(h: str, kind: str):
    lin = [_lin(c) for c in _rgb(h)]
    if kind != "normal":
        m = _CVD[kind]
        lin = [min(1.0, max(0.0, sum(m[i][j] * lin[j] for j in range(3)))) for i in range(3)]
    return _lab(lin)


def delta_e(a: str, b: str, kind: str) -> float:
    la, lb = _sim(a, kind), _sim(b, kind)
    return sum((p - q) ** 2 for p, q in zip(la, lb)) ** 0.5


def min_separation(cols, kind):
    return min(delta_e(a, b, kind) for a, b in itertools.combinations(cols, 2))


def series(t):
    return [t[f"hy-series-{i}"] for i in range(1, 6)]


@pytest.mark.parametrize("theme", THEMES)
def test_every_theme_overrides_only_known_tokens_and_restyles_the_full_palette(theme):
    base = set(_block(":root"))
    if theme == "light":
        return
    own = set(_block(f':root[data-aihydro-theme="{theme}"]'))
    assert own - base == set(), f"{theme} defines unknown tokens {sorted(own - base)}"
    # theme-independent tokens (brand logo, figure paper) may be omitted; everything else must be restated
    fixed = {"hy-logo-a", "hy-logo-b", "hy-logo-eye", "hy-figure-bg", "hy-figure-fg", "hy-dash-1", "hy-dash-2", "hy-dash-3", "hy-dash-4", "hy-dash-5"}
    fixed |= {k for k in base if k.startswith("hy-plate")}
    assert base - own - fixed == set(), f"{theme} lacks {sorted(base - own - fixed)}"


@pytest.mark.parametrize("theme", THEMES)
def test_text_tokens_reach_4_5_on_page_and_card_and_body_reaches_7(theme):
    t = tokens(theme)
    bad = []
    for name in TEXT:
        for s in SURFACES:
            r = ratio(t[f"hy-{name}"], t[f"hy-{s}"])
            floor = 7.0 if name == "fg" else 4.5
            if r < floor:
                bad.append((name, s, round(r, 2)))
    for name in ("brand-1", "brand-2"):                      # gradient headings are text
        for s in SURFACES:
            if ratio(t[f"hy-{name}"], t[f"hy-{s}"]) < 4.5:
                bad.append((name, s, round(ratio(t[f"hy-{name}"], t[f"hy-{s}"]), 2)))
    for a, b in (("on-accent", "btn-1"), ("on-accent", "btn-2"), ("tip-fg", "tip-bg")):
        if ratio(t[f"hy-{a}"], t[f"hy-{b}"]) < 4.5:
            bad.append((a, b, round(ratio(t[f"hy-{a}"], t[f"hy-{b}"]), 2)))
    assert not bad, f"{theme}: {bad}"


# text that sits on a tinted panel: (text token, tint token, base surfaces). The tint is composited over each base.
TINTED = (("accent", "accent-soft"), ("link", "link-soft"), ("ok", "ok-soft"), ("fg", "accent-soft"), ("fg-muted", "accent-soft"))


@pytest.mark.parametrize("theme", THEMES)
def test_text_on_tinted_panels_reaches_4_5(theme):
    t = tokens(theme)
    bad = []
    for name, tint in TINTED:
        for s in SURFACES:
            tv = t[f"hy-{tint}"]
            bg = over(tv, t[f"hy-{s}"]) if tv.startswith("rgba") else t[f"hy-{s}"]
            r = ratio(t[f"hy-{name}"], bg)
            if r < 4.5:
                bad.append((name, tint, s, round(r, 2)))
    # a number being dragged: accent-strong on the stronger tint
    for s in SURFACES:
        tv = t["hy-accent-line"]
        bg = over(tv, t[f"hy-{s}"]) if tv.startswith("rgba") else t[f"hy-{s}"]
        if ratio(t["hy-accent-strong"], bg) < 4.5:
            bad.append(("accent-strong", "accent-line", s, round(ratio(t["hy-accent-strong"], bg), 2)))
    assert not bad, f"{theme}: {bad}"


@pytest.mark.parametrize("theme", THEMES)
def test_graphic_tokens_reach_3_on_page_card_and_stage(theme):
    t = tokens(theme)
    bad = []
    for name in GRAPHIC:
        for s in SURFACES + ("stage",):
            r = ratio(t[f"hy-{name}"], t[f"hy-{s}"])
            if r < 3.0:
                bad.append((name, s, round(r, 2)))
    assert not bad, f"{theme}: {bad}"


@pytest.mark.parametrize("theme", ("light", "dark"))
@pytest.mark.parametrize("kind", ("normal", "protan", "deutan", "tritan"))
def test_series_stay_separable_under_colour_vision_deficiency(theme, kind):
    sep = min_separation(series(tokens(theme)), kind)
    assert sep >= 10, f"{theme}/{kind}: minimum series separation {sep:.1f} < 10"


@pytest.mark.parametrize("theme", ("hc-dark", "hc-light"))
def test_high_contrast_series_are_told_apart_by_dash_pattern(theme):
    t = tokens(theme)
    dashes = [t[f"hy-dash-{i}"] for i in range(1, 6)]
    assert len(set(dashes)) == 5, f"{theme}: dash patterns must be distinct, got {dashes}"
    for kind in ("normal", "protan", "deutan", "tritan"):     # hue alone is not enough here; dashes carry it
        assert min_separation(series(t), kind) > 0


def test_plate_tokens_are_readable_on_the_plate_and_do_not_change_with_the_theme():
    """The dark map/scene/diagram plate is theme-independent: text >= 4.5:1, strokes and markers >= 3:1 on it."""
    base = tokens("light")
    plate = base["hy-plate"]
    for name in ("fg", "muted", "ok", "blue"):
        assert ratio(base[f"hy-plate-{name}"], plate) >= 4.5, name
    for name in ("line", "stream", "drop", "focus"):
        assert ratio(base[f"hy-plate-{name}"], plate) >= 3.0, name
    cell = over(base["hy-plate-cell"], plate)                 # text printed on a diagram cell
    assert ratio(base["hy-plate-muted"], cell) >= 4.5
    assert ratio(base["hy-plate-stream"], cell) >= 4.5
    assert ratio(base["hy-plate-ok"], over(base["hy-plate-cell-lo"], plate)) >= 4.5
    for theme in THEMES:                                       # no themed block restates a plate token
        if theme != "light":
            own = _block(f':root[data-aihydro-theme="{theme}"]')
            assert not [k for k in own if k.startswith("hy-plate")], theme


def test_light_and_dark_use_solid_series_lines():
    for theme in ("light", "dark"):
        t = tokens(theme)
        assert {t[f"hy-dash-{i}"] for i in range(1, 6)} == {"none"}


def test_prefers_dark_block_matches_the_explicit_dark_block():
    m = re.search(r"@media \(prefers-color-scheme: dark\)\s*\{\s*:root:not\(\[data-aihydro-theme\]\)\s*\{(?P<b>[^{}]*)\}", CSS)
    assert m, "prefers-color-scheme: dark fallback block missing"
    auto = {k: v.strip() for k, v in re.findall(r"--(hy-[\w-]+)\s*:\s*([^;]+);", m["b"])}
    explicit = tokens("dark")
    for k, v in auto.items():
        assert explicit[k] == v, (k, v, explicit[k])
    for k in explicit:
        if k not in auto:                                    # theme-independent tokens (logo, figure paper, dashes)
            assert k in tokens("light") and tokens("light")[k] == explicit[k], k


def test_print_block_is_the_light_theme():
    m = re.search(r"@media print\s*\{\s*:root, :root\[data-aihydro-theme\]\s*\{(?P<b>[^{}]*)\}", CSS)
    assert m, "print block missing"
    pr = {k: v.strip() for k, v in re.findall(r"--(hy-[\w-]+)\s*:\s*([^;]+);", m["b"])}
    light = tokens("light")
    for k, v in pr.items():
        if k in ("hy-glow-1", "hy-glow-2", "hy-shadow"):     # print drops the page glow and the shadow
            continue
        assert light[k] == v, (k, v, light[k])


def test_theme_tokens_are_hex_or_known_forms():
    for theme in THEMES:
        for k, v in tokens(theme).items():
            if k.startswith(("hy-bg", "hy-fg")) or k in ("hy-surface", "hy-inset", "hy-axis", "hy-outline", "hy-stage"):
                assert HEX.match(v), (theme, k, v)


def table():
    rows = []
    for theme in THEMES:
        t = tokens(theme)
        for name, floor in (("fg", 7), ("fg-muted", 4.5), ("link", 4.5), ("accent", 4.5), ("ok", 4.5), ("warn", 4.5), ("err", 4.5),
                            ("axis", 3), ("outline", 3), ("series-1", 3), ("series-2", 3), ("series-3", 3), ("series-4", 3), ("series-5", 3), ("rain", 3)):
            rows.append((theme, name, t[f"hy-{name}"], ratio(t[f"hy-{name}"], t["hy-bg"]), ratio(t[f"hy-{name}"], t["hy-surface"]), floor, apca(t[f"hy-{name}"], t["hy-bg"])))
    return rows


if __name__ == "__main__":
    print(f"{'theme':9} {'token':9} {'value':8} {'on bg':>6} {'on surf':>7} {'floor':>5} {'APCA Lc':>8}")
    for th, n, v, a, b, f, lc in table():
        print(f"{th:9} {n:9} {v:8} {a:6.2f} {b:7.2f} {f:5} {lc:8.1f}")
    for th in ("light", "dark"):
        print(th, {k: round(min_separation(series(tokens(th)), k), 1) for k in ("normal", "protan", "deutan", "tritan")})
