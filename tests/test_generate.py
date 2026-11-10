import yaml

from hearth.generate import (
    expected_files,
    render_sources_yml,
    render_staging_sql,
    render_staging_yml,
    spark_regex,
    stale_files,
)
from hearth.metadata import METADATA_DIR, SourceFile, load_all


def _source():
    return load_all()["zillow_zhvi_zip"]


def test_spark_regex_doubles_backslashes():
    assert spark_regex(r"^\d{5}$") == r"^\\d{5}$"


def test_staging_sql_reads_bronze_and_unpivots():
    sql = render_staging_sql(_source())
    assert "{{ source('bronze', 'zillow_zhvi_zip') }}" in sql
    assert "explode(from_json(l._rescued_data" in sql
    assert "cast(nullif(trim(RegionName), '') as string) as zip" in sql
    assert "cast(nullif(trim(_period), '') as date) as month_end" in sql
    assert "cast(nullif(trim(_value), '') as decimal(14,2)) as zhvi" in sql


def test_sources_yml_carries_freshness_and_attribution():
    data = yaml.safe_load(render_sources_yml(load_all()))
    config = data["sources"][0]["tables"][0]["config"]
    assert config["loaded_at_field"] == "_loaded_at"
    assert config["freshness"]["warn_after"] == {"count": 45, "period": "day"}
    assert "Zillow" in config["meta"]["attribution"]


def test_generated_tests_follow_the_metadata_rules():
    data = yaml.safe_load(render_staging_yml(load_all()))
    model = data["models"][0]
    cols = {c["name"]: c for c in model["columns"]}
    assert "not_null" in cols["zip"]["data_tests"]
    assert "data_tests" not in cols["county_name"]  # nullable, no rules
    range_test = cols["zhvi"]["data_tests"][0]["dbt_utils.accepted_range"]
    assert range_test["arguments"] == {"min_value": 0.0}
    unique = model["data_tests"][0]["dbt_utils.unique_combination_of_columns"]
    assert unique["arguments"]["combination_of_columns"] == ["zip", "month_end"]


def test_output_is_deterministic():
    assert expected_files() == expected_files()


def test_changing_metadata_changes_output():
    raw = yaml.safe_load((METADATA_DIR / "zillow_zhvi_zip.yml").read_text(encoding="utf-8"))
    before = render_staging_yml({"x": SourceFile.model_validate(raw).source})
    raw["source"]["rules"][1]["min"] = 5
    after = render_staging_yml({"x": SourceFile.model_validate(raw).source})
    assert before != after


def test_committed_files_are_up_to_date():
    """If this fails, run: uv run python -m hearth generate"""
    assert stale_files(expected_files()) == []
