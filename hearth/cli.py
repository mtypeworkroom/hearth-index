"""Command line: python -m hearth validate | check-file <source_id> <csv>."""

from __future__ import annotations

import argparse
from pathlib import Path

from pydantic import ValidationError

from hearth.metadata import check_header, load_all, read_header


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hearth")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate", help="validate every metadata file")
    check = sub.add_parser("check-file", help="compare a downloaded CSV's header with its metadata")
    check.add_argument("source_id")
    check.add_argument("csv_path", type=Path)
    args = parser.parse_args(argv)

    try:
        sources = load_all()
    except (ValidationError, ValueError) as exc:
        print(f"metadata invalid:\n{exc}")
        return 1
    if args.command == "validate":
        print(f"ok: {len(sources)} source(s): {', '.join(sources) or '-'}")
        return 0
    if args.source_id not in sources:
        print(f"unknown source '{args.source_id}'. Known: {', '.join(sources)}")
        return 1
    header = read_header(args.csv_path)
    errors, warnings = check_header(sources[args.source_id], header)
    for message in warnings:
        print(f"warning: {message}")
    for message in errors:
        print(f"error: {message}")
    if errors:
        return 1
    print(f"header ok: {len(header)} columns")
    return 0
