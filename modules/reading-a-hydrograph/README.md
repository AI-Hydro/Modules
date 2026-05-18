# Reading a Hydrograph

An 18-minute interactive lesson on the anatomy of a storm hydrograph — and how to pull baseflow out of it.

## Learning objectives

By the end of the module, the learner can:

1. Identify the **rising limb**, **peak**, and **recession** on any storm hydrograph and explain what each tells you about the catchment.
2. Apply the **Lyne–Hollick recursive digital filter** for baseflow separation and predict how the **Baseflow Index (BFI)** responds to changes in the filter parameter α.
3. Explain why **doubling rainfall does not double the peak** — i.e., why saturated-soil runoff is non-linear.
4. Recognise the contrasting hydrograph fingerprints of snowmelt-dominated, flashy headwater, and baseflow-dominated catchments.

## Interactions

- **Scrollytelling intro** — three rising-limb / peak / recession steps fire as you scroll.
- **Anatomy SVG plot** with hover tooltips and an inline "probe by dragging" Tangle.
- **BFI explorer** — α slider *and* an inline draggable α in the prose (both stay in sync).
- **Storm comparison** — drag the rainfall-multiplier Tangle inline in a sentence and watch a 2-panel response.
- **3-question checkpoint quiz** covering shape interpretation, filter behaviour, and runoff non-linearity.
- **Python cell** with a gauge dropdown — source regenerates on each change.

## Prerequisites

None beyond basic familiarity with what a streamflow time-series looks like.

## How it runs

Static HTML — drop into any browser and everything except the Python cell works.
Inside the AI-Hydro HTML Preview, the Python cell executes against an isolated kernel
(`numpy`, `matplotlib`); outside, it shows an "Open in AI-Hydro to run" pill.

## License

CC-BY-4.0. Original synthetic data; analytical methods cite the Lyne–Hollick (1979),
Nathan & McMahon (1990), Eckhardt (2005), and SCS (1972) literature.
