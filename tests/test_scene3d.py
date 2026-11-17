"""watershed-runoff, section 5: the real-basin 3-D scene (Fish River, USGS 01013500).

Checks the committed payload, poster and sidecar against each other, against the page and against the numbers the
lesson states; recomputes the polygon area, the D8 routing and the checkpoint answer independently (Python twin of
the shared router); and rebuilds the scene twice when the evidence it is built from is on this machine."""
from __future__ import annotations

import base64
import hashlib
import json
import re
import struct
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from helpers import MODULES, ROOT, SHARED, json_blob, module_text, quiz_item

sys.path.insert(0, str(SHARED))
sys.path.insert(0, str(ROOT / "tools"))
from d8 import d8_path, d8_route  # noqa: E402
import build_scene3d  # noqa: E402

MOD = "watershed-runoff"
D = MODULES / MOD / "data"
T = module_text(MOD)
PAYLOAD_BYTES = (D / "fish-river-scene.json").read_bytes()
P = json.loads(PAYLOAD_BYTES)
PAGE_BEFORE = 109_325            # size of the page at origin/main 9bffa8b, before the real-basin section
BASIN_REF_AREA_KM2 = 2258.5      # basin_ref of the watershed record (2258.516 km2)
EVIDENCE = build_scene3d.DEFAULT_EVIDENCE


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def decode():
    R, C = P["nrows"], P["ncols"]
    runs, mask, i, on = P["mask_runs"], np.zeros(R * C, bool), 0, False
    assert sum(runs) == R * C
    for n in runs:
        if on:
            mask[i:i + n] = True
        i += n
        on = not on
    raw = base64.b64decode(P["h_b64"])
    q = np.frombuffer(raw, dtype="<u2")
    assert len(q) == int(mask.sum())
    z = np.full(R * C, np.nan)
    z[mask] = P["zmin"] + q.astype("float64") * (P["zmax"] - P["zmin"]) / 65535.0
    return mask.reshape(R, C), z.reshape(R, C)


MASK, Z = decode()


def outline_points():
    f = P["outline"]
    pts = [(f[0], f[1])]
    for i in range(2, len(f), 2):
        pts.append((pts[-1][0] + f[i], pts[-1][1] + f[i + 1]))
    return [(x * P["unit_m"], y * P["unit_m"]) for x, y in pts]


# ── the payload ──────────────────────────────────────────────────────────────────────────────────
def test_polygon_area_read_back_from_the_payload_is_within_1_percent_of_basin_ref():
    pts = outline_points()
    x, y = np.array([p[0] for p in pts]), np.array([p[1] for p in pts])
    area = 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))) / 1e6
    assert abs(area / BASIN_REF_AREA_KM2 - 1) < 0.01, area
    assert abs(P["basin_area_km2"] - BASIN_REF_AREA_KM2) < 0.1
    # the terrain cells cover the same area: 8,677 cells of 510 m
    assert abs(int(MASK.sum()) * (P["cell_m"] / 1000) ** 2 / BASIN_REF_AREA_KM2 - 1) < 0.01


def test_mesh_geometry_is_consistent():
    R, C = P["nrows"], P["ncols"]
    assert (R, C) == (153, 116) and max(R, C) <= 160 and P["cell_m"] == 510
    assert P["crs"] == "EPSG:5070" and P["ve"] == 10
    assert np.nanmin(Z) >= P["zmin"] - 1e-9 and np.nanmax(Z) <= P["zmax"] + 1e-9
    o = P["outlet"]
    assert MASK[o["r"], o["c"]] and Z[o["r"], o["c"]] == np.nanmin(Z), "the outlet is the lowest terrain cell"
    # the outline and the channels lie inside the grid's footprint
    W, H = C * P["cell_m"], R * P["cell_m"]
    for x, y in outline_points():
        assert -P["cell_m"] <= x <= W + P["cell_m"] and -P["cell_m"] <= y <= H + P["cell_m"]
    assert P["channels"]["threshold_km2"] == 25.0 and len(P["channels"]["lines"]) >= 20


def test_payload_carries_no_paths_hashes_or_footers():
    text = PAYLOAD_BYTES.decode("utf-8") + (D / "fish-river-poster.attrs.json").read_text(encoding="utf-8")
    blob = re.search(r'<script type="application/json" id="fish-river-scene">(.*?)</script>', T, re.S)[0]
    for s in (text, blob):
        assert "/Users" not in s and "mgalib" not in s and "sha256" not in s.lower()
        assert not re.search(r"[0-9a-f]{40,}", s.replace(P["h_b64"], ""))
    assert "/Users" not in T and "mgalib" not in T


def test_poster_is_a_small_png_of_the_documented_size():
    png = (D / "fish-river-poster.png").read_bytes()
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    w, h = struct.unpack(">II", png[16:24])
    attrs = json.loads((D / "fish-river-poster.attrs.json").read_text(encoding="utf-8"))
    assert (w, h) == (attrs["width"], attrs["height"]) == (P["ncols"] * 3, P["nrows"] * 3)
    assert len(png) <= 50_000, len(png)
    assert len(attrs["alt"]) > 100 and attrs["id"] == "fishPoster"


# ── the page ────────────────────────────────────────────────────────────────────────────────────
def test_page_size_stays_under_the_cap_and_the_added_bytes_are_within_budget():
    size = len((MODULES / MOD / "module.html").read_bytes())
    assert size < 250_000, size
    assert size - PAGE_BEFORE <= 130_000, size - PAGE_BEFORE
    assert len(PAYLOAD_BYTES) <= 40_000


def test_blob_and_poster_in_the_page_are_the_files_on_disk():
    assert json_blob(T, "fish-river-scene") == P
    m = re.search(r'<img [^>]*id="fishPoster"[^>]*>', T)
    assert m, "the poster is in the markup, not created by a script"
    tag = m[0]
    assert 'data-aihydro-scene3d-fallback' in tag and re.search(r'alt="[^"]{100,}"', tag)
    b64 = re.search(r'src="data:image/png;base64,([A-Za-z0-9+/=]+)"', tag)[1]
    assert base64.b64decode(b64) == (D / "fish-river-poster.png").read_bytes()
    # the canvas names its fallback, the poster comes before every script, a visible message is in the markup
    assert re.search(r'<canvas data-aihydro-scene3d data-fallback="#fishPoster" id="fishCanvas"', T)
    assert T.index('id="fishPoster"') < T.index("<script>")
    assert re.search(r'id="fishStatus"[^>]*role="status">Static view:', T)


def test_numbers_the_lesson_states_are_the_payload_numbers():
    sec = T[T.index('id="sec-real"'):T.index('id="sec-runoff"')]
    text = re.sub(r"<[^>]+>", " ", sec)
    R, C = P["nrows"], P["ncols"]
    assert f"{C} columns by {R} rows" in text
    assert f"from {P['zmin']:.0f} to {P['zmax']:.0f} m" in text
    assert f"{P['channels']['threshold_km2']:g} km²" in text and f"{P['cell_m']} m" in text
    assert f"stretched {P['ve']}×" in text and f"exaggeration {P['ve']}×" in text
    f = P["flats"]
    assert f"{f['patches']} flat patches of at least {f['min_km2']:g} km²" in text and f"{f['area_km2']:.1f} km² in all" in text
    assert f"{P['basin_area_km2']:.1f} km²" in text
    assert f"{P['grid_north_to_true_north_deg']:.1f}°" in text
    assert f"{(P['channels']['dem_cell_m'])} m cell" in text
    assert abs(f["area_km2"] / P["basin_area_km2"] - 0.05) < 0.005 and "about 5 %" in text
    assert "17 × 17" in text and P["cell_m"] == 17 * 30


def test_copernicus_credit_is_in_the_references_with_the_manifest_licence_not_in_the_scene():
    prov = json.loads((D / "fish-river-scene.provenance.json").read_text(encoding="utf-8"))
    lic = prov["dem_manifest"]["license"]
    assert lic == "Copernicus DEM License (open use with attribution)" and P["dem"]["licence"] == lic
    refs = T[T.index('id="sec-prov"'):]
    assert "Copernicus Global Digital Elevation Model" in refs and "10.5270/ESA-c5d3d65" in refs and lic in refs
    scene = T[T.index('<div class="real-wrap"'):T.index('id="fishStatus"')]
    assert "Copernicus" not in scene
    assert "Copernicus" not in re.search(r'id="fishLabel" hidden>(.*?)</div>', T, re.S)[1]
    assert "10.5270/ESA-c5d3d65" in (ROOT / "CITATIONS.verified.md").read_text(encoding="utf-8")


def test_synthetic_content_and_labels_remain():
    assert "SYNTHETIC" in T and "Orbit a SYNTHETIC watershed in 3-D" in T
    assert 'id="terrainCanvas"' in T and 'id="routingCanvas"' in T
    assert "derived, not mapped" in T and "Lakes are flat" in T and "The edge is the divide" in T


# ── routing, recomputed with the Python twin ────────────────────────────────────────────────────────
def route():
    R, C = P["nrows"], P["ncols"]
    wall = P["zmax"] + 100
    rows = [[float(Z[r, c]) if MASK[r, c] else wall for c in range(C)] for r in range(R)]
    o = P["outlet"]
    return d8_route(rows, float(P["cell_m"]), outlet=(o["r"], o["c"]), epsilon=1e-4)


def test_every_terrain_cell_drains_to_the_outlet_without_leaving_the_basin():
    R, C = P["nrows"], P["ncols"]
    rt = route()
    o = P["outlet"]["r"] * C + P["outlet"]["c"]
    cells = [int(i) for i in np.flatnonzero(MASK.ravel())]
    for i in cells:
        path = d8_path(rt["rec"], i)
        assert path[-1] == o, i
        assert all(MASK.ravel()[j] for j in path), f"path from {i} crosses the mask"


def test_checkpoint_answer_is_the_independent_path_length_from_the_highest_cell():
    R, C, cell = P["nrows"], P["ncols"], P["cell_m"]
    rt = route()
    flat = np.where(MASK.ravel(), Z.ravel(), -np.inf)
    hi = int(np.argmax(flat))                                  # first maximum, row-major, as the page takes it
    path = d8_path(rt["rec"], hi)
    length = 0.0
    for a, b in zip(path, path[1:]):
        diag = (a // C != b // C) and (a % C != b % C)
        length += cell * (2 ** 0.5 if diag else 1.0)
    assert quiz_item(MOD, "q6")["expected"] == pytest.approx(length / 1000, abs=1e-9)
    assert 20 < length / 1000 < 400
    assert "Give 1 decimal" in quiz_item(MOD, "q6")["prompt"] and "highest cell" in quiz_item(MOD, "q6")["prompt"]


# ── the builder ─────────────────────────────────────────────────────────────────────────────────────
def test_sidecar_describes_the_committed_outputs_and_is_scrubbed():
    path = D / "fish-river-scene.provenance.json"
    s = json.loads(path.read_text(encoding="utf-8"))
    text = path.read_text(encoding="utf-8")
    assert s["schema"] == "hydrofigs.provenance/2" and s["synthetic"] is False and "generated_at" not in s
    assert "/Users" not in text and "mgalib" not in text
    assert [a["sha256"] for a in s["artifacts"] if a["role"] in ("polygon", "dem")] == [build_scene3d.EXPECT_POLYGON_SHA, build_scene3d.EXPECT_DEM_SHA]
    for a in s["artifacts"]:
        assert a["path"].startswith(build_scene3d.WORKSPACE_PREFIX) and re.fullmatch(r"[0-9a-f]{64}", a["sha256"])
    for o in s["outputs"]:
        assert sha((D / o["file"]).read_bytes()) == o["sha256"] and (D / o["file"]).stat().st_size == o["bytes"], o["file"]
    assert s["script_sha256"] == sha((ROOT / "tools" / "build_scene3d.py").read_bytes()), "rebuild after editing the builder"
    prm = s["parameters"]
    assert prm["channels"]["threshold_km2"] == 25.0 and prm["vertical_exaggeration"] == 10 and prm["mesh_cell_m"] == 510
    assert prm["channels"]["tool"].startswith("pysheds 0.5")
    assert all(c["ok"] for c in s["checks"])


@pytest.mark.skipif(not EVIDENCE.exists(), reason="the DEMO-1 evidence is not on this machine (CI): the committed files are checked against each other above")
def test_builder_is_deterministic_and_the_committed_files_are_its_output(tmp_path):
    runs = []
    for k in range(2):
        out = tmp_path / f"run{k}"
        r = subprocess.run([sys.executable, "-s", "-E", str(ROOT / "tools" / "build_scene3d.py"), "--out", str(out)],
                           capture_output=True, text=True, cwd=ROOT)
        assert r.returncode == 0, r.stderr[-2000:]
        runs.append({p.name: sha(p.read_bytes()) for p in sorted(out.iterdir())})
    assert runs[0] == runs[1], "two builds differ"
    assert set(runs[0]) == {"fish-river-scene.json", "fish-river-poster.png", "fish-river-poster.attrs.json", "fish-river-scene.provenance.json"}
    for name, h in runs[0].items():
        assert sha((D / name).read_bytes()) == h, f"{name} on disk is not the builder's output"
    r = subprocess.run([sys.executable, "-s", "-E", str(ROOT / "tools" / "build_scene3d.py"), "--check"], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout[-500:]


def test_builder_refuses_wrong_inputs(tmp_path):
    # a copy of the evidence layout with a different polygon must stop the build before anything is written
    for rel in build_scene3d.FILES.values():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("{}")
    with pytest.raises(SystemExit):
        build_scene3d.load_inputs(tmp_path)


def test_block_mean_and_run_codecs_round_trip():
    a = np.arange(36, dtype="float32").reshape(6, 6)
    a[0, :3] = np.nan
    m = build_scene3d.block_mean(a, 3, 0.5)
    assert m.shape == (2, 2) and m[0, 0] == pytest.approx(10.0)           # mean of the six values present
    assert np.isnan(build_scene3d.block_mean(a, 3, 0.8)[0, 0])             # too little cover: not terrain
    mask = np.array([[0, 1, 1], [1, 0, 0], [0, 0, 1]], bool)
    assert (build_scene3d.runs_decode(build_scene3d.runs_encode(mask), 9).reshape(3, 3) == mask).all()
    pts = [(10, 20), (13, 18), (13, 30)]
    assert build_scene3d.dec_line(build_scene3d.enc_line(pts)) == pts
