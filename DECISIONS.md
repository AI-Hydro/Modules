# Decisions

## 2026-10-02 — Retain existing certification semantics

Synchronize the existing metadata checks without treating a certified manifest
as a validated hydrological result. Preserve workflow ownership of generated APIs.

## 2026-11-17 — One shared filter and D8; real CAMELS data or a SYNTHETIC label

Modules stay single self-contained HTML files, so shared algorithms live in `shared/` and `scripts/build_modules.py` inlines them (and the bundled data blobs) into marked regions; tests fail if a module drifts.
Where a lesson names a real gauge it uses a bundled CAMELS-US v1.2 slice with provenance (`scripts/extract_camels.py`); otherwise it is labelled SYNTHETIC and carries no real gauge id.
Every number a lesson states is computed in a cell or tested against one; numbers that could not be sourced or computed offline (global water-budget magnitudes, TWI class thresholds, a resolution claim) were removed rather than kept.
Citations that fail the cite-verify gate are removed with the claims that depended on them; Dingman (2015) stays as a book with no chapter numbers.

