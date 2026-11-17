# The Watershed: Where Rain Becomes Runoff

**Level:** Intro · **Time:** ~40 min · **License:** CC-BY-4.0 · **Course:** [Introduction to Hydrology](../intro-to-hydrology/)

Define a catchment, trace D8 flow paths across a SYNTHETIC 3-D terrain (depression-filled, drop/distance routing, stream network from flow accumulation), orbit a real basin (the Fish River, Maine, from the Copernicus GLO-30 DEM) and drop rain on it, then turn rainfall into runoff with an executable rational-method cell and an SCS curve-number cell.

## What you'll learn

See the module itself — open it in AI-Hydro's HTML Preview panel.

## Data

Sections 2–4 and 6 are SYNTHETIC (formula-built terrain, assumed design inputs). Section 5 is real: the Copernicus GLO-30 elevation model of the Fish River basin (USGS 01013500), cut to the delineated divide (2258.5 km²), reduced to a 510 m block-mean mesh with a 10× vertical exaggeration. Channels are derived from the DEM at a 25 km² threshold, not mapped. Built by `tools/build_scene3d.py`; payload, poster and provenance sidecar are in `data/`. Credit: European Space Agency & Airbus (2022), Copernicus Global Digital Elevation Model, doi:10.5270/ESA-c5d3d65. The section 5 elevation grid and poster are adapted Copernicus WorldDEM-30 data under the [Licence for the use of the Copernicus WorldDEM-30](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/DEM/resources/license/License-COPDEM-30.pdf), not CC-BY; Article 6(b) notice: "produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved". Article 6(c): "The organisations in charge of the Copernicus programme by law or by delegation do not incur any liability for any use of the Copernicus WorldDEM-30".

## Requirements

Python packages: `numpy`, `matplotlib` (for the two rain→runoff cells). The 3-D view needs AI-Hydro's HTML Preview with WebGL; the poster and the drop-rain map of section 5 work without it.

## Citation

O'Callaghan, J.F. & Mark, D.M. (1984). The extraction of drainage networks from digital elevation data. Comput. Vision Graph. Image Process., 28(3), 323–344. doi:10.1016/S0734-189X(84)80011-0

## License

[CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/) — Mohammad Galib, Purdue University
