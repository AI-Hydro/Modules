#!/usr/bin/env python3
"""Build the real-basin 3-D scene of the watershed-runoff lesson (Fish River, USGS 01013500).

Deterministic: the same inputs and the same library versions give byte-identical outputs
(`--check` rebuilds in memory and compares them with the files on disk).

Inputs (read-only, from the AI-Hydro workspace, by default under
docs/vision-2040/evidence/agu26-demo-1/live; their sha256 values are verified before anything is built):
  workspace/watershed_01013500.geojson          delineated basin polygon (EPSG:4326)
  records/records/watershed.c1ba6d010c79.json   watershed record: area_km2 and the basin_ref geometry digest
  home/.aihydro/cache/data/6455bad6e713c991ee268efd.nc (+ .manifest.json)
                                                Copernicus GLO-30 DEM (EPSG:4326), masked to the polygon

Steps: project the DEM to EPSG:5070 (NAD83 / Conus Albers, equal-area), crop to the basin, block-mean decimate
to a square grid of at most GRID_MAX cells per side, quantize to Uint16, derive channels with pysheds on a
DEFLT_CELL_M grid at a stated contributing-area threshold, simplify the outline and channels
(Douglas-Peucker), render a plan-view hillshade poster, and write

  modules/watershed-runoff/data/fish-river-scene.json            the payload (inlined as a json: blob)
  modules/watershed-runoff/data/fish-river-poster.png            the poster
  modules/watershed-runoff/data/fish-river-poster.attrs.json     attributes of the <img> tag (img: marker)
  modules/watershed-runoff/data/fish-river-scene.provenance.json hydrofigs.provenance/2-style sidecar

The payload and the poster carry no file paths, no hashes and no provenance footer: the only attribution
the lesson shows is the Copernicus credit in its References. Paths and hashes live only in the sidecar,
and only as repository-relative paths.

Run with an interpreter that has numpy, scipy, xarray, rasterio, pyproj, shapely, pysheds and matplotlib
(the AI-Hydro workspace interpreter /opt/miniconda3/bin/python; ~/.aihydro/venvs/tools-2.8 also has
pysheds 0.5). Use `python -s -E`.

Usage:  python tools/build_scene3d.py            write the four files
        python tools/build_scene3d.py --check    exit 1 if a file on disk differs from a fresh build
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
MODULE = ROOT / "modules" / "watershed-runoff" / "data"
DEFAULT_EVIDENCE = Path("/Users/mgalib/Documents/AI-Hydro/docs/vision-2040/evidence/agu26-demo-1/live")
WORKSPACE_PREFIX = "docs/vision-2040/evidence/agu26-demo-1/live/"   # repository-relative names in the sidecar

# sha256 values the build refuses to run without (docs/vision-2040/findings/threejs-studio-feasibility-2026-11-17.md,
# section 4, and the figure V1 provenance record)
EXPECT_POLYGON_SHA = "60c713d4d3e23c15c5d882a7603dde0032c36f487026abc36aec41c611addc0a"
EXPECT_DEM_SHA = "1858528d4116a87e26a0bd975bd9ba978159890551d650e2f2d9fd7591d1a1f4"
EXPECT_GEOM_DIGEST = "sha256:c19f8fcefce76767074c28d4cefcdf657030cfca31bf5d1cbbc8a5f6eb6756c6"

FILES = {
    "polygon": "workspace/watershed_01013500.geojson",
    "record": "records/records/watershed.c1ba6d010c79.json",
    "dem": "home/.aihydro/cache/data/6455bad6e713c991ee268efd.nc",
    "manifest": "home/.aihydro/cache/data/6455bad6e713c991ee268efd.manifest.json",
}

# ---- build parameters (all of them are recorded in the sidecar) ------------------------------------
CRS = "EPSG:5070"
WARP_CELL_M = 30.0          # the DEM is warped to a 30 m grid first (its native 1 arcsec is about 21 x 31 m here)
BLOCK = 17                  # block-mean factor: 17 x 30 m = 510 m mesh cells
MIN_COVER = 0.5             # a mesh cell is terrain when at least half of its 30 m cells hold data
GRID_MAX = 160              # at most this many cells per side
VERT_EXAG = 10              # vertical exaggeration printed in the lesson
CHANNEL_CELL_M = 90.0       # pysheds runs on the 30 m grid block-averaged by 3
CHANNEL_THRESHOLD_KM2 = 25.0
OUTLINE_TOL_M = 120.0       # Douglas-Peucker tolerance of the divide
CHANNEL_TOL_M = 120.0       # Douglas-Peucker tolerance of the channels
UNIT_M = 10                 # vector coordinates are integers in units of 10 m
FLAT_MIN_KM2 = 1.0          # flat patches (lakes in the DEM) counted from this size up
POSTER_PX_PER_CELL = 3
POSTER_COLOURS = 80


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def dump(obj) -> bytes:
    """Canonical JSON: compact, sorted keys, UTF-8, trailing newline."""
    return (json.dumps(obj, separators=(",", ":"), sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


# ---- inputs -----------------------------------------------------------------------------------------
def load_inputs(evidence: Path):
    import xarray as xr
    paths = {k: evidence / v for k, v in FILES.items()}
    shas = {k: sha256_file(p) for k, p in paths.items()}
    if shas["polygon"] != EXPECT_POLYGON_SHA:
        raise SystemExit(f"polygon sha256 {shas['polygon']} != {EXPECT_POLYGON_SHA}")
    if shas["dem"] != EXPECT_DEM_SHA:
        raise SystemExit(f"DEM sha256 {shas['dem']} != {EXPECT_DEM_SHA}")
    man = json.loads(paths["manifest"].read_text(encoding="utf-8"))[0]
    if man["data_sha256"] != shas["dem"]:
        raise SystemExit("DEM manifest data_sha256 does not match the file")
    rec = json.loads(paths["record"].read_text(encoding="utf-8"))
    ref = rec["evidence"]["data"]["basin_ref"]
    if ref["geometry_digest"] != EXPECT_GEOM_DIGEST or man["geom_id"] != ref["geometry_digest"]:
        raise SystemExit("the DEM manifest geom_id and the watershed record geometry_digest disagree")
    poly = json.loads(paths["polygon"].read_text(encoding="utf-8"))
    ds = xr.open_dataset(paths["dem"])
    dem = ds["dem"].values.astype("float32")
    lon, lat = ds["x"].values.astype("float64"), ds["y"].values.astype("float64")
    ds.close()
    return dict(paths=paths, shas=shas, manifest=man, record=rec, ref=ref, poly=poly, dem=dem, lon=lon, lat=lat,
                evidence=evidence)


# ---- projection and decimation ------------------------------------------------------------------------
def warp_to_albers(dem, lon, lat):
    """DEM (rows north to south) -> EPSG:5070 grid of WARP_CELL_M, bilinear, NaN outside the data."""
    from affine import Affine
    from pyproj import Transformer
    from rasterio.crs import CRS as RCRS
    from rasterio.warp import Resampling, reproject
    dx = (lon[-1] - lon[0]) / (len(lon) - 1)
    dy = (lat[0] - lat[-1]) / (len(lat) - 1)          # positive
    src_tf = Affine(dx, 0, lon[0] - dx / 2, 0, -dy, lat[0] + dy / 2)
    tr = Transformer.from_crs("EPSG:4326", CRS, always_xy=True)
    xs, ys = [], []
    for lo, la in ((lon[0], lat[0]), (lon[-1], lat[0]), (lon[0], lat[-1]), (lon[-1], lat[-1])):
        x, y = tr.transform(lo, la)
        xs.append(x); ys.append(y)
    # also the edge midpoints: the rectangle bows in Albers
    for lo in np.linspace(lon[0], lon[-1], 9):
        for la in (lat[0], lat[-1]):
            x, y = tr.transform(lo, la); xs.append(x); ys.append(y)
    x0 = math.floor(min(xs) / WARP_CELL_M) * WARP_CELL_M
    y1 = math.ceil(max(ys) / WARP_CELL_M) * WARP_CELL_M
    ncol = int(math.ceil((max(xs) - x0) / WARP_CELL_M))
    nrow = int(math.ceil((y1 - min(ys)) / WARP_CELL_M))
    dst = np.full((nrow, ncol), np.nan, dtype="float32")
    dst_tf = Affine(WARP_CELL_M, 0, x0, 0, -WARP_CELL_M, y1)
    reproject(dem, dst, src_transform=src_tf, src_crs=RCRS.from_epsg(4326), src_nodata=np.nan,
              dst_transform=dst_tf, dst_crs=RCRS.from_string(CRS), dst_nodata=np.nan,
              resampling=Resampling.bilinear)
    return dst, x0, y1


def crop_to_data(a, x0, y1):
    rows = np.where(np.isfinite(a).any(axis=1))[0]
    cols = np.where(np.isfinite(a).any(axis=0))[0]
    r0, r1, c0, c1 = rows[0], rows[-1] + 1, cols[0], cols[-1] + 1
    # pad to a whole number of BLOCK x BLOCK blocks, anchored at the top-left
    nr = int(math.ceil((r1 - r0) / BLOCK)) * BLOCK
    nc = int(math.ceil((c1 - c0) / BLOCK)) * BLOCK
    out = np.full((nr, nc), np.nan, dtype="float32")
    sub = a[r0:r1, c0:c1]
    out[: sub.shape[0], : sub.shape[1]] = sub
    return out, x0 + c0 * WARP_CELL_M, y1 - r0 * WARP_CELL_M


def block_mean(a, f, min_cover):
    r, c = a.shape[0] // f, a.shape[1] // f
    b = a[: r * f, : c * f].reshape(r, f, c, f)
    ok = np.isfinite(b)
    n = ok.sum(axis=(1, 3))
    s = np.where(ok, b, 0.0).sum(axis=(1, 3), dtype="float64")
    with np.errstate(invalid="ignore", divide="ignore"):
        m = np.where(n >= min_cover * f * f, s / np.maximum(n, 1), np.nan)
    return m


# ---- helpers on the mesh ------------------------------------------------------------------------------
def largest_component(valid, keep_point):
    from scipy import ndimage
    lab, n = ndimage.label(valid, structure=np.ones((3, 3), int))
    return lab == lab[keep_point], n


def runs_encode(valid):
    """Run lengths of the row-major mask, alternating masked, valid, masked, ... (first run may be 0)."""
    flat = valid.ravel()
    runs, cur, n = [], False, 0
    for v in flat:
        if bool(v) == cur:
            n += 1
        else:
            runs.append(n); cur = bool(v); n = 1
    runs.append(n)
    return runs


def runs_decode(runs, size):
    out = np.zeros(size, dtype=bool)
    i, cur = 0, False
    for n in runs:
        if cur:
            out[i:i + n] = True
        i += n; cur = not cur
    return out


def dp_simplify(line, tol):
    from shapely.geometry import LineString
    if len(line) < 3:
        return line
    s = LineString(line).simplify(tol, preserve_topology=False)
    return [tuple(p) for p in s.coords]


def enc_line(pts_units):
    """[x0, y0, dx1, dy1, ...] with integer units."""
    out = [int(pts_units[0][0]), int(pts_units[0][1])]
    for (xa, ya), (xb, yb) in zip(pts_units, pts_units[1:]):
        out += [int(xb - xa), int(yb - ya)]
    return out


def dec_line(flat):
    pts = [(flat[0], flat[1])]
    for i in range(2, len(flat), 2):
        pts.append((pts[-1][0] + flat[i], pts[-1][1] + flat[i + 1]))
    return pts


def shoelace_m2(xy_m):
    x = np.array([p[0] for p in xy_m], dtype="float64"); y = np.array([p[1] for p in xy_m], dtype="float64")
    return 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))


# ---- channels with pysheds ------------------------------------------------------------------------------
def derive_channels(dem30, x0, y0):
    """Channel polylines from D8 flow accumulation of the 90 m DEM; threshold in km2.

    pysheds: fill_pits, fill_depressions, resolve_flats, D8 flow direction, accumulation. A channel cell is a
    cell with at least CHANNEL_THRESHOLD_KM2 draining through it. Segments start at channel heads and
    confluences and end at the next confluence (or the outlet), so they join without gaps.
    """
    import pyproj
    from affine import Affine
    from pysheds.sgrid import sGrid
    from pysheds.sview import Raster, ViewFinder
    f = int(round(CHANNEL_CELL_M / WARP_CELL_M))
    r, c = dem30.shape[0] // f, dem30.shape[1] // f
    b = block_mean(dem30[: r * f, : c * f], f, 0.5)
    nodata = -9999.0
    arr = np.where(np.isfinite(b), b, nodata).astype("float64")
    vf = ViewFinder(affine=Affine(CHANNEL_CELL_M, 0, x0, 0, -CHANNEL_CELL_M, y0), shape=arr.shape, nodata=nodata,
                    crs=pyproj.CRS.from_epsg(5070))
    dem = Raster(arr, vf)
    grid = sGrid.from_raster(dem)
    pit = grid.fill_pits(dem)
    flooded = grid.fill_depressions(pit)
    inflated = grid.resolve_flats(flooded)
    dirmap = (64, 128, 1, 2, 4, 8, 16, 32)        # N NE E SE S SW W NW (pysheds default)
    fdir = grid.flowdir(inflated, dirmap=dirmap, nodata_out=0)
    acc = np.asarray(grid.accumulation(fdir, dirmap=dirmap))
    fd = np.asarray(fdir)
    thr = CHANNEL_THRESHOLD_KM2 * 1e6 / (CHANNEL_CELL_M ** 2)
    chan = (acc >= thr) & (arr != nodata)
    offs = {64: (-1, 0), 128: (-1, 1), 1: (0, 1), 2: (1, 1), 4: (1, 0), 8: (1, -1), 16: (0, -1), 32: (-1, -1)}
    R, C = chan.shape
    ds = {}
    indeg = {}
    for i, j in zip(*np.nonzero(chan)):
        o = offs.get(int(fd[i, j]))
        if o is None:
            continue
        ni, nj = i + o[0], j + o[1]
        if 0 <= ni < R and 0 <= nj < C and chan[ni, nj]:
            ds[(int(i), int(j))] = (int(ni), int(nj))
            indeg[(ni, nj)] = indeg.get((int(ni), int(nj)), 0) + 1
    cells = sorted((int(i), int(j)) for i, j in zip(*np.nonzero(chan)))
    lines = []
    for cell in cells:
        if indeg.get(cell, 0) == 1:
            continue                              # inside a reach: a segment starts at heads and confluences
        path = [cell]
        cur = cell
        while cur in ds:
            cur = ds[cur]
            path.append(cur)
            if indeg.get(cur, 0) != 1:
                break
        if len(path) >= 2:
            lines.append([(x0 + (j + 0.5) * CHANNEL_CELL_M, y0 - (i + 0.5) * CHANNEL_CELL_M) for i, j in path])
    return lines, int(chan.sum()), float(thr), int(acc.max())


def flat_patches(dem30):
    """Patches of exactly constant elevation (lakes are flat in the DEM), counted from FLAT_MIN_KM2 up."""
    from scipy import ndimage
    ok = np.isfinite(dem30)
    big = np.where(ok, dem30, np.nan)
    mx = ndimage.maximum_filter(np.where(ok, dem30, -1e9), size=3)
    mn = ndimage.minimum_filter(np.where(ok, dem30, 1e9), size=3)
    flat = ok & (mx == mn)
    lab, n = ndimage.label(flat)
    sizes = np.bincount(lab.ravel())[1:]
    cell_km2 = WARP_CELL_M ** 2 / 1e6
    big_ones = sizes[sizes * cell_km2 >= FLAT_MIN_KM2]
    return int(len(big_ones)), float(big_ones.sum() * cell_km2), float(ok.sum() * cell_km2)


# ---- poster -----------------------------------------------------------------------------------------------
def compass(east, north):
    """Eight-point compass word for a displacement (east, north)."""
    names = ["east", "north-east", "north", "north-west", "west", "south-west", "south", "south-east"]
    return names[int(round(math.degrees(math.atan2(north, east)) / 45.0)) % 8]


def hillshade(z, cell, ve):
    zf = np.where(np.isfinite(z), z, np.nan)
    pad = np.pad(zf, 1, mode="edge")
    # nearest valid value for the border of the mesh (NaN neighbours take the cell's own height)
    own = np.pad(np.where(np.isfinite(z), z, 0.0), 1, mode="edge")
    pad = np.where(np.isfinite(pad), pad, own)
    zx = (pad[1:-1, 2:] - pad[1:-1, :-2]) / (2 * cell) * ve
    zy = (pad[2:, 1:-1] - pad[:-2, 1:-1]) / (2 * cell) * ve
    L = np.array([-0.55, -0.55, 0.63])
    n = np.sqrt(zx * zx + zy * zy + 1.0)
    return np.clip((-zx * L[0] - zy * L[1] + L[2]) / n, 0, 1)


def render_poster(z, cell, outline_m, lines_m, x0, y0, ve, thr_km2, conv_deg):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image
    R, C = z.shape
    s = POSTER_PX_PER_CELL
    W, H = C * s, R * s
    lo, hi = np.nanmin(z), np.nanmax(z)
    base = matplotlib.colormaps["viridis"]((np.where(np.isfinite(z), z, lo) - lo) / (hi - lo))[..., :3]
    shade = hillshade(z, cell, ve)
    rgb = base * (0.35 + 0.9 * shade[..., None])
    rgb = np.clip(rgb, 0, 1)
    bg = np.array([10, 22, 34]) / 255.0
    img = np.where(np.isfinite(z)[..., None], rgb, bg)
    dpi = 100
    fig = plt.figure(figsize=(W / dpi, H / dpi), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.axis("off")
    ax.imshow(img, extent=(0, W, H, 0), interpolation="bilinear", aspect="auto")
    px = lambda pts: ([(x - x0) / cell * s for x, _ in pts], [(y0 - y) / cell * s for _, y in pts])
    for ln in lines_m:
        xs, ys = px(ln)
        ax.plot(xs, ys, color="#00ffff", lw=0.9 * 0.72, solid_capstyle="round")
    xs, ys = px(outline_m)
    ax.plot(xs, ys, color="#ffffff", lw=1.3 * 0.72, ls=(0, (5, 3)))
    # scale bar and the true-north direction (grid north is up; true north is rotated by the convergence)
    bar_px = 10000 / cell * s
    ax.plot([14, 14 + bar_px], [H - 16, H - 16], color="white", lw=2.2 * 0.72, solid_capstyle="butt")
    ax.text(14 + bar_px / 2, H - 22, "10 km", color="white", fontsize=6.5, ha="center", va="bottom")
    ax.text(W - 8, H - 24, f"Vertical exaggeration {ve}\u00d7 (shading)", color="white", fontsize=6.0,
            ha="right", va="bottom")
    ax.text(W - 8, H - 14, f"DEM-derived channels, threshold {thr_km2:g} km\u00b2", color="white", fontsize=6.0,
            ha="right", va="bottom")
    ax.text(W - 8, H - 4, "No terrain outside the divide (white dashes)", color="#cbd5e1", fontsize=6.0,
            ha="right", va="bottom")
    cx, cy, L = W - 24, 44, 18
    th = math.radians(conv_deg)               # true north is rotated counter-clockwise (to the left) of grid up
    ax.annotate("", xy=(cx - L * math.sin(th), cy - L * math.cos(th)), xytext=(cx, cy),
                arrowprops=dict(arrowstyle="-|>", color="white", lw=1.0))
    ax.text(cx - L * math.sin(th), cy - L * math.cos(th) - 3, "N", color="white", fontsize=6.5, ha="center", va="bottom")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, metadata={"Software": None})
    plt.close(fig)
    im = Image.open(io.BytesIO(buf.getvalue())).convert("RGB")
    if im.size != (W, H):
        raise SystemExit(f"poster is {im.size}, expected {(W, H)}")
    q = im.quantize(colors=POSTER_COLOURS, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    out = io.BytesIO()
    q.save(out, format="PNG", optimize=True, compress_level=9)
    return out.getvalue(), (W, H)


# ---- main build ---------------------------------------------------------------------------------------------
def build(evidence: Path):
    from pyproj import Proj, Transformer
    from shapely.geometry import Polygon
    inp = load_inputs(evidence)
    tr = Transformer.from_crs("EPSG:4326", CRS, always_xy=True)

    warped, wx0, wy1 = warp_to_albers(inp["dem"], inp["lon"], inp["lat"])
    dem30, gx0, gy0 = crop_to_data(warped, wx0, wy1)
    zm = block_mean(dem30, BLOCK, MIN_COVER)
    cell = BLOCK * WARP_CELL_M
    R, C = zm.shape
    if max(R, C) > GRID_MAX:
        raise SystemExit(f"grid {R}x{C} exceeds {GRID_MAX}")

    # gauge, outlet cell: the lowest terrain cell among those that touch the mask edge within 3 km of the gauge
    gx, gy = tr.transform(inp["ref"]["outlet"]["lon"], inp["ref"]["outlet"]["lat"])
    valid = np.isfinite(zm)
    from scipy import ndimage
    edge = valid & ~ndimage.binary_erosion(valid, structure=np.ones((3, 3), int), border_value=0)
    rr, cc = np.nonzero(edge)
    cx_m = gx0 + (cc + 0.5) * cell
    cy_m = gy0 - (rr + 0.5) * cell
    near = np.hypot(cx_m - gx, cy_m - gy) <= 3000.0
    if not near.any():
        raise SystemExit("no edge cell within 3 km of the gauge")
    k = np.argmin(np.where(near, zm[rr, cc], np.inf))
    outlet = (int(rr[k]), int(cc[k]))
    keep, ncomp = largest_component(valid, outlet)
    dropped = int(valid.sum() - keep.sum())
    zm = np.where(keep, zm, np.nan)
    valid = keep

    zmin = round(float(np.nanmin(zm)), 4)
    zmax = round(float(np.nanmax(zm)), 4)
    q = np.rint((np.where(valid, zm, zmin) - zmin) / (zmax - zmin) * 65535).astype("<u2")
    hq = q[valid]                                                   # row-major, terrain cells only
    zq = np.where(valid, zmin + q.astype("float64") * (zmax - zmin) / 65535.0, np.nan)   # what the page decodes

    # outline
    ring = inp["poly"]["coordinates"][0]
    ring_m = [tr.transform(lo, la) for lo, la in ring]
    area_exact = Polygon(ring_m).area / 1e6
    ring_s = dp_simplify(ring_m, OUTLINE_TOL_M)
    ring_u = [(round((x - gx0) / UNIT_M), round((gy0 - y) / UNIT_M)) for x, y in ring_s]
    outline_m = [(gx0 + x * UNIT_M, gy0 - y * UNIT_M) for x, y in ring_u]
    area_payload = shoelace_m2([(x * UNIT_M, y * UNIT_M) for x, y in ring_u]) / 1e6

    # channels
    lines_m, n_chan_cells, thr_cells, acc_max = derive_channels(dem30, gx0, gy0)
    line_u = []
    for ln in lines_m:
        s = dp_simplify(ln, CHANNEL_TOL_M)
        pts = [(round((x - gx0) / UNIT_M), round((gy0 - y) / UNIT_M)) for x, y in s]
        dd = [pts[0]] + [p for a, p in zip(pts, pts[1:]) if p != a]
        if len(dd) >= 2:
            line_u.append(dd)
    chan_m = [[(gx0 + x * UNIT_M, gy0 - y * UNIT_M) for x, y in ln] for ln in line_u]

    n_flat, flat_km2, dem_km2 = flat_patches(dem30)
    conv = float(Proj(CRS).get_factors(inp["ref"]["outlet"]["lon"], inp["ref"]["outlet"]["lat"]).meridian_convergence)

    man = inp["manifest"]
    payload = {
        "schema": "aihydro.modules.scene3d/1",
        "gauge": {"id": "01013500", "name": "Fish River near Fort Kent, Maine",
                  "lon": inp["ref"]["outlet"]["lon"], "lat": inp["ref"]["outlet"]["lat"]},
        "crs": CRS, "cell_m": int(cell), "ncols": int(C), "nrows": int(R),
        "zmin": zmin, "zmax": zmax, "ve": VERT_EXAG,
        "mask_runs": runs_encode(valid),
        "h_b64": base64.b64encode(hq.tobytes()).decode("ascii"),
        "outlet": {"r": outlet[0], "c": outlet[1]},
        "unit_m": UNIT_M,
        "outline": enc_line(ring_u),
        "channels": {"threshold_km2": CHANNEL_THRESHOLD_KM2, "dem_cell_m": int(CHANNEL_CELL_M),
                     "lines": [enc_line(ln) for ln in line_u]},
        "basin_area_km2": round(float(inp["ref"]["area_km2"]), 3),
        "grid_north_to_true_north_deg": round(conv, 2),
        "flats": {"min_km2": FLAT_MIN_KM2, "patches": n_flat, "area_km2": round(flat_km2, 1)},
        "dem": {"product": "Copernicus DEM GLO-30", "resolution_m": 30, "licence": man["license"],
                "citation": man["citation"], "doi": "10.5270/ESA-c5d3d65"},
    }
    rows_v, cols_v = np.nonzero(valid)
    where_outlet = compass(outlet[1] - cols_v.mean(), -(outlet[0] - rows_v.mean()))   # rows grow southward
    png, (pw, ph) = render_poster(zq, cell, outline_m, chan_m, gx0, gy0, VERT_EXAG, CHANNEL_THRESHOLD_KM2, conv)
    relief_m = zmax - zmin
    attrs = {
        "id": "fishPoster", "class": "scene-poster", "width": pw, "height": ph, "data-aihydro-scene3d-fallback": "",
        "alt": (f"Plan-view shaded-relief map of the Fish River basin, USGS gauge 01013500, built from a "
                f"{C} by {R} cell, {int(cell)} m elevation grid. Terrain colour runs from low (dark purple) to high "
                f"(yellow) over about {relief_m:.0f} m of relief. A white dashed line marks the divide; cyan lines are "
                f"DEM-derived channels with at least {CHANNEL_THRESHOLD_KM2:g} square kilometres draining through "
                f"them, converging on the outlet, which lies at the {where_outlet} side of the map. There is no "
                f"terrain outside the divide."),
    }

    sidecar = provenance(inp, payload, png, hq, BLOCK, dropped, ncomp, n_chan_cells, thr_cells, acc_max,
                         area_exact, area_payload, len(line_u), sum(len(l) for l in line_u))
    files = {
        "fish-river-scene.json": dump(payload),
        "fish-river-poster.png": png,
        "fish-river-poster.attrs.json": dump(attrs),
    }
    sidecar["outputs"] = [{"file": n, "sha256": sha256_bytes(b), "bytes": len(b)} for n, b in sorted(files.items())]
    files["fish-river-scene.provenance.json"] = (json.dumps(sidecar, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    return files, dict(area_exact=area_exact, area_payload=area_payload, grid=(R, C), valid=int(valid.sum()),
                       outlet=outlet, zmin=zmin, zmax=zmax, chan_lines=len(line_u), poster=(pw, ph),
                       flats=(n_flat, flat_km2), conv=conv, dropped=dropped, ncomp=ncomp)


def provenance(inp, payload, png, hq, block, dropped, ncomp, n_chan_cells, thr_cells, acc_max, area_exact,
               area_payload, n_lines, n_vertices):
    import matplotlib, PIL, pysheds, pyproj, rasterio, scipy, shapely, xarray
    me = Path(__file__).resolve()
    arts = []
    for key in ("polygon", "record", "dem", "manifest"):
        p = inp["paths"][key]
        arts.append({"role": key, "path": WORKSPACE_PREFIX + FILES[key], "sha256": inp["shas"][key], "bytes": p.stat().st_size})
    return {
        "schema": "hydrofigs.provenance/2",
        "synthetic": False,
        "synthetic_label": None,
        "note": ("Real-basin 3-D scene for the watershed-runoff lesson: Copernicus GLO-30 DEM of the Fish River basin "
                 "(USGS 01013500), masked to the delineated polygon, so the scene is an island: there is no terrain "
                 "outside the divide. Channels are DEM-derived (pysheds D8) at the stated threshold, not mapped "
                 "rivers; lakes are flat in the DEM. Vertical exaggeration is printed in the lesson. No provenance "
                 "is printed on the poster. generated_at is omitted so that a rebuild is byte-identical."),
        "artifacts": arts,
        "basin": {"gauge_id": "01013500", "area_km2_basin_ref": inp["ref"]["area_km2"],
                  "geometry_digest": inp["ref"]["geometry_digest"], "basin_ref_id": inp["ref"]["id"],
                  "minted_by": inp["ref"]["minted_by"]},
        "dem_manifest": {k: inp["manifest"][k] for k in ("product", "source", "license", "citation", "fetched_at",
                                                        "geom_id", "data_sha256")},
        "parameters": {
            "crs": CRS, "warp_cell_m": WARP_CELL_M, "warp_resampling": "bilinear (GDAL via rasterio)",
            "block_mean_factor": block, "mesh_cell_m": block * WARP_CELL_M, "min_cover_fraction": MIN_COVER,
            "grid": [payload["nrows"], payload["ncols"]], "terrain_cells": int(len(hq)),
            "height_quantization": "Uint16, little-endian, row-major, terrain cells only; value = zmin + q*(zmax-zmin)/65535",
            "zmin_m": payload["zmin"], "zmax_m": payload["zmax"],
            "vertical_exaggeration": VERT_EXAG,
            "outlet_rule": "lowest terrain cell touching the mask edge within 3 km of the gauge",
            "disconnected_cells_dropped": dropped, "components_before": ncomp,
            "channels": {"tool": "pysheds " + pysheds.__version__ + " (fill_pits, fill_depressions, resolve_flats, flowdir D8, accumulation)",
                         "dem_cell_m": CHANNEL_CELL_M, "threshold_km2": CHANNEL_THRESHOLD_KM2,
                         "threshold_cells": thr_cells, "channel_cells": n_chan_cells, "max_accumulation_cells": acc_max,
                         "polylines": n_lines, "vertices_after_simplify": n_vertices,
                         "simplify": "Douglas-Peucker, %g m" % CHANNEL_TOL_M},
            "outline": {"simplify": "Douglas-Peucker, %g m" % OUTLINE_TOL_M, "unit_m": UNIT_M,
                        "area_km2_exact_polygon_in_5070": area_exact, "area_km2_from_payload": area_payload},
            "poster": {"px_per_cell": POSTER_PX_PER_CELL, "palette_colours": POSTER_COLOURS, "projection": "plan view"},
        },
        "checks": [
            {"name": "inputs sha256", "ok": True},
            {"name": "payload area within 1% of basin_ref", "ok": abs(area_payload / inp["ref"]["area_km2"] - 1) < 0.01,
             "value": area_payload / inp["ref"]["area_km2"] - 1},
        ],
        "script": "tools/build_scene3d.py",
        "script_sha256": sha256_file(me),
        "environment": {"python": sys.version.split()[0], "numpy": np.__version__, "scipy": scipy.__version__,
                        "matplotlib": matplotlib.__version__, "pillow": PIL.__version__, "pysheds": pysheds.__version__,
                        "pyproj": pyproj.__version__, "rasterio": rasterio.__version__, "shapely": shapely.__version__,
                        "xarray": xarray.__version__},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="exit 1 if the files on disk differ from a fresh build")
    ap.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    ap.add_argument("--out", type=Path, default=MODULE)
    a = ap.parse_args()
    files, info = build(a.evidence)
    for k, v in info.items():
        print(f"{k}: {v}")
    bad = []
    for name, data in files.items():
        p = a.out / name
        if a.check:
            if not p.exists() or p.read_bytes() != data:
                bad.append(name)
        else:
            a.out.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        print(f"{name}: {len(data)} bytes sha256 {sha256_bytes(data)[:16]}")
    if bad:
        print("stale: " + ", ".join(bad))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
