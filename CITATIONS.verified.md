# Citation gate results

Gate: `cite-verify` (OpenAlex + Crossref + Semantic Scholar), run 2026-11-17 for every reference that appears in a module. A citation stays only if the gate passes (two or more indexes resolve to the same DOI) or, for books/handbooks with no DOI, it is marked as such.

Command per entry: `python verify_citation.py --doi <DOI>` (title search was used first for discovery, then the DOI re-verified).

The gate confirms that a work exists and the DOI/title/year/authors are consistent across indexes. It does **not** verify volume/page numbers or that a claim is faithful to the paper; those were written from the index records and are flagged below.

## Passed (kept)

| Reference | DOI | Gate | Indexes matched | Index title / venue / year | Used in |
|---|---|---|---|---|---|
| Nathan & McMahon (1990) | 10.1029/WR026i007p01465 | PASS | 3 (crossref, openalex, semantic_scholar) | Evaluation of automated techniques for base flow and recession analyses / Water Resources Research / 1990 | baseflow-separation, reading-a-hydrograph |
| Ladson et al. (2013) | 10.7158/13241583.2013.11465417 | PASS | 3 (crossref, openalex, semantic_scholar) | A Standard Approach to Baseflow Separation Using The Lyne and Hollick Filter / Australasian Journal of Water Resources / 2013 | baseflow-separation, reading-a-hydrograph, capstone-basin-story |
| Eckhardt (2005) | 10.1002/hyp.5675 | PASS | 3 (crossref, openalex, semantic_scholar) | How to construct recursive digital filters for baseflow separation / Hydrological Processes / 2004 | baseflow-separation, reading-a-hydrograph |
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
- Claims attributed to papers (Nathan & McMahon 1990 recommending alpha = 0.925 for daily data; Ladson et al. 2013 standardising three passes with 30-step reflection, the convention CAMELS also cites; Cunnane 1978 covering the Weibull plotting position; Baker et al. 2004 defining the Richards–Baker index) match standard usage but were not re-read against the full text.
