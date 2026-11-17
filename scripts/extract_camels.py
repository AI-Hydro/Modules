#!/usr/bin/env python3
"""Extract the small CAMELS-US v1.2 slices that the learning modules bundle.

Reads (read-only) from a local CAMELS-US v1.2 copy:
  camels_name.txt, camels_topo.txt, camels_hydro.txt, camels_clim.txt
  basin_timeseries_v1p2_metForcing_obsFlow.zip
    -> basin_dataset_public_v1p2/usgs_streamflow/<HUC>/<gauge>_streamflow_qc.txt
    -> basin_dataset_public_v1p2/basin_mean_forcing/daymet/<HUC>/<gauge>_lump_cida_forcing_leap.txt

Writes, under modules/<id>/data/:
  <gauge>_q.csv          5 water years of daily observed flow (cfs) + USGS QC flag
  <gauge>_wy<YYYY>.csv   one water year of flow + Daymet basin-mean precipitation
  camels_gauges.json     gauge metadata and CAMELS signatures (one source of truth)
  PROVENANCE.json        source file, member path, sha256, period, units, flags,
                         extraction script and citations

Nothing is downloaded. Usage:

  python scripts/extract_camels.py \
      --camels-root /path/to/camels_us  [--repo .] [--only MODULE ...]

--only MODULE (repeatable) limits the run to the named modules (any module id the script knows:
the legacy ones above or a key of LESSON_EXTRACTORS); without it everything is extracted.
Per-lesson extractors (Wave 3 and later) live in the LESSON_EXTRACTORS registry near the end of
this file, each in its own BEGIN/END block so parallel authors never touch the same lines.

Units are kept exactly as distributed (flow in cubic feet per second, precipitation
in mm/day); conversions happen in the module code and are written there.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

ZIP_NAME = "basin_timeseries_v1p2_metForcing_obsFlow.zip"
FLOW_MEMBER = "basin_dataset_public_v1p2/usgs_streamflow/{huc}/{gauge}_streamflow_qc.txt"
FORC_MEMBER = (
    "basin_dataset_public_v1p2/basin_mean_forcing/daymet/{huc}/"
    "{gauge}_lump_cida_forcing_leap.txt"
)

# Water years 1996-2000 are complete (no missing days) for all five gauges and lie
# inside the CAMELS signature period 1989-10-01..2009-09-30.
FIVE_YEAR = ("1995-10-01", "2000-09-30")
REPORT_WY = 1997  # the single water year shown in reading-a-hydrograph

GAUGES = {
    # id: (display name, one-line character derived from CAMELS attributes is built later)
    "01013500": "Fish River near Fort Kent, ME",
    "01031500": "Piscataquis River near Dover-Foxcroft, ME",
    "02472000": "Leaf River near Collins, MS",
    "09484000": "Sabino Creek near Tucson, AZ",
    "14305500": "Siletz River at Siletz, OR",
}

# gauge sets per module (module id -> gauges whose series are bundled)
FIVE_YEAR_MODULES = {
    "real-streamflow-data": ["01013500", "14305500", "09484000", "02472000"],
    "capstone-basin-story": ["01013500", "14305500", "09484000", "02472000"],
}
WY_MODULES = {"reading-a-hydrograph": ["14305500", "01031500", "02472000"]}
META_ONLY_MODULES = {"dem-to-twi": ["01031500"]}

DEFAULT_ATTRIBUTE_FILES = ("camels_name.txt", "camels_topo.txt", "camels_hydro.txt", "camels_clim.txt")

CITATIONS = [
    "Newman, A. J., Clark, M. P., Sampson, K., Wood, A., Hay, L. E., Bock, A., "
    "Viger, R. J., Blodgett, D., Brekke, L., Arnold, J. R., Hopson, T., and Duan, Q. "
    "(2015). Development of a large-sample watershed-scale hydrometeorological data "
    "set for the contiguous USA: data set characteristics and assessment of regional "
    "variability in hydrologic model performance. Hydrol. Earth Syst. Sci., 19, "
    "209-223. doi:10.5194/hess-19-209-2015",
    "Addor, N., Newman, A. J., Mizukami, N., and Clark, M. P. (2017). The CAMELS data "
    "set: catchment attributes and meteorology for large-sample studies. Hydrol. Earth "
    "Syst. Sci., 21, 5293-5313. doi:10.5194/hess-21-5293-2017",
]


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def read_attr(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="") as fh:
        rows = list(csv.DictReader(fh, delimiter=";"))
    return {r["gauge_id"].strip().zfill(8): r for r in rows}


def parse_flow(raw: bytes):
    out = []
    for line in raw.decode().splitlines():
        p = line.split()
        if len(p) < 6:
            continue
        date = dt.date(int(p[1]), int(p[2]), int(p[3]))
        q = float(p[4])
        out.append((date, q, p[5]))
    return out


def parse_forcing(raw: bytes):
    lines = raw.decode().splitlines()
    header = lines[:3]  # lat, elevation, area (m2) per the CAMELS readme
    out = {}
    for line in lines[4:]:
        p = line.split()
        date = dt.date(int(p[0]), int(p[1]), int(p[2]))
        out[date] = float(p[5])  # prcp(mm/day) is the 6th column
    return header, out


def parse_forcing_full(raw: bytes) -> dict:
    """Every column of a Daymet basin-mean forcing file, plus the three header values.

    Returns {"lat": deg, "elev_m": m, "area_m2": m2, "dates": [date], "cols": {name: [float]}} with
    the column names as distributed after stripping units: dayl (s), prcp (mm/day), srad (W/m2),
    swe (mm), tmax (C), tmin (C), vp (Pa). Values are floats exactly as parsed (no rounding).
    """
    lines = raw.decode().splitlines()
    lat, elev, area = (float(lines[i].split()[0]) for i in range(3))
    names = ["dayl", "prcp", "srad", "swe", "tmax", "tmin", "vp"]
    dates: list[dt.date] = []
    cols: dict[str, list[float]] = {n: [] for n in names}
    for line in lines[4:]:
        p = line.split()
        dates.append(dt.date(int(p[0]), int(p[1]), int(p[2])))
        for k, n in enumerate(names):
            cols[n].append(float(p[4 + k]))
    return {"lat": lat, "elev_m": elev, "area_m2": area, "dates": dates, "cols": cols}


def clip(series, start: str, end: str):
    s, e = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    return [r for r in series if s <= r[0] <= e]


def write_csv(path: Path, header: list[str], rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def num(x: str, nd: int = 6):
    return round(float(x), nd)


class Extraction:
    """One extraction run: the CAMELS root, the repo, and read-only cached access to its files.

    Lesson extractors receive one of these. Everything is lazy, so a run restricted with --only never
    opens a file it does not need.

      ctx.attr(name)            {gauge_id: row} for any attribute file, e.g. "camels_soil.txt",
                                "camels_vege.txt" (gauge_id zero-padded to 8; values are raw strings)
      ctx.attr_sha(name)        sha256 of that file's bytes
      ctx.huc(gauge)            two-digit HUC string of a gauge (from camels_name.txt)
      ctx.flow(gauge)           (member, sha256, [(date, q_cfs, qc_flag)])
      ctx.forcing(gauge)        (member, sha256, {date: prcp}, header_lines)  (legacy form)
      ctx.forcing_full(gauge)   (member, sha256, parse_forcing_full(...))
      ctx.prov_base(module_id, attribute_files=None)   provenance skeleton; attribute_files lists the
                                attribute files actually read (default: the four legacy ones)
      ctx.module_dir(module_id) Path of modules/<id>/data (not created)
    """

    def __init__(self, root: Path, repo: Path, extracted_on: str):
        self.root, self.repo, self.extracted_on = root, repo, extracted_on
        self._attr: dict[str, dict] = {}
        self._sha: dict[str, str] = {}
        self._zip = None
        self._flow: dict[str, tuple] = {}
        self._forc: dict[str, tuple] = {}
        self._forc_full: dict[str, tuple] = {}

    def attr(self, name: str) -> dict:
        if name not in self._attr:
            self._attr[name] = read_attr(self.root / name)
        return self._attr[name]

    def attr_sha(self, name: str) -> str:
        if name not in self._sha:
            self._sha[name] = sha256_bytes((self.root / name).read_bytes())
        return self._sha[name]

    def huc(self, gauge: str) -> str:
        return self.attr("camels_name.txt")[gauge]["huc_02"].strip().zfill(2)

    @property
    def zf(self) -> zipfile.ZipFile:
        if self._zip is None:
            self._zip = zipfile.ZipFile(self.root / ZIP_NAME)  # opened read-only
        return self._zip

    def flow(self, g: str):
        if g not in self._flow:
            member = FLOW_MEMBER.format(huc=self.huc(g), gauge=g)
            raw = self.zf.read(member)
            self._flow[g] = (member, sha256_bytes(raw), parse_flow(raw))
        return self._flow[g]

    def forcing(self, g: str):
        if g not in self._forc:
            member = FORC_MEMBER.format(huc=self.huc(g), gauge=g)
            raw = self.zf.read(member)
            header, series = parse_forcing(raw)
            self._forc[g] = (member, sha256_bytes(raw), series, header)
        return self._forc[g]

    def forcing_full(self, g: str):
        if g not in self._forc_full:
            member = FORC_MEMBER.format(huc=self.huc(g), gauge=g)
            raw = self.zf.read(member)
            self._forc_full[g] = (member, sha256_bytes(raw), parse_forcing_full(raw))
        return self._forc_full[g]

    def module_dir(self, module_id: str) -> Path:
        return self.repo / "modules" / module_id / "data"

    def prov_base(self, module_id: str, attribute_files=None) -> dict:
        files = DEFAULT_ATTRIBUTE_FILES if attribute_files is None else tuple(attribute_files)
        return {
            "module": module_id,
            "dataset": "CAMELS-US v1.2 (basin_timeseries_v1p2_metForcing_obsFlow + attribute files)",
            "camels_root_relative_sources": {
                "attribute_files": {n: {"sha256": self.attr_sha(n)} for n in files},
                "archive": ZIP_NAME,
            },
            "extraction_script": "scripts/extract_camels.py",
            "extracted_on": self.extracted_on,
            "citations": CITATIONS,
            "licence_note": (
                "CAMELS-US streamflow originates from USGS NWIS (public domain); "
                "forcing is Daymet basin means as distributed by CAMELS."
            ),
            "access": "read-only local copy; no network access during extraction",
        }


# ---- legacy modules (Waves 1-2): output must stay byte-identical -------------------------------
def extract_legacy(ctx: Extraction, want) -> None:
    repo = ctx.repo
    names = ctx.attr("camels_name.txt")
    topo = ctx.attr("camels_topo.txt")
    hydro = ctx.attr("camels_hydro.txt")
    clim = ctx.attr("camels_clim.txt")

    meta = {}
    for g, disp in GAUGES.items():
        n, t, h, c = names[g], topo[g], hydro[g], clim[g]
        meta[g] = {
            "gauge_id": g,
            "name": disp,
            "camels_name": n["gauge_name"].strip(),
            "huc_02": n["huc_02"].strip().zfill(2),
            "lat": num(t["gauge_lat"], 5),
            "lon": num(t["gauge_lon"], 5),
            "area_km2": num(t["area_gages2"], 2),
            "elev_mean_m": num(t["elev_mean"], 2),
            "q_mean_mm_day": num(h["q_mean"]),
            "runoff_ratio": num(h["runoff_ratio"]),
            "baseflow_index": num(h["baseflow_index"]),
            "q5_mm_day": num(h["q5"]),
            "q95_mm_day": num(h["q95"]),
            "zero_q_freq_as_distributed": num(h["zero_q_freq"]),  # unit not interpreted: see README
            "hfd_mean_doy": num(h["hfd_mean"], 2),
            "p_mean_mm_day": num(c["p_mean"]),
            "pet_mean_mm_day": num(c["pet_mean"]),
            "aridity": num(c["aridity"]),
            "frac_snow": num(c["frac_snow"]),
        }

    flow, forcing, prov_base = ctx.flow, ctx.forcing, ctx.prov_base

    # ---- five-year flow modules -------------------------------------------------
    for mod, gauges in FIVE_YEAR_MODULES.items():
        if not want(mod):
            continue
        d = repo / "modules" / mod / "data"
        prov = prov_base(mod)
        prov["series"] = {}
        for g in gauges:
            member, sha, series = flow(g)
            rows = clip(series, *FIVE_YEAR)
            assert all(r[1] >= 0 and r[2] != "M" for r in rows), f"missing data in {g}"
            write_csv(d / f"{g}_q.csv", ["date", "q_cfs", "usgs_qc"],
                      [(r[0].isoformat(), f"{r[1]:g}", r[2]) for r in rows])
            prov["series"][g] = {
                "file": f"data/{g}_q.csv",
                "source_member": member,
                "source_member_sha256": sha,
                "period": [rows[0][0].isoformat(), rows[-1][0].isoformat()],
                "n_days": len(rows),
                "units": "cubic feet per second (daily mean), as distributed",
                "usgs_qc_flags": {
                    f: sum(1 for r in rows if r[2] == f) for f in sorted({r[2] for r in rows})
                },
                "flag_meaning": {
                    "A": "approved by USGS",
                    "A:e": "approved by USGS, estimated value",
                    "M": "missing (none in this slice)",
                },
            }
        (d / "camels_gauges.json").write_text(
            json.dumps({g: meta[g] for g in gauges}, indent=1) + "\n")
        (d / "PROVENANCE.json").write_text(json.dumps(prov, indent=1) + "\n")

    # ---- one-water-year flow + precipitation module ------------------------------
    for mod, gauges in WY_MODULES.items():
        if not want(mod):
            continue
        d = repo / "modules" / mod / "data"
        prov = prov_base(mod)
        prov["series"] = {}
        start, end = f"{REPORT_WY - 1}-10-01", f"{REPORT_WY}-09-30"
        for g in gauges:
            fm, fsha, fseries = flow(g)
            pm, psha, pseries, _ = forcing(g)
            rows = clip(fseries, start, end)
            assert all(r[1] >= 0 and r[2] != "M" for r in rows), f"missing data in {g}"
            write_csv(d / f"{g}_wy{REPORT_WY}.csv",
                      ["date", "q_cfs", "usgs_qc", "prcp_mm_day"],
                      [(r[0].isoformat(), f"{r[1]:g}", r[2], f"{pseries[r[0]]:g}") for r in rows])
            prov["series"][g] = {
                "file": f"data/{g}_wy{REPORT_WY}.csv",
                "flow_source_member": fm,
                "flow_source_member_sha256": fsha,
                "precip_source_member": pm,
                "precip_source_member_sha256": psha,
                "period": [rows[0][0].isoformat(), rows[-1][0].isoformat()],
                "n_days": len(rows),
                "units": {"q_cfs": "cubic feet per second (daily mean)",
                          "prcp_mm_day": "Daymet basin-mean precipitation, mm/day"},
                "usgs_qc_flags": {
                    f: sum(1 for r in rows if r[2] == f) for f in sorted({r[2] for r in rows})
                },
            }
        (d / "camels_gauges.json").write_text(
            json.dumps({g: meta[g] for g in gauges}, indent=1) + "\n")
        (d / "PROVENANCE.json").write_text(json.dumps(prov, indent=1) + "\n")

    # ---- metadata-only modules ---------------------------------------------------
    for mod, gauges in META_ONLY_MODULES.items():
        if not want(mod):
            continue
        d = repo / "modules" / mod / "data"
        d.mkdir(parents=True, exist_ok=True)
        prov = prov_base(mod)
        prov["series"] = {}
        (d / "camels_gauges.json").write_text(
            json.dumps({g: meta[g] for g in gauges}, indent=1) + "\n")
        (d / "PROVENANCE.json").write_text(json.dumps(prov, indent=1) + "\n")


# ---- per-lesson extractors (Wave 3+) ----------------------------------------------------------
# Each lesson owns exactly one BEGIN/END block below and the one registry line for it; blocks are
# separated by unchanged spacer lines so parallel edits merge cleanly. An extractor is
# `def extract_<id_underscored>(ctx: Extraction) -> None`; it writes only under modules/<id>/data/
# (use ctx.module_dir(id), ctx.attr(...), ctx.flow(g), ctx.forcing_full(g), ctx.prov_base(id,
# attribute_files=[...]) ) and must be deterministic (no clock, no random; ctx.extracted_on only).
#
#
#
#
#
#
# ==== BEGIN extract_precipitation_point_to_basin (packet P1 owns) ====
P1_GAUGES = {
    "01013500": "Fish River near Fort Kent, ME",
    "02472000": "Leaf River near Collins, MS",
    "09484000": "Sabino Creek near Tucson, AZ",
    "14305500": "Siletz River at Siletz, OR",
}
P1_DAILY = ("1995-10-01", "2000-09-30")        # WY1996-2000: 5 water years of daily precipitation and temperature
P1_MONTHLY_FIRST_WY, P1_MONTHLY_LAST_WY = 1990, 2009   # WY1990-2009 = 1989-10-01..2009-09-30, the CAMELS period
P1_ATTRIBUTE_FILES = ("camels_name.txt", "camels_topo.txt", "camels_clim.txt")


def extract_precipitation_point_to_basin(ctx: Extraction) -> None:
    """Daily precipitation + wet-day mean temperature (WY1996-2000), monthly totals (WY1990-2009) and
    the CAMELS attributes the precipitation lesson reproduces, for four basins.

    Precipitation is stored as integer hundredths of a millimetre (the file carries two decimals, so
    nothing is lost). Daily mean temperature is stored only for days with precipitation, in order,
    as the half-degree bin floor(2 * (tmax + tmin) / 2) = floor(tmax + tmin) in whole numbers. For any
    threshold T that is a multiple of 0.5 C, "mean temperature < T" is exactly "bin < 2 * T", so
    the lesson's 0.5 C slider loses nothing, and the page stays small.
    """
    names, topo, clim = ctx.attr("camels_name.txt"), ctx.attr("camels_topo.txt"), ctx.attr("camels_clim.txt")
    out_dir = ctx.module_dir("precipitation-point-to-basin")
    out_dir.mkdir(parents=True, exist_ok=True)
    d0, d1 = (dt.date.fromisoformat(x) for x in P1_DAILY)
    m0, m1 = dt.date(P1_MONTHLY_FIRST_WY - 1, 10, 1), dt.date(P1_MONTHLY_LAST_WY, 9, 30)
    basins, prov_series, month_days = {}, {}, None
    for g, display in P1_GAUGES.items():
        member, sha, ff = ctx.forcing_full(g)
        dates, cols = ff["dates"], ff["cols"]
        prcp_h, tmean_wet, monthly, days_in_month = [], [], {}, {}
        for i, d in enumerate(dates):
            h = round(cols["prcp"][i] * 100)
            assert abs(cols["prcp"][i] * 100 - h) < 1e-6 and h >= 0, f"{g} {d}: prcp {cols['prcp'][i]}"
            if m0 <= d <= m1:
                key = (d.year, d.month)
                monthly[key] = monthly.get(key, 0) + h
                days_in_month[key] = days_in_month.get(key, 0) + 1
            if d0 <= d <= d1:
                prcp_h.append(h)
                if h > 0:
                    s2 = (cols["tmax"][i] + cols["tmin"][i]) * 100
                    assert abs(s2 - round(s2)) < 1e-6, f"{g} {d}: tmax + tmin not in hundredths"
                    tmean_wet.append(int(round(s2)) // 100)   # floor(tmax + tmin) = floor(2 * mean temperature)
        # water-year month order Oct..Sep for WY1990..WY2009
        keys = [(y, m) for wy in range(P1_MONTHLY_FIRST_WY, P1_MONTHLY_LAST_WY + 1)
                for (y, m) in [(wy - 1, 10), (wy - 1, 11), (wy - 1, 12)] + [(wy, k) for k in range(1, 10)]]
        assert len(keys) == 240 and all(k in monthly for k in keys)
        md = [days_in_month[k] for k in keys]
        month_days = md if month_days is None else month_days
        assert md == month_days
        assert len(prcp_h) == 1827
        n = names[g]; t = topo[g]; c = clim[g]
        basins[g] = {
            "gauge_id": g,
            "name": display,
            "camels_name": n["gauge_name"].strip(),
            "huc_02": ctx.huc(g),
            "lat": num(t["gauge_lat"], 5),
            "lon": num(t["gauge_lon"], 5),
            "area_km2": num(t["area_gages2"], 2),
            "elev_mean_m": num(t["elev_mean"], 2),
            "camels": {"p_mean_mm_day": num(c["p_mean"]), "frac_snow": num(c["frac_snow"]),
                       "high_prec_freq_days_per_year": num(c["high_prec_freq"], 4),
                       "high_prec_dur_days": num(c["high_prec_dur"]), "low_prec_freq_days_per_year": num(c["low_prec_freq"], 4)},
            "source_member": member,
            "source_sha256": sha,
            "prcp_hundredths_mm": prcp_h,
            "tmean_halfdeg_bin_on_wet_days": tmean_wet,
            "monthly_hundredths_mm": [monthly[k] for k in keys],
        }
        prov_series[g] = {
            "file": "data/precip-data.json",
            "forcing_source_member": member,
            "forcing_source_member_sha256": sha,
            "daily_period": [d0.isoformat(), d1.isoformat()],
            "n_days": len(prcp_h),
            "n_wet_days_with_tmean": len(tmean_wet),
            "monthly_period": [m0.isoformat(), m1.isoformat()],
            "n_months": len(keys),
            "units": {"prcp_hundredths_mm": "Daymet basin-mean precipitation in hundredths of a mm/day (integer; the file has two decimals)",
                      "tmean_halfdeg_bin_on_wet_days": "floor(tmax + tmin) = floor(2 * mean temperature): the half-degree bin of the daily mean temperature (C), only for days with prcp > 0, in date order; for a threshold T that is a multiple of 0.5, mean < T is exactly bin < 2 * T",
                      "monthly_hundredths_mm": "monthly precipitation totals in hundredths of a mm, water-year order Oct..Sep, WY1990..WY2009"},
        }
    blob = {
        "source": "CAMELS-US v1.2 (Newman et al. 2015; Addor et al. 2017); Daymet basin means (Thornton et al. 1997)",
        "daily_start": d0.isoformat(), "daily_n": 1827,
        "monthly_first_wy": P1_MONTHLY_FIRST_WY, "monthly_last_wy": P1_MONTHLY_LAST_WY,
        "monthly_days": month_days,
        "basins": basins,
    }
    (out_dir / "precip-data.json").write_text(json.dumps(blob, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")
    prov = ctx.prov_base("precipitation-point-to-basin", attribute_files=P1_ATTRIBUTE_FILES)
    prov["series"] = prov_series
    prov["blob"] = "data/precip-data.json (inlined into module.html as <script id=\"precip-data\">)"
    prov["notes"] = [
        "tmean_halfdeg_bin_on_wet_days holds one value per day with prcp > 0, in date order; the matching days are the nonzero entries of prcp_hundredths_mm.",
        "Monthly totals are sums of the daily Daymet basin-mean values over each calendar month; day counts per month are in monthly_days.",
        "CAMELS attributes are copied as distributed (camels_clim.txt: p_mean, frac_snow, high_prec_freq, high_prec_dur, low_prec_freq).",
    ]
    (out_dir / "PROVENANCE.json").write_text(json.dumps(prov, indent=1) + "\n", encoding="utf-8")
# ==== END extract_precipitation_point_to_basin ====
#
#
#
#
#
#
# ==== BEGIN extract_evapotranspiration_budyko (packet P2 owns) ====
ET_GAUGES = ["01013500", "02472000", "09484000", "14305500"]      # the four course basins
ET_WY = ("1996-10-01", "1997-09-30")                              # water year 1997, 365 days
ET_FORCING_VARS = ("dayl", "srad", "tmax", "tmin", "vp")          # as distributed (s, W/m2, C, C, Pa)
ET_ATTRIBUTE_FILES = ("camels_name.txt", "camels_topo.txt", "camels_hydro.txt", "camels_clim.txt")
ET_ALL_DECIMALS = 4                                               # aridity, runoff_ratio, frac_snow rounding


def extract_evapotranspiration_budyko(ctx: Extraction) -> None:
    """evapotranspiration-budyko: one water year of Daymet forcing for the four course basins (PET
    inputs) plus aridity / runoff_ratio / frac_snow for every CAMELS gauge (the Budyko plot).

    Writes modules/evapotranspiration-budyko/data/et-budyko.json (the page's inlined blob) and
    PROVENANCE.json. Daily values are exactly as distributed; the 671-gauge table is rounded to
    ET_ALL_DECIMALS and the rounding is recorded in PROVENANCE.json.
    """
    mod = "evapotranspiration-budyko"
    d = ctx.module_dir(mod)
    d.mkdir(parents=True, exist_ok=True)
    clim, hydro = ctx.attr("camels_clim.txt"), ctx.attr("camels_hydro.txt")
    names, topo = ctx.attr("camels_name.txt"), ctx.attr("camels_topo.txt")
    start, end = (dt.date.fromisoformat(x) for x in ET_WY)

    basins, series = {}, {}
    for g in ET_GAUGES:
        member, sha, full = ctx.forcing_full(g)
        i0 = full["dates"].index(start)
        i1 = full["dates"].index(end) + 1
        assert full["dates"][i0:i1] == [start + dt.timedelta(days=k) for k in range(i1 - i0)], "gap in dates"
        assert i1 - i0 == 365
        b = {
            "name": GAUGES[g],
            "camels_name": names[g]["gauge_name"].strip(),
            "lat": full["lat"],                  # forcing-file header, degrees north
            "elev_m": full["elev_m"],            # forcing-file header, metres
            "area_gages2_km2": num(topo[g]["area_gages2"], 2),
            "huc": ctx.huc(g),                   # member path = FORC_MEMBER with this huc
            "sha256": sha,                       # of that member inside the archive
        }
        for v in ET_FORCING_VARS:
            raw = full["cols"][v][i0:i1]
            ints = [round(x * 100) for x in raw]
            assert all(abs(x * 100 - k) < 1e-6 for x, k in zip(raw, ints)), f"{v} is not a 2-decimal value"
            if v == "dayl":     # smooth in time: store the first value and then day-to-day differences
                ints = [ints[0]] + [ints[k] - ints[k - 1] for k in range(1, len(ints))]
            b[v + "_x100"] = ints
        basins[g] = b
        series[g] = {
            "forcing_member": member,
            "forcing_member_sha256": sha,
            "period": [start.isoformat(), end.isoformat()],
            "n_days": i1 - i0,
            "columns": {"dayl": "s", "srad": "W/m2 (daylight-period mean)", "tmax": "C", "tmin": "C", "vp": "Pa"},
        }
    assert all(len(b[v + "_x100"]) == 365 for b in basins.values() for v in ET_FORCING_VARS)

    course = {}
    for g in ET_GAUGES:
        course[g] = {
            "p_mean": float(clim[g]["p_mean"]), "pet_mean": float(clim[g]["pet_mean"]),
            "aridity": float(clim[g]["aridity"]), "q_mean": float(hydro[g]["q_mean"]),
            "runoff_ratio": float(hydro[g]["runoff_ratio"]), "frac_snow": float(clim[g]["frac_snow"]),
        }

    ids = sorted(set(clim) & set(hydro))
    assert len(ids) == 671 and set(ids) == set(clim) == set(hydro)

    def r(x: str):
        x = x.strip()
        return None if x == "NA" else round(float(x), ET_ALL_DECIMALS)

    allb = {
        "ids": " ".join(ids),
        "aridity": [r(clim[g]["aridity"]) for g in ids],
        "runoff_ratio": [r(hydro[g]["runoff_ratio"]) for g in ids],
        "frac_snow": [r(clim[g]["frac_snow"]) for g in ids],
    }
    assert None not in allb["aridity"] and None not in allb["frac_snow"]
    na = [g for g, v in zip(ids, allb["runoff_ratio"]) if v is None]

    blob = {"wy": {"start": ET_WY[0], "end": ET_WY[1], "n": 365}, "basins": basins, "course": course, "all": allb}
    (d / "et-budyko.json").write_text(json.dumps(blob, separators=(",", ":")) + "\n", encoding="utf-8")

    prov = ctx.prov_base(mod, attribute_files=ET_ATTRIBUTE_FILES)
    prov["blob"] = "data/et-budyko.json (inlined into module.html by scripts/build_modules.py as <script id=\"et-budyko\">)"
    prov["series"] = series
    prov["encoding"] = ("<column>_x100 in the blob = the value as distributed (two decimals) times 100, as integers; "
                        "dayl_x100 holds the first value and then day-to-day differences (lossless)")
    prov["all_gauges_table"] = {
        "attribute_files": ["camels_clim.txt", "camels_hydro.txt"],
        "fields": ["aridity (camels_clim)", "runoff_ratio (camels_hydro)", "frac_snow (camels_clim)"],
        "n_gauges": len(ids),
        "ids": "single space-separated string, ascending",
        "rounding": f"each value rounded to {ET_ALL_DECIMALS} decimal places (to keep the page small); "
                    "the four course basins are also stored unrounded under 'course'",
        "na_runoff_ratio_gauges": na,
        "na_handling": "runoff_ratio is NA in camels_hydro for these gauge(s); stored as null and left out of the Budyko fit",
    }
    prov["units"] = {"daily": "dayl s; srad W/m2 (mean over the daylight period); tmax, tmin C; vp Pa",
                     "attributes": "p_mean, pet_mean, q_mean mm/day; aridity, runoff_ratio, frac_snow dimensionless"}
    prov["usage_note"] = ("PET is recomputed by the lesson from these forcing columns and compared with the tabulated "
                          "pet_mean as a reproduction check; no modelOutput PET is used.")
    (d / "PROVENANCE.json").write_text(json.dumps(prov, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
# ==== END extract_evapotranspiration_budyko ====
#
#
#
#
#
#
# ==== BEGIN extract_runoff_generation (packet P3 owns) ====
RG_PERIOD = ("1995-10-01", "2000-09-30")           # water years 1996-2000, 1827 days
RG_BASINS = ["14305500", "02472000", "09484000"]   # rain-event basins (Siletz, Leaf, Sabino)
RG_OMITTED = "01013500"                            # Fish River: attributes only (frac_snow is the stated reason)
RG_ATTR_FILES = ["camels_name.txt", "camels_topo.txt", "camels_hydro.txt", "camels_clim.txt", "camels_soil.txt"]


def _rg_num(x: float):
    """An int when the value is integral (smaller JSON), else the float exactly as parsed."""
    return int(x) if float(x).is_integer() else float(x)


def extract_runoff_generation(ctx: Extraction) -> None:
    """WY1996-2000 daily flow (as distributed), Daymet basin precipitation (integer hundredths of mm,
    lossless: the file carries two decimals) and the soil / runoff-ratio / snow attributes the lesson
    compares with. Writes data/runoff-events.json and data/PROVENANCE.json."""
    names, topo = ctx.attr("camels_name.txt"), ctx.attr("camels_topo.txt")
    soil, hydro, clim = ctx.attr("camels_soil.txt"), ctx.attr("camels_hydro.txt"), ctx.attr("camels_clim.txt")
    d = ctx.module_dir("runoff-generation")
    d.mkdir(parents=True, exist_ok=True)

    def attrs(g: str) -> dict:
        return {
            "camels_name": names[g]["gauge_name"].strip(),
            "area_km2": num(topo[g]["area_gages2"], 2),
            "soil_conductivity_cm_h": num(soil[g]["soil_conductivity"], 6),
            "soil_porosity": num(soil[g]["soil_porosity"], 6),
            "soil_depth_statsgo_m": num(soil[g]["soil_depth_statsgo"], 6),
            "max_water_content_m": num(soil[g]["max_water_content"], 6),
            "runoff_ratio": num(hydro[g]["runoff_ratio"], 6),
            "frac_snow": num(clim[g]["frac_snow"], 6),
        }

    prov = ctx.prov_base("runoff-generation", attribute_files=RG_ATTR_FILES)
    prov["series"] = {}
    blob = {"period": list(RG_PERIOD), "basins": {}, "omitted": {}}
    for g in RG_BASINS:
        fm, fsha, fseries = ctx.flow(g)
        pm, psha, forc = ctx.forcing_full(g)
        rows = clip(fseries, *RG_PERIOD)
        assert all(r[1] >= 0 and r[2] != "M" for r in rows), f"missing or negative flow in {g}"
        pr = dict(zip(forc["dates"], forc["cols"]["prcp"]))
        hund = []
        for r in rows:
            v = pr[r[0]]
            assert abs(v * 100 - round(v * 100)) < 1e-6, "precipitation is not an integer number of hundredths"
            hund.append(int(round(v * 100)))
        est = [i for i, r in enumerate(rows) if r[2] != "A"]
        assert {r[2] for r in rows} <= {"A", "A:e"}
        blob["basins"][g] = {
            "name": GAUGES[g],
            **attrs(g),
            "flow_member": fm, "flow_sha256": fsha, "precip_member": pm, "precip_sha256": psha,
            "q_cfs": [_rg_num(r[1]) for r in rows],
            "estimated_idx": est,
            "prcp_hundredths_mm": hund,
        }
        prov["series"][g] = {
            "file": "data/runoff-events.json",
            "flow_source_member": fm,
            "flow_source_member_sha256": fsha,
            "precip_source_member": pm,
            "precip_source_member_sha256": psha,
            "period": [rows[0][0].isoformat(), rows[-1][0].isoformat()],
            "n_days": len(rows),
            "units": {"q_cfs": "cubic feet per second (daily mean), as distributed",
                      "prcp_hundredths_mm": "Daymet basin-mean precipitation, integer hundredths of mm/day (lossless)"},
            "usgs_qc_flags": {f: sum(1 for r in rows if r[2] == f) for f in sorted({r[2] for r in rows})},
        }
    blob["omitted"][RG_OMITTED] = {"name": GAUGES[RG_OMITTED], **attrs(RG_OMITTED)}
    prov["omitted_gauge_attributes_only"] = RG_OMITTED
    prov["soil_conductivity_unit"] = "cm/hr (CAMELS attribute documentation, camels_attributes_v2.0)"
    (d / "runoff-events.json").write_text(json.dumps(blob, separators=(",", ":")) + "\n")
    (d / "PROVENANCE.json").write_text(json.dumps(prov, indent=1) + "\n")
# ==== END extract_runoff_generation ====
#
#
#
#
#
#
# Registry: module id -> extractor, in run order. One line per lesson.
LESSON_EXTRACTORS = {
    "precipitation-point-to-basin": extract_precipitation_point_to_basin,
    "evapotranspiration-budyko": extract_evapotranspiration_budyko,
    "runoff-generation": extract_runoff_generation,
}

LEGACY_MODULES = [*FIVE_YEAR_MODULES, *WY_MODULES, *META_ONLY_MODULES]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--camels-root", required=True, type=Path)
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parent.parent)
    ap.add_argument("--extracted-on", default=dt.date.today().isoformat(),
                    help="date recorded in PROVENANCE.json (default: today)")
    ap.add_argument("--only", action="append", metavar="MODULE",
                    help="extract only this module (repeatable); default: all")
    a = ap.parse_args()
    known = [*LEGACY_MODULES, *LESSON_EXTRACTORS]
    for m in a.only or []:
        if m not in known:
            ap.error(f"unknown module {m!r}; known: {', '.join(known)}")
    sel = set(a.only) if a.only else None

    def want(mod: str) -> bool:
        return sel is None or mod in sel

    ctx = Extraction(a.camels_root, a.repo, a.extracted_on)
    if any(want(m) for m in LEGACY_MODULES):
        extract_legacy(ctx, want)
    for mod, fn in LESSON_EXTRACTORS.items():
        if want(mod):
            fn(ctx)

    print("extracted OK", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
