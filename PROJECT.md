# Modules

Community learning modules and the generated modules API.

## Current state — 2026-11-17

Waves 1 and 2 of the 2026-11-17 modules audit are implemented on branch `fix/modules-wave2-a11y` (built on Wave 1, `fix/modules-wave1-science`).

- Wave 1: one shared Lyne-Hollick filter and D8, real CAMELS-US data with provenance (`modules/*/data`), SYNTHETIC labels elsewhere, verified citations (`CITATIONS.verified.md`).
- Wave 2: one shared quiz engine with numeric/interpretive items computed from the lessons, standalone rendering (pre-rendered cell outputs, plain fallbacks), keyboard and ARIA access, CVD-safe TWI map, hygiene, license in every manifest, generated README/course page/API, PR workflow (`.github/workflows/checks.yml`).
- Open: Wave 3 items of the audit; the owner decisions listed there (certificate wording, NEH-4, course name); confirmation in the installed AI-Hydro build that `location.ancestorOrigins` is available to the preview iframe (see DECISIONS.md).

Everything the PR workflow runs is one command each, listed in CONTRIBUTING.md. `shared/` holds the single copy of every piece of shared code; `python scripts/build_modules.py` inlines it, the data and the pre-rendered outputs into the pages.

History — 2026-10-02

Existing manifest-certification work reviewed for repository synchronization.
Certification checks metadata completeness, not scientific validity.
Workflow YAML and embedded Python compile; shared certification tests pass.

Read CHANGELOG.md for what changed, README.md for usage, ROADMAP.md for remaining checks, and PROGRESS.md for
verification. Generated API publication remains owned by build-api.yml.
