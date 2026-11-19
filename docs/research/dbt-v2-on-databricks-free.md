# dbt v2 on Databricks Free: what changes and what breaks

Question (issue #35): should Hearth Index move from dbt Core 1.11 (dbt-databricks 1.13,
dbt_utils 1.4.1, Python 3.12 pinned) to **dbt v2**, the Rust engine formerly called
dbt Fusion? What changes or breaks if it does?

Checked on 2026-11-19 against docs.getdbt.com, getdbt.com, hub.getdbt.com,
github.com/dbt-labs and docs.databricks.com. Nothing was installed or run. Statements
about *our* files come from reading the repo (`dbt_project.yml`, `packages.yml`,
`profiles.yml`, `pyproject.toml`, `models/staging/*`).

## Short answer: wait (try it side by side, don't switch yet)

- v2 is GA and Databricks is listed as GA, so it is a real option now. But nothing in
  the docs covers **Free Edition**, our **Spark-only SQL** (`lateral view explode`) or
  our `catalog:` profile key. Those three are exactly where we would break.
- The free `dbt` binary is **not open source** (dbt Product Licensing Agreement). The
  Apache 2.0 build (`dbt-oss`) leaves out SQL comprehension, the very feature that
  makes v2 interesting.
- Plan: run the "Real-run check" below in a throwaway worktree. If it is clean, open a
  small follow-up issue (widen `require-dbt-version`, add v2 to CI). Until then keep
  dbt Core 1.11 under `uv` as the official path.

Dates: GA was announced **2026-09-16** at dbt Summit. [GA post][ga] I found **no
November 2026 milestone**. The "Supported data platforms" page (updated 2026-11-14)
lists Databricks as "Generally available". [platforms][platforms]

## 1. Databricks and Free Edition support

- Naming: "The dbt Fusion engine is now just called dbt, and dbt Core v2 is now called
  dbt OSS." [dbt vs dbt OSS][oss]
- Databricks lifecycle: "Generally available". The same page warns: "An adapter can
  reach GA in the dbt platform before it reaches GA for local use", and it does not
  split the two. So **local GA for Databricks is unverified**. [platforms][platforms]
- Auth: PAT ("Service Account / User Token"), Native OAuth, OIDC federation. PAT is
  supported, though Databricks calls it legacy. [Databricks setup v2][dbx-setup],
  [supported features][features]
- Connection: `dbt-databricks` is the only method; `http_path` can point at a SQL
  warehouse. [Databricks setup v2][dbx-setup]
- **Free Edition is not mentioned** in the dbt docs. Databricks' own limits page says
  Free Edition has "One SQL warehouse, limited to a 2X-Small cluster size" and may not
  be used commercially; it says nothing about PATs or dbt. [Free Edition limits][free]
  Our dbt Core setup already works there, and v2 uses the same connection type, so it
  will *probably* work. Unverified until the live check.
- Possible profile snag: the v2 examples use `database:` for the catalog (with
  `auth_type: databricks_cli` in the PAT example), while our `profiles.yml` uses
  `catalog:`. The `dbt init` prompt does say "Catalog". Whether v2 accepts `catalog:` is
  **unverified**. [Databricks setup v2][dbx-setup]
- Threads: on Databricks v2 manages parallelism itself, and `threads` (ours: 4) only
  acts as a cap. [upgrading][upgrade]

## 2. Will it parse/compile our staging SQL?

- **What v2 adds:** "static analysis". v2 parses the SQL in every model (like a
  compiler checking types) instead of only rendering Jinja to text. There are three
  modes: [about static analysis][sa-about], [config][sa-config]
  - `baseline` (default): analyse, report problems as **warnings**, keep running.
  - `strict`: "nothing runs until the entire project is proven valid".
  - `off`: skip analysis for the model **and everything downstream** (it cascades).
  - `on` / `unsafe` are deprecated synonyms for `strict`. [upgrading][upgrade]
- **Dialect limits:** the docs list unsupported "advanced types (`STRUCT`, `ARRAY`,
  `GEOGRAPHY`)" and some functions. They do not mention Spark's `LATERAL VIEW`,
  `explode` or `from_json`. [about static analysis][sa-about] `stg_zillow_zhvi_zip`
  uses all three, plus a `map<string,string>` type string. A search found no dbt-labs
  issue about `lateral view` either. So whether v2 understands it is **unverified**.
  Expectation: in `baseline` the worst case is a warning. In `strict` it could block
  the run.
- `stg_hud_usps_zip_county` uses only plain SQL (`cast`, `nullif`, `trim`, `rlike`).
  Expected to pass, but unverified.
- **`rescuedDataColumn` is not a dbt question.** It is used only in `hearth/loader.py`
  (`read_files` / `COPY INTO`), which runs through the Python connector. dbt only sees
  the `_rescued_data` string column.
- **Opting a model out**, if it fails (put it in the generator, not by hand):

  ```yaml
  models:
    - name: stg_zillow_zhvi_zip
      config:
        static_analysis: off
  ```

  or `{{ config(static_analysis='off') }}` in the SQL. `--static-analysis off` on the
  command line overrides everything. [config][sa-config] dbt asks you to report SQL
  that is valid for your warehouse but fails to parse. [about static analysis][sa-about]
  A cleaner fix would be rewriting the unpivot as `select ... from latest_load,
  lateral explode(...)` or `explode` in the select list. Whether v2 parses those forms
  is also unverified.
- **Introspection:** in `baseline`, v2 uses the live database "as the source of truth",
  so `compile` may need a working connection to learn the source columns.
  [about static analysis][sa-about]

## 3. dbt_utils, `config:` nesting and deprecations

- **dbt_utils 1.4.1 is v2 compatible.** The hub shows a "v2 compatible" badge,
  `require-dbt-version` `>=1.3.0, <3.0.0`, and parse "Passed" on `2.0.0-preview.193`.
  [hub dbt_utils][hub] The upgrade guide names dbt_utils as compatible.
  [upgrading][upgrade]
- **Our own `dbt_project.yml` will warn.** It says `require-dbt-version: [">=1.8.0",
  "<2.0.0"]`. v2 says: "If it excludes `2.0.0`, dbt v2 will warn today and error in a
  future release." Fix: `">=1.10.0,<3.0.0"`. Bypass for a test: `--no-version-check`.
  [require-dbt-version][rdv]
- **Our generated YAML is already in v2 style.** `meta`, `freshness` and
  `loaded_at_field` sit under `config:` (the dbt 1.10 change we already hit). Generic
  test arguments sit under `arguments:`. The readiness checklist says deprecation
  warnings in v1 "will become errors once you upgrade to dbt v2". [readiness][ready]
  Our current Core build is clean (per the Gotchas list), so no known errors. The
  `dbt-autofix` tool can check this without installing v2. [readiness][ready]
- **Stricter in v2** (relevant to the generator): unknown YAML keys, misspelled
  configs and unused config paths in `dbt_project.yml` are now **errors**. Missing
  macros or vars fail at `parse`, not `compile`. `--models`/`-m` is an error (use
  `--select`). [upgrading][upgrade] Risk: our `dbt_project.yml` configures
  `intermediate` and `marts` folders that do not exist yet. That could count as
  "unused config paths". Unverified.
- `config.get('owner')` no longer reads from `meta`; use `config.meta_get('owner')`.
  We do not do this today. [upgrading][upgrade]

## 4. Python pin, Windows install, and `uv`

- v2 is a **single native binary**: no Python needed for the standalone install. dbt
  recommends it because dbt "will always be available from your CLI, without having to
  first activate a virtual environment". [GA post][ga]
- Windows options (official): [install][install], [extension install][ext]
  - PowerShell: `irm https://public.cdn.getdbt.com/fs/install/install.ps1 | iex`
  - winget: `winget install --id dbtLabs.dbt --exact`
  - pip: `python -m pip install dbt`
- Windows install path: `C:\Users\<username>\.local\bin\dbt.exe`, added to `Path`.
  Alias `dbtf` exists "if you already have another dbt CLI installed". Windows steps for
  the alias are not documented. [extension install][ext] Update: `dbt system update`.
- **Living alongside `uv`:** our `pyproject.toml` pins `dbt-core>=1.10,<1.12`, so
  `uv run dbt ...` keeps using Core 1.11 from `.venv`. (`uv run` puts the venv first on
  `PATH`; this is standard uv behaviour, but I did not re-check it here.) In a plain
  shell, `dbt` would become v2. To avoid confusion, call v2 by its full path.
  "`dbt-oss` and `dbt` cannot share a Python environment", so do **not** `uv add dbt`.
  [install][install]
- Do not use `pip install dbt-core` to get v2: on 2.x it now installs **dbt OSS**.
  [dbt vs dbt OSS][oss]
- **Python 3.12 pin:** v2 removes *dbt's* reason for the pin, but only once Core is
  gone from `pyproject.toml`. The `hearth` tooling still runs under uv. Whether it is
  fine on 3.13+ is a separate question (not checked).

## 5. Licence: public MIT repo and GitHub Actions

| Piece | Licence | Source |
|---|---|---|
| `dbt-labs/dbt-core` repo (`main` = v2 Rust source) | Apache 2.0 | [dbt-core repo][core-repo] |
| `dbt-oss` binary / dbt Core v1.x / adapters / language spec | Apache 2.0 | [licence FAQ][faq] |
| `dbt` binary (fka Fusion) | Proprietary, **dbt Product Licensing Agreement**; free, no login needed | [licensing][lic], [PLA][pla] |
| `dbt-labs/dbt-fusion` repo | README: "Most code is licensed under ELv2"; repo marked ARCHIVE, code moved | [dbt-fusion repo][fusion-repo] |

- The FAQ says the ELv2 code "was moved to the dbt repository under Apache 2.0" and
  that internal use is free "without restriction", with no user cap. [licence FAQ][faq]
- **Public MIT repo:** no conflict. We commit only our SQL/YAML/Python, not the binary.
  Do not vendor `dbt.exe` into the repo. The PLA forbids removing notices and limits
  *redistribution* (e.g. as a managed service). [licence FAQ][faq]
- **GitHub Actions:** the FAQ allows deploying "into any environment you choose" but
  does not mention CI by name. So running the proprietary `dbt` in a public CI runner
  is **probably fine but unverified**. I did not read the full PLA. `dbt-oss` in CI is
  safe (Apache 2.0) but has no static analysis. [licence FAQ][faq], [dbt vs dbt OSS][oss]

## 6. Column lineage and the diagram tickets

- **dbt Docs v2 exists:** `dbt docs generate` builds and exports a static site;
  `dbt docs serve` previews it on port **8580**; `--output-dir site` writes a
  self-contained folder "you can host on ... GitHub Pages". [docs cmd][docs-cmd]
  Docs v2 is in both distributions. [dbt vs dbt OSS][oss]
- **Column-level lineage** needs a strict build against the live warehouse:
  `dbt build --generate-info-schema --static-analysis strict`, then
  `dbt docs generate --no-compile`. Without that, Docs v2 "hides those features".
  [docs cmd][docs-cmd] (A search snippet showed `--write-index` instead of
  `--generate-info-schema`; the docs disagree, so check `--help`.)
- **Catch for us:** strict lineage requires the Zillow `lateral view` model to pass
  strict analysis. Turning it `off` cascades, which hides lineage for it and every
  downstream mart. Static analysis (and so lineage) is only in the proprietary `dbt`,
  not `dbt-oss`. [dbt vs dbt OSS][oss], [availability][avail]
- **For the tickets:**
  - The *Mermaid-from-metadata* ticket is unaffected. It reads `metadata/sources/*.yml`,
    not dbt.
  - The *dbt docs on GitHub Pages* ticket: v2 gives a proper static export with
    column-level lineage. But building it needs warehouse credentials (a `build`), so
    CI would need the Databricks token as a secret, or the site is built locally.
    v1 `dbt docs generate` also needs a connection, so this is not new.
- Compile-time checks: `strict` catches type errors and bad column references before
  anything runs on the warehouse. That saves warehouse start-ups on Free Edition's
  single 2X-Small warehouse. [config][sa-config]

## Real-run check for the owner

Use a throwaway git worktree so `package-lock.yml` (tracked) and `target/` on `main`
are not touched. Commands are PowerShell, run from `c:\repos\hearth_index`.

**1. Install v2 (user-level; does not touch `.venv`)**

```powershell
irm https://public.cdn.getdbt.com/fs/install/install.ps1 | iex
```

Open a **new** PowerShell window, then:

```powershell
$v2 = "$HOME\.local\bin\dbt.exe"
& $v2 --version          # expect a 2.x version
uv run dbt --version     # expect still 1.11.x (Core under uv)
```

(Want to read the script first? Use `irm <url> -OutFile install.ps1` and open it. The
other option is `winget install --id dbtLabs.dbt --exact`.)

**2. Throwaway worktree plus credential-free checks (dummy env vars, no secrets)**

```powershell
git worktree add ..\hearth_v2_try
cd ..\hearth_v2_try
$env:DATABRICKS_HOST='dummy.cloud.databricks.com'; $env:DATABRICKS_HTTP_PATH='/sql/1.0/warehouses/x'; $env:DATABRICKS_TOKEN='x'
& $v2 deps --profiles-dir .
& $v2 parse --profiles-dir .
& $v2 compile --profiles-dir . --static-analysis off
```

Look for:
- `deps`: dbt_utils 1.4.1 installs; no `dbt1065` for dbt_utils.
- `parse`: expected a `dbt1065`-style warning for **our** `require-dbt-version`.
  Any **error** about the `catalog:` profile key, unknown YAML keys or unused config
  paths (`intermediate`, `marts`) is a real break.
- `compile ... off`: both staging models render. Without a warehouse, this checks Jinja
  and YAML only, not SQL.

**3. One live check (real `.env`, separate schema so dev views are untouched)**

```powershell
$env:DATABRICKS_SCHEMA='hearth_index_v2try'
Remove-Item Env:DATABRICKS_HOST,Env:DATABRICKS_HTTP_PATH,Env:DATABRICKS_TOKEN
uv run --no-project --env-file ..\hearth_index\.env -- $v2 debug --profiles-dir .
uv run --no-project --env-file ..\hearth_index\.env -- $v2 build --profiles-dir . --static-analysis strict
```

Look for:
- `debug`: connection OK (it may take a minute while the warehouse wakes up).
- `build ... strict`: does `stg_zillow_zhvi_zip` fail analysis on `lateral view`?
  - If yes, re-run with `--static-analysis baseline`: it should build with a warning.
  - All tests should pass the same as on Core.

Clean up afterwards: `cd ..\hearth_index; git worktree remove ..\hearth_v2_try`. Then
drop schema `hearth_index_v2try` in Databricks.

## Unverified

- Whether Databricks is GA for **local** v2 (the platforms page does not split
  platform/local).
- Free Edition and PAT with v2 (not in dbt docs).
- Whether v2 static analysis accepts `lateral view explode(from_json(...,
  'map<string,string>'))`.
- Whether the v2 Databricks profile accepts `catalog:` (examples use `database:`).
- Whether unused config paths `intermediate`/`marts` in `dbt_project.yml` error in v2.
- Whether `parse` needs a live connection, and how `compile` behaves offline.
- Running the proprietary `dbt` binary in public GitHub Actions (full PLA not read).
- `--generate-info-schema` vs `--write-index` flag name for column lineage.
- `uv run --no-project --env-file ... -- <exe path>` running a non-Python binary
  (standard uv usage, not re-checked here).
- No November 2026 Databricks milestone found; GA was 2026-09-16.

## Sources

- [dbt v2 is GA (2026-09-16)][ga]
- [What's the difference between dbt and dbt OSS? (2026-09-16)][oss]
- [Supported data platforms (updated 2026-11-14)][platforms]
- [Supported features / requirements (updated 2026-10-29)][features]
- [Feature availability (updated 2026-10-29)][avail]
- [Connect Databricks, dbt v2 (updated 2026-10-26)][dbx-setup]
- [Databricks Free Edition limitations (updated 2026-11-16)][free]
- [About static analysis (updated 2026-10-29)][sa-about]
- [static_analysis config (updated 2026-10-19)][sa-config]
- [Upgrading to v2 (updated 2026-10-29)][upgrade]
- [dbt v2 readiness checklist (updated 2026-10-23)][ready]
- [require-dbt-version (updated 2026-09-10)][rdv]
- [dbt_utils on the package hub][hub]
- [Install dbt (updated 2026-10-29)][install]
- [Install dbt extension / CLI (updated 2026-09-16)][ext]
- [dbt licensing (updated 2026-10-23)][lic]
- [dbt licences FAQ][faq]
- [dbt Product Licensing Agreement][pla] (linked, not read in full)
- [dbt-labs/dbt-core repo][core-repo]
- [dbt-labs/dbt-fusion repo][fusion-repo]
- [dbt docs commands, v2 (updated 2026-10-23)][docs-cmd]

[ga]: https://docs.getdbt.com/blog/dbt-v2-is-ga
[oss]: https://docs.getdbt.com/blog/comparing-dbt-and-dbt-oss
[platforms]: https://docs.getdbt.com/docs/supported-data-platforms
[features]: https://docs.getdbt.com/docs/fusion/supported-features
[avail]: https://docs.getdbt.com/docs/fusion/fusion-availability
[dbx-setup]: https://docs.getdbt.com/docs/local/connect-data-platform/databricks-setup
[free]: https://docs.databricks.com/aws/en/getting-started/free-edition-limitations
[sa-about]: https://docs.getdbt.com/docs/build/about-static-analysis
[sa-config]: https://docs.getdbt.com/reference/resource-configs/static-analysis
[upgrade]: https://docs.getdbt.com/docs/dbt-versions/dbt-upgrade/upgrading-to-v2
[ready]: https://docs.getdbt.com/docs/dbt/dbt-readiness
[rdv]: https://docs.getdbt.com/reference/project-configs/require-dbt-version
[hub]: https://hub.getdbt.com/dbt-labs/dbt_utils/latest/
[install]: https://docs.getdbt.com/docs/local/install-dbt
[ext]: https://docs.getdbt.com/docs/install-dbt-extension
[lic]: https://docs.getdbt.com/docs/dbt-licensing
[faq]: https://www.getdbt.com/licenses-faq
[pla]: https://www.getdbt.com/dbt-product-license-agreement
[core-repo]: https://github.com/dbt-labs/dbt-core
[fusion-repo]: https://github.com/dbt-labs/dbt-fusion
[docs-cmd]: https://docs.getdbt.com/reference/commands/cmd-docs?version=2
