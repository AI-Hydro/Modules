# Contributing a Learning Module

## Quick checklist

- [ ] `modules/<your-id>/module.html` — the self-contained module
- [ ] `modules/<your-id>/manifest.json` — metadata (required fields below)
- [ ] `modules/<your-id>/README.md` — description, learning objectives, prerequisites
- [ ] `modules/<your-id>/thumbnail.png` — 640×360 screenshot (optional but recommended)
- [ ] Module renders correctly in a plain browser (static fallback works)
- [ ] Module opens without CSP errors in AI-Hydro HTML Preview
- [ ] At least one interactive element (slider, quiz, map, chart)
- [ ] At least one checkpoint (quiz question or summary)
- [ ] Provenance footer with data sources and citations

## Required manifest fields

```json
{
  "moduleId": "your-unique-id",
  "title": "Human-readable title",
  "description": "One or two sentences shown in the marketplace card",
  "version": "0.1.0",
  "author": "Your Name",
  "license": "CC-BY-4.0",
  "topic": "terrain-analysis",
  "level": "intro",
  "estimatedMinutes": 15,
  "tags": ["keyword1", "keyword2"],
  "requires": {
    "executable": true,
    "python": ["numpy"]
  }
}
```

**Valid levels:** `intro`, `intermediate`, `advanced`

**Suggested topics:** `terrain-analysis`, `streamflow`, `hydrograph`, `water-quality`, `modelling`, `remote-sensing`, `data-access`

## Branding contract

Every module must follow the [AI-Hydro brand guide](https://github.com/AI-Hydro/AI-Hydro/blob/main/branding.md):
- Dark-first design (`#0a0a15` background)
- Cyan/blue accent palette (`#00A3FF`, `#00DDFF`)
- Quicksand (display), Poppins (headings), Nunito (body), JetBrains Mono (code)
- AI-Hydro logo in the module header

## Standalone fallback rule

Modules must render statically in any browser. Executable cells must degrade gracefully when outside the AI-Hydro preview — replace run buttons with a "Open in AI-Hydro to run" pill. The injected `aihydroCellBridge.ts` handles this automatically via `window.aihydro.isStandalone`.

## Module manifest block

Embed the manifest in the HTML file for the panel to parse:
```html
<script type="application/vnd.aihydro.module+json">
{ ... same fields as manifest.json ... }
</script>
```

## PR review

CI checks:
1. `manifest.json` is valid JSON with all required fields
2. `module.html` renders without CSP errors (headless browser check — coming soon)
3. Author and license fields are present

Human review checks branding compliance, accuracy of hydrology content, and originality.
