# Changelog

All notable changes to the learning modules. Versions are per module (`manifest.json` and the manifest embedded in `module.html` carry the same number).

## 2026-11-17 — Wave 1: science and data honesty

Source: `docs/vision-2040/findings/modules-audit-2026-11-17.md` (Wave 1 items and the cross-cutting items).

### Cross-cutting

- **One Lyne–Hollick filter.** `shared/lyne_hollick.js` and `shared/lyne_hollick.py` implement the standard multi-pass form: three passes (forward, backward, forward), each pass filtering the baseflow of the *previous* pass, with the series reflected 30 steps at both ends. They replace six copy-pasted variants, are inlined by `scripts/build_modules.py` (modules stay single self-contained HTML files with no new script hosts) and agree to 1e-9 (tests).
- **One D8.** `shared/d8.js` / `shared/d8.py`: priority-flood depression filling seeded at the outlet, steepest descent by drop/distance, flow accumulation, slope with an explicit floor, TWI.
- **Real data.** `scripts/extract_camels.py` extracts small slices of CAMELS-US v1.2 (read-only) into `modules/<id>/data/` with `PROVENANCE.json` (source member, sha256, period, units, USGS QC flags, extraction script, citations). Used by real-streamflow-data, capstone-basin-story, reading-a-hydrograph and dem-to-twi.
- **Tests.** `tests/` (pytest + node) assert the claims the lessons make.
- **Citations.** Every reference went through the cite-verify gate; failures were removed with their claims. See `CITATIONS.verified.md`.
- Gauge identities corrected from CAMELS: 01031500 is the Piscataquis River near Dover-Foxcroft, ME; 02472000 is the Leaf River near Collins, MS; 09484000 is Sabino Creek near Tucson, AZ; 14305500 is the Siletz River at Siletz, OR (rain-dominated).

### baseflow-separation 0.1.x → 0.2.0
- BFI is computed live by the shared filter (the invented `estimateBFI` formula and the stated "BFI ≈ 0.55" are gone; at α = 0.925 the series gives 0.742).
- The compare wipe and the Python cell use the same deterministic SYNTHETIC series (no random numbers, no second hand-typed JS hydrograph); the known true baseflow share is printed for comparison.
- Cascade bug fixed (passes re-filtered raw Q); reflection at both ends added.
- "Lower α for sub-daily" removed (α is per time step; the equivalent hourly α is α^(1/24)); unsourced "BFI 0.4–0.8 typical" removed; caveat that BFI is a filter output.
- Duplicate font link removed; manifest.json (0.1.0) and embedded (0.1.1) versions reconciled.

### reading-a-hydrograph 0.2.0 → 0.3.0
- SCS-CN storm pair is no longer degenerate (25 mm and 50 mm at CN 75 both exceed Ia = 16.9 mm); P, Ia and S shown in mm; peak ratio shown only when both storms produce runoff; formula typo fixed; catchment area stated; routed volume equals depth × area.
- Quiz Q3 rewritten (the "already-wet catchment" claim was wrong).
- §6 now plots a real CAMELS water year (observed flow and Daymet basin precipitation) for three correctly named gauges; fabricated rain removed; BFI compared with the CAMELS signature.
- "Published Lyne–Hollick default" corrected (Nathan & McMahon 1990; Ladson et al. 2013).

### real-streamflow-data 0.2.0 → 0.3.0
- Silent fallback to synthetic data removed. The cell holds a real, offline CAMELS-US snapshot (5 water years, 4 gauges) and prints site, parameter 00060, period, snapshot date and approval status. A separate optional cell requests NWIS live and reports failures instead of substituting data.
- Gauge metadata, map coordinates and card facts come from CAMELS; descriptions are derived from the data (e.g. 704 zero-flow days at Sabino Creek).
- Return period uses Weibull plotting positions on annual maxima with a short-record caveat; month binning uses real dates; custom gauge ids are validated (8–15 digits).
- Removed the suspicious "Moore et al. 2019" and unused Pettitt references.

### capstone-basin-story 0.2.0 → 0.3.0
- Real CAMELS observed flow replaces seeded synthetic series under real gauge names; BFI, flashiness (Richards–Baker, Baker et al. 2004), flow-duration percentiles and the story text are computed, never asserted. Percentile labels fixed (Q90 is the *low* flow). Mean Q is converted to mm/day with the CAMELS area.
- TWI step now runs the shared D8 pipeline on a SYNTHETIC hillslope and says so; the forced mean (`twi - twi.mean() + twiMean`) is gone and the per-gauge TWI claims were removed.
- Quiz rewritten to match the data (the "BFI 0.08 for an arid basin" claim contradicted the module's own cell).
- Custom-gauge option removed (no data can be produced for it offline).

### watershed-runoff 0.1.x → 0.2.0
- D8 fixed: outlet is the lowest edge cell, depressions filled (priority-flood), steepest drop **per unit distance**; every cell now reaches the outlet (was 0 of 1024); path walks are guarded.
- Stream network derived from flow accumulation; invented metre units replaced by an explicit synthetic-metres convention; contributing area shown for every click.
- New executable rational-method cell and SCS curve-number cell (both labelled SYNTHETIC); "Original D8" re-attributed to O'Callaghan & Mark (1984).

### water-cycle-in-motion 0.1.x → 0.2.0
- Unsourced global magnitudes removed (land precipitation ≈ 1000 mm/yr, T ≈ 40 % of ET, river discharge, infiltration range); Trenberth et al. (2007) is cited as the place to find them.
- Dew-point lapse corrected: computed from physical constants in a new cell (dry adiabatic 9.76 K/km, dew point 1.75 K/km).
- ΔS → 0 stated as a long-term-average property; bathtub is mass-conserving (storage in mm, ΔS = P − ET − R by construction); unused snowpack store removed from the list; scrubber has an `<input type=range>` fallback.

### dem-to-twi 0.2.0 → 0.3.0
- Flow directions are computed (the hand-typed `FLOW_TO` disagreed with drop/distance D8 at four cells) and tested against a brute-force reference.
- New compute-from-DEM cell (fill → D8 → accumulation → slope → TWI) that also repeats the computation at 60 m; the invented area/slope grids are gone.
- Slope floor stated (tan β ≥ 0.001) with its effect; class thresholds replaced by relative terciles; the Sørensen resolution claim removed; a = A/w explained.
- Map marker moved to the CAMELS outlet (45.17501, −69.3147), name corrected, and the fake "simulated wetness" overlay removed.

### course-certificate 0.1.0 → 0.1.1
- `acquireVsCodeApi()` is called once; "open in browser" is a button instead of firing on load; module counts agree (seven learning modules plus the certificate). Institution wording, signature and completion logic unchanged (owner decisions).

### course intro-to-hydrology 0.2.0 → 0.3.0
- Abstract and module abstracts updated to match the modules; "eight modules" corrected to seven learning modules plus the certificate.

### Not changed (Wave 2)
Accessibility, quiz-engine unification, CSP/hygiene, CI and API generation (`api/` is regenerated by `build-api.yml`).
