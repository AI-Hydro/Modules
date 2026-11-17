# Introduction to Hydrology

**8 modules · ~5 hours (305 min of lessons) · Intro level · CC-BY-4.0**  
**Author:** Mohammad Galib, Purdue University

A hands-on, animated tour through the whole hydrologic cycle — from the first flash of water vapour rising off the ocean to a full basin characterisation at your fingertips. Seven learning modules, each showcasing a different interactive capability of the AI-Hydro learning hub, followed by a personalised certificate of completion.

## Module sequence

| # | Module | Time | Prerequisites |
|---|--------|------|---------------|
| 1 | [The Water Cycle in Motion](../../modules/water-cycle-in-motion/) | 30 min | none |
| 2 | [The Watershed: Where Rain Becomes Runoff](../../modules/watershed-runoff/) | 40 min | M1 |
| 3 | [Reading a Hydrograph](../../modules/reading-a-hydrograph/) | 30 min | M1 |
| 4 | [Splitting the Flow: Baseflow Separation](../../modules/baseflow-separation/) | 40 min | M3 |
| 5 | [Catching the Flow: Real Streamflow Data](../../modules/real-streamflow-data/) | 45 min | M3 |
| 6 | [The Shape of the Land: DEM to TWI](../../modules/dem-to-twi/) | 55 min | M2 |
| 7 | [Capstone: A Basin's Water Story](../../modules/capstone-basin-story/) | 60 min | M4, M5, M6 |
| 8 | [Congratulations: Course Complete](../../modules/course-certificate/) | 5 min | M7 |

## Prerequisite graph

Generated from the `prerequisites` of each module in `course.json`; an arrow means "comes before".

```mermaid
flowchart TD
    M1["M1 · The Water Cycle in Motion"]
    M2["M2 · The Watershed: Where Rain Becomes Runoff"]
    M3["M3 · Reading a Hydrograph"]
    M4["M4 · Splitting the Flow: Baseflow Separation"]
    M5["M5 · Catching the Flow: Real Streamflow Data"]
    M6["M6 · The Shape of the Land: DEM to TWI"]
    M7["M7 · Capstone: A Basin's Water Story"]
    M8["M8 · Congratulations: Course Complete"]
    M1 --> M2
    M1 --> M3
    M3 --> M4
    M3 --> M5
    M2 --> M6
    M4 --> M7
    M5 --> M7
    M6 --> M7
    M7 --> M8
```

## Loading the course in AI-Hydro

Open the HTML Preview panel → Courses → paste the `course.json` URL:

```
https://raw.githubusercontent.com/AI-Hydro/Modules/main/courses/intro-to-hydrology/course.json
```

## License

[CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/)
