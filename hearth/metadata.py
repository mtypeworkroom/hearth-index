"""Source metadata: the single source of truth that dbt files are generated from.

Every field is validated (extra keys are rejected) so typos fail early, and the file is
cross-checked: columns must come from declared file columns, rules must name real columns.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Annotated, ClassVar, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

METADATA_DIR = Path(__file__).resolve().parent.parent / "metadata" / "sources"
_NAME = r"^[a-z][a-z0-9_]*$"
# Column types the generator knows how to cast to (Databricks/Spark SQL names).
_TYPE = r"^(string|date|int|bigint|boolean|double|decimal\(\d{1,2},\s?\d{1,2}\))$"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Owner(_Strict):
    name: str
    contact: str


class Access(_Strict):
    kind: Literal["file_download", "api"]
    url: str
    url_status: str = "unverified"
    format: Literal["csv", "json"]


class License(_Strict):
    terms_url: str
    attribution: str
    redistribution: Literal["allowed", "not_allowed", "unverified"]


class Refresh(_Strict):
    cadence: Literal["daily", "weekly", "monthly", "quarterly", "annual"]


class Freshness(_Strict):
    warn_after_days: int = Field(gt=0)
    error_after_days: int = Field(gt=0)

    @model_validator(mode="after")
    def _ordered(self) -> Freshness:
        if self.error_after_days <= self.warn_after_days:
            raise ValueError("error_after_days must be larger than warn_after_days")
        return self


Geography = Literal["zip", "county", "cbsa", "state", "tract"]


class Grain(_Strict):
    """What one row is. A crosswalk lists several geographies: one row per pair and period.

    `geography: zip` is shorthand for `geography: [zip]`.
    """

    geography: list[Geography] = Field(min_length=1)
    time: Literal["month", "quarter", "year"]

    @field_validator("geography", mode="before")
    @classmethod
    def _one_or_many(cls, value: object) -> object:
        return [value] if isinstance(value, str) else value

    @model_validator(mode="after")
    def _no_repeats(self) -> Grain:
        if len(set(self.geography)) != len(self.geography):
            raise ValueError("grain geography must not repeat")
        return self

    def describe(self) -> str:
        """Plain-English row grain, e.g. 'zip, county and quarter'."""
        parts = [*self.geography, self.time]
        return f"{', '.join(parts[:-1])} and {parts[-1]}"


class ValueColumns(_Strict):
    """Wide files: every column whose header matches `pattern` is one period's value."""

    pattern: str
    month_column: str = Field(pattern=_NAME)
    value_column: str = Field(pattern=_NAME)

    @model_validator(mode="after")
    def _regex_compiles(self) -> ValueColumns:
        re.compile(self.pattern)
        return self


def _check_file_column_names(columns: list[str], key: str) -> None:
    """File headers become quoted SQL identifiers: no quotes, blanks or duplicates."""
    bad = [c for c in columns if "`" in c or "'" in c or not c.strip()]
    if bad:
        raise ValueError(f"{key} contain unsafe or blank names: {bad}")
    if len(set(columns)) != len(columns):
        raise ValueError(f"{key} contain duplicates")


class WideShape(_Strict):
    """Wide files: ID columns, then one column per period (e.g. Zillow ZHVI).

    The ID columns land in bronze as strings; the period columns are captured as JSON in
    `_rescued_data` and unpivoted in staging into `month_column` and `value_column`.
    """

    layout: Literal["wide"]
    id_columns: list[str] = Field(min_length=1)
    value_columns: ValueColumns

    # Which metadata key lists the file columns (used in validation messages).
    FILE_COLUMNS_KEY: ClassVar[str] = "id_columns"

    @model_validator(mode="after")
    def _safe_header_names(self) -> WideShape:
        _check_file_column_names(self.id_columns, self.FILE_COLUMNS_KEY)
        return self

    @property
    def file_columns(self) -> list[str]:
        """Declared file headers. They land in bronze as STRING columns, in this order."""
        return self.id_columns

    @property
    def derived_columns(self) -> set[str]:
        """Columns created in staging (by unpivoting), so they have no 'from'."""
        return {self.value_columns.month_column, self.value_columns.value_column}

    def check_header(self, header: list[str]) -> tuple[list[str], list[str]]:
        """Layout-specific header check. Returns (errors, warnings)."""
        errors: list[str] = []
        warnings: list[str] = []
        pattern = re.compile(self.value_columns.pattern)
        value_cols = [h for h in header if pattern.fullmatch(h)]
        id_cols = [h for h in header if not pattern.fullmatch(h)]
        missing = [c for c in self.id_columns if c not in header]
        if missing:
            errors.append(f"missing expected columns: {missing}")
        extra = [c for c in id_cols if c not in self.id_columns]
        if extra:
            warnings.append(f"new columns not in metadata (ignored until added): {extra}")
        if not value_cols:
            errors.append("no columns match the period pattern")
        elif header[len(id_cols) :] != value_cols:
            errors.append("period columns are not all at the end of the header")
        return errors, warnings


class LongShape(_Strict):
    """Long files: one row per record, every column declared (e.g. HUD-USPS crosswalks).

    All declared columns land in bronze as strings; staging casts them directly, no unpivot.
    """

    layout: Literal["long"]
    file_columns: list[str] = Field(min_length=1)

    FILE_COLUMNS_KEY: ClassVar[str] = "file_columns"

    @model_validator(mode="after")
    def _safe_header_names(self) -> LongShape:
        _check_file_column_names(self.file_columns, self.FILE_COLUMNS_KEY)
        return self

    @property
    def derived_columns(self) -> set[str]:
        """Long files create no columns in staging; every column has a 'from'."""
        return set()

    def check_header(self, header: list[str]) -> tuple[list[str], list[str]]:
        """Declared columns must come first, in order; extra columns at the end only warn.

        Order matters because the loader passes an explicit schema to read_files, which may
        map CSV columns by position; a moved column would silently land under the wrong name.
        """
        errors: list[str] = []
        warnings: list[str] = []
        missing = [c for c in self.file_columns if c not in header]
        if missing:
            errors.append(f"missing expected columns: {missing}")
        elif header[: len(self.file_columns)] != self.file_columns:
            errors.append(f"columns are not in the declared order: {self.file_columns}")
        extra = [c for c in header if c not in self.file_columns]
        if extra:
            warnings.append(f"new columns not in metadata (ignored until added): {extra}")
        return errors, warnings


# The layout is an explicit choice: pydantic picks the shape class from `layout`.
# New layouts join this union.
Shape = Annotated[WideShape | LongShape, Field(discriminator="layout")]


class Column(_Strict):
    name: str = Field(pattern=_NAME)
    # Header in the source file. Absent for the columns created by unpivoting.
    from_: str | None = Field(default=None, alias="from")
    type: str = Field(pattern=_TYPE)
    nullable: bool = True
    pattern: str | None = None
    # Severity of the generated pattern test. `warn` for known, documented exceptions.
    pattern_severity: Literal["warn", "error"] = "error"
    units: str | None = None
    description: str | None = None

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    @model_validator(mode="after")
    def _severity_needs_pattern(self) -> Column:
        if "pattern_severity" in self.model_fields_set and self.pattern is None:
            raise ValueError(f"column {self.name}: pattern_severity is set but pattern is not")
        return self


class UniqueRule(_Strict):
    kind: Literal["unique"]
    columns: list[str] = Field(min_length=1)
    severity: Literal["warn", "error"] = "error"


class RangeRule(_Strict):
    kind: Literal["range"]
    column: str
    min: float | None = None
    max: float | None = None
    severity: Literal["warn", "error"] = "error"

    @model_validator(mode="after")
    def _has_bound(self) -> RangeRule:
        if self.min is None and self.max is None:
            raise ValueError("range rule needs min or max")
        return self


Rule = Annotated[UniqueRule | RangeRule, Field(discriminator="kind")]


class Source(_Strict):
    id: str = Field(pattern=_NAME)
    title: str
    owner: Owner
    access: Access
    license: License
    refresh: Refresh
    freshness: Freshness
    grain: Grain
    shape: Shape
    columns: list[Column] = Field(min_length=1)
    rules: list[Rule] = Field(default_factory=list)

    @model_validator(mode="after")
    def _cross_checks(self) -> Source:
        names = [c.name for c in self.columns]
        if len(set(names)) != len(names):
            raise ValueError("duplicate column names")
        shape = self.shape
        made = shape.derived_columns
        for col in self.columns:
            if col.from_ is None:
                if col.name not in made:
                    raise ValueError(
                        f"column {col.name} has no 'from' and is not a derived "
                        f"({shape.layout} layout) column"
                    )
            elif col.from_ not in shape.file_columns:
                raise ValueError(
                    f"column {col.name}: 'from' {col.from_} is not in {shape.FILE_COLUMNS_KEY}"
                )
        missing = made - set(names)
        if missing:
            raise ValueError(f"derived columns must be declared in columns: {sorted(missing)}")
        for rule in self.rules:
            used = rule.columns if isinstance(rule, UniqueRule) else [rule.column]
            unknown = [c for c in used if c not in names]
            if unknown:
                raise ValueError(f"rule {rule.kind} uses unknown columns: {unknown}")
        for col in self.columns:
            if col.pattern:
                re.compile(col.pattern)
        return self


class SourceFile(_Strict):
    schema_version: Literal[1]
    source: Source


def load_source(path: Path) -> Source:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return SourceFile.model_validate(data).source


def load_all(directory: Path = METADATA_DIR) -> dict[str, Source]:
    sources: dict[str, Source] = {}
    for path in sorted(directory.glob("*.yml")):
        source = load_source(path)
        if source.id != path.stem:
            raise ValueError(f"{path.name}: source id '{source.id}' must match the file name")
        if source.id in sources:
            raise ValueError(f"duplicate source id {source.id}")
        sources[source.id] = source
    return sources


def check_header(source: Source, header: list[str]) -> tuple[list[str], list[str]]:
    """Compare a real file's header with the metadata. Returns (errors, warnings).

    The layout decides what a valid header looks like; duplicates are always an error.
    """
    errors, warnings = source.shape.check_header(header)
    if len(set(header)) != len(header):
        errors.append("duplicate column names in header")
    return errors, warnings


def read_header(path: Path) -> list[str]:
    """Read only the first line of a CSV; no data rows are loaded."""
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return next(csv.reader(handle))
