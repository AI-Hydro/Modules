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
