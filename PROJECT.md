# Modules

Community learning modules and the generated modules API.

## Current state — 2026-11-17

Wave 1 of the 2026-11-17 modules audit (science and data honesty) is implemented on branch `fix/modules-wave1-science`: one shared Lyne-Hollick filter and D8, real CAMELS-US data with provenance (`modules/*/data`), SYNTHETIC labels elsewhere, repo-local tests (`tests/`), verified citations (`CITATIONS.verified.md`), per-module version bumps (`CHANGELOG.md`). Wave 2 (accessibility, quiz engines, CSP/hygiene, CI/API) is open.

History — 2026-10-02

Existing manifest-certification work reviewed for repository synchronization.
Certification checks metadata completeness, not scientific validity.
Workflow YAML and embedded Python compile; shared certification tests pass.

Read CHANGELOG.md for what changed, README.md for usage, ROADMAP.md for remaining checks, and PROGRESS.md for
verification. Generated API publication remains owned by build-api.yml.
