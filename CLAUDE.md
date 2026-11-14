# Hearth Index

A metadata-driven housing data product built on public data, with dbt on Databricks
Free Edition. It is a resume/portfolio project: the owner (Stefanie) needs to
understand every dbt object, so explain what you do in plain English.

Goal: housing prices and trends by ZIP code, rolled up the geography hierarchy
ZIP -> county -> metro (CBSA) -> state -> nation.

## How to work with me

- Keep every message short. One small step at a time.
- For terminal steps give a short command block and ask for the output.
- Never ask me to paste secrets. Secrets live only in `.env` (git-ignored).
- Never print, log or commit `.env`, tokens, or raw data files.
- I am on Windows, PowerShell, VS Code. Use `uv run ...` for Python.
- I like metadata over hand-written dbt. If a dbt object can be generated, generate it.
- Explain dbt/Spark concepts when asked; I have a SQL Server/Oracle background.

## Core design: metadata is the source of truth

```
metadata/sources/*.yml  --(pydantic validate)-->  hearth generate
        -> models/staging/_sources.yml, _staging.yml, stg_<source>.sql   (GENERATED)
        -> committed to git; CI/pytest fails if they drift from the metadata
```

- Never hand-edit generated files (they start with `GENERATED ... Do not edit`).
  Change the YAML or `hearth/generate.py`, then run `uv run python -m hearth generate`.
- Vocabulary follows ODCS; provenance/licence fields follow Frictionless/OWID ideas.
- Generated output must be deterministic (so the drift check is reliable).

## Layout

- `metadata/sources/` source definitions (one YAML per source)
- `hearth/metadata.py` pydantic models, `load_source`, `check_header`
- `hearth/generate.py` renders dbt sources/staging/tests from metadata
- `hearth/loader.py` lands CSVs in Databricks bronze (append-only, idempotent via sha256)
- `hearth/fetch.py` downloads API sources (HUD-USPS crosswalk) to git-ignored `raw_data/`
- `hearth/cli.py` commands: `validate`, `generate [--check]`, `load <id> <csv> [--dry-run]`,
  `check-file <id> <csv>`, `fetch-hud zip-county|zip-cbsa`
- `tests/` pytest, including the generated-files drift check
- `models/staging/` generated dbt files; `dbt_project.yml`, `packages.yml`, `profiles.yml`
- `README.md` overview plus the dbt best-practice list (5 tips from the video) to follow

## Commands

```
uv run python -m hearth validate
uv run python -m hearth generate            # regenerate dbt files
uv run python -m hearth generate --check    # fail if committed files are stale
uv run pytest -q
uv run ruff check .
uv run ruff format .
uv run --env-file .env dbt build --profiles-dir .
uv run --env-file .env python -m hearth load zillow_zhvi_zip <csv>
uv run --env-file .env python -m hearth fetch-hud zip-county
```

## Platform

- Databricks Free Edition. Catalog `workspace`; bronze schema `bronze`; dbt dev schema
  `hearth_index_dev`; serverless 2X-Small SQL warehouse. It stops itself when idle.
- `.env` holds `DATABRICKS_HOST`, `DATABRICKS_HTTP_PATH`, `DATABRICKS_TOKEN`
  and `HUD_TOKEN` (a ~390-char JWT from huduser.gov/hudapi). Never read it aloud.
- dbt core 1.11, dbt-databricks 1.13, dbt_utils 1.4.1. Python 3.12 (3.14 breaks dbt).
- Bronze is all text, append-only (`_file_sha256`, `_loaded_at`, `_source_file`), with
  `bronze._load_log` for idempotency. Staging reads the latest load only.
- Wide Zillow file: read with `rescuedDataColumn`; staging unpivots the JSON with
  `lateral view explode(from_json(..., 'map<string,string>'))`.

## Gotchas already hit (do not repeat)

- dbt 1.10+: `meta`, `freshness`, `loaded_at_field` must be nested under `config:`.
- Column-level `dbt_utils.expression_is_true` already prefixes the column name, so the
  expression is `rlike '...'`, not `zip rlike '...'`.
- Spark SQL strings: regex backslashes are doubled (`'^\\d{5}$'`).
- CTEs need commas between them. CTE naming convention: `src`, ..., `renamed`.
- Files must be written to the repo by me/the owner; always re-run `generate --check`
  after copying generator changes so a stale local copy is caught.

## Rules

- This file holds general instructions only. Feature specs, status and roadmap live in
  GitHub issues on https://github.com/mtypeworkroom/hearth-index, created with `/to-spec`
  (label `ready-for-agent`). Read the relevant issue before starting a feature.
- Redistribution terms for Zillow/HUD/FHFA are unverified. Do not commit data files.
- Small commits with clear messages. Tests alongside code. No floats for money (decimal).
- Verify claims about external APIs against a real response before encoding them.
