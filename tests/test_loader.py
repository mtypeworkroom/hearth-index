import hashlib

import pytest

from hearth.loader import (
    Settings,
    already_loaded_sql,
    insert_sql,
    load_file,
    log_sql,
    setup_statements,
    sha256_file,
    volume_path,
)
from hearth.metadata import load_all
from tests.test_metadata import FIXTURE

SHA = "a" * 64


def _source():
    return load_all()["zillow_zhvi_zip"]


def test_sha256_matches_hashlib():
    assert sha256_file(FIXTURE) == hashlib.sha256(FIXTURE.read_bytes()).hexdigest()


def test_setup_is_create_only():
    statements = setup_statements(_source(), "workspace")
    assert all(s.startswith("CREATE ") and "IF NOT EXISTS" in s for s in statements)
    joined = "\n".join(statements).upper()
    for word in ("DROP ", "DELETE ", "TRUNCATE ", "REPLACE "):
        assert word not in joined


def test_bronze_table_has_id_columns_and_audit_columns():
    table_sql = setup_statements(_source(), "workspace")[2]
    assert "`RegionName` STRING" in table_sql
    for col in ("_rescued_data", "_source_file", "_file_sha256", "_loaded_at"):
        assert col in table_sql


def test_insert_reads_volume_and_rescues_period_columns():
    sql = insert_sql(_source(), "workspace", SHA)
    assert f"/Volumes/workspace/bronze/landing/zillow_zhvi_zip/{SHA}.csv" in sql
    assert "rescuedDataColumn => '_rescued_data'" in sql
    assert "schema => '`RegionID` STRING" in sql
    assert sql.startswith("INSERT INTO `workspace`.`bronze`.`zillow_zhvi_zip`")


def test_unsafe_values_are_rejected():
    with pytest.raises(ValueError):
        volume_path("work space", "zillow_zhvi_zip", SHA)
    with pytest.raises(ValueError):
        already_loaded_sql(_source(), "workspace", "x' OR '1'='1")
    with pytest.raises(ValueError):
        setup_statements(_source(), "a`b")


def test_log_escapes_quotes():
    assert "it''s" in log_sql(_source(), "workspace", SHA, "it's.csv", 5)


def test_dry_run_checks_header_without_connecting():
    settings = Settings(host="h", http_path="p", token="t", catalog="workspace")
    message = load_file(_source(), FIXTURE, settings, dry_run=True)
    assert message.startswith("dry run ok")


def test_bad_header_stops_the_load(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("RegionID,Nope\n1,2\n", encoding="utf-8")
    settings = Settings(host="h", http_path="p", token="t", catalog="workspace")
    with pytest.raises(ValueError, match="header check failed"):
        load_file(_source(), bad, settings, dry_run=True)
