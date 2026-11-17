# Rain and Snow: From Gauge to Basin

**Level:** Intro · **Time:** ~35 min · **License:** CC-BY-4.0 · **Course:** [Introduction to Hydrology](../intro-to-hydrology/)

From a rain gauge to a basin average: build the arithmetic, Thiessen and inverse-distance estimates on a synthetic storm field you can inspect completely, then use real CAMELS-US Daymet precipitation for four basins to see how hard, how often and when it falls, test a rain-snow temperature threshold, and reproduce two CAMELS climate attributes with a live Python cell.

## What you'll learn

See the module itself — open it in AI-Hydro's HTML Preview panel. In short:

- why a gauge is a point and a basin mean is an inference;
- the arithmetic mean, Thiessen polygons and inverse-distance weighting, and how the gauge network decides the answer (section 2 is SYNTHETIC and labelled as such);
- daily intensity, wet-day frequency, high-precipitation days and dry spells in four real basins;
- the monthly regime and the winter and summer shares;
- a rain/snow temperature threshold and its effect on the snow fraction;
- a reproduction check of CAMELS `p_mean` and `high_prec_freq`, with the differences explained by period and rule.

## Requirements

Python packages: `numpy`, `matplotlib`. Real data (CAMELS-US v1.2, Daymet basin means for gauges 01013500, 02472000, 09484000 and 14305500) are bundled in `data/precip-data.json` with provenance in `data/PROVENANCE.json`; no network access.

## Citation

Newman, A. J. et al. (2015). Development of a large-sample watershed-scale hydrometeorological data set for the contiguous USA. Hydrology and Earth System Sciences, 19, 209-223. doi:10.5194/hess-19-209-2015

## License

[CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/) — Mohammad Galib, Purdue University
