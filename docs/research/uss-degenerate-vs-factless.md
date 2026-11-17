# Exclusion reason in the USS: degenerate column or factless fact?

Question: some ZIP x county x month rows are left out of the county value with an
`exclusion_reason` (`no_value`, `no_crosswalk`, `state_only_code`, `not_in_zillow`).
The reason must work as a **slicer** in Power BI or Streamlit. Should it be

1. a **degenerate dimension**: a column on `fct_home_value` (left-out rows stay in
   the fact), carried into the bridge and found by the generator through a naming
   convention, or
2. a **factless fact** `fct_home_value_exclusion` (ZIP x county x month + reason) as
   its own bridge stage, with `fct_home_value` holding only used rows?

Checked on 2026-11-17 against Kimball Group pages and the free chapter of the USS book.

## What Puppini says

Only chapter 9 of *The Unified Star Schema* (Inmon & Puppini) is freely available, as
a publisher excerpt. The copyright page says **2020** (first printing 2020), not 2021.
Quotes from that chapter:

- "The Bridge is a table that only contains IDs. This is a very simplified version."
  (p. 76)
- "The Bridge is a table that absorbs all the PKs and FKs from all the tables." (p. 78)
- "The USS approach requires every table to have a 'unique identifier' ... When the
  unique identifier consists of multiple columns, it is recommended to concatenate
  (or hash) them into one single column." (p. 77)
- "multiple stages per table ... is an advanced topic that goes beyond the scope of
  this book." (p. 88)

**Not found:** anything by Puppini on degenerate dimensions, factless facts, or text
attributes in the bridge. The rest of the book was not reachable, and no Puppini
website or GitHub turned up. Searches of LinkedIn and talks found nothing on these
topics. So the points below about how his rules apply are **my inference**, not his
words:

- A factless fact is a table with a PK and FKs. Under "absorbs all the PKs and FKs" it
  is an ordinary stage, and it needs its own hashed PK (zip|county|month).
- A text column like `exclusion_reason` is **neither a PK nor an FK**. Strictly, his
  definition does not put it in the bridge. It either stays on its table as an
  attribute, or becomes an FK to a small dimension.
- Our bridge also carries measures, so it goes beyond his "only IDs" form. Secondary
  sources (Towards Data Science, "Escaping SQL Traps with the USS", which returned 403
  to a direct fetch and was read only through search snippets) describe moving measures
  into the bridge, each mapped to its own stage, to avoid fan traps.

## What Kimball says

- **Degenerate dimension:** "a dimension ... that has no content except for its primary
  key ... placed in the fact table with the explicit acknowledgment that there is no
  associated dimension table." Example: invoice number on invoice-line facts.
  (Kimball techniques page)
- Design Tip #46: "A degenerate dimension (DD) acts as a dimension key in the fact
  table ... Transaction control header numbers ... are typically degenerate dimensions,
  such as order, ticket, credit card transaction, or check numbers."
- **Factless fact table:** "the event merely records a set of dimensional entities
  coming together at a moment in time." It can also show what did *not* happen: "a
  factless coverage table that contains all the possibilities ... and an activity
  table that contains the events that did happen." (Kimball techniques page)
- **Junk dimension:** "Transactional business processes typically produce a number of
  miscellaneous, low-cardinality flags and indicators." (Kimball techniques page)

**What this means here:** in Kimball's terms `exclusion_reason` is **not** a
degenerate dimension. A DD is a high-cardinality operational ID such as an order
number. A four-value status code is a low-cardinality **flag**, which Kimball puts in
a small dimension (a junk dimension or its own table). Option 2 matches Kimball's
coverage idea: the used rows are the "activity" and the left-out rows are the
"coverage minus activity", stored as their own table.

## How each option behaves as a slicer

Power BI USS set-up: each table connects to the bridge one-to-many on its key, and
filters flow from the tables **into** the bridge. A slicer on a bridge column keeps
only bridge rows that have the selected value. Rows from other stages have null there,
so they drop out.

| | Option 1: column on fact | Option 2: factless stage |
|---|---|---|
| Pick `no_crosswalk` | Keeps only left-out fact rows. Dimension-stage rows drop. | Keeps only exclusion-stage rows. Value measures show blank, which is correct. |
| Used rows in slicer | Show as "(Blank)" unless given a value such as `included`, and dimension stages are also blank. Confusing. | Not in the slicer; they are a different stage. |
| Weighted avg `sum(zhvi*res_ratio)/sum(res_ratio)` | **Every** measure must filter to used rows. `no_value` rows have `res_ratio` but null `zhvi`, so without the filter the denominator is silently too big. | Correct as written: the fact holds only used rows. |
| Coverage counts | `countrows` split by reason, on one stage. | Used = rows in the fact stage, left out = rows in the exclusion stage. Two simple measures. |
| Fact grain | Changes to "candidate rows", with null county for `no_crosswalk` and null `zhvi` for `no_value`/`not_in_zillow`. | Stays "rows used in the calculation". |
| Streamlit | `where exclusion_reason = ?` on one stage | `where stage = 'fct_home_value_exclusion' and exclusion_reason = ?` |

**A small `dim_exclusion_reason` (4 rows + description + sort order) helps in both
options:**

- A slicer reads from a dimension table, so it lists every reason, even one with no
  rows. Today `state_only_code` has no rows, because none of the 9 state-only ZIPs is
  in Zillow (see `hud-state-only-geoids.md`). A slicer on a bridge column would not
  show it.
- `exclusion_reason_key` becomes an ordinary FK, so the bridge absorbs it under
  Puppini's own rule. The generator needs **no** degenerate-key detection.
- In both options, a reason slicer does not narrow a ZIP or county slicer list unless
  the relationship filters both ways or a visual-level filter is added.

**Volume:** if `not_in_zillow` is stored for every crosswalk ZIP that is missing from
Zillow, for every month, it may become the largest stage. Count it before choosing.

## Naming conventions vs metadata

- Kimball abbreviates degenerate dimension as **DD** (Design Tip #46). His examples
  are named `..._number`, such as invoice number and order number.
- A `dd_` prefix or `_dd` suffix is common in practice. I found **no primary source**
  for it, so treat it as folk convention.
- A generator could detect it with a regex on column names, for example
  `^dd_|_number$`. That rule is fragile. `_number` also matches measures. A prefix
  leaks into the column names report users see. And `exclusion_reason` would need
  renaming to be found.
- **Declaring it in metadata is better** and fits this project ("metadata is the
  source of truth"). For example, give each column a role in the model's YAML
  (`config: meta: uss_role: degenerate | fk | measure`), which the USS generator
  reads. The rule is then explicit, pydantic can validate it, and it shows in
  diffs. If the owner wants a naming convention too, the generator can **check**
  that names match the declared roles, rather than **infer** the roles from names.

## Recommendation

**Option 2 plus `dim_exclusion_reason`.**

- `fct_home_value` keeps only used rows, so the weighted average and the "every
  calculation is verifiable" rule need no hidden filter.
- `fct_home_value_exclusion` is a factless fact (Kimball's coverage idea) at ZIP x
  county x month, with a hashed PK and FK `exclusion_reason_key`. It is one more
  stage, and the existing generator handles it like any other fact.
- `dim_exclusion_reason` is a tiny dimension generated from metadata (the list of
  reasons with descriptions). It provides the slicer and lists all four reasons.
- Show coverage as two measures side by side: ZIPs used and ZIPs left out (plus
  residential weight).
- Do not call `exclusion_reason` a degenerate dimension; by Kimball's definition it is
  not one. If a true DD ever appears, declare it in metadata rather than by name.

## Sources

- [The Unified Star Schema, ch. 9 excerpt (Inmon & Puppini, Technics Publications, 2020; PDF via TechTarget)](https://cdn.ttgtmedia.com/rms/pdf/The-Unified-Star-Schema.pdf)
- [Kimball Group: Degenerate Dimensions](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/degenerate-dimension/)
- [Kimball Group: Design Tip #46, Another Look at Degenerate Dimensions](https://www.kimballgroup.com/2003/06/design-tip-46-another-look-at-degenerate-dimensions/)
- [Kimball Group: Factless Fact Tables](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/factless-fact-table/)
- [Kimball Group: Junk Dimensions](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/junk-dimension/)
- Secondary: [Escaping SQL Traps with the Unified Star Schema (Towards Data Science)](https://towardsdatascience.com/escaping-sql-traps-with-the-unified-star-schema-562c534b1a3e/) (403 on direct fetch; read only through search snippets)
- Secondary: [David Jayatillake, "The Bridge of Puppini" (Substack)](https://davidsj.substack.com/p/the-bridge-of-puppini)
