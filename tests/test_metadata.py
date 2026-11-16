from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from hearth.cli import main
from hearth.metadata import (
    METADATA_DIR,
    SourceFile,
    check_header,
    load_all,
    load_source,
    read_header,
)

FIXTURE = Path(__file__).parent / "fixtures" / "zillow_header_sample.csv"
ZILLOW = METADATA_DIR / "zillow_zhvi_zip.yml"


def _raw():
    return yaml.safe_load(ZILLOW.read_text(encoding="utf-8"))


def test_real_metadata_loads():
    assert "zillow_zhvi_zip" in load_all()


def test_unknown_key_is_rejected():
    raw = _raw()
    raw["source"]["owner"]["phone"] = "x"
    with pytest.raises(ValidationError):
        SourceFile.model_validate(raw)


def test_column_from_must_be_declared_id_column():
    raw = _raw()
    raw["source"]["columns"][0]["from"] = "Nope"
    with pytest.raises(ValidationError, match="not in id_columns"):
        SourceFile.model_validate(raw)


def test_rule_must_name_real_column():
    raw = _raw()
    raw["source"]["rules"][0]["columns"] = ["zip", "ghost"]
    with pytest.raises(ValidationError, match="unknown columns"):
        SourceFile.model_validate(raw)


def test_freshness_must_be_ordered():
    raw = _raw()
    raw["source"]["freshness"] = {"warn_after_days": 50, "error_after_days": 40}
    with pytest.raises(ValidationError, match="larger"):
        SourceFile.model_validate(raw)


def test_range_rule_needs_a_bound():
    raw = _raw()
    raw["source"]["rules"][1] = {"kind": "range", "column": "zhvi"}
    with pytest.raises(ValidationError, match="min or max"):
        SourceFile.model_validate(raw)


def test_header_matches_sample():
    source = load_source(ZILLOW)
    errors, warnings = check_header(source, read_header(FIXTURE))
    assert errors == []
    assert warnings == []


def test_missing_column_is_an_error():
    source = load_source(ZILLOW)
    header = [h for h in read_header(FIXTURE) if h != "Metro"]
    errors, _ = check_header(source, header)
    assert any("Metro" in e for e in errors)


def test_new_column_is_a_warning_not_an_error():
    source = load_source(ZILLOW)
    header = read_header(FIXTURE)
    header.insert(9, "Newcol")
    errors, warnings = check_header(source, header)
    assert errors == []
    assert any("Newcol" in w for w in warnings)


def test_period_column_in_the_middle_is_an_error():
    source = load_source(ZILLOW)
    header = read_header(FIXTURE)
    header.insert(10, "Newcol")
    errors, _ = check_header(source, header)
    assert any("at the end" in e for e in errors)


def test_no_period_columns_is_an_error():
    source = load_source(ZILLOW)
    errors, _ = check_header(source, read_header(FIXTURE)[:9])
    assert any("no columns match" in e for e in errors)


def test_cli_validate_and_check_file(capsys):
    assert main(["validate"]) == 0
    assert main(["check-file", "zillow_zhvi_zip", str(FIXTURE)]) == 0
    assert "header ok" in capsys.readouterr().out
    assert main(["check-file", "nope", str(FIXTURE)]) == 1


def test_layout_must_be_a_known_choice():
    raw = _raw()
    raw["source"]["shape"]["layout"] = "tall"
    with pytest.raises(ValidationError, match="layout"):
        SourceFile.model_validate(raw)


def test_layout_is_required():
    raw = _raw()
    del raw["source"]["shape"]["layout"]
    with pytest.raises(ValidationError, match="layout"):
        SourceFile.model_validate(raw)


def test_wide_shape_declares_its_file_and_derived_columns():
    shape = load_source(ZILLOW).shape
    assert shape.layout == "wide"
    assert shape.file_columns[0] == "RegionID"
    assert shape.derived_columns == {"month_end", "zhvi"}


# --- long layout (one row per record, no unpivot) ---------------------------------------

HUD = METADATA_DIR / "hud_usps_zip_county.yml"
HUD_FIXTURE = Path(__file__).parent / "fixtures" / "hud_zip_county_header_sample.csv"


def _hud_raw():
    return yaml.safe_load(HUD.read_text(encoding="utf-8"))


def test_hud_metadata_loads_as_long_layout():
    source = load_all()["hud_usps_zip_county"]
    assert source.shape.layout == "long"
    assert source.shape.file_columns[:2] == ["zip", "geoid"]
    assert source.shape.derived_columns == set()
    assert source.access.kind == "api"
    assert source.refresh.cadence == "quarterly"
    assert source.license.redistribution == "unverified"
    assert (source.grain.geography, source.grain.time) == ("zip", "quarter")


def test_hud_columns_are_typed_without_floats():
    cols = {c.name: c for c in load_source(HUD).columns}
    assert cols["county_fips"].from_ == "geoid"
    for name in ("res_ratio", "bus_ratio", "oth_ratio", "tot_ratio"):
        assert cols[name].type.startswith("decimal(")
    assert cols["year"].type == "int"
    assert cols["quarter"].type == "int"
    assert all(c.type not in ("double", "float") for c in cols.values())


def test_long_layout_rejects_wide_settings():
    raw = _hud_raw()
    raw["source"]["shape"]["value_columns"] = {
        "pattern": "x",
        "month_column": "m",
        "value_column": "v",
    }
    with pytest.raises(ValidationError, match="value_columns"):
        SourceFile.model_validate(raw)


def test_wide_layout_needs_its_settings():
    raw = _raw()
    del raw["source"]["shape"]["value_columns"]
    with pytest.raises(ValidationError, match="value_columns"):
        SourceFile.model_validate(raw)


def test_duplicate_file_columns_are_rejected():
    raw = _raw()
    raw["source"]["shape"]["id_columns"].append("RegionID")
    with pytest.raises(ValidationError, match="duplicates"):
        SourceFile.model_validate(raw)


def test_pattern_severity_needs_a_pattern():
    raw = _hud_raw()
    raw["source"]["columns"][2]["pattern_severity"] = "warn"  # city has no pattern
    with pytest.raises(ValidationError, match="pattern_severity"):
        SourceFile.model_validate(raw)


def test_long_from_must_be_a_declared_file_column():
    raw = _hud_raw()
    raw["source"]["columns"][0]["from"] = "Nope"
    with pytest.raises(ValidationError, match="not in file_columns"):
        SourceFile.model_validate(raw)


def test_long_column_without_from_is_rejected():
    raw = _hud_raw()
    del raw["source"]["columns"][0]["from"]
    with pytest.raises(ValidationError, match="no 'from'"):
        SourceFile.model_validate(raw)


def test_long_header_matches_sample():
    errors, warnings = check_header(load_source(HUD), read_header(HUD_FIXTURE))
    assert (errors, warnings) == ([], [])


def test_long_missing_column_is_an_error():
    header = [h for h in read_header(HUD_FIXTURE) if h != "geoid"]
    errors, _ = check_header(load_source(HUD), header)
    assert any("geoid" in e for e in errors)


def test_long_duplicate_column_is_an_error():
    header = read_header(HUD_FIXTURE) + ["zip"]
    errors, _ = check_header(load_source(HUD), header)
    assert any("duplicate" in e for e in errors)


def test_long_reordered_columns_are_an_error():
    header = read_header(HUD_FIXTURE)
    header[0], header[1] = header[1], header[0]
    errors, _ = check_header(load_source(HUD), header)
    assert any("declared order" in e for e in errors)


def test_long_extra_column_in_the_middle_is_an_error():
    header = read_header(HUD_FIXTURE)
    header.insert(2, "newcol")
    errors, _ = check_header(load_source(HUD), header)
    assert any("declared order" in e for e in errors)


def test_long_extra_column_is_a_warning():
    header = read_header(HUD_FIXTURE) + ["newcol"]
    errors, warnings = check_header(load_source(HUD), header)
    assert errors == []
    assert any("newcol" in w for w in warnings)


def test_cli_check_file_long(capsys):
    assert main(["check-file", "hud_usps_zip_county", str(HUD_FIXTURE)]) == 0
    assert "header ok" in capsys.readouterr().out
