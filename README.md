# Hearth Index

A metadata-driven housing data product: home values, rents and affordability trends by ZIP code,
built with dbt on Databricks from public data (Zillow Research, HUD, FHFA, Census).

**Status:** slice 1 in progress. One source (Zillow home values by ZIP) goes from a metadata file
to generated dbt models. The loader and the marts are not built yet.

## How it works

The metadata files in `metadata/sources/` are the single source of truth. A small Python package
(`hearth/`) validates them and generates the dbt sources, staging models and tests, so nothing
that describes a source is written by hand twice.

```
metadata/sources/*.yml  ->  hearth validate  ->  hearth generate  ->  models/staging/*  ->  dbt build
```

- Generated files carry a "GENERATED, do not edit" header. Edit the metadata, then regenerate.
- A test fails if the committed generated files no longer match the metadata.
- `hearth check-file` compares a downloaded file's header with the metadata (drift check).

## Quick start

```
uv sync
copy the Databricks host, HTTP path and token into .env (git-ignored)
uv run --env-file .env dbt debug --profiles-dir .
uv run python -m hearth validate
uv run python -m hearth generate
uv run pytest
```

## Layout

| Folder | Purpose |
|---|---|
| `metadata/sources/` | One YAML file per source: access, license, freshness, columns, rules |
| `hearth/` | Metadata validator, generator and command line |
| `models/staging/` | Generated: one staging model per raw source |
| `models/intermediate/` | Joins and reusable logic (later slices) |
| `models/marts/` | Published tables (later slices) |
| `tests/` | Python tests for the validator and generator |

## dbt best practices

These practices are required for this project. They come from
[this video on five tips for a successful dbt project](https://youtu.be/qOx8l_QFz9I).

1. **Staging layer.** One staging model per raw source, named `stg_<source_id>`. Renaming, type
   casting and simple clean-up happen only here, and every later model reads from staging, never
   from raw. Known exclusions are filtered here so they are visible. The generator enforces the
   one-to-one rule.
2. **CTEs for structure.** Every model follows the same order: import CTEs (`select *` from a
   source or `ref`), then one CTE per logical step, then a `final` CTE, and the file ends with
   `select * from final`. To debug, change what the last line selects from.
3. **Directories carry configuration.** Materialization and other shared settings live in
   `dbt_project.yml` per folder (`staging` as views, `marts` as tables), not in each model. Run a
   layer with a path selector such as `dbt build --select models/staging`.
4. **Style guide in the README** (below), so it stays visible while you work.
5. **Do not optimize for fewer lines.** New lines are cheap and brain power is expensive. Prefer
   several readable steps to one clever expression. Keep one column per line and put each join
   condition on its own line.

### Style guide

These conventions are proposed starting points; change them here first, then follow them.

- **Names:** snake_case for columns, models and metadata ids. Staging models are `stg_<source_id>`,
  intermediate models `int_<purpose>`, marts named for what a row is (for example `zip_month_affordability`).
- **Columns:** booleans start with `is_` or `has_`; timestamps end in `_at`; a month is the
  last day of the month in `month_end`; money is `decimal` in US dollars, never a float.
- **Geography:** ZIP codes are 5-character strings, never numbers, so leading zeros survive.
- **SQL:** lowercase keywords, four-space indent, one column per line, explicit `as` for aliases.
- **Tests:** every model has a primary-key style test (unique and not null); tests that come from
  a metadata rule are generated, not hand-written.
- **Metadata over code:** if a fact about a source can live in `metadata/`, it does.

## Data and licensing

Source terms are recorded in each metadata file. Redistribution terms for Zillow, HUD and FHFA data
are **unverified**; raw files are not committed (`raw_data/` is git-ignored), and published
datasets should not ship until the terms are checked. Zillow requires attribution.
