"""Land a downloaded file in Databricks as text, exactly as received (bronze).

Steps: check the header against the metadata, skip if this exact file was loaded before,
upload the file to a Unity Catalog volume, then insert it into an append-only bronze table.
The file's ID columns land as strings; every other column (one per month for wide files) is
captured in `_rescued_data` as JSON, so new periods never change the table.
Nothing here deletes or overwrites data.
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path

from hearth.metadata import Source, check_header, read_header

BRONZE_SCHEMA = "bronze"
VOLUME = "landing"
LOG_TABLE = "_load_log"
_SAFE = re.compile(r"^[A-Za-z0-9_]+$")
_SHA = re.compile(r"^[0-9a-f]{64}$")


def _q(name: str) -> str:
    """Quote an identifier for Databricks SQL."""
    return f"`{name}`"


def _fq(catalog: str, table: str) -> str:
    if not _SAFE.fullmatch(catalog):
        raise ValueError(f"unsafe catalog name: {catalog!r}")
    return f"{_q(catalog)}.{_q(BRONZE_SCHEMA)}.{_q(table)}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def volume_path(catalog: str, source_id: str, sha: str) -> str:
    if not (_SAFE.fullmatch(catalog) and _SAFE.fullmatch(source_id) and _SHA.fullmatch(sha)):
        raise ValueError("unsafe value in volume path")
    return f"/Volumes/{catalog}/{BRONZE_SCHEMA}/{VOLUME}/{source_id}/{sha}.csv"


def setup_statements(source: Source, catalog: str) -> list[str]:
    """Create-only statements: schema, volume, bronze table and load log."""
    id_cols = ",\n    ".join(f"{_q(c)} STRING" for c in source.shape.id_columns)
    return [
        f"CREATE SCHEMA IF NOT EXISTS {_q(catalog)}.{_q(BRONZE_SCHEMA)}",
        f"CREATE VOLUME IF NOT EXISTS {_q(catalog)}.{_q(BRONZE_SCHEMA)}.{_q(VOLUME)}",
        f"""CREATE TABLE IF NOT EXISTS {_fq(catalog, source.id)} (
    {id_cols},
    `_rescued_data` STRING,
    `_source_file` STRING,
    `_file_sha256` STRING,
    `_loaded_at` TIMESTAMP
)""",
        f"""CREATE TABLE IF NOT EXISTS {_fq(catalog, LOG_TABLE)} (
    `source_id` STRING,
    `file_sha256` STRING,
    `file_name` STRING,
    `row_count` BIGINT,
    `loaded_at` TIMESTAMP
)""",
    ]


def already_loaded_sql(source: Source, catalog: str, sha: str) -> str:
    if not _SHA.fullmatch(sha):
        raise ValueError("unsafe checksum")
    return (
        f"SELECT count(*) FROM {_fq(catalog, LOG_TABLE)} "
        f"WHERE source_id = '{source.id}' AND file_sha256 = '{sha}'"
    )


def insert_sql(source: Source, catalog: str, sha: str) -> str:
    path = volume_path(catalog, source.id, sha)
    schema_ddl = ", ".join(f"{_q(c)} STRING" for c in source.shape.id_columns)
    id_cols = ", ".join(_q(c) for c in source.shape.id_columns)
    return f"""INSERT INTO {_fq(catalog, source.id)}
SELECT {id_cols}, `_rescued_data`, _metadata.file_path, '{sha}', current_timestamp()
FROM read_files(
    '{path}',
    format => 'csv',
    header => true,
    schema => '{schema_ddl}',
    rescuedDataColumn => '_rescued_data'
)"""


def count_sql(source: Source, catalog: str, sha: str) -> str:
    return f"SELECT count(*) FROM {_fq(catalog, source.id)} WHERE _file_sha256 = '{sha}'"


def log_sql(source: Source, catalog: str, sha: str, file_name: str, rows: int) -> str:
    name = file_name.replace("'", "''")
    return (
        f"INSERT INTO {_fq(catalog, LOG_TABLE)} VALUES "
        f"('{source.id}', '{sha}', '{name}', {int(rows)}, current_timestamp())"
    )


@dataclass
class Settings:
    host: str
    http_path: str
    token: str
    catalog: str

    @classmethod
    def from_env(cls) -> Settings:
        missing = [
            k
            for k in ("DATABRICKS_HOST", "DATABRICKS_HTTP_PATH", "DATABRICKS_TOKEN")
            if not os.environ.get(k)
        ]
        if missing:
            raise RuntimeError(f"missing environment variables: {missing} (put them in .env)")
        return cls(
            host=os.environ["DATABRICKS_HOST"],
            http_path=os.environ["DATABRICKS_HTTP_PATH"],
            token=os.environ["DATABRICKS_TOKEN"],
            catalog=os.environ.get("DATABRICKS_CATALOG", "workspace"),
        )


def load_file(source: Source, csv_path: Path, settings: Settings, *, dry_run: bool = False) -> str:
    """Load one file. Returns a short status message."""
    errors, warnings = check_header(source, read_header(csv_path))
    if errors:
        raise ValueError("header check failed: " + "; ".join(errors))
    sha = sha256_file(csv_path)
    if dry_run:
        target = volume_path(settings.catalog, source.id, sha)
        return f"dry run ok: header matches, sha256 {sha[:12]}..., would upload to {target}"

    from databricks import sql
    from databricks.sdk import WorkspaceClient

    with sql.connect(
        server_hostname=settings.host, http_path=settings.http_path, access_token=settings.token
    ) as conn:
        with conn.cursor() as cur:
            for statement in setup_statements(source, settings.catalog):
                cur.execute(statement)
            cur.execute(already_loaded_sql(source, settings.catalog, sha))
            if cur.fetchone()[0] > 0:
                return f"skipped: this exact file was already loaded (sha256 {sha[:12]}...)"
            client = WorkspaceClient(host=f"https://{settings.host}", token=settings.token)
            with csv_path.open("rb") as handle:
                client.files.upload(
                    volume_path(settings.catalog, source.id, sha), handle, overwrite=True
                )
            cur.execute(insert_sql(source, settings.catalog, sha))
            cur.execute(count_sql(source, settings.catalog, sha))
            rows = int(cur.fetchone()[0])
            cur.execute(log_sql(source, settings.catalog, sha, csv_path.name, rows))
    return f"loaded {rows} rows from {csv_path.name} (sha256 {sha[:12]}...)"
