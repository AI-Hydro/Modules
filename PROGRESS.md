# Progress

## 2026-10-02 — Repository synchronization verification

Workflow YAML and embedded Python compile; shared certification tests pass. Reviewed existing changes before committing to the existing remote.
No credentials or private research artifacts included.

## 2026-11-17 — Wave 1: science and data honesty

Implemented Wave 1 of `docs/vision-2040/findings/modules-audit-2026-11-17.md` for all eight modules (see CHANGELOG.md).
Verification: `/opt/miniconda3/bin/python -s -E -m pytest tests` and `node --test tests/js/*.test.js` (no network); `python scripts/build_modules.py --check`
confirms every module carries the shared Lyne-Hollick / D8 text and the bundled CAMELS data verbatim. Citations: CITATIONS.verified.md.
Not done (Wave 2): accessibility, quiz-engine unification, CSP/hygiene, CI/API, README module table.


## 2026-11-17 — Wave 2: function, accessibility, repository

Implemented Wave 2 of `docs/vision-2040/findings/modules-audit-2026-11-17.md` (see CHANGELOG.md and DECISIONS.md).
Verification (no network): `/opt/miniconda3/bin/python -s -E -m pytest tests`, `node --test tests/js/*.test.js`, and the scripts the PR workflow runs:
`build_modules.py --check`, `render_static_outputs.py --check`, `gen_docs.py --check`, `validate_manifests.py`, `check_csp.py`, `build_api.py --check`.
Rendering was also checked by hand in a browser pane over a local static server (quiz states, keyboard sliders, DEM grid, canvas cursor, fallbacks).
Not done: a check inside the installed AI-Hydro build (the quiz completion message depends on `location.ancestorOrigins`); Wave 3 of the audit.

## 2026-11-17 — Wave 3: three new lessons

Merged the three lesson packets (precipitation-point-to-basin, evapotranspiration-budyko, runoff-generation) into `feat/modules-wave3-lessons` after the phase-A generic data-blob and per-lesson extractor work; the combined extraction reproduces every bundled `data/` directory byte for byte (`extract_camels.py --extracted-on 2026-11-17`, `git diff --exit-code modules/*/data`).
Phase B: course 0.4.0 (eleven modules, ten learning modules plus the certificate, estimatedHours 7), certificate 0.1.3 (counts), renumbered cross-references, DOI scan fixed for SICI-style DOIs, tests tightened (module set equals course set; SYNTHETIC labelling covers the new lessons), generated README/course page/API rebuilt.
Verification (no network): `build_modules.py --check`, `render_static_outputs.py --check`, `gen_docs.py --check`, `validate_manifests.py`, `check_csp.py`, `build_api.py --check`, `/opt/miniconda3/bin/python -s -E -m pytest tests -q` (with and without `CAMELS_ROOT`), `node --test tests/js/*.test.js`.
Not done: rendering the three new lessons inside the installed AI-Hydro build; owner decisions on the references without DOI (FAO-56, Budyko 1974, NEH-4).
