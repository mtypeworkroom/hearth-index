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
    tables = {t["name"]: t for t in data["sources"][0]["tables"]}
    config = tables["zillow_zhvi_zip"]["config"]
    assert config["loaded_at_field"] == "_loaded_at"
    assert config["freshness"]["warn_after"] == {"count": 45, "period": "day"}
    assert "Zillow" in config["meta"]["attribution"]


def test_generated_tests_follow_the_metadata_rules():
    data = yaml.safe_load(render_staging_yml(load_all()))
    model = next(m for m in data["models"] if m["name"] == "stg_zillow_zhvi_zip")
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


# --- long layout ---------------------------------------------------------------------------


def _hud():
    return load_all()["hud_usps_zip_county"]


def test_long_staging_casts_directly_from_latest_load():
    sql = render_staging_sql(_hud())
    assert "{{ source('bronze', 'hud_usps_zip_county') }}" in sql
    assert "explode" not in sql and "_rescued_data" not in sql
    assert "where _loaded_at = (select max(_loaded_at) from src)" in sql
    assert "cast(nullif(trim(geoid), '') as string) as county_fips" in sql
    assert "cast(nullif(trim(res_ratio), '') as decimal(38,30)) as res_ratio" in sql
    assert "cast(nullif(trim(year), '') as int) as year" in sql
    assert "from latest_load\n)" in sql
    ctes = [line.split(" as (")[0] for line in sql.splitlines() if line.endswith(" as (")]
    assert ctes == ["with src", "latest_load", "renamed"]


def test_long_generated_tests():
    data = yaml.safe_load(render_staging_yml(load_all()))
    model = next(m for m in data["models"] if m["name"] == "stg_hud_usps_zip_county")
    cols = {c["name"]: c for c in model["columns"]}
    for key in ("zip", "county_fips", "year", "quarter"):
        assert "not_null" in cols[key]["data_tests"]
    for key in ("zip", "county_fips"):
        assert any(
            isinstance(t, dict)
            and t.get("dbt_utils.expression_is_true", {}).get("arguments")
            == {"expression": r"rlike '^\\d{5}$'"}  # backslash doubled for Spark SQL
            for t in cols[key]["data_tests"]
        )
    for ratio in ("res_ratio", "bus_ratio", "oth_ratio", "tot_ratio"):
        rng = next(t for t in cols[ratio]["data_tests"] if "dbt_utils.accepted_range" in t)
        assert rng["dbt_utils.accepted_range"]["arguments"] == {"min_value": 0, "max_value": 1}
    unique = model["data_tests"][0]["dbt_utils.unique_combination_of_columns"]
    assert unique["arguments"]["combination_of_columns"] == ["zip", "county_fips"]


def test_pattern_severity_is_carried_into_the_test():
    data = yaml.safe_load(render_staging_yml(load_all()))
    model = next(m for m in data["models"] if m["name"] == "stg_hud_usps_zip_county")
    cols = {c["name"]: c for c in model["columns"]}
    fips = next(t for t in cols["county_fips"]["data_tests"] if isinstance(t, dict))
    assert fips["dbt_utils.expression_is_true"]["config"] == {"severity": "warn"}
    zip_test = next(t for t in cols["zip"]["data_tests"] if isinstance(t, dict))
    assert "config" not in zip_test["dbt_utils.expression_is_true"]


def test_descriptions_state_the_full_grain():
    sql = render_staging_sql(_hud())
    assert "one row per zip, county and quarter." in sql
    data = yaml.safe_load(render_staging_yml(load_all()))
    model = next(m for m in data["models"] if m["name"] == "stg_hud_usps_zip_county")
    assert "one row per zip, county and quarter" in model["description"]
