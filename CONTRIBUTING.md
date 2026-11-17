# Contributing a Learning Module

## Quick checklist

- [ ] `modules/<your-id>/module.html` — the self-contained module
- [ ] `modules/<your-id>/manifest.json` — metadata (required fields below)
- [ ] `modules/<your-id>/README.md` — description, learning objectives, prerequisites
- [ ] `modules/<your-id>/thumbnail.png` — 640×360 screenshot (optional but recommended)
- [ ] Module renders correctly in a plain browser with no AI-Hydro bridge (standalone rule below)
- [ ] Module opens without CSP errors in AI-Hydro HTML Preview (`python scripts/check_csp.py` is clean)
- [ ] At least one interactive element (slider, quiz, map, chart)
- [ ] A checkpoint built with the shared quiz engine, with at least one numeric or interpretive item whose answer is computed from the lesson
- [ ] Provenance footer with data sources and citations
- [ ] `python scripts/build_modules.py`, `python scripts/gen_docs.py` and the tests pass (see "Checks")

## Required manifest fields

```json
{
  "moduleId": "your-unique-id",
  "title": "Human-readable title",
  "description": "One or two sentences shown in the marketplace card",
  "version": "0.1.0",
  "license": "CC-BY-4.0",
  "author": "Your Name, Your Institution",
  "topic": "terrain-analysis",
  "level": "intro",
  "estimatedMinutes": 15,
  "tags": ["keyword1", "keyword2"],
  "requires": {
    "executable": true,
    "python": ["numpy"]
  },
  "citation": { "text": "Author (Year). Title. Venue.", "doi": "10.xxxx/xxxx" }
}
```

**Valid levels:** `intro`, `intermediate`, `advanced`. **Suggested topics:** `terrain-analysis`, `streamflow`, `hydrograph`, `water-quality`, `modelling`, `remote-sensing`, `data-access`.
`updatedAt` is not kept in the manifest: the API takes it from the last git commit that touched the module. `createdAt` is optional (otherwise the first commit date is used).

## One manifest, two naming schemes

`manifest.json` is what the marketplace API reads. The preview reads a block embedded in `module.html` with different field names. **Do not edit the embedded block**: put a marker pair where it goes and run the build, which generates it from `manifest.json`:

```html
<!--@@BEGIN manifest:module@@--><!--@@END manifest:module@@-->
```

| `manifest.json` | embedded block |
|---|---|
| `moduleId` | `id` |
| `estimatedMinutes` | `estimated_minutes` |
| `author` (`"Name, Institution"`) | `authors: [{name, affiliation}]` |
| `title`, `version`, `license`, `topic`, `level`, `requires`, `citation` | same names |

The embedded block also carries `ai_hydro_preview_min_version`. `scripts/validate_manifests.py` and the tests fail if the two ever disagree.

## Branding contract

Every module must follow the [AI-Hydro brand guide](https://github.com/AI-Hydro/AI-Hydro/blob/main/branding.md):
- Dark-first design (`#0a0a15` background)
- Cyan/blue accent palette (`#00A3FF`, `#00DDFF`)
- Quicksand (display), Poppins (headings), Nunito (body), JetBrains Mono (code), loaded from the Google Fonts link with system-font fallbacks; that link is the **only** external host a module may reference
- AI-Hydro logo in the module header

## Standalone rendering rule

Without the `window.aihydro` bridge (a plain browser tab) a module must still be meaningful:

- **Code panes update.** Controls that rewrite a cell's source must do it themselves, then ask the bridge to mirror it (`aihydro.rewriteCell`) only if it is present.
- **Every executable cell shows a pre-rendered output.** Put `<!--@@BEGIN static:<cell-id>@@--><!--@@END static:<cell-id>@@-->` inside the cell's `.aihydro-output`, then run `python scripts/render_static_outputs.py` (it runs each cell headless with `python -s -E` and stores text plus a PNG in `modules/<id>/static/`; add alt text for each figure to `static/alt.json`). The bridge replaces the static block when the learner runs the cell. A cell that cannot run headless (network, a long render) gets an authored note saying so, never made-up output.
- **Interactive widgets work in plain JavaScript.** Where a map or 3-D view needs the bridge, draw a plain fallback in a *separate* element, only when `window.parent === window` and there is no bridge (`shared/cmap.js` has a shaded-relief renderer, `shared/geosketch.js` a longitude/latitude sketch). Never invent geometry.
- **Run buttons** show "Open in AI-Hydro to run" outside the preview.
- Keep three.js, Plotly and Leaflet loading through the bridge; do not add a CDN.

## Shared code

Code used by more than one module lives in `shared/` and is inlined between `@@BEGIN`/`@@END` markers by `python scripts/build_modules.py` (run it after editing `shared/`, `modules/<id>/data/`, `modules/<id>/static/` or a manifest; `--check` fails if a module is stale). Marker kinds: `js:`, `css:`, `pyjs:`, `pypre:`, `json:`, `manifest:` and `static:` (see the docstring of the script).

| File | What it is |
|---|---|
| `shared/ready.js` | one shared promise behind `whenReady()`; never write your own `setInterval` poll |
| `shared/quiz.js`, `quiz.css` | the checkpoint engine |
| `shared/a11y.js`, `a11y.css` | keyboard sliders, `activatable`, `data-scroll` navigation, live regions, reduced-motion helper, focus styles |
| `shared/cmap.js` | viridis colour map and shaded-relief renderer (use it instead of red-green scales) |
| `shared/geosketch.js` | longitude/latitude SVG sketch of points and polygons |
| `shared/lyne_hollick.*`, `shared/d8.*` | the one baseflow filter and D8 pipeline (JS and Python twins) |

### Checkpoints

```js
HydroQuiz.mount(document.getElementById('quiz'), {
  quizId: '<module-id>-checkpoint', moduleId: '<module-id>',
  items: [
    { id: 'q1', type: 'choice', prompt: '…', options: ['…', '…', '…'], correct: 1,
      feedback: ['why option 0 is wrong', null, 'why option 2 is wrong'], explain: 'shown when correct' },
    { id: 'q2', type: 'numeric', unit: 'mm', prompt: '…', answer: function () { return STORM.runoff(40); },
      tol: { abs: 0.02 }, hint: '…', explain: function (a) { return '… = ' + a.toFixed(2); } }
  ]
});
```

Rules: no hand-typed answers (use a function over the page's data or code, `HydroQuiz.sourceConstant(cellId, 'NAME')` reads a constant from a cell's source); a wrong-answer message must not name the right answer; no inline handlers; do not use the class names `aihydro-quiz`, `aihydro-quiz-submit` or ids ending in `SubmitBtn` (the bridge auto-wires those with its own engine). Completion is posted to the host as `artifact/quizComplete` with an explicit target origin, never `'*'`.

### Accessibility rules

Every control that works by dragging also works from the keyboard (`HydroA11y.slider`); every dynamic readout is in a polite live region; no information is carried by colour alone (labels, patterns, values in cells); text contrast is at least AA; with `prefers-reduced-motion` nothing auto-animates and the widgets still update; no inline `onclick` (use `addEventListener` or `data-scroll`).

## Data and citations

- Real-data slices come from CAMELS-US via `scripts/extract_camels.py` and ship with `data/PROVENANCE.json` (source member, sha256, period, units, QC flags, citations). Label anything else SYNTHETIC; do not give synthetic series real gauge ids.
- Every number a lesson states must come from a cell or from a cited, verified source; run each citation through the cite-verify gate and record it in `CITATIONS.verified.md`.

## Checks

These run on every pull request (`.github/workflows/checks.yml`) and are the same commands you run locally:

```bash
python scripts/build_modules.py --check          # shared code, data, manifests and static outputs are inlined
python scripts/render_static_outputs.py --check  # a cell's pre-rendered output matches its current source
python scripts/gen_docs.py --check               # README table and course page match the manifests
python scripts/validate_manifests.py             # manifests valid; embedded block agrees; course graph valid
python scripts/check_csp.py                      # no external hosts except Google Fonts, no eval/fetch/WebSocket
python scripts/build_api.py --check              # api/*.json are current
python -m pytest tests -q                        # use /opt/miniconda3/bin/python -s -E locally in the AI-Hydro workspace
node --test tests/js/*.test.js
```

Regenerate instead of editing by hand: `build_modules.py`, `render_static_outputs.py` (after a cell changes), `gen_docs.py`, `build_api.py`.

## PR review

Automated: the checks above. Human review checks branding compliance, accuracy of the hydrology, and originality. The API's `certification.metadata_complete` only says the manifest is complete; `certification.scientific_review` stays `null` until a reviewer records a review.
