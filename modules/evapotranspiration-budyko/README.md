# The Return Flow: Evapotranspiration and the Budyko Curve

**Level:** Intro · **Time:** ~40 min · **License:** CC-BY-4.0 · **Course:** [Introduction to Hydrology](../../courses/intro-to-hydrology/)

Compute potential evapotranspiration two ways (Hargreaves–Samani and Priestley–Taylor) from real Daymet weather for four CAMELS-US basins, compare the result with the tabulated CAMELS `pet_mean` as a reproduction check, derive long-term actual evapotranspiration from P − Q, and place 670 CAMELS basins in Budyko space with a Fu curve whose ω you fit yourself. Basins outside the Budyko limits are read as assumptions that do not hold (steady state, closed basin), not as data problems.

## What you'll learn

- Why PET is a demand set by energy and AET is limited by supply, and what the two Budyko limits are.
- How Hargreaves–Samani (temperature plus extraterrestrial radiation) and Priestley–Taylor (net radiation) are built, step by step, from real Daymet columns.
- How the one-water-year numbers compare with the 1989–2009 CAMELS `pet_mean`, and why they differ (period, method, radiation inputs).
- Why AET = P − Q only holds as a long-term average, and what a Budyko plot of 670 basins shows.

## Requirements

Python packages: `numpy`, `matplotlib`. The data (a Daymet water year for four basins and three attributes for 671 gauges) are bundled in `data/et-budyko.json` with provenance in `data/PROVENANCE.json`; no network access.

## Data

CAMELS-US v1.2 (Newman et al. 2015; Addor et al. 2017); Daymet forcing (Thornton et al. 1997). The bundled slice is rebuilt by `python scripts/extract_camels.py --camels-root <path> --only evapotranspiration-budyko`.

## Citation

Zhang, L., Hickel, K., Dawes, W. R., Chiew, F. H. S., Western, A. W. & Briggs, P. R. (2004). A rational function approach for estimating mean annual evapotranspiration. Water Resources Research. doi:10.1029/2003WR002710

## License

[CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/) — Mohammad Galib, Purdue University
