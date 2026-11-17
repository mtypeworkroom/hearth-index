# HUD crosswalk rows with a 2-digit county code

Question: in the HUD-USPS ZIP-county crosswalk (2026 Q2), some rows have a 2-digit
`geoid` instead of a 5-digit county FIPS. What are they, does HUD document them, and
what should the county roll-up do with them?

Checked on 2026-11-17 against the loaded file (`hud_usps_zip_county_2026q2.csv`,
54,570 rows) and HUD's published documentation.

## What the rows are

9 rows of 54,570 have a 2-digit `geoid`. In each one the code is the **state or
territory FIPS code** of the row's `state`, and the ZIP has no other row (so the
whole ZIP is assigned to the state, ratios = 1).

| ZIP   | Place            | `state` | `geoid` | `res_ratio` | `oth_ratio` |
|-------|------------------|---------|---------|-------------|-------------|
| 77352 | Livingston       | TX      | 48      | 1           | 1           |
| 96799 | Pago Pago        | AS      | 60      | 0           | 1           |
| 96940 | Koror            | PW      | 70      | 0           | 1           |
| 96941 | Pohnpei          | FM      | 64      | 0           | 1           |
| 96942 | Chuuk            | FM      | 64      | 0           | 1           |
| 96943 | Yap              | FM      | 64      | 0           | 1           |
| 96944 | Kosrae           | FM      | 64      | 0           | 1           |
| 96960 | Majuro           | MH      | 68      | 0           | 1           |
| 96970 | Ebeye            | MH      | 68      | 0           | 1           |

Two groups:

- **Pacific (8 rows):** American Samoa and the Freely Associated States (Palau,
  Micronesia, Marshall Islands). `res_ratio` is 0: no residential addresses, so these
  rows carry no weight in a residential roll-up even if kept.
- **ZIP 77352, Livingston TX (1 row):** a real Texas ZIP (Polk County per a
  third-party ZIP site, which shows ~6,900 residential mailboxes but no coordinates).
  HUD gives it only the state, with `res_ratio` 1. Likely an address HUD could not
  geocode (for example a mail-forwarding or PO Box ZIP). **Why** is unverified.

## Does HUD document them?

**No.** HUD documents that the county field is a 5-digit GEOID (state FIPS + county
FIPS) and that some records cannot be geocoded, so some ZIPs are missing. It does not
document a state-only fallback code. HUD's own pages (`usps_crosswalk.html`,
`uspszip-api.html`) returned empty responses to an automated fetch; the statements
above come from search snippets of those pages and a HUD Cityscape article.

## Effect on this project today

None of the 9 ZIPs appear in the Zillow ZHVI ZIP file, so today they change no county
value. They would matter only if Zillow later publishes 77352.

## Recommendation for the county roll-up

Treat a state-only row as **"no county match"**. Bronze always keeps it as it came in, and staging (silver) carries it through (the existing
`warn` pattern test keeps it visible), and in the roll-up leave the ZIP out with its
own reason, e.g. `state_only_geoid`, alongside the other left-out reasons the
roll-up decision already requires. Do not guess a county (for 77352 that would be
Polk) — that would be an unverifiable value in a report calculation.

## Sources

- Loaded file `raw_data/hud_usps_zip_county_2026q2.csv` (git-ignored; not committed).
- [HUD USPS ZIP Code Crosswalk Files](https://www.huduser.gov/portal/datasets/usps_crosswalk.html)
- [HUD-USPS ZIP Code Crosswalk API](https://www.huduser.gov/portal/dataset/uspszip-api.html)
- [Cityscape vol. 20 no. 2, ch. 16 (HUD)](https://www.huduser.gov/portal/periodicals/cityscpe/vol20num2/ch16.pdf)
- [HUD-USPS ZIP Crosswalk Files, archived docs (DataLumos)](https://www.datalumos.org/datalumos/project/219325/version/V1/view)
- [ZIP Code 77352 (zip-codes.com, third-party)](https://www.zip-codes.com/zip-code/77352/zip-code-77352.asp)
