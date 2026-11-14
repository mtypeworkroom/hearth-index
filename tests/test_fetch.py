import json

import pytest

from hearth.fetch import FIELDS, fetch_crosswalk, parse_response

TOKEN = "fake-token"


def _body(crosswalk="zip-county", results=None, **extra):
    if results is None:
        results = [
            {"zip": "78701", "geoid": "48453", "city": "AUSTIN", "state": "TX",
             "res_ratio": 1, "bus_ratio": 1, "oth_ratio": 1, "tot_ratio": 1},
            {"zip": "00601", "geoid": "72001", "city": "ADJUNTAS", "state": "PR",
             "res_ratio": 0.9974515800203874, "bus_ratio": 0, "oth_ratio": 0,
             "tot_ratio": 0.9970528928183652},
        ]  # fmt: skip
    data = {"year": "2026", "quarter": "2", "input": "All", "crosswalk_type": crosswalk}
    return json.dumps({"data": {**data, "results": results}, **extra}).encode()


def test_numbers_keep_exact_text_and_rows_are_sorted():
    meta, rows = parse_response(_body(), "zip-county")
    assert meta == {"year": "2026", "quarter": "2"}
    assert [r["zip"] for r in rows] == ["00601", "78701"]
    assert rows[0]["res_ratio"] == "0.9974515800203874"
    assert rows[1]["tot_ratio"] == "1"
    assert list(rows[0]) == FIELDS


def test_wrong_crosswalk_type_is_rejected():
    with pytest.raises(RuntimeError, match="asked for zip-cbsa"):
        parse_response(_body(crosswalk="zip-county"), "zip-cbsa")


def test_api_error_is_reported():
    with pytest.raises(RuntimeError, match="Unauthenticated"):
        parse_response(json.dumps({"error": "Unauthenticated"}).encode(), "zip-county")


def test_empty_results_rejected():
    with pytest.raises(RuntimeError, match="no rows"):
        parse_response(_body(results=[]), "zip-county")


def test_fetch_writes_deterministic_csv(tmp_path):
    calls = []

    def opener(url, headers):
        calls.append((url, headers))
        return _body()

    path, rows = fetch_crosswalk("zip-county", tmp_path, token=TOKEN, opener=opener)
    first = path.read_bytes()
    fetch_crosswalk("zip-county", tmp_path, token=TOKEN, opener=opener)
    assert path.read_bytes() == first
    assert path.name == "hud_usps_zip_county_2026q2.csv"
    assert rows == 2
    assert first.decode().splitlines()[0] == ",".join(FIELDS)
    url, headers = calls[0]
    assert "type=2" in url and "query=All" in url
    assert headers["Authorization"] == f"Bearer {TOKEN}"


def test_unknown_crosswalk_rejected(tmp_path):
    with pytest.raises(ValueError, match="unknown crosswalk"):
        fetch_crosswalk("zip-tract", tmp_path, token=TOKEN, opener=lambda u, h: b"")
