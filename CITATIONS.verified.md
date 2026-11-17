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

## Wave 3 lessons (in progress)

Each packet adds one row per DOI that passes `verify_citation.py --doi <DOI>`; a DOI that fails is removed from the page together with its claim. The placeholder row is deleted when the first real row is added. Rows live only in the packet's own table.

### precipitation-point-to-basin

| Reference | DOI | Gate | Indexes matched | Index title / venue / year | Used in |
|---|---|---|---|---|---|
| _pending (P1)_ | _none yet_ | _not run_ | 0 | _placeholder_ | precipitation-point-to-basin |

### evapotranspiration-budyko

| Reference | DOI | Gate | Indexes matched | Index title / venue / year | Used in |
|---|---|---|---|---|---|
| _pending (P2)_ | _none yet_ | _not run_ | 0 | _placeholder_ | evapotranspiration-budyko |

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
