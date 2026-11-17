# Citation gate results

Gate: `cite-verify` (OpenAlex + Crossref + Semantic Scholar), run 2026-11-17 for every reference that appears in a module. A citation stays only if the gate passes (two or more indexes resolve to the same DOI) or, for books/handbooks with no DOI, it is marked as such.

Command per entry: `python verify_citation.py --doi <DOI>` (title search was used first for discovery, then the DOI re-verified).

The gate confirms that a work exists and the DOI/title/year/authors are consistent across indexes. It does **not** verify volume/page numbers or that a claim is faithful to the paper; those were written from the index records and are flagged below.

## Passed (kept)

| Reference | DOI | Gate | Indexes matched | Index title / venue / year | Used in |
|---|---|---|---|---|---|
| Nathan & McMahon (1990) | 10.1029/WR026i007p01465 | PASS | 3 (crossref, openalex, semantic_scholar) | Evaluation of automated techniques for base flow and recession analyses / Water Resources Research / 1990 | baseflow-separation, reading-a-hydrograph |
| Ladson et al. (2013) | 10.7158/13241583.2013.11465417 | PASS | 3 (crossref, openalex, semantic_scholar) | A Standard Approach to Baseflow Separation Using The Lyne and Hollick Filter / Australasian Journal of Water Resources / 2013 | baseflow-separation, reading-a-hydrograph, capstone-basin-story |
| Eckhardt (2005) | 10.1002/hyp.5675 | PASS | 3 (crossref, openalex, semantic_scholar) | How to construct recursive digital filters for baseflow separation / Hydrological Processes / 2005 (Crossref issue year; OpenAlex lists 2004, online-first) | baseflow-separation, reading-a-hydrograph |
| Newman et al. (2015) | 10.5194/hess-19-209-2015 | PASS | 3 (crossref, openalex, semantic_scholar) | Development of a large-sample watershed-scale hydrometeorological data set for the contiguous USA: data set characteristics and assessment of regional variability in hydrologic model performance / Hydrology and earth system sciences / 2015 | real-streamflow-data, reading-a-hydrograph, capstone-basin-story |
| Addor et al. (2017) | 10.5194/hess-21-5293-2017 | PASS | 3 (crossref, openalex, semantic_scholar) | The CAMELS data set: catchment attributes and meteorology for large-sample studies / Hydrology and earth system sciences / 2017 | real-streamflow-data, reading-a-hydrograph, capstone-basin-story, dem-to-twi |
| Baker et al. (2004) | 10.1111/j.1752-1688.2004.tb01046.x | PASS | 3 (crossref, openalex, semantic_scholar) | A NEW FLASHINESS INDEX: CHARACTERISTICS AND APPLICATIONS TO MIDWESTERN RIVERS AND STREAMS1 / JAWRA Journal of the American Water Resources Association / 2004 | capstone-basin-story |
| Beven & Kirkby (1979) | 10.1080/02626667909491834 | PASS | 2 (crossref, openalex) | A physically based, variable contributing area model of basin hydrology / Un modèle à base physique de zone d'appel variable de l'hydrologie du bassin versant / Hydrological Sciences Bulletin / 1979 | dem-to-twi, capstone-basin-story |
| Quinn et al. (1991) | 10.1002/hyp.3360050106 | PASS | 3 (crossref, openalex, semantic_scholar) | The prediction of hillslope flow paths for distributed hydrological modelling using digital terrain models / Hydrological Processes / 1991 | dem-to-twi |
| Sørensen et al. (2006) | 10.5194/hess-10-101-2006 | PASS | 3 (crossref, openalex, semantic_scholar) | On the calculation of the topographic wetness index: evaluation of different methods based on field observations / Hydrology and earth system sciences / 2006 | dem-to-twi |
| Tarboton (1997) | 10.1029/96WR03137 | PASS | 3 (crossref, openalex, semantic_scholar) | A new method for the determination of flow directions and upslope areas in grid digital elevation models / Water Resources Research / 1997 | dem-to-twi |
| O'Callaghan & Mark (1984) | 10.1016/S0734-189X(84)80011-0 | PASS | 3 (crossref, openalex, semantic_scholar) | The extraction of drainage networks from digital elevation data / Computer Vision Graphics and Image Processing / 1984 | watershed-runoff, dem-to-twi |
| Barnes et al. (2014) | 10.1016/j.cageo.2013.04.024 | PASS | 3 (crossref, openalex, semantic_scholar) | Priority-flood: An optimal depression-filling and watershed-labeling algorithm for digital elevation models / Computers & Geosciences / 2013 | watershed-runoff, dem-to-twi, capstone-basin-story |
| Cunnane (1978) | 10.1016/0022-1694(78)90017-3 | PASS | 3 (crossref, openalex, semantic_scholar) | Unbiased plotting positions — A review / Journal of Hydrology / 1978 | real-streamflow-data |
| Trenberth et al. (2007) | 10.1175/JHM600.1 | PASS | 3 (crossref, openalex, semantic_scholar) | Estimates of the Global Water Budget and Its Annual Cycle Using Observational and Model Data / Journal of Hydrometeorology / 2007 | water-cycle-in-motion |

## Wave 3 lessons (2026-11-17)

One table per lesson (same columns as the table above, so the repository scan `test_every_doi_in_the_modules_passed_the_gate` reads all of them). Each row is a DOI that passes `verify_citation.py --doi <DOI>`; a DOI that fails is removed from the page together with its claim.

### precipitation-point-to-basin

| Reference | DOI | Gate | Indexes matched | Index title / venue / year | Used in |
|---|---|---|---|---|---|
| Thiessen (1911) | 10.1175/1520-0493(1911)39<1082b:PAFLA>2.0.CO;2 | PASS | 3 (crossref, openalex, semantic_scholar) | PRECIPITATION AVERAGES FOR LARGE AREAS / Monthly Weather Review / 1911 | precipitation-point-to-basin |
| Shepard (1968) | 10.1145/800186.810616 | PASS | 3 (crossref, openalex, semantic_scholar) | A two-dimensional interpolation function for irregularly-spaced data / Proceedings of the 1968 23rd ACM national conference (OpenAlex: ACM National Meeting) / 1968 | precipitation-point-to-basin |
| Thornton et al. (1997) | 10.1016/S0022-1694(96)03128-9 | PASS | 3 (crossref, openalex, semantic_scholar) | Generating surfaces of daily meteorological variables over large regions of complex terrain / Journal of Hydrology / 1997 | precipitation-point-to-basin |
| Jennings et al. (2018) | 10.1038/s41467-018-03629-7 | PASS | 3 (crossref, openalex, semantic_scholar) | Spatial variation of the rain–snow temperature threshold across the Northern Hemisphere / Nature Communications / 2018 | precipitation-point-to-basin |

### evapotranspiration-budyko

| Reference | DOI | Gate | Indexes matched | Index title / venue / year | Used in |
|---|---|---|---|---|---|
| Priestley & Taylor (1972) | 10.1175/1520-0493(1972)100<0081:OTAOSH>2.3.CO;2 | PASS | 3 (crossref, openalex, semantic_scholar) | On the Assessment of Surface Heat Flux and Evaporation Using Large-Scale Parameters / Monthly Weather Review / 1972 | evapotranspiration-budyko |
| Hargreaves & Samani (1985) | 10.13031/2013.26773 | PASS | 3 (crossref, openalex, semantic_scholar) | Reference Crop Evapotranspiration from Temperature / Applied Engineering in Agriculture / 1985 | evapotranspiration-budyko |
| Zhang et al. (2004) | 10.1029/2003WR002710 | PASS | 3 (crossref, openalex, semantic_scholar) | A rational function approach for estimating mean annual evapotranspiration / Water Resources Research / 2004 | evapotranspiration-budyko |
| Zhang, Dawes & Walker (2001) | 10.1029/2000WR900325 | PASS | 3 (crossref, openalex, semantic_scholar) | Response of mean annual evapotranspiration to vegetation changes at catchment scale / Water Resources Research / 2001 | evapotranspiration-budyko |
| Thornton, Running & White (1997) | 10.1016/S0022-1694(96)03128-9 | PASS | 3 (crossref, openalex, semantic_scholar) | Generating surfaces of daily meteorological variables over large regions of complex terrain / Journal of Hydrology / 1997 | evapotranspiration-budyko |

Newman et al. (2015) and Addor et al. (2017) are cited by the lesson as data credits; both already pass (see the table above; their "Used in" cells are not edited here). Gate run for this lesson on 2026-11-17: `verify_citation.py --doi <DOI>` for each of the five rows plus Newman and Addor, all `gate_pass: true`.

Notes for human review (evapotranspiration-budyko):

- The gate confirms existence and DOI/title/year/author consistency only. Volume and page numbers are not given in the lesson's reference list for these five works for that reason.
- Priestley & Taylor (1972): the DOI contains `<` and `>`. The page shows it as written (`&lt;`/`&gt;` markup) and links it with `<`/`>` percent-encoded; the repository scan normalises HTML entities and percent-encoding and matches the whole DOI. Attribution wording: α = 1.26 is described as "the value associated with Priestley & Taylor (1972) for a wet surface"; written from the index record, not from the full text.
- Zhang et al. (2004): used for "the Fu form of the Budyko curve with the parameter written ω". Web records say Fu's model is the starting point of that paper; the full text was not read. Fu (1981) itself is deliberately not cited.
- Zhang, Dawes & Walker (2001): title-level claim only (mean annual evapotranspiration responds to vegetation).
- Thornton et al. (1997): cited only as the Daymet reference.
- CAMELS `pet_mean`: described as Priestley–Taylor with α "calibrated for each catchment", the wording of the CAMELS attributes table (camels_attributes_v2.0.pdf, "estimated by N15 using Priestley-Taylor formulation calibrated for each catchment"), next to the Addor et al. (2017) citation.

Books and handbooks without a DOI used by this lesson (marked on the page "Reference without DOI — pending owner decision"; not index-verifiable; owner to decide whether they stay):

| Reference | Used for |
|---|---|
| Allen, R. G., Pereira, L. S., Raes, D. & Smith, M. (1998). *Crop evapotranspiration: guidelines for computing crop water requirements.* FAO Irrigation and Drainage Paper 56. FAO, Rome | Ra geometry, net-radiation, Δ and γ expressions (written from the handbook's standard formulas) |
| Budyko, M. I. (1974). *Climate and Life.* Academic Press, New York | the two limits and the idea of Budyko space |

### runoff-generation

| Reference | DOI | Gate | Indexes matched | Index title / venue / year | Used in |
|---|---|---|---|---|---|
| Horton (1933) | 10.1029/TR014i001p00446 | PASS | 3 (crossref, openalex, semantic_scholar) | The Rôle of infiltration in the hydrologic cycle / Transactions American Geophysical Union / 1933 | runoff-generation |
| Dunne & Black (1970) | 10.1029/WR006i005p01296 | PASS | 3 (crossref, openalex, semantic_scholar) | Partial Area Contributions to Storm Runoff in a Small New England Watershed / Water Resources Research / 1970 | runoff-generation |
| Green & Ampt (1911) | 10.1017/S0021859600001441 | PASS | 3 (crossref, openalex, semantic_scholar) | Studies on Soil Phyics. (index spelling of the title) / The Journal of Agricultural Science / 1911 | runoff-generation |
| Mein & Larson (1973) | 10.1029/WR009i002p00384 | PASS | 3 (crossref, openalex, semantic_scholar) | Modeling infiltration during a steady rain / Water Resources Research / 1973 | runoff-generation |
| Merz, Blöschl & Parajka (2006) | 10.1016/j.jhydrol.2006.06.008 | PASS | 3 (crossref, openalex, semantic_scholar) | Spatio-temporal variability of event runoff coefficients / Journal of Hydrology / 2006 | runoff-generation |
| Blume, Zehe & Bronstert (2007) | 10.1623/hysj.52.5.843 | PASS | 3 (crossref, openalex, semantic_scholar) | Rainfall—runoff response, event-based runoff coefficients and hydrograph separation / Hydrological Sciences Journal / 2007 | runoff-generation |
| Cosby et al. (1984) | 10.1029/WR020i006p00682 | PASS | 3 (crossref, openalex, semantic_scholar) | A Statistical Exploration of the Relationships of Soil Moisture Characteristics to the Physical Properties of Soils / Water Resources Research / 1984 | runoff-generation |
| Thornton, Running & White (1997) | 10.1016/S0022-1694(96)03128-9 | PASS | 3 (crossref, openalex, semantic_scholar) | Generating surfaces of daily meteorological variables over large regions of complex terrain / Journal of Hydrology / 1997 | runoff-generation |

runoff-generation notes (gate run 2026-11-17, `verify_citation.py --doi <DOI>`; Newman et al. 2015, Addor et al. 2017, Beven & Kirkby 1979, Nathan & McMahon 1990 and Ladson et al. 2013 are in the main table above):

- **Rejected DOI.** The plan listed `10.1016/j.jhydrol.2006.03.006` for Merz et al. (2006). The gate passes that DOI (3 indexes) but it resolves to a different paper, Arp et al., *Surface-water hydrodynamics and regimes of a small mountain stream–lake ecosystem* (J. Hydrol. 2006). It is not cited anywhere. The title search for *Spatio-temporal variability of event runoff coefficients* (Merz) returned `10.1016/j.jhydrol.2006.06.008`, which passes with 3 indexes and matching authors, and is the DOI used.
- **Claims are kept to what the titles support:** Horton (infiltration in the hydrologic cycle; the infiltration-excess attribution), Dunne & Black (partial-area contributions to storm runoff; the saturation-excess attribution), Green & Ampt and Mein & Larson (infiltration models; the Mein & Larson ponding-time formula for a steady rain), Merz et al. and Blume et al. (event runoff coefficients), Cosby et al. (named only as one of the sources the CAMELS attribute documentation lists for soil_conductivity; read from `camels_attributes_v2.0.pdf`), Thornton et al. (credit for the Daymet forcing). No result from these papers is quoted.
- **Flagged for human review:** volume, issue and page numbers in the lesson's reference list were written from index records and memory; the gate does not check them (the start pages of the AGU papers agree with their DOI suffixes).

### watershed-runoff (real-basin scene, 2026-11-17)

| Reference | DOI | Gate | Indexes matched | Index title / venue / year | Used in |
|---|---|---|---|---|---|
| European Space Agency & Airbus (2022) | 10.5270/ESA-c5d3d65 | PASS | 2 (crossref, openalex) | Copernicus DEM (dataset; OpenAlex lists no venue, Crossref lists "Copernicus DEM") / 2022 | watershed-runoff |

Command: `verify_citation.py --doi 10.5270/ESA-c5d3d65` (2026-11-17; Semantic Scholar did not match, `doi_agreement` true). The entry is a dataset, so the gate shows existence and DOI/title/year/authors only. Credit line and licence wording on the page are those of the DEM's own manifest (`citation` and `license` fields of the AI-Hydro data record): "Copernicus DEM License (open use with attribution)". The licence text itself (https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/DEM/resources/license/License-COPDEM-30.pdf) requires, for adapted data, the Article 6(b) notice "produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved" and states the Article 6(c) disclaimer "The organisations in charge of the Copernicus programme by law or by delegation do not incur any liability for any use of the Copernicus WorldDEM-30"; both are in the lesson's References entry, with the licence's title ("Licence for the use of the Copernicus WorldDEM-30") and link. Resolved (was: owner to confirm).

### Wave 3 references without a DOI: owner decision pending

Each is shown on its page in a block marked "Reference without DOI — pending owner decision" (the same treatment as NEH-4 above). None of them can be gate-verified; the owner decides whether they stay.

| Reference | Lesson | Used for |
|---|---|---|
| USDA-SCS (1972), *National Engineering Handbook, Section 4: Hydrology* (NEH-4) | watershed-runoff (existing) | curve-number definitions |
| Allen, R. G., Pereira, L. S., Raes, D. & Smith, M. (1998), FAO Irrigation and Drainage Paper 56 | evapotranspiration-budyko | extraterrestrial radiation, net radiation, Δ and γ expressions |
| Budyko, M. I. (1974), *Climate and Life*, Academic Press | evapotranspiration-budyko | the two limits and the idea of Budyko space |

## Failed the gate (removed, together with the claims that depended on them)

| Reference | Gate result | Action |
|---|---|---|
| Lyne & Hollick (1979), *Stochastic time-variable rainfall-runoff modelling*, Inst. Eng. Australia Nat. Conf. Publ. 79/10 | FAIL: 1 index, and it returned an unrelated 2012 book chapter (DOI 10.1002/9781119951001.ch3) | Reference removed. The filter is still *named* the Lyne–Hollick filter and is described through Nathan & McMahon (1990), Ladson et al. (2013) and Eckhardt (2005), which pass. Manifest citation now Ladson et al. (2013). |
| Jenson & Domingue (1988), *Extracting topographic structure from digital elevation data for geographic information system analysis*, PE&RS 54(11) | FAIL: 1 index (OpenAlex), no DOI | Removed. It had also been mis-attributed as the "original D8"; D8 is attributed to O'Callaghan & Mark (1984), which passes. |
| "Moore, C. et al. (2019) dataretrieval" (USGS software release, probably Hodson et al.) | FAIL: 0 indexes | Removed. The module now mentions the `dataretrieval` package only as an optional tool, without a citation. |
| Pettitt (1979), *A non-parametric approach to the change-point problem* | not run: the module never used it | Removed (unused). |
| Sørensen et al. (2006) claim "mean TWI varies by 1–2 units between 25 m and 200 m" | claim not verifiable offline | Claim removed; the paper is kept only for what its title says (comparison of TWI calculation methods against field observations). Resolution dependence is demonstrated by a computation in the module instead. |
| Trenberth et al. (2007) magnitudes (land precipitation about 720 mm/yr, ocean about 1030 mm/yr) | paper passes, but its table could not be read offline | All global magnitudes removed from the module; the paper is cited only as the place to find them. |

## Books and handbooks without a DOI (kept; not index-verifiable)

| Reference | Treatment |
|---|---|
| Dingman, S. L. (2015). *Physical Hydrology*, 3rd ed., Waveland Press | Book, no DOI. Cited identically (3rd ed., 2015, marked as a book) in every module. **No chapter numbers are quoted**: the old modules disagreed (chapters 2, 3 and 6) and the correct chapters could not be verified offline. |
| USDA-SCS (1972). *National Engineering Handbook, Section 4: Hydrology* | Government handbook, no DOI, not in the indexes. Kept as the source of the curve-number definitions (S = 25400/CN − 254 mm, Ia = 0.2 S). Marked as a handbook; flagged for the owner because it is not gate-verifiable. |

## Flagged for human review (not machine-checkable)

- Volume, issue and page numbers in the reference lists were copied from the earlier module text or written from index records; the gate does not check them. Ladson et al. (2013) is cited as *Australasian Journal of Water Resources*, 17(1) with its DOI and no page range.
- Attribution wording was softened after review because only abstracts and index records were available: alpha = 0.925 is described as "commonly used for daily data (e.g. Nathan & McMahon 1990)"; Ladson et al. (2013) "propose a standardised procedure including reflection of the series" (the three-pass and 30-step details are not attributed to them); CAMELS is mentioned only as citing Ladson et al. (2013) for its baseflow index (camels_attributes_v2.0.pdf, camels_hydro table). Cunnane 1978 (Weibull plotting position) and Baker et al. 2004 (Richards–Baker index) match standard usage but were not re-read against the full text.
- Eckhardt (2005): the DOI record (Crossref) gives 2005 for the issue; OpenAlex's 2004 is the online-first date. All modules use 2005.
