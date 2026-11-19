# dbt Charts vs Streamlit for the dashboard

Question (issue #37): should the dashboard be built with **dbt Charts** instead of the
Streamlit app decided in issue #26? dbt Charts is dashboards written as YAML + SQL files
in a `charts/` folder of the dbt repo, with an optional hosted service at dbtcharts.com.

Checked on 2026-11-19 against dbtcharts.com, docs.dbtcharts.com, github.com/dbt-labs/dbt-charts
and getdbt.com. Nothing was installed or run. I did **not** watch the Nov 2026 webinar
(it is a video), so nothing here relies on it; anything said only there is
unverified.

## Short answer: keep Streamlit, revisit after the dashboard v1 ships

- dbt Charts **does support Databricks** and does **not** need dbt platform, Fusion or
  dbt v2. It is **open source (Apache 2.0)** but **beta, pre-1.0**, and launched only on
  2026-10-27. The syntax "will change before 1.0".
- It can express most of what #26 asks for (multi-select filter, weighted average in
  SQL, a county choropleth). The awkward part is the **aggregation-level picker**: there
  is no documented way to let a picker choose the `GROUP BY` column.
- It would fit our "generate it from metadata" style very well (plain YAML files).
- Hosting at dbtcharts.com does **not** solve the public-hosting question. It runs your
  queries from dbt Labs servers with your stored credentials, caches results there, and
  would put Zillow/HUD-derived numbers on a public link.
- Plan: build #26 in Streamlit as decided. Revisit dbt Charts when it reaches 1.0, or
  when the Streamlit v1 is done, whichever is later (see "Revisit trigger").

## 1. Databricks, dbt version, status, cost

- **Databricks: yes.** The README lists Athena, BigQuery, ClickHouse, Databricks,
  PostgreSQL, Redshift, Snowflake, Spark and Trino; install with
  `dbt-charts[databricks]`. [README][readme], [installation][install]
- **Free Edition / serverless: not mentioned.** The hosted connection page says the IP
  allowlist rule "applies to serverless SQL warehouses too". It lists PAT or service
  principal auth. Nothing on Free Edition. **Unverified**, but locally it uses the same
  `dbt-databricks` adapter we already run, so it will *probably* work. [connections][conn]
- **dbt version:** dbt is optional. Inside a dbt project it reuses the connection from
  `profiles.yml` (via the adapter "as a library"; it "never runs the `dbt` command").
  The adapters depend on **dbt Core 1.x**. No exact Core or `dbt-databricks` version is
  stated, so 1.11 + 1.13 is **probably fine but unverified**. [installation][install]
- `ref()` in chart SQL reads `target/manifest.json`, so run `dbt parse` first.
  [queries][queries]
- **Install advice:** install with `uv tool install` (its own environment), not into
  our `.venv`, so its dbt Core does not clash with ours. The docs give this advice for
  dbt v2 users; for us it avoids two dbt Core pins fighting. [installation][install]
- **Not tied to dbt platform / Fusion / v2.** None of the pages require them.
- **Status: beta.** "dbt Charts is pre-1.0"; YAML syntax will change before 1.0 (old
  boards still parse). Python 3.11 to 3.14. [README][readme] Announced 2026-10-27 at dbt
  Summit. [launch blog][blog] The GitHub repo shows no tagged releases. [repo][repo]
- **Licence:** language and `dct` CLI are **Apache 2.0**, "the same license as dbt".
  [launch blog][blog], [repo][repo]
- **Cost:** the CLI is free. Hosted platform "Individual" plan is free for up to
  3 collaborators with unlimited queries; "Team" is per seat, price not published.
  "Never a meter on your warehouse bill". [pricing][pricing] Warehouse compute is still
  ours (Databricks Free Edition).

## 2. Chart file format and our generator

A board is one YAML file with `variables` (pickers), `queries` (SQL), `charts` and a
layout (`rows`/`cols`/`tabs`). [quick guide][quick] Charts do not aggregate: "the chart
does not aggregate or infer meaning"; SQL does the grouping. [quick guide][quick]

Sketch (field names from the docs; **not run**):

```yaml
variables:
  counties:
    input: multiselect
    options:
      query: "select county_fips as value, county_name as label from {{ ref('dim_county') }}"
queries:
  trend:
    sql: |
      select month,
             sum(zhvi * res_ratio) / sum(res_ratio) as home_value
      from {{ ref('uss_bridge') }}
      where {{ filter('county_fips', counties) }}
      group by month
charts:
  trend_chart:
    query: trend
    type: line
    x: month
    y: home_value
rows:
  - trend_chart
```

Against the #26 requirements:

| Need | dbt Charts | Source |
|---|---|---|
| Multi-select geography picker | Yes: `input: multiselect`, options from a query; `filter()` turns a list into `IN` and an empty pick into `1=1` | [variables][vars], [queries][queries] |
| One picker that hides the dimension split (state -> metro -> county -> ZIP) | Possible via one options query that unions the levels. Cascading pickers not documented. **Unverified** | [variables][vars] |
| Aggregation level (6 levels) | **Not documented.** Jinja `if/else` in SQL is not documented, and the docs advise against building column names from user input. Workaround: generate one query + chart per level and show one with `visible:`. **Unverified** | [queries][queries], [variables][vars] |
| Weighted average | Yes, it is just SQL. The formula would live in generated SQL rather than in a Python app | [quick guide][quick] |
| Coverage by `exclusion_reason` | Yes: `bar` / `table` / `kpi` chart types | [charts][charts] |
| County map | Yes: `type: map`, built-in `geo.source: us-counties`; `lookup` must match the shape keys exactly (leading zeros). No built-in ZIP/ZCTA or CBSA shapes; custom GeoJSON/TopoJSON URL allowed | [maps][maps] |
| Screenshot for README | Yes: `dct render board.yml --format png`. Replaces the Playwright step in `hearth screenshot-dashboard` | [render][render] |

**Can `hearth generate` emit these?** Yes, easily. A board is plain YAML; the generator
already writes deterministic YAML/SQL. It could turn `metadata/reporting/measures.yml`
and `dashboard.yml` into `charts/*.yml` and drift-check them like the staging files.
`dct validate` and `dct render` (exits 1 on a chart error) could join CI. [render][render]
This is actually a *better* fit for the "nothing hand-written" rule than #26, where the
Python app is hand-written. Catch: the format is pre-1.0, so the generator would chase
syntax changes.

## 3. Hosting at dbtcharts.com

- **Who runs the queries:** dbt Labs. "Queries run from Platform's servers" at
  `34.85.252.27/32`; the warehouse must be reachable from the internet. On Databricks
  you add that IP to the workspace IP access list. [platform][platform], [connections][conn]
- **Credentials:** entered in the platform (PAT or service principal), "encrypted at
  rest", write-only, "never read from the repository". [connections][conn] So our
  Databricks token would live at dbt Labs, not only in `.env`.
- **Does data leave the warehouse?** Yes. The pricing page says "Query results are
  cached, so the same board render doesn't re-bill your warehouse" and refreshes are
  deduplicated across viewers. [pricing][pricing] Where and how long results are stored
  on the platform is **unverified** (the refresh page only describes the local `dct`
  cache). [refresh][refresh] Refresh is manual; "There is no scheduled refresh".
- **Public?** Off by default. "Anyone with the link" makes a board viewable without an
  account, but only if it is enabled at org **and** project level. Outside visitors are
  view-only and cannot refresh. [access control][access]
- **Effect on the open public-hosting question:** it *helps* with warehouse cost (cache,
  no per-view queries, visitors cannot trigger refresh) and keeps credentials out of a
  public app. It *does not help* with redistribution: a public link still republishes
  Zillow/HUD-derived values, and the data now also sits on a third party's servers. It
  is also beta, with no published data-retention terms. So the blocker stays the same.
- **Local-only route:** `dct serve` (live preview) and `dct render --format html`
  (static page) work with no hosting at all. Whether the static HTML keeps working
  filters without a warehouse is **unverified**. [render][render], [static sites][static]

## 4. Which reads better to a hiring reviewer (opinion)

*Opinion, not sourced.*

- **Streamlit** is widely known. A reviewer sees Python, a live connector, caching and
  a metadata-driven UI: solid, unsurprising engineering. Risk: "another Streamlit demo".
- **dbt Charts** shows "charts as code in the dbt repo", generated and CI-checked. That
  matches the project's story (metadata -> generated, drift-checked artefacts) and is
  current. Risk: few reviewers will know it yet, it is beta, and the variable
  aggregation level may need workarounds that look hacky.
- For a **data engineer / architect** role, the strongest signal is the metadata layer
  (`measures.yml`, `dashboard.yml`) and gold-only reads, not the chart tool. Both tools
  can show that. A short dbt Charts board *next to* the Streamlit app, generated from
  the same `measures.yml`, would show the measures really are tool-neutral, which is the
  point #26 makes.

## 5. Recommendation

**Keep Streamlit for #26.** Reasons: dbt Charts is beta and pre-1.0; the 6-level
aggregation picker is not a documented feature; hosting does not unblock the
redistribution question; and #26 is already designed.

**Revisit trigger:** whichever comes later of (a) Streamlit dashboard v1 merged, or
(b) dbt Charts 1.0 released. Check again no later than **2027-03-01**. At that point,
consider a small spike: generate one `charts/trend.yml` from `measures.yml` and render
it locally (no hosting). Things to test in that spike:

1. `dct validate` against our `profiles.yml` (Free Edition, PAT, `catalog:` key).
2. Whether a variable can pick the group-by level (or the `visible:` workaround).
3. `us-counties` lookup with our 5-digit county FIPS.

## Unverified

- Databricks **Free Edition** with dbt Charts (local or hosted).
- Exact dbt Core / `dbt-databricks` versions supported (only "dbt Core 1.x" is stated).
- Variable-driven `GROUP BY` / Jinja `if/else` in queries.
- Exact SQL that `filter()` produces for a multiselect (docs say "list-to-`IN`").
- Where and how long the hosted platform stores cached query results.
- Whether static HTML from `dct render` keeps working filters offline.
- `us-counties` key format (example only shows numeric state codes).
- Anything said only in the Nov 2026 "What's shipping in dbt" webinar (not watched).

## Sources

- [dbt Charts home][home]
- [dbt Charts README (GitHub)][readme]
- [dbt-labs/dbt-charts repo][repo]
- [Launch blog, getdbt.com (2026-10-27)][blog]
- [Quick guide][quick]
- [Installation & setup][install]
- [Variables][vars]
- [Queries][queries]
- [Charts][charts]
- [Maps][maps]
- [dct render][render]
- [Static sites][static]
- [Platform: getting started][platform]
- [Platform: data connections][conn]
- [Platform: access control][access]
- [Platform: refresh][refresh]
- [Pricing][pricing]

[home]: https://dbtcharts.com
[readme]: https://raw.githubusercontent.com/dbt-labs/dbt-charts/HEAD/README.md
[repo]: https://github.com/dbt-labs/dbt-charts
[blog]: https://www.getdbt.com/blog/dbt-charts-open-source-dashboard-yaml
[quick]: https://docs.dbtcharts.com/quick-guide/
[install]: https://docs.dbtcharts.com/guides/installation/
[vars]: https://docs.dbtcharts.com/variables/
[queries]: https://docs.dbtcharts.com/queries/
[charts]: https://docs.dbtcharts.com/charts/
[maps]: https://docs.dbtcharts.com/charts/maps/
[render]: https://docs.dbtcharts.com/cli/render/
[static]: https://docs.dbtcharts.com/integrations/static-sites/
[platform]: https://docs.dbtcharts.com/platform/getting-started/
[conn]: https://docs.dbtcharts.com/platform/connections/
[access]: https://docs.dbtcharts.com/platform/access-control/
[refresh]: https://docs.dbtcharts.com/platform/refresh/
[pricing]: https://dbtcharts.com/pricing/
