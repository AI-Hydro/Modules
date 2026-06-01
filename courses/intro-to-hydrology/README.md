# Introduction to Hydrology

**7 modules · ~5 hours · Intro level · CC-BY-4.0**  
**Author:** Mohammad Galib, Purdue University

A hands-on, animated tour through the whole hydrologic cycle — from the first flash of water vapour rising off the ocean to a full basin characterisation at your fingertips. Each module showcases a different interactive capability of the AI-Hydro learning hub.

## Module sequence

| # | Module | Time | Showcases |
|---|--------|------|-----------|
| 1 | [The Water Cycle in Motion](../../modules/water-cycle-in-motion/) | 30 min | Manim animation, timeline |
| 2 | [The Watershed: Where Rain Becomes Runoff](../../modules/watershed-runoff/) | 40 min | 3-D scene3d, rain sim |
| 3 | [Reading a Hydrograph](../../modules/reading-a-hydrograph/) | 30 min | bindParam, scrollytelling |
| 4 | [Splitting the Flow: Baseflow Separation](../../modules/baseflow-separation/) | 40 min | α-slider, compare wipe |
| 5 | [Catching the Flow: Real Streamflow Data](../../modules/real-streamflow-data/) | 45 min | Leaflet map, USGS NWIS |
| 6 | [The Shape of the Land: DEM to TWI](../../modules/dem-to-twi/) | 55 min | scene3d, compare, D8 |
| 7 | [Capstone: A Basin's Water Story](../../modules/capstone-basin-story/) | 60 min | plot FDC, timeline, synthesis |

## Prerequisite DAG

```
M1 Water Cycle
  ├── M2 Watershed ──────────────────── M6 DEM→TWI ──┐
  └── M3 Hydrograph                                   ├── M7 Capstone
        └── M4 Baseflow ─────────────────────────────┤
              └── M5 Real Data ──────────────────────┘
```

## Loading the course in AI-Hydro

Open the HTML Preview panel → Courses → paste the `course.json` URL:

```
https://raw.githubusercontent.com/AI-Hydro/Modules/main/courses/intro-to-hydrology/course.json
```

## License

[CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/)
