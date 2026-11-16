# What portfolio reviewers look for (data engineer / data architect)

Research for issue #9. Gathered 2026-11-15.

## Question

What do hiring managers and reviewers check when they open a data engineering or data
architecture portfolio repo on GitHub? What do strong public dbt / data platform repos do well?
How does hearth-index compare?

## A note on evidence quality

There is little first-hand writing from named hiring managers on this. Most "what hiring
managers want" pages are from bootcamps or training sellers (Northcoders, Data Engineer
Academy, DataExpert.io). They agree with each other, but they have a commercial interest and
their numbers (e.g. "ahead of 90% of portfolios") are unverified. Below, **[weak]** marks claims
found only in those sources. The stronger evidence is what real public projects actually do.

## Key findings

1. **The README is read first, and maybe only.** GitHub says a README should say what the
   project does, why it is useful, and how to get started
   ([GitHub Docs: About READMEs][gh-readme]). Career guides say reviewers scan the README, the
   visible folder structure and whether CI exists, in a few minutes **[weak]**
   ([Data Engineer Academy checklist][dea-check]).
2. **Show the whole system, not one script.** A data consultant (SeattleDataGuy) recommends
   projects that cover ingestion, storage and a visible end product, using several kinds of
   source (APIs, CSVs, JSON), and praises projects "documented in a way that shows off what
   work was done" ([SeattleDataGuy][sdg]). Joseph Machado (Start Data Engineering) lists
   version control, code organisation, tests with data quality checks and CI/CD as parts of a
   good project ([Start Data Engineering][sde]).
3. **An architecture diagram near the top.** Recommended by career guides **[weak]**
   ([Data Engineer Academy checklist][dea-check]). Real projects do it: Cal-ITP keeps a Mermaid
   flowchart (a diagram written as text that GitHub draws for you) of ingest -> model ->
   analyse ([Cal-ITP architecture][calitp-arch]).
4. **Tests and CI count as proof of production habits.** Bootcamp sources say tests, a
   decent README and regular, meaningful commits matter **[weak]**
   ([Northcoders][nc]). Every strong example below has automated checks (pre-commit hooks,
   lint, CI jobs).
5. **Explain trade-offs.** Guides suggest a "trade-offs / what I'd do in production" section
   **[weak]** ([Data Engineer Academy checklist][dea-check]). For an architect audience this is
   the main signal: decisions and why, which is what ADRs (Architecture Decision Records:
   short dated notes of one decision, its context and consequences) are for.
6. **Follow the community's conventions so reviewers recognise the shape.** dbt Labs'
   structure guide: staging (`stg_`, one per source) -> intermediate -> marts, sources in
   `_sources.yml`, and "above all stay consistent" ([dbt: How we structure][dbt-struct]).
7. **A licence is expected.** With no licence, "no one may reproduce, distribute, or create
   derivative works" from your code ([GitHub Docs: Licensing][gh-lic]). Strong examples carry
   one (Apache-2.0, AGPL-3.0, MIT).
8. **Easy to run.** jaffle_shop_duckdb promises under one minute "from `git clone` to
   `dbt docs serve`", with a dev container option ([jaffle_shop_duckdb][jsd]).

## Example repos

**dbt Labs jaffle-shop** ([repo][js], [duckdb variant][jsd]) - the reference dbt project.
- README with a table of contents, prerequisites, numbered setup steps and "checkpoints".
- Standard layout: `models/`, `seeds/`, `macros/`, `data-tests/`, `analyses/`.
- `.pre-commit-config.yaml` (ruff, YAML check, whitespace) plus `.sqlfluff` (SQL linter).
- `Taskfile.yml` wraps common commands; pinned `requirements.txt`.
- DuckDB variant: runs locally with no cloud account, Apache-2.0 licence, dev container.
- Honest framing: says it is "not a demonstration of best practices".

**GitLab Data Team analytics** ([2019 post by the team manager][gl-blog], [handbook][gl-hb])
- Production dbt code, issues and docs all public; MIT licensed ([gl-blog]).
- Published dbt docs site used as the model reference ([gl-blog]).
- Handbook pages for a dbt guide, SQL style guide, CI jobs, a dbt change workflow and a merge
  request template for model changes ([handbook][gl-hb]). (The repo itself blocked automated
  fetching, so this is from the handbook and blog, not the repo files.)

**Cal-ITP data-infra** ([repo][calitp], [docs site][calitp-docs]) - California's public
transit data warehouse.
- README explains the repo structure folder by folder; `warehouse/` is the dbt project.
- Separate MkDocs docs site with an architecture overview and Mermaid diagram
  ([architecture][calitp-arch]).
- `CONTRIBUTING.md`, `runbooks/`, dev container, pre-commit, SQLFluff, GitHub Actions lint
  workflow, `uv.lock`, AGPL-3.0 licence.

## Applies to hearth-index

| Finding | Already done? | Gap |
|---|---|---|
| README: what, why, how to start | Partly. Good "how it works" and quick start | Status line is stale (says loader not built; it is, and HUD is in). No "why this matters" for a data architect. Issue #17 |
| Architecture diagram | No (only a one-line text flow) | Add a Mermaid diagram: sources -> bronze -> staging -> marts, plus metadata -> generator. Issue #11 |
| Decision records / trade-offs | No. `docs/adr/` and `CONTEXT.md` do not exist | Write ADRs for the big calls (metadata-driven generation, append-only bronze, all-text bronze, Free Edition). Issue #10 |
| Tests | Yes. pytest for metadata, generator, loader, fetch; generated dbt tests; drift check | Make them visible: mention in README what each test layer proves |
| CI on every push | No. There is no `.github/workflows/` | Add GitHub Actions: ruff, pytest, `generate --check` (none need Databricks). Issue #12 |
| Lint / pre-commit | Partly. ruff via `uv run`, no hooks | Optional: pre-commit config; SQLFluff for SQL style |
| dbt layering conventions | Yes. `stg_` per source, `_sources.yml`, style guide in README | Intermediate and marts are empty; a reviewer sees only staging. Issue #16 |
| Data quality | Yes. Metadata rules -> generated tests, freshness in metadata, header drift check | Showcase it: it is the repo's most distinctive feature |
| Licence | No `LICENSE` file | Pick a code licence; separate data attribution notice (Zillow requires it). Issue #13 |
| Easy to reproduce | Partly. `uv.lock`, `.python-version`, clear commands | Needs Databricks + tokens; offer a no-cloud path (`validate`, `generate`, `pytest`) up front |
| Docs site / data dictionary | No published dbt docs | Generated data dictionary (issue #7); optionally publish `dbt docs` |
| Whole system, end product | Not yet. Ingest + staging only | A first mart and one chart/table of results. Issue #16 |
| Repo hygiene | Mostly. Clean history, small commits | `logs/` is ignored, but `.user.yml` (a dbt anonymous user id file) is committed; ignore and remove it. Issue #15 |

## Sources

- [gh-readme]: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes
- [gh-lic]: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository
- [dbt-struct]: https://docs.getdbt.com/best-practices/how-we-structure/1-guide-overview
- [js]: https://github.com/dbt-labs/jaffle-shop
- [jsd]: https://github.com/dbt-labs/jaffle_shop_duckdb
- [gl-blog]: https://about.gitlab.com/blog/open-source-analytics/
- [gl-hb]: https://handbook.gitlab.com/handbook/enterprise-data/platform/dbt-guide/
- [calitp]: https://github.com/cal-itp/data-infra
- [calitp-docs]: https://docs.calitp.org/data-infra/
- [calitp-arch]: https://docs.calitp.org/data-infra/architecture/architecture_overview.html
- [sdg]: https://seattledataguy.substack.com/p/5-data-engineering-projects-to-add
- [sde]: https://www.startdataengineering.com/post/data-engineering-projects/
- [nc]: https://www.northcoders.com/blog/what-employers-look-for-in-junior-data-engineers/ (bootcamp, weak)
- [dea-check]: https://dataengineeracademy.com/blog/data-engineer-portfolio-review-checklist-2026-what-hiring-managers-actually-score/ (training seller, weak; not opened in full, claims taken from search summaries)

[gh-readme]: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes
[gh-lic]: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository
[dbt-struct]: https://docs.getdbt.com/best-practices/how-we-structure/1-guide-overview
[js]: https://github.com/dbt-labs/jaffle-shop
[jsd]: https://github.com/dbt-labs/jaffle_shop_duckdb
[gl-blog]: https://about.gitlab.com/blog/open-source-analytics/
[gl-hb]: https://handbook.gitlab.com/handbook/enterprise-data/platform/dbt-guide/
[calitp]: https://github.com/cal-itp/data-infra
[calitp-docs]: https://docs.calitp.org/data-infra/
[calitp-arch]: https://docs.calitp.org/data-infra/architecture/architecture_overview.html
[sdg]: https://seattledataguy.substack.com/p/5-data-engineering-projects-to-add
[sde]: https://www.startdataengineering.com/post/data-engineering-projects/
[nc]: https://www.northcoders.com/blog/what-employers-look-for-in-junior-data-engineers/
[dea-check]: https://dataengineeracademy.com/blog/data-engineer-portfolio-review-checklist-2026-what-hiring-managers-actually-score/
