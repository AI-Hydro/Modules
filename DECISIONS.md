# Decisions

## 2026-10-02 — Retain existing certification semantics

Synchronize the existing metadata checks without treating a certified manifest
as a validated hydrological result. Preserve workflow ownership of generated APIs.

## 2026-11-17 — One shared filter and D8; real CAMELS data or a SYNTHETIC label

Modules stay single self-contained HTML files, so shared algorithms live in `shared/` and `scripts/build_modules.py` inlines them (and the bundled data blobs) into marked regions; tests fail if a module drifts.
Where a lesson names a real gauge it uses a bundled CAMELS-US v1.2 slice with provenance (`scripts/extract_camels.py`); otherwise it is labelled SYNTHETIC and carries no real gauge id.
Every number a lesson states is computed in a cell or tested against one; numbers that could not be sourced or computed offline (global water-budget magnitudes, TWI class thresholds, a resolution claim) were removed rather than kept.
Citations that fail the cite-verify gate are removed with the claims that depended on them; Dingman (2015) stays as a book with no chapter numbers.


## 2026-11-17 — Wave 2: one quiz engine, origin-checked completion, derived (not hand-kept) metadata

- **Quizzes.** One engine in `shared/quiz.js`. Answers are functions of the lesson's data or code, never literals; wrong answers never name the right one; revealing is not passing. The old engines posted `{type:'aihydro-quiz-complete'}` to `'*'`, a message the extension does not handle (only the bridge's own wiring of `.aihydro-quiz-submit` reported progress). The engine posts the extension's real `artifact/quizComplete`, with `window.__aihydroArtifact` identity, to `location.ancestorOrigins[0]` (the embedding shell). The shell checks `event.source`, not `origin`, and the sandboxed iframe has an opaque origin, so a named target origin is the only restriction available to the page. If no origin can be determined nothing is posted rather than falling back to `'*'`. Risk to confirm in the installed build: that `ancestorOrigins` is populated for the preview iframe; an extension-side `aihydro.reportQuiz()` would remove the dependency.
- **Embedded manifest is generated.** `manifest.json` keeps the marketplace/API names (`moduleId`, `estimatedMinutes`, `author`); the preview reads `id`, `estimated_minutes`, `authors[]`. Both consumers keep their schema; `build_modules.py` derives the embedded block from the file manifest with one mapping, so they cannot disagree. `updatedAt` left the manifests: the API derives it from git history.
- **Certification semantics.** The inline certifier checks metadata only (citation, description, tags, estimated minutes). It now says so (`metadata_complete`) and carries `scientific_review: null` until a human records a review, so a badge can no longer imply scientific validity. Alternative considered: dropping the block entirely; kept because the checks catch real omissions.
- **Fallbacks outside the preview.** A 2-D canvas must not be created on a canvas the bridge may later take for WebGL, so fallbacks use separate elements and only appear when `window.parent === window` and no bridge exists (a plain browser tab).
- **Static outputs** are run headless at default settings and stored with the sha256 of the source that produced them; CI checks the hash, not the bytes of the PNG, so a different matplotlib build cannot fail a pull request, but a changed cell source cannot ship a stale figure.

## 2026-11-17 — Wave 3: three lessons (precipitation, evapotranspiration, runoff generation)

The owner asked for these lessons to be added to the course (2026-11-17), so the course goes from eight to eleven modules (ten learning modules plus the certificate). Certificate counts follow (10); its wording, signature and completion check remain owner decisions.

- **Module ids** are frozen: `precipitation-point-to-basin`, `evapotranspiration-budyko`, `runoff-generation`. Order: water cycle, precipitation, evapotranspiration, runoff generation, watershed, then the existing lessons. Evapotranspiration and runoff generation both need precipitation; watershed-runoff needs runoff generation.
- **Reproduction-check framing, with an embargo.** Whatever CAMELS tabulates (`p_mean`, `frac_snow`, `high_prec_freq`, `pet_mean`, `runoff_ratio`, `soil_conductivity`) is shown as a reproduction check; differences are explained by period and method (CAMELS 1989–2009 against the lesson's water years, own radiation inputs, Priestley–Taylor with α calibrated per catchment). No lesson says that a CAMELS value is wrong, biased or in error, and none states which threshold CAMELS used for `frac_snow`; tests lint the pages for this. Budyko-space points outside the limits are read as assumptions that do not hold (closed basin, steady state, snow, seasonality), never as data errors.
- **Encodings.** Daymet precipitation is stored losslessly as integer hundredths of a mm (the files carry two decimals). Daily temperature is stored only on wet days, as the half-degree bin floor(tmax + tmin), which makes "mean temperature below T" exactly "bin below 2T" for the 0.5 °C thresholds of the rain/snow slider. The 671-gauge Budyko table is rounded to a stated number of decimals (recorded in `PROVENANCE.json`); the four course basins also keep unrounded values. Page budget: each page at most 200 KB (hard cap 250 KB).
- **`modelOutput` is not used.** The CAMELS model-output archive (`basin_timeseries_v1p2_modelOutput_daymet.zip`) is online-only on Box and was not touched; PET in the lessons is computed from the Daymet forcing.
- **runoff-generation merges the two SYNTHETIC cells** (column and hillslope) into one cell, `column-hillslope`, to keep the page under 200 KB; the real-events cell stays separate.
- **Event rain is summed over the same window as the quickflow.** An event starts on a day with at least 10 mm after two days under 1 mm; the window runs to the next event or 10 days; event rain and event quickflow are both summed over that window, so the runoff coefficient is a ratio of like with like. The thresholds are teaching choices; the median coefficient is shown for 5, 10 and 20 mm. The antecedent-wetness wording is generated from computed medians and a rank correlation.
- **Merz et al. (2006) DOI.** The planned 10.1016/j.jhydrol.2006.03.006 passes the gate but resolves to a different paper (Arp et al.); the lesson cites 10.1016/j.jhydrol.2006.06.008.
- **References without DOI** (FAO-56, Budyko 1974, NEH-4) sit in blocks marked "Reference without DOI — pending owner decision"; Fu (1981) is not cited, the Fu form is cited through Zhang et al. (2004).
- **DOI scan.** `test_every_doi_in_the_modules_passed_the_gate` normalises HTML entities and percent-encoding and matches SICI-style DOIs (`<`, `>`, `(`, `)`, `;`) in full. The two lessons that had worked around the old pattern now show their DOIs as written.
- **Numbered cross-references** in the older lessons ("Module 5", "M6") follow the new order; lessons otherwise point to topics by name where they can.
- **Page size.** The evapotranspiration-budyko page is about 221 KB (220,758 bytes before the fixes below), over the 200 KB target and under the 250 KB hard cap. It was not trimmed: the size comes from the inlined 670-basin table, the four-basin Daymet forcing blob and the two pre-rendered figures, all of which the lesson computes from.

