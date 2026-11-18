# County to metro and state: which source

Question: which source should map every US county to its metro (CBSA) and state, so
`dim_geo_county` (county -> metro -> state) can carry `metro_name`, `state_code` and
`state_name`? This replaces the HUD ZIP-CBSA crosswalk as the metro source. Main
candidate: the OMB / Census Bureau CBSA delineation file ("List 1").

Checked on 2026-11-18 against census.gov, www2.census.gov file listings, the OMB 2020
standards (Federal Register) and files downloaded to a scratch folder **outside** the
repo (nothing added to `raw_data/` or committed). Figures marked "counted" come from
those files. Two cross-checks (marked "local") read our own git-ignored files in
`raw_data/`.

## 1. Delineation vintage and cadence

- **Latest: July 2023, OMB Bulletin 23-01.** The delineation page links only
  `list1_2023.xlsx` and `list2_2023.xlsx`; the page was last revised August 4, 2023.
  The www2 folder listing has vintages from 1950 to `2023/`, nothing newer.
  [Delineation files][delin], [folder listing][delin-dir]
- The file's own footer: "based on OMB, July 2023 delineations" with a link to
  `OMB-Bulletin-23-01.pdf`. (counted)
- Census says the current delineations apply the 2020 standards and were "effective
  July 2023". [About metro/micro][about]
- A web search found no OMB bulletin replacing 23-01. [search: BLS 2025 note][bls-2025]
  Treat "no newer bulletin" as **checked on the Census page only**, not on OMB's site.
- **Cadence (2020 standards):** OMB delineates after each decennial census (2023 from
  2020 Census data), may issue **annual updates** ("one per year in those years when
  there is an update", mainly new areas qualifying), and reviews all areas in **2028**
  (mid-decade, ACS-based). Other aspects do not change between censuses.
  [2020 standards, §10][std]

## 2. List 1 file layout (counted)

URL: `https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2023/delineation-files/list1_2023.xlsx`
(144 KB, one sheet `List 1`, 1,921 rows in Excel).

| Excel rows | Content | Action |
|---|---|---|
| 1 | Accessibility note ("Table with row headers in column A...") | skip |
| 2 | Title "List 1. CORE BASED STATISTICAL AREAS ... JULY 2023" | skip |
| 3 | Header | use |
| 4 - 1918 | **1,915 data rows**, one per county | use |
| 1919 | blank | skip |
| 1920 - 1921 | "Note: ..." (2020 standards link) and "Source: ..." (Bulletin 23-01) | skip |

Columns (header row 3, all cells are **text**, so leading zeros are kept):

| Column | Example | Notes |
|---|---|---|
| `CBSA Code` | `10100` | 5 digits; 935 distinct |
| `Metropolitan Division Code` | blank | 37 divisions in 13 large metros; blank otherwise |
| `CSA Code` | `198` | 3 digits; 185 distinct; blank when not in a CSA |
| `CBSA Title` | `Aberdeen, SD` | one title per code |
| `Metropolitan/Micropolitan Statistical Area` | `Micropolitan Statistical Area` | 2 values |
| `Metropolitan Division Title` | blank | |
| `CSA Title` | `Columbus-Marion-Zanesville, OH` | |
| `County/County Equivalent` | `Brown County` | UTF-8, e.g. `Añasco Municipio` |
| `State Name` | `South Dakota` | full name only, **no 2-letter code** |
| `FIPS State Code` | `46` | 2 digits, separate column |
| `FIPS County Code` | `013` | 3 digits, separate column |
| `Central/Outlying County` | `Central` | 1,325 Central, 590 Outlying |

- Key: `FIPS State Code || FIPS County Code` is 5 chars and **unique** (1,915 distinct,
  no duplicates). So List 1 has one row per county; it is already county grain.
- Coverage: **metro and micro** areas (393 metro CBSAs / 1,252 counties, 542 micro
  CBSAs / 663 counties), metropolitan divisions, CSAs and the central/outlying flag.
  52 "states": 50 + DC + Puerto Rico.
- List 2 (`list2_2023.xlsx`) is principal cities by place code; not needed here.
- Central/outlying meaning: central = contains a substantial part of an urban area;
  outlying = joined by commuting ties. [2020 standards, §11][std]

## 3. Counties not in any CBSA

List 1 lists only counties **inside** a CBSA. For the full county list use the
**2026 Census Gazetteer counties file** (already chosen for centre points in
[map-geography.md](map-geography.md)).

| File | Rows (counted) | Delimiter | Columns relevant here | Connecticut |
|---|---|---|---|---|
| `2026_Gaz_counties_national.txt` [gaz] | 3,222 (50 + DC + PR) | `\|` | `USPS` (2-letter), `GEOID` (5-char), `NAME` | 9 planning regions `09110`-`09190` |
| `codes2020/national_county2020.txt` [codes] | 3,235 (adds AS, GU, MP, UM, VI) | `\|` | `STATE` (2-letter), `STATEFP`, `COUNTYFP`, `COUNTYNAME`, `CLASSFP`, `FUNCSTAT` | old 8 counties `09001`-`09015` |

- Join List 1 to the Gazetteer on the 5-char code: **all 1,915 List 1 counties match**,
  and **all county names are identical**. **1,307** Gazetteer counties are in no CBSA
  (most in TX 121, KS 70, NE 64). (counted)
- Neither county file has a state **name**; both have the 2-letter code.
- `national_county2020.txt` is the 2020 vintage (ANSI page last revised May 1, 2023)
  and still has the pre-2022 Connecticut counties, so it **does not join** to List 1
  for CT. [ANSI code lists][ansi] Do not use it as the county list.

## 4. State codes and names

| File | Rows (counted) | Columns | Territories |
|---|---|---|---|
| `codes2020/national_state2020.txt` [codes] | 57 | `STATE` (2-letter), `STATEFP`, `STATENS`, `STATE_NAME` | AS 60, GU 66, MP 69, PR 72, UM 74, VI 78 |
| `2026_Gaz_state_national.txt` [gaz] | 52 | `USPS`, `GEOID` (2-digit), `NAME`, areas, lat/long | PR only |

- Recommended: `national_state2020.txt`. State FIPS codes and names do not change with
  vintage, it covers all territories, and it gives FIPS -> 2-letter -> name in one row.
  Note its names are formal: `Commonwealth of the Northern Mariana Islands`,
  `United States Virgin Islands`. (counted)
- Territories matter only for HUD rows such as American Samoa's state-only `60`
  ([hud-state-only-geoids.md](hud-state-only-geoids.md)); no CBSA exists outside the
  50 states, DC and PR. [2020 standards, §E][std]

## 5. Connecticut and Puerto Rico

- **Connecticut:** the Census Bureau replaced the 8 counties with **9 planning regions**
  (`09110`-`09190`) as county-equivalents for data from 2022 on; OMB delineations are
  affected. [Federal Register 2022-12063][ct-fr], [Census CT note][ct-pdf]
  - List 1 2023: planning regions (9 rows, e.g. `09120` Greater Bridgeport Planning
    Region -> Bridgeport-Stamford-Danbury, CT). (counted)
  - Gazetteer 2026: planning regions. (counted)
  - `national_county2020.txt`: old 8 counties. (counted)
  - HUD ZIP-county 2026 Q2: planning regions `09110`-`09190`. (local)
  - Zillow ZHVI: `CountyName` still uses the **old 8 county names** (Hartford County,
    Fairfield County, ...). (local) Not a join problem as long as the ZIP -> county
    link comes from HUD, but Zillow's county name must not be used as a key.
- **Puerto Rico:** 78 municipios are county-equivalents in the Gazetteer; 71 are in a
  CBSA in List 1 (names end in `Municipio`). (counted)
- **Zillow's own `Metro` column** uses older titles, e.g. `Bridgeport-Stamford-Norwalk, CT`
  where 2023 says `Bridgeport-Stamford-Danbury, CT`. (local) Another reason to take
  `metro_name` from List 1 rather than from `stg_zillow_zhvi_zip.metro_name`.

## 6. Licence

- US federal government works are not copyrightable: "Copyright protection under this
  title is not available for any work of the United States Government". [17 USC 105][usc105]
- Census asks users to "cite the Census Bureau as the source of the original data" and
  to use a suggested citation where one is given. [Census citation policy][cite]
  Neither Census page states "public domain" in those words; the public-domain status
  rests on 17 USC 105. OMB's delineations are equally a federal work.
- Suggested source note: "U.S. Census Bureau, Population Division, List 1 (July 2023),
  based on OMB Bulletin 23-01; U.S. Census Bureau, 2026 Gazetteer Files; ANSI/FIPS code
  lists (2020)."

## 7. `metro_name` and multi-state metros

- `metro_name` = `CBSA Title` (one title per code, counted). Also keep `cbsa_code` and
  `metro_type` (metro/micro), since 542 of 935 CBSAs are micro areas.
- **59 CBSAs span more than one state** (counted), e.g. `35620` New York-Newark-Jersey
  City, NY-NJ (NY, NJ) and `47900` Washington-Arlington-Alexandria, DC-VA-MD-WV (4).
  The suffix in the title lists states but is not a key. So **state always comes from
  the county** (first two digits of the county FIPS), never from the metro.
- Consequence for the hierarchy: county -> metro and county -> state are both correct,
  but **metro -> state is not a tree**. A "metro inside state" roll-up must group by
  (metro, state) or pick one; do not add `state_code` to a metro dimension.

## Recommendation

Build `dim_geo_county` from three Census files, one bronze source each:

1. **Spine:** `2026_Gaz_counties_national.txt` -> `county_fips` (`GEOID`), `county_name`
   (`NAME`), `state_code` (`USPS`), plus lat/long. 3,222 rows, CT planning regions.
2. **Metro:** left join `list1_2023.xlsx` on `FIPS State Code || FIPS County Code` ->
   `cbsa_code`, `metro_name` (`CBSA Title`), `metro_type`, `is_central_county`,
   optionally CSA and metro division. 1,307 counties get null metro (show as
   "Not in a metro area" or leave null; decide in the model, not here).
3. **State:** join `national_state2020.txt` on `STATEFP` = left 2 of `county_fips` ->
   `state_fips` (2-digit), `state_code` (2-letter, check it equals the Gazetteer `USPS`),
   `state_name`.

Suggested tests: `county_fips` unique and 5 digits; every List 1 key exists in the
Gazetteer (relationship test); `state_code` from both files agrees.

Loading notes: List 1 is `.xlsx`, so the loader needs an xlsx reader (skip rows 1-2,
stop at the first blank row), or convert to CSV in `fetch`. Keep all values as text.

**Unverified / open:**

- Whether OMB published any update after Bulletin 23-01 (checked only via the Census
  page and a web search, not OMB's own site).
- The 2028 mid-decade review will change some delineations; the vintage should be a
  metadata field so a new List 1 can be swapped in.
- Zillow's old CT county names and older metro titles: the Zillow-to-HUD ZIP join is
  unaffected, but reports that show Zillow's names will disagree with this dimension.

## Sources

- Downloaded (scratch folder, not committed): `list1_2023.xlsx`, `list2_2023.xlsx`,
  `2026_Gaz_counties_national.txt`, `2026_Gaz_state_national.txt`,
  `national_county2020.txt`, `national_state2020.txt`.
- Local, git-ignored: `raw_data/hud_usps_zip_county_2026q2.csv`,
  `raw_data/Zip_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv`.
- [Census delineation files][delin]
- [Census delineation folder listing][delin-dir]
- [About metropolitan and micropolitan statistical areas (Census)][about]
- [2020 Standards for Delineating CBSAs, 86 FR (2021-07-16), govinfo][std]
- [Census Gazetteer files][gaz]
- [Census ANSI/FIPS code lists][ansi] and [codes2020 folder][codes]
- [Change to County-Equivalents in the State of Connecticut, Federal Register 2022-12063][ct-fr]
- [Final Changes to County Equivalents in Connecticut (Census PDF)][ct-pdf]
- [17 U.S.C. § 105 (Cornell LII)][usc105]
- [Census citation policy][cite]
- [BLS LAUS geography changes in 2025][bls-2025]

[delin]: https://www.census.gov/geographies/reference-files/time-series/demo/metro-micro/delineation-files.html
[delin-dir]: https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/
[about]: https://www.census.gov/programs-surveys/metro-micro/about.html
[std]: https://www.govinfo.gov/content/pkg/FR-2021-07-16/html/2021-15159.htm
[gaz]: https://www.census.gov/geographies/reference-files/time-series/geo/gazetteer-files.html
[ansi]: https://www.census.gov/library/reference/code-lists/ansi.html
[codes]: https://www2.census.gov/geo/docs/reference/codes2020/
[ct-fr]: https://www.federalregister.gov/documents/2022/06/06/2022-12063/change-to-county-equivalents-in-the-state-of-connecticut
[ct-pdf]: https://www2.census.gov/geo/pdfs/reference/ct_county_equiv_change.pdf
[usc105]: https://www.law.cornell.edu/uscode/text/17/105
[cite]: https://www.census.gov/about/policies/citation.html
[bls-2025]: https://www.bls.gov/lau/geography-and-data-changes-in-2025.htm
