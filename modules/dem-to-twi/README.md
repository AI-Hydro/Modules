# From DEM to TWI

**Level:** Intro · **Time:** ~20 min · **License:** CC-BY-4.0

An interactive learning module that walks through every step of computing the Topographic Wetness Index (TWI) from a Digital Elevation Model.

## What you'll learn

- Why some hillslope cells are wetter than others
- How D8 flow direction routing works (click any DEM cell to trace its flow path)
- Why ln() is used instead of raw a/tan(β)
- D8 vs D∞ algorithm trade-offs
- How DEM resolution affects TWI values
- How to compute TWI in Python with numpy

## What's inside

- **Interactive 5×5 DEM** — click any cell to highlight upstream contributors and downstream flow path, compute approximate TWI
- **Real Leaflet map** — USGS gauge 01031500 (Piscataquis basin, Maine) with simulated qualitative TWI overlay
- **Live calculator** — move sliders to see TWI, tan(β), and a/tan(β) update instantly
- **Deep-dive reveals** — expandable explanations of Why ln, D8 vs D∞, resolution dependence
- **Python cells** — point TWI and 16×16 synthetic catchment heatmap (requires AI-Hydro preview kernel)
- **Checkpoint quiz** — test your understanding
- **References** — 6 peer-reviewed citations with DOI links

## Running in AI-Hydro

Install via the Modules Marketplace in the HTML Preview panel. Requires numpy and matplotlib for the executable cells.

## Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md) or open an issue on this repository.
