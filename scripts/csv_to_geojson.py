#!/usr/bin/env python3
# MIT License
# Copyright (c) 2026 MaStR Visualizer contributors

"""Convert a DuckDB unit CSV to a streamed GeoJSON FeatureCollection."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path


DEFAULT_PROPERTIES = ("mastr_id", "tech_type", "capacity_mw", "status", "municipality_name", "state")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Input CSV path")
    parser.add_argument("--lon-field", default="lon", help="CSV longitude column")
    parser.add_argument("--lat-field", default="lat", help="CSV latitude column")
    parser.add_argument("--properties", help="Comma-separated CSV fields to retain as properties")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    properties = tuple(args.properties.split(",")) if args.properties else DEFAULT_PROPERTIES
    with args.input.open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        output = sys.stdout
        output.write('{"type":"FeatureCollection","features":[\n')
        first = True
        for row in reader:
            try:
                longitude = float(row[args.lon_field])
                latitude = float(row[args.lat_field])
            except (KeyError, TypeError, ValueError):
                continue
            if not math.isfinite(longitude) or not math.isfinite(latitude):
                continue
            feature = {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [longitude, latitude]},
                "properties": {name: _value(row.get(name)) for name in properties if name in row},
            }
            if not first:
                output.write(",\n")
            json.dump(feature, output, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
            first = False
        output.write("\n]}\n")
    return 0


def _value(value: str | None) -> str | float | int | None:
    if not value:
        return None
    try:
        number = float(value)
    except ValueError:
        return value
    if not math.isfinite(number):
        return None
    return int(number) if number.is_integer() else number


if __name__ == "__main__":
    raise SystemExit(main())
