# Map geography: centre points, boundary shapes and who can draw them

Question: to put home values on a map we need, per ZIP and per county, either a
**centre point** (lat/long) or a **boundary shape** (polygon). Where do these come from,
in what format and under what terms? Can Databricks Free Edition store and query them?
What can Streamlit and a BI tool draw, and what input does each need?

Checked on 2026-11-18 against census.gov, www2.census.gov file listings,
docs.databricks.com, docs.streamlit.io, plotly/pydeck docs and learn.microsoft.com.
Some counts below come from files downloaded to a scratch folder **outside** the repo
(nothing was added to `raw_data/` or committed). Those are marked "counted".

## 1. Centre points: Census Gazetteer files

- **Latest vintage: 2026.** The listing has `2012_Gazetteer/` to `2026_Gazetteer/`. The
  2026 county and ZCTA files are dated 2026-09-08. [Gazetteer page][gaz-page],
  [folder listing][gaz-2026]
- **Format:** "pipe-delimited text". National files come zipped. [Gazetteer page][gaz-page]
  Counted: plain ASCII, LF line endings, header row. Lat/long are signed decimal degrees
  with 6 decimals, e.g. `32.532237|-86.64644`. (The record-layout page does not state the
  unit or sign, so this is from the file only.)
- **Download URLs** (small):
  - Counties: `https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2026_Gazetteer/2026_Gaz_counties_national.zip` (136K zip). Counted: **3,222** rows.
  - ZCTAs: `https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2026_Gazetteer/2026_Gaz_zcta_national.zip` (930K zip). Counted: **33,791** rows.
  - Also `2026_Gaz_cbsa_national.zip` (44K) and `2026_Gaz_state_national.zip` (2.8K). [folder listing][gaz-2026]
- **Columns** ([record layouts][gaz-layout]):
  - Counties: `USPS` (state abbreviation), `GEOID` (state + county FIPS, 5 chars),
    `GEOIDFQ`, `ANSICODE`, `NAME`, `ALAND`, `AWATER` (square metres), `ALAND_SQMI`,
    `AWATER_SQMI`, `INTPTLAT`, `INTPTLONG`.
  - ZCTAs: `GEOID` ("2020 Census 5-digit ZCTA"), `GEOIDFQ`, `ALAND`, `AWATER`,
    `ALAND_SQMI`, `AWATER_SQMI`, `INTPTLAT`, `INTPTLONG`. No name and no state column.
- `INTPTLAT/INTPTLONG` is the "internal point", not a mathematical centroid. [record layouts][gaz-layout]
- Coverage: 50 states, DC and Puerto Rico; Island Areas excluded. [Gazetteer page][gaz-page]
- The ZCTA set is the **2020 Census** delineation. It will not change until the next
  census. [record layouts][gaz-layout]

### ZCTA is not the same as a USPS ZIP code

- ZIP codes are USPS delivery routes. Census holds them as address points, which are
  "unsuitable for mapping". ZCTAs are area approximations built from 2020 census blocks.
  [ZCTA page][zcta-page]
- Each block goes to one ZCTA, "usually to the ZCTA that reflects the most frequently
  occurring ZIP Code". The ZCTA code is that most common ZIP. "Users should not use ZCTAs
  to identify the official USPS ZIP Code." [TIGER/Line 2025 tech doc, §4.23][tl-doc]
- **Which ZIPs have no ZCTA:** "ZIP Codes that cover primarily nonresidential or post
  office box addresses may not have a corresponding ZCTA because the delineation process
  uses primarily residential addresses". [TIGER tech doc, §4.23][tl-doc] The ZCTA page
  adds "Not all valid ZIP Codes are represented by a 2020 ZCTA", but also says a ZCTA
  **may** represent a PO box-only ZIP or "a single institutional or corporate delivery
  point". So PO box and single-organisation ZIPs **often**, not always, lack a ZCTA.
  [ZCTA page][zcta-page]
- **Military (APO/FPO):** no Census page mentions them. Counted: no ZCTA, and no ZIP in
  our HUD crosswalk, starts with `09`, `340` or `962`–`966`. (That these are the military
  prefixes is from general knowledge, **unverified** against USPS.) So they do not affect us.
- **Rough counts (counted, our own files):**
  - HUD ZIP-county 2026 Q2: 39,484 distinct ZIPs. **5,767 (about 15%) have no 2020
    ZCTA** with the same code. 74 ZCTAs are not in HUD.
  - Zillow ZHVI ZIP file: 26,265 ZIPs. **Only 7 have no ZCTA**: 08739, 18934, 19481, 88032,
    95424, 95433, 98206. Zillow covers residential ZIPs, which is what ZCTAs are built from.
  - A matching code does **not** prove the same area; a ZCTA is only an approximation of
    the ZIP's area.

## 2. Boundary shapes: cartographic boundary files

- **Latest vintage: 2025** (`GENZ2025`). TIGER/Line, the full-detail product, has `TIGER2026`.
  [CB page][cb-page], [tiger listing][tiger-root]
- **Formats:** shapefile, ESRI file geodatabase, GeoPackage and KML (KML only for some
  layers). All come zipped. **No GeoJSON.** [CB description PDF][cb-desc], [CB page][cb-page]
- **Scales:** 1:500,000 (`500k`), 1:5,000,000 (`5m`), 1:20,000,000 (`20m`). "not all
  geographic area boundaries are available at all target scales". [CB description PDF][cb-desc]
- **Shapefile sizes, 2025** ([GENZ2025/shp][genz25-shp]; KML is a bit smaller, [GENZ2025/kml][genz25-kml]):

| Layer | 500k | 5m | 20m |
|---|---|---|---|
| County `cb_2025_us_county_*` | 11M | 2.8M | 886K |
| CBSA `cb_2025_us_cbsa_*` | 4.5M | 1.2M | 343K |
| State `cb_2025_us_state_*` | 3.1M | 1.1M | 181K |
| Nation `cb_2025_us_nation_*` | – | 417K | 86K |

- **ZCTA:** not in 2025. The 2025 page says to use the "2020" tab. [CB 2025 page][cb-2025]
  Only **one** scale exists: `cb_2020_us_zcta520_500k.zip`, 64M shapefile, 44M KML.
  [GENZ2020/shp][genz20-shp], [GENZ2020/kml][genz20-kml] The full TIGER/Line version
  `tl_2026_us_zcta520.zip` is 505M. [TIGER2026/ZCTA520][tl-zcta]
- **Intended use:** "specifically designed for small scale thematic mapping". Do not use
  for "area or perimeter calculation", "geocoding addresses" or "determining precise
  geographic area relationships". Shapes are clipped to the US outline, so some offshore
  areas are missing. [CB description PDF][cb-desc]
- **Coordinate system:** TIGER/Line is "GCS NAD83" (each shapefile has a `.prj`).
  [TIGER tech doc, §3.3.3][tl-doc] That the CB files use the same datum is **unverified**
  (likely, but not stated in the CB description). Maps below want WGS84 (SRID 4326); for
  small-scale maps the NAD83/WGS84 difference does not matter (my inference).
- CBSA shapes follow OMB delineations "as of July 2023" (stated for TIGER/Line 2025).
  [TIGER tech doc, §4.13][tl-doc]

## 3. Licence and terms

From the TIGER/Line 2025 technical documentation, chapter 1 ([tl-doc]):

- "Copyright protection is not available for any work of the United States Government
  (Title 17 U.S.C., Section 105). Thus, you are free to reproduce census materials as you
  see fit. We would ask, however, that you cite the Census Bureau as the source."
- Disclaimer: "No warranty, expressed or implied, is made with regard to the accuracy of
  the data ... The boundary information ... is for statistical data collection and
  tabulation purposes only ... not legal land descriptions."
- Repackaging: the Bureau "requests that any repackaging ... include a conspicuously
  placed statement to this effect". "TIGER/Line" is a registered trademark and must not be
  used in a product name.

The word "public domain" does not appear. The Gazetteer and cartographic boundary pages
have **no** separate licence text that I found; the "census materials" statement and
17 U.S.C. §105 apply to them too, but an explicit statement for those two products is
**unverified**. In practice: free to use and redistribute, cite "Source: U.S. Census
Bureau", and repeat the no-warranty note.

## 4. Databricks Free Edition: spatial SQL

- **ST functions and types exist.** "Support for GEOMETRY values is generally available.
  Support for GEOGRAPHY values is in Public Preview." Applies to Databricks Runtime 17.1+
  and Databricks SQL. [ST functions][dbx-st]
- Useful functions: `st_point(x, y [, srid])`, `st_geomfromwkt(wkt [, srid])`,
  `st_geomfromgeojson(json)` (returns SRID 4326), `st_geomfromwkb`, `st_asgeojson`.
  [ST functions][dbx-st]
- `GEOMETRY(srid)`: about 11,000 SRIDs supported. `GEOMETRY(ANY)` "cannot be persisted".
  `GEOGRAPHY` allows SRID 4326 only. Neither can be a **dimension** in a metric view; use it
  as a measure. [GEOMETRY type][dbx-geom], [GEOGRAPHY type][dbx-geog]
- **Serverless SQL warehouse / Free Edition:** the ST page does not mention either. The Free
  Edition limits page lists only serverless compute and "One SQL warehouse, limited to a
  2X-Small cluster size", and is silent on spatial. [Free Edition limits][dbx-free]
  Whether ST functions run on **our** warehouse is **unverified**; one query settles it:
  `select st_asgeojson(st_point(-86.64644, 32.532237, 4326))`.
- **H3:** "In Databricks Runtime 17.0 or above, H3 expressions are supported on all compute
  types except classic Databricks SQL warehouses". Our warehouse is serverless, so it should
  work, but that is read from the exclusion, not stated. [H3 functions][dbx-h3]
- **Reading shapefiles / GeoJSON directly: no.** `read_files` formats are avro, binaryFile,
  csv, file, json, orc, parquet, text, xml. [read_files][dbx-readfiles] Databricks' own spatial
  tutorial stores polygons as **WKT text** in JSON and converts with `ST_GeomFromWKT`.
  [spatial pipeline tutorial][dbx-tut]
- Whether dbt-databricks 1.13 handles `GEOMETRY` columns in models and contracts is
  **unverified**.
- **Fallback:** convert shapes to WKT or GeoJSON text **before** loading (in Python, in
  `hearth fetch`), store as `STRING` in bronze/silver, and cast with `st_geomfromwkt` /
  `st_geomfromgeojson` only in a view that needs it. Strings work everywhere and in every
  consumer below.

## 5. Consumers: what each can draw

**Streamlit**

- `st.map`: points only, "a scatterplot overlaid onto" a map. Needs `lat`/`lon` columns (or
  named via `latitude=`/`longitude=`); size in metres and colour can come from columns. It
  wraps `st.pydeck_chart`. Carto tiles by default, no key. [st.map][st-map]
- `st.pydeck_chart`: any pydeck layer; selection events with `on_select`. Advise "don't
  display more than eight Pydeck charts on a single page". [st.pydeck_chart][st-pydeck]
- pydeck `ScatterplotLayer` takes a DataFrame or list of dicts; `GeoJsonLayer` is shown
  with a GeoJSON URL, fill colour from a feature property, e.g.
  `get_fill_color="[255, 255, properties.growth * 255]"`. [pydeck Layer][pdk-layer],
  [GeoJsonLayer example][pdk-geojson]
- Plotly `px.choropleth_map`: `geojson` "Must contain a Polygon feature collection, with
  IDs", matched to `locations` via `featureidkey`. [px.choropleth_map][px-chmap] No token
  needed for Plotly styles; the old `*_mapbox` traces "were removed in Plotly.py 7".
  [Mapbox to MapLibre][px-maplibre]

**Power BI**

- **Shape map:** custom TopoJSON or GeoJSON file or URL. "plots up to a maximum of 1,500
  data points". [Shape map][pbi-shape] That is too few for 3,222 counties or ~26k ZIPs;
  fine for states and CBSAs (counted: 935 rows in `2026_Gaz_cbsa_national`, metro + micro).
- **Azure Maps visual, reference layer:** GeoJSON, WKT, KML, SHP or CSV with a WKT column;
  binds data to shapes by matching the Location field to a feature property. "renders only
  the first 30,000 features". Microsoft's own example maps Census ZCTAs after simplifying
  with mapshaper (keep 5% of points, 4-decimal coordinates). [Azure Maps reference layer][azm-ref]
  33,791 ZCTAs exceed 30,000, so filter (e.g. by state) or drop ZCTAs without data.
- **Filled map (Bing):** geocodes names/codes ("countries/regions, states, counties, cities,
  zip codes"), sends them to Bing; Bing Maps is "scheduled for deprecation", move to Azure
  Maps. [Filled map][pbi-filled]

**Databricks AI/BI dashboards**

- **Point map:** separate longitude/latitude columns or one geometry column
  (`Point`/`MultiPoint`). [Maps][dbx-maps]
- **Choropleth:** either built-in regions looked up by name/code (country, state, county,
  ZIP/postal, CSA/CBSA, legislative, NUTS), or **Custom geometry**: a `GEOMETRY`/`GEOGRAPHY`
  column with `Polygon`/`MultiPolygon`. Renderer is SRID 4326; SRID 0 is "not rendered";
  no `GeometryCollection`. [Maps][dbx-maps]
- Counted from Databricks' lookup CSVs: US counties are keyed by the 5-digit FIPS code
  (`country_specific_code`, 3,143 US rows) [county lookup][dbx-county]; the ZIP lookup has
  40,796 ZIPs and contains **all** 26,265 Zillow ZIPs [ZIP lookup][dbx-zip]; CBSA by
  `cbsa_code` [CBSA lookup][dbx-cbsa]. So a county or ZIP choropleth needs **no shapes of
  our own**. ZIP boundaries in choropleths were added in April 2026 (AI/BI release notes,
  read through search snippets only). [AI/BI release notes 2026][dbx-aibi-rn]
- Whether AI/BI dashboards and these maps are available in Free Edition is **unverified**
  (not listed as unsupported on the limits page).

## Implications for the model

Design rule: no column may appear in more than one dimension. Points go on `dim_geo_zip`
and `dim_geo_county`; shapes go in separate tables keyed the same way.

- **Points:** give each dimension its own named columns, e.g. `zip_latitude`,
  `zip_longitude` on `dim_geo_zip` and `county_latitude`, `county_longitude` on
  `dim_geo_county`. Never repeat county lat/long on the ZIP dimension. Use
  `decimal(9,6)`: it holds the 6 decimals in the source exactly.
- **ZIP vs ZCTA key mismatch:** `dim_geo_zip` is keyed by USPS ZIP (from HUD). The
  Gazetteer is keyed by ZCTA. Join `zip_code = zcta_geoid` as a **left** join:
  - about 15% of HUD ZIPs (5,767) get no point; only 7 Zillow ZIPs do;
  - ZCTAs with no HUD ZIP (74) simply drop out;
  - add a flag on `dim_geo_zip` only, e.g. `has_zcta`, so a map can say "no shape/point
    for this ZIP" instead of silently dropping it;
  - document that the point is the ZCTA's internal point, an approximation of the ZIP.
- **Do not fill missing ZIP points with the county point.** It would put many ZIPs on one
  spot and blur the "every number is verifiable" rule. Leave null.
- **Shape tables:** `geo_zip_shape` keyed by `zip_code` (rows only where a ZCTA exists),
  `geo_county_shape` by `county_fips`, plus `geo_cbsa_shape` and `geo_state_shape` if
  wanted. One `geometry_geojson STRING` (or WKT) column each, plus `shape_source` and
  `shape_vintage`. They are 1:1 extensions of the dimension, not dimensions with
  attributes, so no column is repeated.
- **Vintage drift:** ZCTAs are 2020, counties 2025/2026, HUD 2026 Q2. A county code
  change can leave a HUD county with no point or shape. A dbt `relationships` test with
  severity `warn` would show it.

## Recommendation

*(Recommendation, not a verified fact.)*

1. **Start with points only.** Land `2026_Gaz_counties_national` and
   `2026_Gaz_zcta_national` in bronze as-is (small, pipe-delimited; the loader must accept
   `|`). Add lat/long to `dim_geo_county` and `dim_geo_zip` with `has_zcta`. That already
   drives `st.map`, pydeck scatter, Databricks point maps and Power BI lat/long maps.
2. **For filled maps, use built-in regions first.** Databricks AI/BI choropleths accept
   county FIPS and ZIP codes directly; no shapes needed.
3. **Shapes later, as strings.** If Streamlit/Plotly or Power BI Azure Maps need polygons,
   fetch `cb_2025_us_county_5m` (or `20m`), `cb_2025_us_state_20m`, `cb_2025_us_cbsa_5m`
   and `cb_2020_us_zcta520_500k`. Convert to simplified GeoJSON in Python, filter ZCTAs to
   ZIPs we have, store as `STRING`. Use native `GEOMETRY` only after one test query proves
   ST functions run on the Free Edition warehouse.
4. **Licence:** add the Census source line and no-warranty note to the source metadata
   (provenance fields). Keep the project rule of not committing data files, even though
   Census data is free to redistribute.

## Sources

- gaz-page: <https://www.census.gov/geographies/reference-files/time-series/geo/gazetteer-files.html>
- gaz-2026: <https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2026_Gazetteer/>
- gaz-layout: <https://www.census.gov/programs-surveys/geography/technical-documentation/records-layout/gaz-record-layouts.html>
- zcta-page: <https://www.census.gov/programs-surveys/geography/guidance/geo-areas/zctas.html>
- tl-doc: <https://www2.census.gov/geo/pdfs/maps-data/data/tiger/tgrshp2025/TGRSHP2025_TechDoc.pdf>
- cb-page: <https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.html>
- cb-2025: <https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.2025.html>
- cb-desc: <https://www2.census.gov/geo/tiger/GENZ2025/description.pdf>
- tiger-root: <https://www2.census.gov/geo/tiger/>
- genz25-shp: <https://www2.census.gov/geo/tiger/GENZ2025/shp/>
- genz25-kml: <https://www2.census.gov/geo/tiger/GENZ2025/kml/>
- genz20-shp: <https://www2.census.gov/geo/tiger/GENZ2020/shp/>
- genz20-kml: <https://www2.census.gov/geo/tiger/GENZ2020/kml/>
- tl-zcta: <https://www2.census.gov/geo/tiger/TIGER2026/ZCTA520/>
- dbx-st: <https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-st-geospatial-functions>
- dbx-geom: <https://docs.databricks.com/aws/en/sql/language-manual/data-types/geometry-type>
- dbx-geog: <https://docs.databricks.com/aws/en/sql/language-manual/data-types/geography-type>
- dbx-h3: <https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-h3-geospatial-functions>
- dbx-free: <https://docs.databricks.com/aws/en/getting-started/free-edition-limitations>
- dbx-readfiles: <https://docs.databricks.com/aws/en/sql/language-manual/functions/read_files>
- dbx-tut: <https://docs.databricks.com/aws/en/ldp/tutorial-spatial-pipelines>
- dbx-maps: <https://docs.databricks.com/aws/en/dashboards/manage/visualizations/maps>
- dbx-county: <https://assets.docs.databricks.com/_extras/documents/county-district-names.csv>
- dbx-zip: <https://assets.docs.databricks.com/_extras/documents/zipcode-codes.csv>
- dbx-cbsa: <https://assets.docs.databricks.com/_extras/documents/us-cbsa-codes.csv>
- dbx-aibi-rn: <https://docs.databricks.com/aws/en/ai-bi/release-notes/2026>
- st-map: <https://docs.streamlit.io/develop/api-reference/charts/st.map>
- st-pydeck: <https://docs.streamlit.io/develop/api-reference/charts/st.pydeck_chart>
- pdk-layer: <https://deckgl.readthedocs.io/en/latest/layer.html>
- pdk-geojson: <https://deckgl.readthedocs.io/en/latest/gallery/geojson_layer.html>
- px-chmap: <https://plotly.com/python-api-reference/generated/plotly.express.choropleth_map.html>
- px-maplibre: <https://plotly.com/python/mapbox-to-maplibre/>
- pbi-shape: <https://learn.microsoft.com/en-us/power-bi/visuals/desktop-shape-map>
- pbi-filled: <https://learn.microsoft.com/en-us/power-bi/visuals/power-bi-visualization-filled-maps-choropleths>
- azm-ref: <https://learn.microsoft.com/en-us/azure/azure-maps/power-bi-visual-add-reference-layer>

[gaz-page]: https://www.census.gov/geographies/reference-files/time-series/geo/gazetteer-files.html
[gaz-2026]: https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2026_Gazetteer/
[gaz-layout]: https://www.census.gov/programs-surveys/geography/technical-documentation/records-layout/gaz-record-layouts.html
[zcta-page]: https://www.census.gov/programs-surveys/geography/guidance/geo-areas/zctas.html
[tl-doc]: https://www2.census.gov/geo/pdfs/maps-data/data/tiger/tgrshp2025/TGRSHP2025_TechDoc.pdf
[cb-page]: https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.html
[cb-2025]: https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.2025.html
[cb-desc]: https://www2.census.gov/geo/tiger/GENZ2025/description.pdf
[tiger-root]: https://www2.census.gov/geo/tiger/
[genz25-shp]: https://www2.census.gov/geo/tiger/GENZ2025/shp/
[genz25-kml]: https://www2.census.gov/geo/tiger/GENZ2025/kml/
[genz20-shp]: https://www2.census.gov/geo/tiger/GENZ2020/shp/
[genz20-kml]: https://www2.census.gov/geo/tiger/GENZ2020/kml/
[tl-zcta]: https://www2.census.gov/geo/tiger/TIGER2026/ZCTA520/
[dbx-st]: https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-st-geospatial-functions
[dbx-geom]: https://docs.databricks.com/aws/en/sql/language-manual/data-types/geometry-type
[dbx-geog]: https://docs.databricks.com/aws/en/sql/language-manual/data-types/geography-type
[dbx-h3]: https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-h3-geospatial-functions
[dbx-free]: https://docs.databricks.com/aws/en/getting-started/free-edition-limitations
[dbx-readfiles]: https://docs.databricks.com/aws/en/sql/language-manual/functions/read_files
[dbx-tut]: https://docs.databricks.com/aws/en/ldp/tutorial-spatial-pipelines
[dbx-maps]: https://docs.databricks.com/aws/en/dashboards/manage/visualizations/maps
[dbx-county]: https://assets.docs.databricks.com/_extras/documents/county-district-names.csv
[dbx-zip]: https://assets.docs.databricks.com/_extras/documents/zipcode-codes.csv
[dbx-cbsa]: https://assets.docs.databricks.com/_extras/documents/us-cbsa-codes.csv
[dbx-aibi-rn]: https://docs.databricks.com/aws/en/ai-bi/release-notes/2026
[st-map]: https://docs.streamlit.io/develop/api-reference/charts/st.map
[st-pydeck]: https://docs.streamlit.io/develop/api-reference/charts/st.pydeck_chart
[pdk-layer]: https://deckgl.readthedocs.io/en/latest/layer.html
[pdk-geojson]: https://deckgl.readthedocs.io/en/latest/gallery/geojson_layer.html
[px-chmap]: https://plotly.com/python-api-reference/generated/plotly.express.choropleth_map.html
[px-maplibre]: https://plotly.com/python/mapbox-to-maplibre/
[pbi-shape]: https://learn.microsoft.com/en-us/power-bi/visuals/desktop-shape-map
[pbi-filled]: https://learn.microsoft.com/en-us/power-bi/visuals/power-bi-visualization-filled-maps-choropleths
[azm-ref]: https://learn.microsoft.com/en-us/azure/azure-maps/power-bi-visual-add-reference-layer
