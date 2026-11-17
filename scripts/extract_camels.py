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
      --camels-root /path/to/camels_us  [--repo .]

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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--camels-root", required=True, type=Path)
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parent.parent)
    ap.add_argument("--extracted-on", default=dt.date.today().isoformat(),
                    help="date recorded in PROVENANCE.json (default: today)")
    a = ap.parse_args()
    root, repo = a.camels_root, a.repo

    names = read_attr(root / "camels_name.txt")
    topo = read_attr(root / "camels_topo.txt")
    hydro = read_attr(root / "camels_hydro.txt")
    clim = read_attr(root / "camels_clim.txt")
    attr_sha = {
        n: sha256_bytes((root / n).read_bytes())
        for n in ("camels_name.txt", "camels_topo.txt", "camels_hydro.txt", "camels_clim.txt")
    }

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

    zpath = root / ZIP_NAME
    zf = zipfile.ZipFile(zpath)  # opened read-only
    flow_cache: dict[str, tuple[str, str, list]] = {}
    forc_cache: dict[str, tuple[str, str, dict, list]] = {}

    def flow(g: str):
        if g not in flow_cache:
            member = FLOW_MEMBER.format(huc=meta[g]["huc_02"], gauge=g)
            raw = zf.read(member)
            flow_cache[g] = (member, sha256_bytes(raw), parse_flow(raw))
        return flow_cache[g]

    def forcing(g: str):
        if g not in forc_cache:
            member = FORC_MEMBER.format(huc=meta[g]["huc_02"], gauge=g)
            raw = zf.read(member)
            header, series = parse_forcing(raw)
            forc_cache[g] = (member, sha256_bytes(raw), series, header)
        return forc_cache[g]

    def prov_base(module_id: str) -> dict:
        return {
            "module": module_id,
            "dataset": "CAMELS-US v1.2 (basin_timeseries_v1p2_metForcing_obsFlow + attribute files)",
            "camels_root_relative_sources": {
                "attribute_files": {n: {"sha256": s} for n, s in attr_sha.items()},
                "archive": ZIP_NAME,
            },
            "extraction_script": "scripts/extract_camels.py",
            "extracted_on": a.extracted_on,
            "citations": CITATIONS,
            "licence_note": (
                "CAMELS-US streamflow originates from USGS NWIS (public domain); "
                "forcing is Daymet basin means as distributed by CAMELS."
            ),
            "access": "read-only local copy; no network access during extraction",
        }

    # ---- five-year flow modules -------------------------------------------------
    for mod, gauges in FIVE_YEAR_MODULES.items():
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
        d = repo / "modules" / mod / "data"
        d.mkdir(parents=True, exist_ok=True)
        prov = prov_base(mod)
        prov["series"] = {}
        (d / "camels_gauges.json").write_text(
            json.dumps({g: meta[g] for g in gauges}, indent=1) + "\n")
        (d / "PROVENANCE.json").write_text(json.dumps(prov, indent=1) + "\n")

    print("extracted OK", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
