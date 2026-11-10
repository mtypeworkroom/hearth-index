"""Source metadata: the single source of truth that dbt files are generated from.

Every field is validated (extra keys are rejected) so typos fail early, and the file is
cross-checked: columns must come from declared ID columns, rules must name real columns.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

METADATA_DIR = Path(__file__).resolve().parent.parent / "metadata" / "sources"
_NAME = r"^[a-z][a-z0-9_]*$"


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


class Grain(_Strict):
    geography: Literal["zip", "county", "cbsa", "state", "tract"]
    time: Literal["month", "quarter", "year"]


class ValueColumns(_Strict):
    """Wide files: every column whose header matches `pattern` is one period's value."""

    pattern: str
    month_column: str = Field(pattern=_NAME)
    value_column: str = Field(pattern=_NAME)

    @model_validator(mode="after")
    def _regex_compiles(self) -> ValueColumns:
        re.compile(self.pattern)
        return self


class Shape(_Strict):
    layout: Literal["wide"]
    id_columns: list[str] = Field(min_length=1)
    value_columns: ValueColumns


class Column(_Strict):
    name: str = Field(pattern=_NAME)
    # Header in the source file. Absent for the columns created by unpivoting.
    from_: str | None = Field(default=None, alias="from")
    type: str
    nullable: bool = True
    pattern: str | None = None
    units: str | None = None
    description: str | None = None

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


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
        made = {self.shape.value_columns.month_column, self.shape.value_columns.value_column}
        for col in self.columns:
            if col.from_ is None:
                if col.name not in made:
                    raise ValueError(
                        f"column {col.name} has no 'from' and is not an unpivot column"
                    )
            elif col.from_ not in self.shape.id_columns:
                raise ValueError(f"column {col.name}: 'from' {col.from_} is not in id_columns")
        missing = made - set(names)
        if missing:
            raise ValueError(f"unpivot columns must be declared in columns: {sorted(missing)}")
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
    """Compare a real file's header with the metadata. Returns (errors, warnings)."""
    errors: list[str] = []
    warnings: list[str] = []
    shape = source.shape
    pattern = re.compile(shape.value_columns.pattern)
    value_cols = [h for h in header if pattern.fullmatch(h)]
    id_cols = [h for h in header if not pattern.fullmatch(h)]
    missing = [c for c in shape.id_columns if c not in header]
    if missing:
        errors.append(f"missing expected columns: {missing}")
    extra = [c for c in id_cols if c not in shape.id_columns]
    if extra:
        warnings.append(f"new columns not in metadata (ignored until added): {extra}")
    if not value_cols:
        errors.append("no columns match the period pattern")
    elif header[len(id_cols) :] != value_cols:
        errors.append("period columns are not all at the end of the header")
    if len(set(header)) != len(header):
        errors.append("duplicate column names in header")
    return errors, warnings


def read_header(path: Path) -> list[str]:
    """Read only the first line of a CSV; no data rows are loaded."""
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return next(csv.reader(handle))
