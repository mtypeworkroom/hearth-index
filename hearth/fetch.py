"""Download a HUD-USPS ZIP crosswalk from the HUD USER API and save it as a CSV.

One call with `query=All` returns every ZIP for the latest quarter. The CSV keeps every
value exactly as HUD sent it (numbers are kept as text, never turned into floats) and the
rows are sorted, so the same API data always produces a byte-identical file. That makes
the loader's sha256 check skip a re-load of an unchanged quarter.

Type codes were confirmed against real responses for ZIP 78701 on 2026-11-14:
1 = zip-tract, 2 = zip-county, 3 = zip-cbsa.
"""

from __future__ import annotations

import csv
import json
import os
import urllib.request
from collections.abc import Callable
from pathlib import Path

API_URL = "https://www.huduser.gov/hudapi/public/usps?type={type}&query=All"
CROSSWALKS = {"zip-county": 2, "zip-cbsa": 3}
FIELDS = [
    "zip",
    "geoid",
    "city",
    "state",
    "res_ratio",
    "bus_ratio",
    "oth_ratio",
    "tot_ratio",
    "year",
    "quarter",
]

# Takes (url, headers) and returns the raw response body. Tests pass a fake one.
Opener = Callable[[str, dict[str, str]], bytes]


def _http_get(url: str, headers: dict[str, str]) -> bytes:
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=300) as response:
        return response.read()


def hud_token() -> str:
    token = os.environ.get("HUD_TOKEN", "").strip().strip("\"'")
    if not token:
        raise RuntimeError("HUD_TOKEN is not set (put it in .env)")
    return token


def parse_response(body: bytes, crosswalk: str) -> tuple[dict[str, str], list[dict[str, str]]]:
    """Return (metadata, rows). Numbers stay as the exact text HUD sent."""
    payload = json.loads(body, parse_float=str, parse_int=str)
    if "error" in payload:
        raise RuntimeError(f"HUD API error: {payload['error']}")
    data = payload.get("data", payload)
    if isinstance(data, list):
        data = data[0] if data else {}
    if data.get("crosswalk_type") != crosswalk:
        raise RuntimeError(f"asked for {crosswalk} but HUD returned {data.get('crosswalk_type')!r}")
    meta = {"year": str(data.get("year", "")), "quarter": str(data.get("quarter", ""))}
    if not (meta["year"].isdigit() and meta["quarter"] in {"1", "2", "3", "4"}):
        raise RuntimeError(f"unexpected year/quarter in response: {meta}")
    results = data.get("results") or []
    if not results:
        raise RuntimeError("HUD returned no rows")
    rows = []
    for item in results:
        row = {f: "" if item.get(f) is None else str(item.get(f)) for f in FIELDS[:-2]}
        rows.append({**row, **meta})
    rows.sort(key=lambda r: (r["zip"], r["geoid"]))
    return meta, rows


def output_path(out_dir: Path, crosswalk: str, meta: dict[str, str]) -> Path:
    name = f"hud_usps_{crosswalk.replace('-', '_')}_{meta['year']}q{meta['quarter']}.csv"
    return out_dir / name


def write_csv(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def fetch_crosswalk(
    crosswalk: str, out_dir: Path, *, token: str, opener: Opener = _http_get
) -> tuple[Path, int]:
    """Download one crosswalk and write it as CSV. Returns (path, row count)."""
    if crosswalk not in CROSSWALKS:
        raise ValueError(f"unknown crosswalk {crosswalk!r}. Known: {', '.join(CROSSWALKS)}")
    url = API_URL.format(type=CROSSWALKS[crosswalk])
    headers = {"Authorization": f"Bearer {token}", "User-Agent": "hearth-index"}
    meta, rows = parse_response(opener(url, headers), crosswalk)
    path = output_path(out_dir, crosswalk, meta)
    write_csv(rows, path)
    return path, len(rows)
