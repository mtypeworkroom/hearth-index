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
