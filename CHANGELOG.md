# Changelog

All notable changes to the learning modules. Versions are per module (`manifest.json` and the manifest embedded in `module.html` carry the same number).

## 2026-11-17 — Real-basin 3-D scene (pilot P1) in watershed-runoff

Owner-approved pilot of docs/vision-2040/findings/threejs-studio-feasibility-2026-11-17.md (P1). Owner ruling: the Copernicus DEM credit goes in the lesson's References, not in the scene.

### watershed-runoff 0.3.0 → 0.4.0
- New section 5, "A real basin: the Fish River, Maine (USGS 01013500)": an orbitable 3-D surface of the Copernicus GLO-30 DEM (510 m block-mean mesh, 116 × 153 cells, vertical exaggeration 10× printed in the scene), the divide outline and DEM-derived channels (pysheds 0.5, threshold 25 km², labelled as derived), and a "drop rain here" map that traces the D8 path to the outlet with the shared `shared/d8.js` on the same mesh (mouse, touch and keyboard; readout in a live region; the 3-D scene shows the path too). Caveats on the page: exaggeration, block-mean smoothing, derived channels, lakes flat in the DEM (counted from the data: 9 patches of at least 1 km², 110.8 km²), the DEM cut to the divide (the scene is an island) and map orientation. One checkpoint item (question 6): the D8 path length from the highest mesh cell to the outlet, computed from the scene data.
- The scene works without the 3-D bridge: a plan-view poster and a status message are in the markup, the drop-rain map is plain 2-D canvas, and the poster is replaced by the live canvas only after the bridge's `scene3d` has drawn a frame (two animation frames after it resolves). With the released bridge or the hardened one (AI-Hydro PR 181) the same markup applies; `data-fallback="#fishPoster"` lets the hardened bridge hide the poster itself.
- The synthetic sections (2, 3, 4 and the two design calculations) are unchanged; only their numbers moved (rain to runoff is now section 6, the checkpoint 7). The synthetic 3-D horseshoe is kept: it shows D8 on a terrain whose answer is known, which the real basin cannot.
- Sources & Further Reading: Copernicus DEM (ESA & Airbus, 2022, doi:10.5270/ESA-c5d3d65) with the licence wording from the DEM's manifest.
- Page size 109 KB → 224 KB (hard cap 250 KB): payload 31.8 KB, poster 41.7 KB (as base64 55.6 KB), code and markup about 27 KB.

### Repository
- `tools/build_scene3d.py` builds the scene deterministically from the DEMO-1 evidence (polygon and DEM verified by sha256) into `modules/watershed-runoff/data/`: `fish-river-scene.json` (the payload, inlined as a `json:` blob), `fish-river-poster.png` and `.attrs.json` (inlined by the new `img:` marker), and `fish-river-scene.provenance.json` (hydrofigs.provenance/2 style; repository-relative paths; no paths, hashes or provenance footers in the page or on the poster).
- `scripts/build_modules.py`: new `img:<name>` marker, an `<img>` from `data/<name>.png` and `data/<name>.attrs.json`.
- `tests/js/fakedom.js`: the fake `setInterval` returns a positive id like a real timer (id 0 made `shared/ready.js` arm a second poll when two handlers call `whenReady`).

## 2026-11-17 — Wave 3: precipitation, evapotranspiration and runoff generation

Owner request, 2026-11-17: add the precipitation, evapotranspiration and runoff-generation lessons to the course. Everything in the Wave 2 changelog below is unchanged; certificate wording, signature and completion logic stay owner decisions.

### Course intro-to-hydrology 0.3.0 → 0.4.0
- Three lessons added after the water cycle: precipitation-point-to-basin (order 2), evapotranspiration-budyko (3), runoff-generation (4). Prerequisites: precipitation needs water-cycle-in-motion; evapotranspiration-budyko and runoff-generation need precipitation; watershed-runoff now needs runoff-generation. Course abstract says ten learning modules; estimatedHours 5 → 7 (420 min of lessons); new tags precipitation, evapotranspiration, Budyko, runoff-generation, infiltration.
- `courseOrder` in the manifests: watershed-runoff 5, reading-a-hydrograph 6, baseflow-separation 7, real-streamflow-data 8, dem-to-twi 9, capstone-basin-story 10, course-certificate 11. Numbered cross-references in the older lessons ("Module 5", "M6", "Modules 5 and 7") follow the new numbers; water-cycle-in-motion says "the next nine modules".

### course-certificate 0.1.2 → 0.1.3
- Counts follow the course: "All ten learning modules done", "10 Learning Modules · ~7 Hours", "Requires completion of all 10 course modules", share text "10 modules". Institution wording, signature block and completion check are unchanged and still owner decisions.

### Review fixes (same day)
- precipitation-point-to-basin: figure alt text now describes the one map the cell draws; gauge labels near the right edge no longer clip; one quiz hint and the reproduction note reworded. runoff-generation and evapotranspiration-budyko: hints reworded to point at where to look; a neutral note of possible reasons next to events with RC above 1 and points outside the Budyko limits.

### Repository
- `test_every_doi_in_the_modules_passed_the_gate` now matches DOIs that contain `<`, `>`, `(`, `)`, `;` in full (SICI-style, e.g. Thiessen 1911, Priestley & Taylor 1972), after normalising HTML entities and percent-encoding; regression test added. The two lessons that worked around the old pattern show those DOIs as written.
- Module set must equal the course's module set and the manifests' `courseOrder` must equal the position in `course.json`; the SYNTHETIC-label test covers the new lessons.


### precipitation-point-to-basin new → 0.1.0
- New lesson, "Rain and Snow: From Gauge to Basin" (topic precipitation, 35 min). A gauge is a point (a computed funnel-to-basin ratio); a SYNTHETIC 60 × 60 km storm field with six gauges G1 to G6 (toggle buttons with `aria-pressed`, IDW power slider, map radio group) compares the arithmetic mean, Thiessen polygons and inverse-distance weighting against a known true mean, with a Thiessen raster labelled by region and a weights table; four real CAMELS-US basins (basin cards) show the daily exceedance curve, wet-day share, high-precipitation days, longest dry spell and largest day for water years 1996 to 2000, the 20-water-year monthly regime with DJF and JJA shares, and the snow fraction against a rain/snow temperature threshold (−2 to +3 °C) with CAMELS `frac_snow` beside it as a reference; a reproduction check recomputes CAMELS `p_mean` from 20 years of monthly totals and `high_prec_freq` from five years of daily values and says what differs (the period).
- Two executable cells with pre-rendered outputs and alt text: `areal-precip` (SYNTHETIC, rebuilt from the gauge set and IDW power) and `precip-climate` (REAL, rebuilt from the basin and threshold). Seven-item checkpoint (four choices, three numeric) whose answers are computed from the page's own model and data and recomputed independently in the tests.
- Data: `data/precip-data.json` (about 37 KB; daily precipitation in integer hundredths of a mm and the half-degree temperature bin on wet days for WY1996–2000, monthly totals for WY1990–2009, four basins) with `data/PROVENANCE.json` (source member paths, sha256). Extractor: `extract_precipitation_point_to_basin` in `scripts/extract_camels.py`. The temperature is stored as the bin floor(tmax + tmin) so that "mean temperature < T" is exactly "bin < 2 T" for the 0.5 °C thresholds the lesson uses.
- Citations (all pass the gate, see `CITATIONS.verified.md`): Thiessen 1911, Shepard 1968, Thornton et al. 1997, Jennings et al. 2018, with Newman et al. 2015 and Addor et al. 2017 for the data.

### evapotranspiration-budyko new → 0.1.0
- New lesson "The Return Flow: Evapotranspiration and the Budyko Curve" (topic evapotranspiration, ~40 min, course order 3).
- Real data: Daymet water year 1997 (dayl, srad, tmax, tmin, vp) for four CAMELS basins, and aridity / runoff_ratio / frac_snow for 671 gauges (`data/et-budyko.json`, 64.8 KB with provenance; extractor `--only evapotranspiration-budyko`).
- PET two ways (Hargreaves–Samani; Priestley–Taylor with the net-radiation budget shown step by step, α slider), checked against the tabulated `pet_mean` as a reproduction check with the period/method differences stated.
- Long-term AET from E = P − Q; Budyko space with 670 basins, both limits, a Fu curve with an ω slider and an in-lesson least-squares fit; points outside the limits are read as assumptions that do not hold, not as data problems.
- Page size is about 221 KB, over the 200 KB target and under the 250 KB cap; it was not trimmed because it carries the inlined 670-basin table, the forcing blob and two figures.
- Two executable cells (`pet-two-ways`, `budyko-camels`) with pre-rendered outputs; seven-item checkpoint with computed answers; five DOIs gate-verified, two handbooks without DOI marked pending the owner's decision.

### runoff-generation new → 0.1.0
- New lesson, "Runoff Generation: Infiltration Excess and Saturation Excess" (course order 4, about 40 min, prerequisite: the precipitation lesson). Seven sections plus references and provenance: the two mechanisms; a SYNTHETIC Green–Ampt column (ponding time from Mein & Larson, cumulative infiltration from the implicit Green–Ampt equation, rain-intensity and duration sliders); a finite storage deficit with a mass-balance readout P = F + R_IE + R_SE; a keyboard-operable mechanism map over intensity × deficit computed by the same model (text labels plus fill and hatching in three classes); a SYNTHETIC 20-column hillslope whose saturated area grows with storm depth (wetter-start toggle); real events; and a seven-item checkpoint.
- Real part (§6): CAMELS-US v1.2 daily USGS discharge and Daymet basin-mean rain for water years 1996–2000, three basins (Siletz, Leaf, Sabino). Events are days with at least 10 mm after two days under 1 mm, a window of up to 10 days, event rain and quickflow both summed over that same window, quickflow from the shared Lyne–Hollick filter (α = 0.925), event runoff coefficient and 7-day antecedent rain; the thresholds are stated as teaching choices and the median RC is shown for 5, 10 and 20 mm. The antecedent-wetness wording is generated from the computed medians and rank correlation, not typed. Fish River is left out with its CAMELS `frac_snow` as the stated reason. The largest daily rain (as a 24-hour mean) is set beside the CAMELS `soil_conductivity` (cm/hr) and the lesson says only what that computation shows. CAMELS `runoff_ratio` is shown as context for a different period, not as a one-to-one check.
- Two executable cells with pre-rendered output: `column-hillslope` (the two SYNTHETIC models in one cell, kept in one to stay under the 200 KB page budget) and `event-runoff-ratios` (REAL; Lyne–Hollick inlined from `shared/lyne_hollick.py`). The JS models and the cells agree to 1e-6 and are recomputed independently in `tests/test_runoff_generation.py` (including explicit time stepping of the column, an independent event detector and the quiz answers).
- Data: `data/runoff-events.json` (blob, about 40 KB) and `data/PROVENANCE.json` (source members and sha256), written by the `runoff-generation` extractor in `scripts/extract_camels.py`.
- Citations (all pass the gate, see CITATIONS.verified.md): Horton 1933, Dunne & Black 1970, Green & Ampt 1911, Mein & Larson 1973, Merz et al. 2006, Blume et al. 2007, Cosby et al. 1984, Thornton et al. 1997. The DOI first planned for Merz et al. (10.1016/j.jhydrol.2006.03.006) resolves to a different paper and was replaced by 10.1016/j.jhydrol.2006.06.008.

## 2026-11-17 — Wave 2: function, accessibility, repository

Source: `docs/vision-2040/findings/modules-audit-2026-11-17.md` (Wave 2). Content questions from Wave 1 are unchanged; nothing about the certificate's institution wording, signature or completion logic, NEH-4 or the course name was touched.

### Cross-cutting

- **One bridge-ready promise.** `shared/ready.js` replaces the per-call `setInterval` in every module: `whenReady()` calls share one promise, at most one 50 ms poll exists per page (none when the bridge is already there) and it stops after about 10 s outside the preview. The dead `bindParam(...)` calls (wrong signature, they never did anything) were removed with it.
- **One quiz engine.** `shared/quiz.js` + `shared/quiz.css` replace three engines (radio + submit that revealed the answer, one-shot buttons that locked after one try, bridge-wired blocks). Retry is always possible; nothing about the answer is in the DOM before the first attempt; a wrong answer gets feedback for that choice without naming the right one; "Show explanation" appears after two misses and never counts as correct; native radios / text field + Check button (Enter checks a numeric answer), `fieldset`/`legend`, `role=status` live regions. Completion is posted as `artifact/quizComplete` (the exact message the extension handles) with an explicit target origin taken from `location.ancestorOrigins` (the extension listens on `event.source` and does no origin check, and the iframe is sandboxed without `allow-same-origin`); `'*'` is never used and nothing is posted when the origin cannot be determined or the page is standalone. Every module with a checkpoint keeps its existing questions and gains numeric or interpretive items whose answers are computed from the page's own data or code and recomputed independently in the tests.
- **Standalone rendering.** Each executable cell ships a pre-rendered output (`modules/<id>/static/`, produced by `scripts/render_static_outputs.py` with `python -s -E`; stored stdout plus a palette-quantised PNG, with alt text) inlined into the cell's `.aihydro-output` and replaced by the bridge on a real run. The Manim cell shows the final frame rendered with Manim; the NWIS cell says plainly it needs the network. Code panes already followed the controls without the bridge (tested). Where a map or 3-D view needs the bridge, a plain-canvas/SVG fallback is shown outside the preview (shaded relief from the DEM, a longitude/latitude sketch of the gauges and catchment, a plain-SVG flow-duration curve); no geometry is invented.
- **Accessibility.** `shared/a11y.js`: keyboard sliders (WAI-ARIA keys) for the tangle numbers (reading-a-hydrograph) and both compare wipes; roving-tabindex grid with Enter/Space and a text list of upstream and path cells (dem-to-twi SVG cells; the `role="img"` parent that hid them is now a labelled group); keyboard cursor, text readout and `role=application` for the watershed canvas; polite live regions for readouts in every module (the bathtub readout no longer rewrites a live region every frame; a calm spoken summary follows the slider); the bathtub re-steps under reduced motion (each slider change runs 30 days, plus an "Advance 10 days" button), SMIL animation is paused, the capstone auto-play is hidden, smooth scrolling is off; visible focus rings; WCAG AA contrast fixes (axis labels, dimmed flux labels, certificate placeholder).
- **Non-colour-only encodings.** The red/amber/green TWI map is now viridis (`shared/cmap.js`, 17 anchors sampled from matplotlib's viridis) with the value printed in each cell and the outlet outlined; flood days in the matplotlib plots are amber *and* hatched; quickflow is hatched in the baseflow plots; flux arrows differ by dash pattern as well as colour and keep their text labels; the upstream/path overlays have dashed/solid outlines and a text list.
- **Hygiene.** The dead Leaflet normaliser (it only acts on `.folium-map`, which no module has) is gone from every module; baseflow-separation no longer ships the saved preview/editor styles, `contenteditable` cards and bridge-generated compare nodes; all inline `onclick` handlers became `addEventListener`/`data-scroll`; the double-firing print button of the certificate fires once; "unlock the next module" text is gone (nothing is gated); fonts keep the existing Google Fonts link as the only external host with system fallbacks; three.js still loads through the bridge.
- **Repository.** `license` is in every `manifest.json`; the embedded manifest is generated from it (`build_modules.py`, one field mapping) and a test compares them; `updatedAt` is no longer hand-kept in manifests (the API takes it from git). `scripts/gen_docs.py` generates the README module table and the course page (table + prerequisite graph) with a `--check` mode; `scripts/build_api.py` builds `api/modules.json` and `api/courses.json` (from `course.json`) with git-derived `updatedAt`; the API workflow triggers on `modules/**`, `courses/**`, `shared/**` and runs it; `.github/workflows/checks.yml` runs the tests, `build_modules.py --check`, the static-output, docs and API checks, manifest validation and `scripts/check_csp.py` (only the Google Fonts hosts are allowed) on every pull request. The "certified" badge is replaced by `metadata_complete` (what the checker looks at) and `scientific_review` (`null` until a human records one); schema in `api/README.md`.

Size: the eight pages grew from 671 451 to about 1.04 MB in total (the shared engine, accessibility code, pre-rendered outputs and figures; baseflow-separation also lost the saved preview styles).

### baseflow-separation 0.2.0 → 0.3.0
- Shared quiz (5 items: the three content questions, a numeric BFI at α = 0.98, and an interpretive item choosing the α whose BFI is closest to the synthetic series' known true share), keyboard compare divider, hatched quickflow with a legend, live BFI readout and meter, pre-rendered cell output.
- The wipe layout bug (labels and divider stretched over the whole panel) is fixed.

### reading-a-hydrograph 0.3.0 → 0.4.0
- Tangle numbers are keyboard sliders (`role=slider`, arrows/Page/Home/End) wired to the range inputs; direct labels for the rising and falling limbs; hatched quickflow; live readouts; shared quiz with computed prompt for Q3, a numeric curve-number item and a numeric item on the §6 gauge BFI; pre-rendered CAMELS figure.

### watershed-runoff 0.2.0 → 0.3.0
- The routing canvas is operable by keyboard (arrow keys, Shift for four cells, Enter/Space to drop a raindrop) with a text readout of the cursor cell and the traced path; shaded-relief fallback for the 3-D terrain outside AI-Hydro; shared quiz with numeric area and rational-method items computed from the DEM and the cell's own constants; pre-rendered outputs for both design cells.

### water-cycle-in-motion 0.2.0 → 0.3.0
- Bathtub re-steps under reduced motion and no longer floods a live region; flux arrows differ by dash pattern; labelled stage slider with spoken stage text; shared quiz with a numeric condensation height computed from the dew-point cell's constants and a numeric steady-state runoff computed by running the bucket; pre-rendered dew-point output and the Manim final frame.

### real-streamflow-data 0.3.0 → 0.4.0
- Gauge cards are keyboard buttons with `aria-pressed`; flood days hatched; plain longitude/latitude sketch of the four gauges where there is no Leaflet bridge; shared quiz with a numeric P95 threshold and a data question on the largest daily flow, both computed from the bundled records; pre-rendered snapshot output.

### dem-to-twi 0.3.0 → 0.4.0
- TWI map is viridis with values in the cells and the outlet outlined (the red/green map is gone), also in the Python cell; the DEM cells form a keyboard grid (arrows, Enter/Space) with text lists of upstream and path cells; keyboard compare divider; shaded-relief and catchment-outline fallbacks; concept animation pauses under reduced motion; shared quiz whose Q3 numbers are computed by re-running the §6 pipeline in the page, plus numeric TWI items; pre-rendered outputs.

### capstone-basin-story 0.3.0 → 0.4.0
- Gauge cards are keyboard buttons; plain-SVG flow-duration curve and gauge sketch outside AI-Hydro; auto-play hidden under reduced motion, stage text announced; flood days hatched; shared quiz with prompts computed from the records (flashiness values, TWI example), a numeric Leaf River BFI and a numeric mean TWI of the synthetic hillslope; pre-rendered outputs for all four cells.

### course-certificate 0.1.1 → 0.1.2
- Print button no longer prints twice; the name preview is a polite live region; placeholder contrast raised; focus styles. Institution wording, signature and completion logic unchanged (owner decisions).

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

### 2026-11-17 review fixes
- capstone: the 5-year vs CAMELS BFI difference is no longer given a cause; both values are shown for all four gauges.
- Softened unconfirmed attributions (alpha = 0.925, Ladson et al. 2013 procedure, CAMELS filter); filter headers now read "multi-pass with reflection; initial quickflow 0 for each pass"; Eckhardt is 2005 everywhere.
